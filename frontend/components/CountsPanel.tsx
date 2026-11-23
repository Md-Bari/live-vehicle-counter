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

  return (
    <>
      <div className="stats">
        <div className="stat"><span>Total passed</span><strong>{total.total}</strong></div>
        <div className="stat in"><span>IN</span><strong>{total.in}</strong></div>
        <div className="stat out"><span>OUT</span><strong>{total.out}</strong></div>
        <div className="stat muted">
          <span>In view now</span>
          <strong>{Object.values(state?.in_frame ?? {}).reduce((a, b) => a + b, 0)}</strong>
        </div>
      </div>

      <section className="card">
        <div className="card-head">
          <h2>Counts by vehicle type</h2>
          <div className="row">
            <a className="btn ghost" href={api.csvUrl()} download>Download CSV</a>
            <button className="btn ghost" onClick={reset}>Reset</button>
          </div>
        </div>
        {visible.length === 0 ? (
          <p className="hint">No vehicles yet. Counts appear here as tracked objects cross the line.</p>
        ) : (
          <table className="counts">
            <thead>
              <tr><th>Type</th><th className="bar-col" aria-label="share" /><th>IN</th><th>OUT</th><th>Total</th><th>In view</th></tr>
            </thead>
            <tbody>
              {visible.map((c) => (
                <tr key={c.name}>
                  <td><span className="swatch" style={{ background: c.color }} />{c.name}</td>
                  <td className="bar-col"><div className="bar"><div style={{ width: `${(c.total / max) * 100}%`, background: c.color }} /></div></td>
                  <td className="num">{c.in}</td>
                  <td className="num">{c.out}</td>
                  <td className="num strong">{c.total}</td>
                  <td className="num muted">{state?.in_frame[c.name] ?? 0}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </>
  );
}
