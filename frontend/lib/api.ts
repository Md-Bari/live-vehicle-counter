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

