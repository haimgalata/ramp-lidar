import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { DiffPayload } from "../api/types";
import { useAppStore } from "../state/appStore";
import Viewer3D from "./Viewer3D";

/** Difference visualization (spec section 14): cloud-to-cloud distance
 * heatmap between a chosen result and either the Original cloud or another
 * result, with a configurable min/max threshold and a legend. */
export default function DiffViewer() {
  const results = useAppStore((s) => s.results);
  const nonBaseline = results.filter((r) => r.algorithm_name !== null);

  const [resultId, setResultId] = useState<string>("");
  const [otherId, setOtherId] = useState<string>(""); // "" => compare vs Original
  const [minMm, setMinMm] = useState(0);
  const [maxMm, setMaxMm] = useState(10);
  const [diff, setDiff] = useState<DiffPayload | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!resultId && nonBaseline.length > 0) setResultId(nonBaseline[0].id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nonBaseline.length]);

  const load = async () => {
    if (!resultId) return;
    setBusy(true);
    setError(null);
    try {
      const payload = await api.getResultDiff(resultId, otherId || null, minMm, maxMm);
      setDiff(payload);
    } catch (e: any) {
      setError(e.message ?? "Diff computation failed");
    } finally {
      setBusy(false);
    }
  };

  const geometry = diff
    ? {
        positions: Float32Array.from(diff.positions),
        colors: Float32Array.from(diff.colors),
        hasRealColor: true, // these ARE meaningful colors (the distance heatmap)
        count: diff.point_count,
        bounds: null,
      }
    : { positions: new Float32Array(0), colors: null, hasRealColor: false, count: 0, bounds: null };

  // Compute bounds locally since the API doesn't send them for diff payloads.
  if (diff && diff.point_count > 0) {
    const min: [number, number, number] = [Infinity, Infinity, Infinity];
    const max: [number, number, number] = [-Infinity, -Infinity, -Infinity];
    for (let i = 0; i < geometry.positions.length; i += 3) {
      for (let a = 0; a < 3; a++) {
        const v = geometry.positions[i + a];
        if (v < min[a]) min[a] = v;
        if (v > max[a]) max[a] = v;
      }
    }
    (geometry as any).bounds = { min, max };
  }

  return (
    <div className="panel">
      <h3>Difference Visualization</h3>
      <div className="diff-controls">
        <label>
          Result
          <select value={resultId} onChange={(e) => setResultId(e.target.value)}>
            {nonBaseline.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Compare against
          <select value={otherId} onChange={(e) => setOtherId(e.target.value)}>
            <option value="">Original</option>
            {results
              .filter((r) => r.id !== resultId)
              .map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name}
                </option>
              ))}
          </select>
        </label>
        <label>
          Min (mm)
          <input type="number" value={minMm} onChange={(e) => setMinMm(parseFloat(e.target.value))} />
        </label>
        <label>
          Max (mm)
          <input type="number" value={maxMm} onChange={(e) => setMaxMm(parseFloat(e.target.value))} />
        </label>
        <button disabled={busy || !resultId} onClick={load}>
          {busy ? "Computing…" : "Compute Diff"}
        </button>
      </div>
      {error && <div className="error-text">{error}</div>}

      {diff && (
        <>
          <Viewer3D geometry={geometry as any} showAxes showBoundingBox={false} height={380} />
          <div className="diff-legend">
            <div className="diff-gradient-bar" style={{
              background: "linear-gradient(90deg, rgb(26,64,230), rgb(26,191,89), rgb(242,217,26), rgb(230,38,26))",
            }} />
            <div className="diff-legend-labels">
              <span>{minMm.toFixed(1)} mm</span>
              <span>{maxMm.toFixed(1)} mm</span>
            </div>
            <div className="kv-grid">
              <span>Mean Distance</span>
              <span>{diff.mean_distance_mm.toFixed(3)} mm</span>
              <span>Max Distance</span>
              <span>{diff.max_distance_mm.toFixed(3)} mm</span>
            </div>
            <div className="diff-bins">
              {diff.bin_counts.map((b) => (
                <div key={b.label} className="diff-bin-row">
                  <span>{b.label}</span>
                  <span>{b.count.toLocaleString()} pts</span>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
