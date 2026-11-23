/**
 * Backend base URL, baked in at build time.
 * Unset → http://localhost:8001 (local dev). Set to "" → same origin as the page
 * (Docker: an nginx gateway routes /api and /ws to the backend).
 */
export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001").replace(/\/$/, "");

/** WebSocket base URL; for same-origin it is derived from the page address (browser only). */
export function wsUrl(): string {
  if (API_URL) return API_URL.replace(/^http/, "ws");
  return `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}`;
}

export type Direction = "in" | "out";
export type ClassCount = { in: number; out: number; total: number };

export interface CrossingEvent {
  timestamp: number;
  track_id: number;
  class: string;
  direction: Direction;
}

export interface PipelineState {
  status: "idle" | "starting" | "running" | "finished" | "error";
  error: string | null;
  source: { type: string; source: string; model: string; conf: number } | null;
  fps: number;
  frames: number;
  frame_size: [number, number] | null;
  in_frame: Record<string, number>;
  counts: {
    line: { a: [number, number]; b: [number, number] };
    total: ClassCount;
    per_class: Record<string, ClassCount>;
  };
  recent_events: CrossingEvent[];
}

export interface ModelInfo { id: string; label: string; imgsz: number; available: boolean }
export interface Camera { index: number; label: string }
export interface UploadResult { file_id: string; filename: string; size_mb: number; frames: number; fps: number }

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: init?.body && !(init.body instanceof FormData) ? { "Content-Type": "application/json" } : undefined,
  });
  if (!res.ok) {
    let msg = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      msg = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail ?? body);
    } catch { /* not JSON */ }
    throw new Error(msg);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string; gpu: string | null; pipeline: string }>("/api/health"),
  models: () => request<ModelInfo[]>("/api/models"),
  cameras: () => request<Camera[]>("/api/cameras"),
  start: (body: { source_type: "camera" | "url" | "file"; source: string; model: string; conf: number; loop: boolean }) =>
    request<PipelineState>("/api/start", { method: "POST", body: JSON.stringify(body) }),
  stop: () => request<PipelineState>("/api/stop", { method: "POST" }),
  reset: () => request<PipelineState>("/api/reset", { method: "POST" }),
  setLine: (a: [number, number], b: [number, number]) =>
    request("/api/line", { method: "POST", body: JSON.stringify({ a, b }) }),
  csvUrl: () => `${API_URL}/api/events.csv`,
  streamUrl: (key: number) => `${API_URL}/api/stream?k=${key}`,

  /** Upload with progress (fetch has no upload progress). */
  upload: (file: File, onProgress: (pct: number) => void) =>
    new Promise<UploadResult>((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      const fd = new FormData();
      fd.append("file", file);
      xhr.open("POST", `${API_URL}/api/upload`);
      xhr.upload.onprogress = (e) => e.lengthComputable && onProgress(Math.round((e.loaded / e.total) * 100));
      xhr.onload = () => {
        let body: { detail?: unknown } & Partial<UploadResult> = {};
        try { body = JSON.parse(xhr.responseText); } catch { /* ignore */ }
        if (xhr.status >= 200 && xhr.status < 300) resolve(body as UploadResult);
        else reject(new Error(typeof body.detail === "string" ? body.detail : `upload failed (${xhr.status})`));
      };
      xhr.onerror = () => reject(new Error("upload failed: backend unreachable"));
      xhr.send(fd);
    }),
};
