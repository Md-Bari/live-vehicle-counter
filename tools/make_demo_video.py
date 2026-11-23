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


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("out", nargs="?", default=str(Path(__file__).parent / "demo_traffic.mp4"))
    ap.add_argument("--images", type=int, default=8)
    ap.add_argument("--seconds", type=float, default=4.0, help="pan duration per image")
    a = ap.parse_args()

    W, H, FPS = 1280, 720, 25
    vw = cv2.VideoWriter(a.out, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
    for path in busiest_images(a.images):
        img = cv2.imread(str(path))
        if img is None:
            continue
        s = H / img.shape[0]
        img = cv2.resize(img, (max(int(img.shape[1] * s), int(W * 1.6)), H))  # make wide enough to pan
        for x in np.linspace(0, img.shape[1] - W, int(a.seconds * FPS)).astype(int):
            vw.write(img[:, x:x + W])
    vw.release()
    print("wrote", a.out)
