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


def test_health_and_models(client):
    assert client.get("/api/health").json()["status"] == "ok"
    models = client.get("/api/models").json()
    assert {m["id"] for m in models} == {"yolo26m", "yolo26s"}
    assert all(m["available"] for m in models)


def test_validation(client):
    assert client.post("/api/start", json={"source_type": "camera", "source": "abc"}).status_code == 400
    assert client.post("/api/start", json={"source_type": "url", "source": "file:///etc/passwd"}).status_code == 400
    assert client.post("/api/start", json={"source_type": "file", "source": "missing.mp4"}).status_code == 404
    assert client.post("/api/line", json={"a": [0, 0], "b": [2, 1]}).status_code == 422
    assert client.post("/api/upload", files={"file": ("x.txt", b"hi", "text/plain")}).status_code == 400


@pytest.mark.parametrize("model", ["yolo26s", "yolo26m"])
def test_upload_run_and_count(client, pan_video, model):
    up = client.post("/api/upload", files={"file": ("pan.mp4", pan_video.read_bytes(), "video/mp4")})
    assert up.status_code == 200, up.text
    file_id = up.json()["file_id"]

    assert client.post("/api/line", json={"a": [0.5, 0.0], "b": [0.5, 1.0]}).status_code == 200
    r = client.post("/api/start", json={"source_type": "file", "source": file_id, "model": model, "conf": 0.3})
    assert r.status_code == 200, r.text

    deadline = time.time() + 120
    while time.time() < deadline:
        st = client.get("/api/state").json()
        if st["status"] in ("finished", "error"):
            break
        time.sleep(0.5)
    assert st["status"] == "finished", st
    assert st["frames"] == 60
    assert st["counts"]["total"]["total"] > 0, "expected some vehicles to cross the line"
    # camera pans right => objects move right-to-left => every crossing has the same direction
    t = st["counts"]["total"]
    assert min(t["in"], t["out"]) == 0, t

    csv = client.get("/api/events.csv").text.strip().splitlines()
    assert csv[0].startswith("timestamp_iso") and len(csv) - 1 == t["total"]
    print(f"\n{model}: counted {t['total']} crossings:",
          {k: v["total"] for k, v in st["counts"]["per_class"].items() if v["total"]})
    (main.UPLOAD_DIR / file_id).unlink(missing_ok=True)


def test_stream_and_ws(client):
    with client.websocket_connect("/ws/state") as ws:
        msg = ws.receive_json()
        assert "counts" in msg and "status" in msg
    assert main.processor.jpeg is not None and main.processor.jpeg[:2] == b"\xff\xd8"   # last annotated frame is a JPEG
