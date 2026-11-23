"""Backend settings. Override with environment variables where noted."""
import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent.parent                     # d:/Shitol/detection
MODELS_DIR = Path(os.getenv("MODELS_DIR", PROJECT_DIR / "models"))
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", BACKEND_DIR / "uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

