"use client";

import { useEffect, useRef, useState } from "react";
import { PipelineState, wsUrl } from "./api";

/** Subscribes to /ws/state and reconnects automatically. */
export function useLiveState() {
  const [state, setState] = useState<PipelineState | null>(null);
  const [connected, setConnected] = useState(false);
  const retry = useRef(0);

  useEffect(() => {
    let ws: WebSocket | null = null;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let closed = false;

    const connect = () => {
      ws = new WebSocket(`${wsUrl()}/ws/state`);
      ws.onopen = () => { retry.current = 0; setConnected(true); };
      ws.onmessage = (e) => {
        try { setState(JSON.parse(e.data)); } catch { /* ignore malformed frame */ }
      };
      ws.onclose = () => {
        setConnected(false);
        if (closed) return;
        const delay = Math.min(5000, 500 * 2 ** retry.current++);
        timer = setTimeout(connect, delay);
      };
      ws.onerror = () => ws?.close();
    };
    connect();
    return () => { closed = true; clearTimeout(timer); ws?.close(); };
  }, []);

  return { state, connected };
}
