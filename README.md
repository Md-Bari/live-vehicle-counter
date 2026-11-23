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
