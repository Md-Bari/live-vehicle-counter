"""End-to-end API test: upload a synthetic 'pan' video built from a dataset image, run the
pipeline, and check that vehicles crossing a vertical line are counted."""
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import main  # noqa: E402

PROJECT = Path(__file__).resolve().parents[3]
TEST_IMG = PROJECT / "dataset" / "test" / "images" / "5518.jpg"   # busy road scene


