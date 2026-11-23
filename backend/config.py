"""Backend settings. Override with environment variables where noted."""
import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent.parent                     # d:/Shitol/detection
MODELS_DIR = Path(os.getenv("MODELS_DIR", PROJECT_DIR / "models"))
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", BACKEND_DIR / "uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Trained detectors (imgsz must match training)
MODELS = {
    "yolo26m": {"path": MODELS_DIR / "vehicle_yolo26m.pt", "imgsz": 960,
                "label": "YOLO26m · 960px (more accurate)"},
    "yolo26s": {"path": MODELS_DIR / "vehicle_yolo26s.pt", "imgsz": 640,
                "label": "YOLO26s · 640px (faster)"},
}
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "yolo26m")

# Frontend origins allowed to call the API
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")

STREAM_MAX_WIDTH = int(os.getenv("STREAM_MAX_WIDTH", 1280))   # annotated stream is downscaled to this width
JPEG_QUALITY = int(os.getenv("JPEG_QUALITY", 80))
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", 2048))
VIDEO_EXTS = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".m4v", ".mpg", ".mpeg", ".wmv"}
