"use client";

import { api, PipelineState } from "@/lib/api";
import { classColor } from "@/lib/colors";

export default function CountsPanel({ state }: { state: PipelineState | null }) {
  const total = state?.counts.total ?? { in: 0, out: 0, total: 0 };
  const perClass = Object.entries(state?.counts.per_class ?? {}).map(([name, c], i) => ({ name, ...c, color: classColor(i) }));
  const max = Math.max(1, ...perClass.map((c) => c.total));
  const visible = perClass.filter((c) => c.total > 0 || (state?.in_frame[c.name] ?? 0) > 0).sort((x, y) => y.total - x.total);

  const reset = async () => {
    if (confirm("Reset all counts?")) await api.reset().catch((e) => alert(e.message));
  };

