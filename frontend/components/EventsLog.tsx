"use client";

import { PipelineState } from "@/lib/api";
import { classColor } from "@/lib/colors";

export default function EventsLog({ state }: { state: PipelineState | null }) {
  const names = Object.keys(state?.counts.per_class ?? {});
  const events = state?.recent_events ?? [];
  return (
    <section className="card">
      <h2>Recent crossings</h2>
      {events.length === 0 ? (
        <p className="hint">Nothing has crossed the line yet.</p>
      ) : (
