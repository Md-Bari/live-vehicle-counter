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

