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

