import { useMemo } from "react";
import { api } from "../api/client";
import type { ProcessingResult } from "../api/types";
import { useAppStore } from "../state/appStore";

function fmt(n: number | null | undefined, digits = 2, suffix = ""): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return `${n.toFixed(digits)}${suffix}`;
}

const SORTABLE_COLUMNS: { key: keyof ProcessingResult; label: string }[] = [
  { key: "slope_error", label: "Error" },
  { key: "plane_rmse", label: "Plane RMSE" },
  { key: "improvement_pct", label: "Improvement" },
  { key: "processing_time_ms", label: "Time" },
  { key: "point_count", label: "Points" },
];

/** Central comparison table (spec section 17) with sortable columns and
 * per-row export/delete actions. */
export default function ResultsTable() {
  const results = useAppStore((s) => s.results);
  const sortKey = useAppStore((s) => s.sortKey);
  const sortDir = useAppStore((s) => s.sortDir);
  const setSort = useAppStore((s) => s.setSort);
  const removeResult = useAppStore((s) => s.removeResult);

  const sorted = useMemo(() => {
    const rows = [...results];
    if (!sortKey) return rows;
    rows.sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      const an = av === null || av === undefined ? Infinity : (av as number);
      const bn = bv === null || bv === undefined ? Infinity : (bv as number);
      return sortDir === "asc" ? an - bn : bn - an;
    });
    return rows;
  }, [results, sortKey, sortDir]);

  const handleExport = async (r: ProcessingResult, format: "ply" | "pcd") => {
    await api.exportResult(r.id, format, r.name.replace(/\s+/g, "_"));
  };

  const handleDelete = async (r: ProcessingResult) => {
    await api.deleteResult(r.id);
    removeResult(r.id);
  };

  if (results.length === 0) {
    return (
      <div className="panel">
        <h3>Results</h3>
        <div className="muted">No results yet. Run an algorithm, pipeline, or slope analysis first.</div>
      </div>
    );
  }

  return (
    <div className="panel">
      <div className="panel-header-row">
        <h3>Results Comparison</h3>
        <div className="algo-actions">
          <button onClick={() => api.exportResultsTable(results[0].experiment_id, "csv")}>Export CSV</button>
          <button onClick={() => api.exportResultsTable(results[0].experiment_id, "json")}>Export JSON</button>
        </div>
      </div>
      <div className="table-scroll">
        <table className="results-table">
          <thead>
            <tr>
              <th>Version</th>
              <th>Points</th>
              <th>Removed %</th>
              <th>Slope</th>
              <th>Ground Truth</th>
              {SORTABLE_COLUMNS.map((c) => (
                <th key={c.key} onClick={() => setSort(c.key)} className="sortable">
                  {c.label} {sortKey === c.key ? (sortDir === "asc" ? "▲" : "▼") : ""}
                </th>
              ))}
              <th>Export</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((r) => (
              <tr key={r.id} className={r.algorithm_name === null ? "baseline-row" : ""}>
                <td>
                  <strong>{r.name}</strong>
                  <div className="muted tiny">{r.source_type}</div>
                </td>
                <td>{r.point_count.toLocaleString()}</td>
                <td>{fmt(r.points_removed_pct, 1, "%")}</td>
                <td>{fmt(r.calculated_slope, 2, "°")}</td>
                <td>{fmt(r.ground_truth_slope, 2, "°")}</td>
                <td className={r.slope_error !== null && r.slope_error < 0.5 ? "good" : ""}>
                  {fmt(r.slope_error, 2, "°")}
                </td>
                <td>{fmt(r.plane_rmse, 4)}</td>
                <td className={r.improvement_pct !== null && r.improvement_pct > 0 ? "good" : r.improvement_pct !== null && r.improvement_pct < 0 ? "bad" : ""}>
                  {r.improvement_pct === null ? "—" : `${r.improvement_pct.toFixed(1)}%`}
                </td>
                <td>{fmt(r.processing_time_ms, 1, " ms")}</td>
                <td>
                  <button className="small-btn" onClick={() => handleExport(r, "ply")}>
                    PLY
                  </button>
                  <button className="small-btn" onClick={() => handleExport(r, "pcd")}>
                    PCD
                  </button>
                </td>
                <td>
                  {r.algorithm_name !== null && (
                    <button className="small-btn danger" onClick={() => handleDelete(r)}>
                      ✕
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
