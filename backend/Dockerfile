# syntax=docker/dockerfile:1
# Vehicle Counter backend: FastAPI + YOLO26 (ultralytics) on CUDA 12.8 PyTorch.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    YOLO_CONFIG_DIR=/tmp/Ultralytics \
    MODELS_DIR=/models \
    UPLOAD_DIR=/data/uploads

# OpenCV runtime libraries (its wheel bundles FFmpeg for files and RTSP/HTTP streams)
RUN apt-get update \
 && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# PyTorch first (large, rarely changes). cu128 wheels support RTX 50-series (Blackwell).
# For a CPU-only image: --build-arg TORCH_INDEX=https://download.pytorch.org/whl/cpu
ARG TORCH_INDEX=https://download.pytorch.org/whl/cu128
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install torch==2.11.0 torchvision==0.26.0 --index-url ${TORCH_INDEX}

COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

COPY . .

RUN useradd --create-home --groups video app \
 && mkdir -p /data/uploads \
 && chown -R app:app /data /app
USER app

EXPOSE 8001
HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/api/health', timeout=4)"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--proxy-headers", "--forwarded-allow-ips", "*"]
