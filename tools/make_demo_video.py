"""Build a demo video for trying the app without a real traffic clip.

It pans a camera window across busy test images, so the vehicles move across the frame and a
vertical counting line in the middle will count them. A real road video will behave better.

    python make_demo_video.py [out.mp4] [--images 8]
"""
import argparse
from pathlib import Path

import cv2
import numpy as np

PROJECT = Path(__file__).resolve().parents[2]
TEST = PROJECT / "dataset" / "test"


def busiest_images(n):
    scored = []
    for lbl in (TEST / "labels").glob("*.txt"):
        k = sum(1 for l in lbl.read_text().splitlines() if l.strip())
        img = TEST / "images" / (lbl.stem + ".jpg")
        if img.exists():
            scored.append((k, img))
    scored.sort(reverse=True)
    return [p for _, p in scored[:n]]


