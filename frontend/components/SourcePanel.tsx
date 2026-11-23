"use client";

import { useEffect, useState } from "react";
import { api, Camera, ModelInfo, PipelineState, UploadResult } from "@/lib/api";

type SourceType = "camera" | "url" | "file";

export default function SourcePanel({ state, onStarted }: { state: PipelineState | null; onStarted: () => void }) {
  const [type, setType] = useState<SourceType>("file");
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [model, setModel] = useState("yolo26m");
  const [conf, setConf] = useState(0.35);
  const [loop, setLoop] = useState(false);
  const [cameras, setCameras] = useState<Camera[] | null>(null);
  const [camera, setCamera] = useState("0");
  const [url, setUrl] = useState("");
  const [upload, setUpload] = useState<UploadResult | null>(null);
  const [progress, setProgress] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const running = state?.status === "running" || state?.status === "starting";

  useEffect(() => {
    api.models().then((m) => {
      setModels(m);
      const first = m.find((x) => x.available);
      if (first && !m.find((x) => x.id === model && x.available)) setModel(first.id);
    }).catch((e) => setError(`Backend unreachable: ${e.message}`));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const probeCameras = async () => {
    setError(null); setCameras(null); setBusy(true);
    try {
      const c = await api.cameras();
      setCameras(c);
      if (c.length) setCamera(String(c[0].index));
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  };

  const onFile = async (f: File | undefined) => {
    if (!f) return;
    setError(null); setUpload(null); setProgress(0);
    try { setUpload(await api.upload(f, setProgress)); }
    catch (e) { setError((e as Error).message); }
    finally { setProgress(null); }
  };

  const start = async () => {
    setError(null); setBusy(true);
    try {
      const source = type === "camera" ? camera : type === "url" ? url : upload?.file_id ?? "";
      await api.start({ source_type: type, source, model, conf, loop });
      onStarted();
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  };

