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

