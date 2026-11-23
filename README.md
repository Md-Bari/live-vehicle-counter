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

