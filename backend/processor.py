"""Background video pipeline: capture -> YOLO26 + ByteTrack -> line counting -> annotated JPEG."""
from __future__ import annotations

import logging
import sys
import threading
import time
from collections import Counter, deque
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from config import MODELS, STREAM_MAX_WIDTH, JPEG_QUALITY
from counter import LineCounter


def open_camera(index: int) -> cv2.VideoCapture:
    """DirectShow on Windows (fast open); V4L2/default backend elsewhere (e.g. in Docker)."""
    return cv2.VideoCapture(index, cv2.CAP_DSHOW) if sys.platform == "win32" else cv2.VideoCapture(index)

log = logging.getLogger("processor")

# One distinct BGR colour per class
_PALETTE = [(56, 56, 255), (151, 157, 255), (31, 112, 255), (29, 178, 255), (49, 210, 207), (10, 249, 72),
            (23, 204, 146), (134, 219, 61), (52, 147, 26), (187, 212, 0), (168, 153, 44), (255, 194, 0),
            (147, 69, 52), (255, 115, 100), (236, 24, 0), (255, 56, 132), (133, 0, 82)]


@dataclass
class SessionConfig:
    source_type: str          # "camera" | "url" | "file"
    source: str               # camera index, stream URL, or uploaded file path
    model: str                # key in config.MODELS
    conf: float = 0.35
    loop: bool = False        # replay files when they end


class LatestFrameReader:
    """Reads a live source on its own thread and keeps only the newest frame, so processing never lags behind."""

    def __init__(self, cap: cv2.VideoCapture):
        self.cap, self.frame, self.ok = cap, None, True
        self._lock = threading.Lock()
        self._new = threading.Event()
        self._stop = False
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        while not self._stop:
            ok, frame = self.cap.read()
            if not ok:
                self.ok = False
                self._new.set()
                return
            with self._lock:
                self.frame = frame
            self._new.set()

    def read(self, timeout=5.0):
        if not self._new.wait(timeout):
            return False, None
        self._new.clear()
        if not self.ok:
            return False, None
        with self._lock:
            return self.frame is not None, self.frame

    def stop(self):
        self._stop = True


class ClassVoter:
    """Stabilises each track's class.

    The detector classifies every frame independently, so a vehicle can flip between similar
    classes (Pickup / Car, MPV / Car ...). Each track keeps a confidence-weighted vote over its
    detections; older frames slowly fade (`decay` per frame), so a confident later view can
    still overturn a wrong early guess. Hysteresis: the shown class only changes when another
    class has `margin` times its vote, so near-ties do not flip-flop.
    On the demo video this cut label switches by 80% (137 -> 28).
    """

    def __init__(self, n_classes: int, decay: float = 0.99, margin: float = 2.0, ttl_frames: int = 150):
        self.n, self.decay, self.margin, self.ttl = n_classes, decay, margin, ttl_frames
        self._votes: dict[int, np.ndarray] = {}
        self._seen: dict[int, int] = {}
        self._cls: dict[int, int] = {}

    def update(self, track_id: int, cls: int, conf: float, frame_idx: int) -> int:
        v = self._votes.get(track_id)
        if v is None:
            v = self._votes[track_id] = np.zeros(self.n, dtype=np.float32)
        else:
            v *= self.decay ** (frame_idx - self._seen[track_id])
        v[cls] += conf
        self._seen[track_id] = frame_idx
        best, cur = int(v.argmax()), self._cls.get(track_id)
        if cur is None or (best != cur and v[best] > v[cur] * self.margin):
            self._cls[track_id] = cur = best
        return cur

    def prune(self, frame_idx: int) -> None:
        """Forget tracks not seen for `ttl_frames` (ByteTrack may revive a lost id within its buffer)."""
        for tid in [t for t, f in self._seen.items() if frame_idx - f > self.ttl]:
            del self._votes[tid], self._seen[tid], self._cls[tid]


