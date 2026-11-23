# Vehicle Counter

Live vehicle-type detection and counting. A FastAPI backend runs the fine-tuned YOLO26 detector with ByteTrack tracking and counts every vehicle that crosses a line you draw. A Next.js dashboard shows the annotated live video, the counts per vehicle type and direction, and a log of crossings.

17 classes: Bicycle, Bus, Bhotbhoti, Car, CNG, Easybike, Leguna, Motorbike, MPV, Pedestrian, Pickup, PowerTiller, Rickshaw, ShoppingVan, Truck, Van, Wheelbarrow.

```
app/
├── backend/                FastAPI + ultralytics
│   ├── main.py             REST + MJPEG stream + WebSocket
│   ├── processor.py        capture → YOLO26 + ByteTrack → counting → annotated JPEG (background thread)
│   ├── counter.py          line-crossing logic
│   ├── config.py           model paths, ports, limits (env-overridable)
│   └── tests/              pytest: counter unit tests + end-to-end API test
├── frontend/               Next.js 16 (App Router, TypeScript)
│   ├── app/page.tsx        dashboard
│   ├── components/         VideoView, SourcePanel, CountsPanel, EventsLog
│   └── lib/                API client, WebSocket hook
├── nginx/default.conf      Docker gateway: / → frontend, /api + /ws → backend
├── docker-compose.yml      full system in Docker (GPU)
├── docker-compose.cpu.yml  override for machines without an NVIDIA GPU
├── tools/make_demo_video.py   builds a demo clip from dataset images
├── start_docker.bat        builds and starts the Docker stack, opens the browser
└── start_app.bat           starts both servers natively and opens the browser
```

The models are loaded from `../models/` (`vehicle_yolo26m.pt`, `vehicle_yolo26s.pt`).

## Run with Docker (recommended)

**Requirements:** Docker Desktop (WSL 2 backend on Windows) or Docker Engine + the NVIDIA Container Toolkit on Linux, and an NVIDIA driver. No Python or Node.js needed.

```bat
docker compose up -d --build        :: or double-click start_docker.bat
```

If the build stops with `additional privileges requested` (Compose's *bake* builder on Windows paths), run `set COMPOSE_BAKE=false` first, or put `COMPOSE_BAKE=false` in `.env`. `start_docker.bat` already does this.

Open **http://localhost:8088**. Everything goes through one port:

| Path | Served by |
|---|---|
| `/` | dashboard (Next.js container) |
| `/api/*`, `/ws/*` | FastAPI container (GPU) |
| `/docs` | API docs (Swagger) |

```
browser ──► gateway (nginx :8088) ──┬──► frontend  (Next.js standalone, :3000)
                                    └──► backend   (FastAPI + YOLO26 + CUDA, :8001)
                                            ├─ ../models  mounted read-only at /models
                                            └─ uploads    named volume at /data/uploads
```

| Command | What it does |
|---|---|
| `docker compose logs -f backend` | follow the backend log |
| `docker compose ps` | container status and health |
| `docker compose down` | stop (uploaded videos are kept in the `uploads` volume) |
| `docker compose down -v` | stop and delete uploaded videos |
| `docker compose up -d --build` | rebuild after code changes |

**Settings:** copy `.env.example` to `.env` to change the port (`APP_PORT`), the default model, or the models folder (`MODELS_PATH`). The first build downloads CUDA PyTorch (about 3 GB); later builds are cached.

**No NVIDIA GPU:** `docker compose -f docker-compose.yml -f docker-compose.cpu.yml up -d --build` builds a CPU-only image. It works, but expect a few FPS; pick YOLO26s.

**Cameras in Docker:** Docker Desktop on Windows/macOS cannot pass a USB webcam into a container. Use a video file or an IP camera/RTSP URL (phone IP-camera apps work), or run the backend natively for a webcam. On a Linux host, uncomment the `devices:` entry in `docker-compose.yml`. Inside a container, `localhost` means the container itself: for a stream served by the host machine use `host.docker.internal` instead.

## Run natively

**Requirements:** Python 3.10+ with a CUDA build of PyTorch, and Node.js 20+.

```bat
:: one-time setup
pip install -r backend\requirements.txt
cd frontend && npm install && npm run build && cd ..

:: every time
start_app.bat
```

Or start the two servers yourself:

```bat
cd backend  && python -m uvicorn main:app --host 0.0.0.0 --port 8001
cd frontend && npm run start        :: or: npm run dev
```

| Part | URL |
|---|---|
| Dashboard | http://localhost:3000 |
| API docs (Swagger) | http://localhost:8001/docs |

The backend uses port **8001** because Docker Desktop already uses 8000 on this machine. To use another port, start uvicorn with `--port N` and set `NEXT_PUBLIC_API_URL=http://localhost:N` in `frontend/.env.local`, then rebuild the frontend.

## Using it

1. **Choose a source:**
   - **Video file:** upload any mp4/avi/mov/mkv. It plays at its native speed, like a live feed. Tick *Loop video* to replay it.
   - **Webcam:** a camera attached to the computer running the backend. Press *Detect* to list cameras.
   - **IP camera / URL:** an RTSP, RTMP or HTTP stream, for example `rtsp://user:pass@192.168.1.10:554/stream`. This covers CCTV cameras and phone IP-camera apps.
2. **Choose a model:**
   - **YOLO26m @ 960px** is more accurate (test mAP50 0.896). It runs at about 25+ FPS on an RTX 5070 Ti.
   - **YOLO26s @ 640px** is faster (test mAP50 0.884).
3. **Set the confidence threshold.** The default of 0.35 works well. Raise it to reduce false detections, or lower it to catch more distant vehicles.
4. **Press Start.**
5. **Place the counting line.** Use *Draw counting line* and click two points on the video, or use the *Horizontal* / *Vertical* presets. Draw it across the road, where vehicles pass. The green **IN** and blue **OUT** arrows show which direction counts as which.
6. **Read the results.** The cards show the totals, the table shows counts per vehicle type and direction, and the right panel lists each crossing. *Download CSV* exports every crossing with a timestamp; *Reset* clears the counts.

## How counting works

