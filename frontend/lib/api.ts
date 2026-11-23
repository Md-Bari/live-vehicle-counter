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

