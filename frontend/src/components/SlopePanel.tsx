import { useState } from "react";
import { api } from "../api/client";
import type { PlaneFitParams, ProcessingResult } from "../api/types";
import { useAppStore } from "../state/appStore";

interface Props {
  experimentId: string;
  source: "original" | "roi";
  baseline: ProcessingResult | undefined;
}

const DEFAULT_PARAMS: PlaneFitParams = { distance_threshold: 0.01, num_iterations: 1000, min_inliers: 50 };

function fmt(n: number | null | undefined, digits = 4): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return n.toFixed(digits);
}

/** RANSAC plane fitting + ramp slope calculation (spec section 7). Running
 * this creates/refreshes the "Original" baseline that every processing
 * result's improvement percentage is measured against. */
export default function SlopePanel({ experimentId, source, baseline }: Props) {
  const [params, setParams] = useState<PlaneFitParams>(DEFAULT_PARAMS);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const upsertResult = useAppStore((s) => s.upsertResult);

  const run = async () => {
    setBusy(true);
    setError(null);
    try {
      const result = await api.analyzeSlope(experimentId, source, params);
      upsertResult(result);
    } catch (e: any) {
      setError(e.message ?? "Slope analysis failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="panel">
      <h3>Ramp Slope (RANSAC Plane Fit)</h3>
      <label className="param-row">
        <span>Distance Threshold (m)</span>
        <input
          type="number"
          step={0.001}
          value={params.distance_threshold}
          onChange={(e) => setParams({ ...params, distance_threshold: parseFloat(e.target.value) })}
        />
      </label>
      <label className="param-row">
        <span>Iterations</span>
        <input
          type="number"
          step={50}
          value={params.num_iterations}
          onChange={(e) => setParams({ ...params, num_iterations: parseInt(e.target.value) })}
        />
      </label>
      {error && <div className="error-text">{error}</div>}
      <button disabled={busy} onClick={run}>
        {busy ? "Analyzing…" : `Calculate Slope on ${source === "roi" ? "ROI" : "Original"}`}
      </button>

      {baseline && baseline.calculated_slope !== null && (
        <div className="kv-grid" style={{ marginTop: 10 }}>
          <span>Slope</span>
          <span className="highlight">{fmt(baseline.calculated_slope, 2)}°</span>
          <span>Plane Equation</span>
          <span>
            {fmt(baseline.plane_a, 3)}x + {fmt(baseline.plane_b, 3)}y + {fmt(baseline.plane_c, 3)}z + {fmt(baseline.plane_d, 3)} = 0
          </span>
          <span>Plane Normal</span>
          <span>{baseline.plane_normal ? baseline.plane_normal.map((v) => v.toFixed(3)).join(", ") : "—"}</span>
          <span>Inliers / Outliers</span>
          <span>
            {baseline.inlier_count ?? "—"} / {baseline.outlier_count ?? "—"}
          </span>
          <span>Plane RMSE</span>
          <span>{fmt(baseline.plane_rmse)} m</span>
          <span>Mean Pt→Plane Dist</span>
          <span>{fmt(baseline.mean_point_to_plane_distance)} m</span>
          {baseline.ground_truth_slope !== null && (
            <>
              <span>Ground Truth</span>
              <span>{fmt(baseline.ground_truth_slope, 2)}°</span>
              <span>Absolute Error</span>
              <span className="highlight">{fmt(baseline.slope_error, 2)}°</span>
            </>
          )}
        </div>
      )}
    </div>
  );
}
