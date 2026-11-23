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

  const stop = async () => {
    setBusy(true);
    try { await api.stop(); } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  };

  const canStart = !busy && !running && (type === "camera" ? camera !== "" : type === "url" ? url.trim() !== "" : !!upload);

  return (
    <section className="card">
      <h2>Video source</h2>

      <div className="tabs" role="tablist">
        {(["file", "camera", "url"] as SourceType[]).map((t) => (
          <button key={t} role="tab" aria-selected={type === t} className={type === t ? "tab active" : "tab"}
                  onClick={() => setType(t)} disabled={running}>
            {t === "file" ? "Video file" : t === "camera" ? "Webcam" : "IP camera / URL"}
          </button>
        ))}
      </div>

      {type === "file" && (
        <div className="field">
          <label className="file-drop">
            <input type="file" accept="video/*" disabled={running || progress !== null}
                   onChange={(e) => onFile(e.target.files?.[0])} />
            <span>{progress !== null ? `Uploading… ${progress}%` : upload ? "Choose another video" : "Choose a video file"}</span>
          </label>
          {progress !== null && <div className="progress"><div style={{ width: `${progress}%` }} /></div>}
          {upload && (
            <p className="hint">
              <strong>{upload.filename}</strong> · {upload.size_mb} MB · {upload.frames} frames @ {upload.fps.toFixed(0)} fps
            </p>
          )}
          <label className="check">
            <input type="checkbox" checked={loop} onChange={(e) => setLoop(e.target.checked)} disabled={running} />
            Loop video
          </label>
        </div>
      )}

      {type === "camera" && (
        <div className="field">
          <div className="row">
            <select value={camera} onChange={(e) => setCamera(e.target.value)} disabled={running}>
              {(cameras ?? [{ index: 0, label: "Camera 0" }]).map((c) => (
                <option key={c.index} value={c.index}>{c.label}</option>
              ))}
            </select>
            <button className="btn ghost" onClick={probeCameras} disabled={busy || running}>Detect</button>
          </div>
          {cameras && cameras.length === 0 && <p className="hint warn">No cameras found on the backend machine.</p>}
          <p className="hint">Uses a camera attached to the computer running the backend.</p>
        </div>
      )}

