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
