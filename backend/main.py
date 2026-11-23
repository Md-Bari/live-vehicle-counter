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
