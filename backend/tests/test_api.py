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


@pytest.fixture(scope="module")
def client():
    with TestClient(main.app) as c:
        yield c


@pytest.fixture(scope="module")
def pan_video(tmp_path_factory):
    """Slide a 60%-wide window across the image so every object moves right-to-left on screen."""
    img = cv2.imread(str(TEST_IMG))
    assert img is not None, TEST_IMG
    h, w = img.shape[:2]
    win = int(w * 0.6)
    out = tmp_path_factory.mktemp("vid") / "pan.mp4"
    vw = cv2.VideoWriter(str(out), cv2.VideoWriter_fourcc(*"mp4v"), 25, (win, h))
    for x in np.linspace(0, w - win, 60).astype(int):
        vw.write(img[:, x:x + win])
    vw.release()
    return out

