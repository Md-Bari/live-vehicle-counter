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

