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

