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

