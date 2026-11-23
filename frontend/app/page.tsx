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