class VideoProcessor:
    def __init__(self):
        self.counter = LineCounter()
        self.lock = threading.Lock()                 # guards counter + stats
        self.frame_cond = threading.Condition()
        self.jpeg: bytes | None = None
        self.frame_id = 0
        self.status = "idle"                         # idle | starting | running | finished | error
        self.error: str | None = None
        self.config: SessionConfig | None = None
        self.names: list[str] = []
        self.fps = 0.0
        self.frames = 0
        self.in_frame: Counter = Counter()
        self.frame_size: tuple[int, int] | None = None
        self.all_events: deque = deque(maxlen=100_000)   # for CSV export
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self.voter = ClassVoter(1)

    # ---------------------------------------------------------------- control
    def start(self, cfg: SessionConfig):
        self.stop()
        if cfg.model not in MODELS:
            raise ValueError(f"unknown model {cfg.model!r}")
        self._stop.clear()
        self.config, self.status, self.error = cfg, "starting", None
        self.fps, self.frames, self.frame_size = 0.0, 0, None
        self.in_frame = Counter()
        with self.lock:
            self.counter.reset()
            self.all_events.clear()
        self._thread = threading.Thread(target=self._run, args=(cfg,), daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10)
        self._thread = None
        if self.status in ("running", "starting"):
            self.status = "idle"

    def set_line(self, a, b):
        with self.lock:
            self.counter.set_line(tuple(a), tuple(b))

    def reset_counts(self):
        with self.lock:
            self.counter.reset()
            self.all_events.clear()

    # ---------------------------------------------------------------- state
    def state(self) -> dict:
        with self.lock:
            snap = self.counter.snapshot(self.names or [])
            recent = [e.as_dict() for e in list(self.counter.events)[-25:]][::-1]
        return {
            "status": self.status, "error": self.error,
            "source": None if not self.config else {"type": self.config.source_type, "source": self.config.source,
                                                    "model": self.config.model, "conf": self.config.conf},
            "fps": round(self.fps, 1), "frames": self.frames,
            "frame_size": self.frame_size,
            "in_frame": dict(self.in_frame),
            "counts": snap, "recent_events": recent,
        }

    def events_csv(self) -> str:
        with self.lock:
            rows = list(self.all_events)
        lines = ["timestamp_iso,timestamp,track_id,class,direction"]
        for e in rows:
            iso = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(e.timestamp)) + f".{int(e.timestamp % 1 * 1000):03d}"
            lines.append(f"{iso},{e.timestamp:.3f},{e.track_id},{e.cls},{e.direction}")
        return "\n".join(lines) + "\n"

    # ---------------------------------------------------------------- pipeline
    def _load_model(self, key: str):
        from ultralytics import YOLO
        spec = MODELS[key]
        # a fresh YOLO object per session gives a fresh tracker state
        model = YOLO(str(spec["path"]), task="detect")
        return model, spec["imgsz"]

    def _open(self, cfg: SessionConfig) -> cv2.VideoCapture:
        if cfg.source_type == "camera":
            idx = int(cfg.source)
            cap = open_camera(idx)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280); cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        elif cfg.source_type == "file":
            if not Path(cfg.source).exists():
                raise FileNotFoundError(cfg.source)
            cap = cv2.VideoCapture(cfg.source)
        else:
            cap = cv2.VideoCapture(cfg.source, cv2.CAP_FFMPEG)
        if not cap.isOpened():
            raise RuntimeError(f"could not open video source: {cfg.source}")
        return cap

    def _run(self, cfg: SessionConfig):
        cap, reader = None, None
        try:
            model, imgsz = self._load_model(cfg.model)
            self.names = [model.names[i] for i in range(len(model.names))]
            self.voter = ClassVoter(len(self.names))
            cap = self._open(cfg)
            is_file = cfg.source_type == "file"
            src_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
            if not 1 <= src_fps <= 120:
                src_fps = 25.0
            reader = None if is_file else LatestFrameReader(cap)
            self.status = "running"
            t_prev, next_due = time.perf_counter(), time.perf_counter()

            while not self._stop.is_set():
                if is_file:
                    ok, frame = cap.read()
                    if not ok:
                        if cfg.loop:
                            # Rewind. Track ids keep increasing (tracker not reset), so each pass counts again;
                            # positions are cleared so the jump from last to first frame is not seen as a crossing.
                            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                            with self.lock:
                                self.counter.clear_positions()
                            continue
                        self.status = "finished"
                        break
                else:
                    ok, frame = reader.read()
                    if not ok or frame is None:
                        raise RuntimeError("video stream ended or camera disconnected")

