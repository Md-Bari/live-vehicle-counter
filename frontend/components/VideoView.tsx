"use client";

import { useEffect, useRef, useState, MouseEvent } from "react";
import { api, PipelineState } from "@/lib/api";

type Pt = [number, number];

const BLANK = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7";

/**
 * MJPEG <img> that really closes its connection. Chromium browsers keep an MJPEG request open
 * after the <img> is removed or re-keyed, so each Start/Stop leaked a stream: the leaked streams
 * used up the ~6 connections per server and the browser kept decoding every one of them, slowing
 * the dashboard down more with every run. Pointing the src elsewhere first aborts the request.
 */
function MjpegStream({ src }: { src: string }) {
  const ref = useRef<HTMLImageElement>(null);
  useEffect(() => {
    const img = ref.current;
    if (!img) return;
    img.src = src;
    return () => { img.src = BLANK; };
  }, [src]);
  // eslint-disable-next-line @next/next/no-img-element
  return <img ref={ref} alt="Annotated live video" draggable={false} />;
}

export default function VideoView({ state, streamKey }: { state: PipelineState | null; streamKey: number }) {
  const box = useRef<HTMLDivElement>(null);
  const [drawing, setDrawing] = useState(false);
  const [first, setFirst] = useState<Pt | null>(null);
  const [hover, setHover] = useState<Pt | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [W, H] = state?.frame_size ?? [1280, 720];
  const live = state?.status === "running" || state?.status === "starting";
  const hasFrame = (state?.frames ?? 0) > 0;
  const line = state?.counts.line ?? { a: [0, 0.6] as Pt, b: [1, 0.6] as Pt };

  const toNorm = (e: MouseEvent): Pt => {
    const r = box.current!.getBoundingClientRect();
    const clamp = (v: number) => Math.min(1, Math.max(0, v));
    return [clamp((e.clientX - r.left) / r.width), clamp((e.clientY - r.top) / r.height)];
  };

  const save = async (a: Pt, b: Pt) => {
    setError(null);
    try { await api.setLine(a, b); } catch (e) { setError((e as Error).message); }
  };

  const onClick = (e: MouseEvent) => {
    if (!drawing) return;
    const p = toNorm(e);
    if (!first) { setFirst(p); return; }
    if (Math.hypot((p[0] - first[0]) * W, (p[1] - first[1]) * H) < 10) return; // too short
    save(first, p);
    setFirst(null); setHover(null); setDrawing(false);
  };

  // Shown line: the one being drawn, otherwise the backend's
  const a: Pt = drawing && first ? first : (line.a as Pt);
  const b: Pt | null = drawing && first ? hover : (line.b as Pt);

  // Unit normal pointing to the "IN" side (matches backend: cross(a,b,p) > 0), in pixel space
  let arrows: { inP: Pt; outP: Pt; mid: Pt } | null = null;
  if (b && !(drawing && first)) {
    const dx = (b[0] - a[0]) * W, dy = (b[1] - a[1]) * H;
    const len = Math.hypot(dx, dy) || 1;
    const nx = -dy / len, ny = dx / len;
    // anchor near the start of the line, where it usually crosses less traffic than the middle
    const t = 0.12;
    const mid: Pt = [(a[0] + (b[0] - a[0]) * t) * W, (a[1] + (b[1] - a[1]) * t) * H];
    const d = Math.min(W, H) * 0.09;
    arrows = { mid, inP: [mid[0] + nx * d, mid[1] + ny * d], outP: [mid[0] - nx * d, mid[1] - ny * d] };
  }
  const sw = Math.max(2, W / 400);

