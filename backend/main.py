"""FastAPI backend: live vehicle-type detection + line-crossing counting.

Run:  uvicorn main:app --host 0.0.0.0 --port 8001      (from app/backend)
Docs: http://localhost:8001/docs
(Port 8000 is taken by Docker Desktop on this machine.)
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

import cv2
from fastapi import FastAPI, File, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel, Field, field_validator

from config import CORS_ORIGINS, DEFAULT_MODEL, MAX_UPLOAD_MB, MODELS, UPLOAD_DIR, VIDEO_EXTS
from processor import SessionConfig, VideoProcessor, open_camera

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
processor = VideoProcessor()


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    processor.stop()


app = FastAPI(title="Vehicle Counter API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])


# ------------------------------------------------------------------ schemas
class StartRequest(BaseModel):
    source_type: Literal["camera", "url", "file"]
    source: str = Field(..., description="camera index (e.g. '0'), stream URL (rtsp/http), or file_id from /api/upload")
    model: str = DEFAULT_MODEL
    conf: float = Field(0.35, ge=0.05, le=0.95)
    loop: bool = False

    @field_validator("model")
    @classmethod
    def known_model(cls, v):
        if v not in MODELS:
            raise ValueError(f"model must be one of {list(MODELS)}")
        return v


class LineRequest(BaseModel):
    a: tuple[float, float]
    b: tuple[float, float]

    @field_validator("a", "b")
    @classmethod
    def normalized(cls, v):
        if not all(0.0 <= c <= 1.0 for c in v):
            raise ValueError("coordinates must be normalized to 0..1")
        return v


# ------------------------------------------------------------------ routes
@app.get("/api/health")
def health():
    import torch
    return {"status": "ok", "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            "pipeline": processor.status, "streams": _active_streams}


@app.get("/api/models")
def list_models():
    return [{"id": k, "label": v["label"], "imgsz": v["imgsz"], "available": v["path"].exists()}
            for k, v in MODELS.items()]


@app.get("/api/cameras")
def list_cameras(max_index: int = 4):
    """Probe local camera indices (on the machine running the backend)."""
    found = []
    for i in range(max_index):
        cap = open_camera(i)
        if cap.isOpened():
            ok, _ = cap.read()
            if ok:
                found.append({"index": i, "label": f"Camera {i}"})
        cap.release()
    return found


@app.post("/api/upload")
async def upload_video(file: UploadFile = File(...)):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in VIDEO_EXTS:
        raise HTTPException(400, f"unsupported file type {ext!r}; allowed: {sorted(VIDEO_EXTS)}")
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", Path(file.filename).stem)[:60]
    file_id = f"{uuid.uuid4().hex[:8]}_{safe}{ext}"
    dest = UPLOAD_DIR / file_id
    size, limit = 0, MAX_UPLOAD_MB * 1024 * 1024
    with dest.open("wb") as f:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > limit:
                f.close(); dest.unlink(missing_ok=True)
                raise HTTPException(413, f"file larger than {MAX_UPLOAD_MB} MB")
            f.write(chunk)
    cap = cv2.VideoCapture(str(dest))
    ok = cap.isOpened() and cap.read()[0]
    info = {"frames": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)), "fps": cap.get(cv2.CAP_PROP_FPS)}
    cap.release()
    if not ok:
        dest.unlink(missing_ok=True)
        raise HTTPException(400, "could not decode video")
    return {"file_id": file_id, "filename": file.filename, "size_mb": round(size / 1e6, 1), **info}


@app.post("/api/start")
def start(req: StartRequest):
    if not MODELS[req.model]["path"].exists():
        raise HTTPException(400, f"model file missing: {MODELS[req.model]['path']}")
    source = req.source.strip()
    if req.source_type == "camera":
        if not source.isdigit():
            raise HTTPException(400, "camera source must be an index like '0'")
    elif req.source_type == "file":
        path = (UPLOAD_DIR / Path(source).name).resolve()   # only files inside the upload dir
        if not path.exists():
            raise HTTPException(404, "uploaded file not found; upload it first via /api/upload")
        source = str(path)
    elif not re.match(r"^(rtsp|rtmp|http|https)://", source, re.I):
        raise HTTPException(400, "stream URL must start with rtsp://, rtmp://, http:// or https://")
    processor.start(SessionConfig(req.source_type, source, req.model, req.conf, req.loop))
    return processor.state()


@app.post("/api/stop")
def stop():
    processor.stop()
    return processor.state()


@app.post("/api/line")
def set_line(req: LineRequest):
    try:
        processor.set_line(req.a, req.b)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return processor.state()["counts"]["line"]


@app.post("/api/reset")
def reset():
    processor.reset_counts()
    return processor.state()


@app.get("/api/state")
def state():
    return processor.state()


@app.get("/api/events.csv", response_class=PlainTextResponse)
def events_csv():
    return PlainTextResponse(processor.events_csv(), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="vehicle_counts_{time.strftime("%Y%m%d_%H%M%S")}.csv"'})


_active_streams = 0   # open MJPEG connections (reported by /api/health)


@app.get("/api/stream")
async def stream(request: Request):
    """MJPEG stream of annotated frames: use directly as <img src>."""
    boundary = "frame"

    async def gen():
        global _active_streams
        _active_streams += 1
        try:
            last = -1
            idle_since = next_check = time.monotonic()
            while True:
                if processor.frame_id != last and processor.jpeg is not None:
                    last, jpg = processor.frame_id, processor.jpeg
                    idle_since = time.monotonic()
                    yield (b"--" + boundary.encode() + b"\r\nContent-Type: image/jpeg\r\nContent-Length: "
                           + str(len(jpg)).encode() + b"\r\n\r\n" + jpg + b"\r\n")
                else:
                    await asyncio.sleep(0.01)
                    now = time.monotonic()
                    # While no frames are flowing, nothing is written, so a closed client would go unnoticed:
                    # check explicitly so abandoned streams end instead of piling up across Start/Stop cycles.
                    if now >= next_check:
                        next_check = now + 0.5
                        if await request.is_disconnected():
                            return
                    if now - idle_since > 3600:   # nothing for an hour: end the response
                        return
        finally:
            _active_streams -= 1

    return StreamingResponse(gen(), media_type=f"multipart/x-mixed-replace; boundary={boundary}",
                             headers={"Cache-Control": "no-cache, no-store", "Pragma": "no-cache",
                                      "X-Accel-Buffering": "no"})


@app.websocket("/ws/state")
async def ws_state(ws: WebSocket):
    """Pushes the pipeline state (counts, fps, recent events) 4 times per second."""
    await ws.accept()
    try:
        while True:
            await ws.send_json(processor.state())
            await asyncio.sleep(0.25)
    except (WebSocketDisconnect, RuntimeError):
        pass
