import { useMemo } from "react";
import { useAppStore } from "../state/appStore";

/** Simple ranking of results by slope accuracy (spec section 18). */
export default function Leaderboard() {
  const results = useAppStore((s) => s.results);

  const ranked = useMemo(
    () =>
      results
        .filter((r) => r.slope_error !== null)
        .sort((a, b) => (a.slope_error as number) - (b.slope_error as number)),
    [results]
  );

  if (ranked.length === 0) {
    return (
      <div className="panel">
        <h3>Leaderboard</h3>
        <div className="muted">Set a Ground Truth and run at least one slope analysis to rank results.</div>
      </div>
    );
  }

  return (
    <div className="panel">
      <h3>Leaderboard — Closest to Ground Truth</h3>
      <ol className="leaderboard-list">
        {ranked.map((r, i) => (
          <li key={r.id} className={i === 0 ? "best" : ""}>
            <span className="rank">#{i + 1}</span>
            <span className="lb-name">{r.name}</span>
            <span className="lb-error">Error {r.slope_error?.toFixed(2)}°</span>
            {i === 0 && <span className="best-badge">BEST</span>}
          </li>
        ))}
      </ol>
    </div>
  );
}
