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
        <ul className="events">
          {events.map((e) => (
            <li key={`${e.track_id}-${e.direction}-${e.timestamp}`}>
              <time>{new Date(e.timestamp * 1000).toLocaleTimeString()}</time>
              <span className="swatch" style={{ background: classColor(names.indexOf(e.class)) }} />
              <span className="ev-class">{e.class}</span>
              <span className="ev-id">#{e.track_id}</span>
              <span className={`pill ${e.direction}`}>{e.direction.toUpperCase()}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
