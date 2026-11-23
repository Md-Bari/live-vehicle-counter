"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useLiveState } from "@/lib/useLiveState";
import SourcePanel from "@/components/SourcePanel";
import VideoView from "@/components/VideoView";
import CountsPanel from "@/components/CountsPanel";
import EventsLog from "@/components/EventsLog";

const STATUS_LABEL: Record<string, string> = {
  idle: "Idle", starting: "Starting…", running: "Running", finished: "Finished", error: "Error",
};

export default function Home() {
  const { state, connected } = useLiveState();
  const [streamKey, setStreamKey] = useState(() => Date.now());
  const [gpu, setGpu] = useState<string | null | undefined>(undefined);

  useEffect(() => { api.health().then((h) => setGpu(h.gpu)).catch(() => setGpu(undefined)); }, [connected]);

  const status = connected ? state?.status ?? "idle" : "offline";

  return (
    <div className="page">
      <header className="topbar">
        <div className="brand">
          <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden>
            <path fill="currentColor" d="M5 11l1.5-4.5A2 2 0 0 1 8.4 5h7.2a2 2 0 0 1 1.9 1.5L19 11v6a1 1 0 0 1-1 1h-1a1 1 0 0 1-1-1v-1H8v1a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1v-6zm2.2 0h9.6l-1-3.2a1 1 0 0 0-1-.8H9.2a1 1 0 0 0-1 .8L7.2 11zM7.5 13a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zm9 0a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3z" />
          </svg>
          <h1>Vehicle Counter</h1>
        </div>
        <div className="meta">
          <span className={`status ${status}`}>{connected ? STATUS_LABEL[status] ?? status : "Backend offline"}</span>
          {state?.status === "running" && <span className="chip">{state.fps.toFixed(1)} FPS</span>}
          {state?.source && <span className="chip">{state.source.model}</span>}
          {gpu !== undefined && <span className="chip">{gpu ?? "CPU"}</span>}
        </div>
      </header>

      <main className="layout">
        <div className="main-col">
          <VideoView state={state} streamKey={streamKey} />
          <CountsPanel state={state} />
        </div>
        <aside className="side-col">
          <SourcePanel state={state} onStarted={() => setStreamKey(Date.now())} />
          <EventsLog state={state} />
        </aside>
      </main>
    </div>
  );
}
