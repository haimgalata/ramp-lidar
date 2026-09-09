import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { PointCloudPoints } from "../api/types";
import { useAppStore } from "../state/appStore";
import { usePointCloudGeometry } from "../hooks/usePointCloudGeometry";
import Viewer3D from "./Viewer3D";

interface Props {
  experimentId: string;
  source: "original" | "roi";
}

/** Mode B -- Parallel Algorithm Comparison (spec sections 11-12): runs each
 * selected algorithm independently against the same source cloud and shows
 * all results (plus the source) side by side with optional camera sync. */
export default function ParallelViewers({ experimentId, source }: Props) {
  const algorithms = useAppStore((s) => s.algorithms);
  const parallelStepIds = useAppStore((s) => s.parallelStepIds);
  const parallelAlgoParams = useAppStore((s) => s.parallelAlgoParams);
  const parallelViewerResultIds = useAppStore((s) => s.parallelViewerResultIds);
  const setParallelViewerResultIds = useAppStore((s) => s.setParallelViewerResultIds);
  const syncCameras = useAppStore((s) => s.syncCameras);
  const toggleSyncCameras = useAppStore((s) => s.toggleSyncCameras);
  const upsertResult = useAppStore((s) => s.upsertResult);
  const results = useAppStore((s) => s.results);

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    if (parallelStepIds.length === 0) return;
    setBusy(true);
    setError(null);
    try {
      const algos = parallelStepIds.map((id) => ({
        algorithm_id: id,
        parameters:
          parallelAlgoParams[id] ??
          Object.fromEntries((algorithms.find((a) => a.id === id)?.parameters ?? []).map((p) => [p.key, p.default])),
      }));
      const runResults = await api.runParallel({ experiment_id: experimentId, source, algorithms: algos });
      runResults.forEach(upsertResult);
      setParallelViewerResultIds(runResults.map((r) => r.id));
    } catch (e: any) {
      setError(e.message ?? "Parallel run failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="panel">
      <div className="panel-header-row">
        <h3>Parallel Algorithm Comparison</h3>
        <label className="checkbox-row">
          <input type="checkbox" checked={syncCameras} onChange={toggleSyncCameras} />
          Sync Cameras
        </label>
      </div>
      <p className="muted small">
        Selected for parallel run: {parallelStepIds.length === 0 ? "none (use \"+ Parallel Set\" in the library)" :
          parallelStepIds.map((id) => algorithms.find((a) => a.id === id)?.name ?? id).join(", ")}
      </p>
      {error && <div className="error-text">{error}</div>}
      <button disabled={busy || parallelStepIds.length === 0} onClick={run}>
        {busy ? "Running…" : "Run Selected Algorithms in Parallel"}
      </button>

      <div className="multi-viewer-grid">
        <ViewerSlot label="Original" experimentId={experimentId} source={source} syncCameras={syncCameras} />
        {parallelViewerResultIds.map((id) => {
          const r = results.find((x) => x.id === id);
          return (
            <ViewerSlot
              key={id}
              label={r?.name ?? id}
              resultId={id}
              syncCameras={syncCameras}
            />
          );
        })}
      </div>
    </div>
  );
}

function ViewerSlot({
  label,
  experimentId,
  source,
  resultId,
  syncCameras,
}: {
  label: string;
  experimentId?: string;
  source?: "original" | "roi";
  resultId?: string;
  syncCameras: boolean;
}) {
  const [points, setPoints] = useState<PointCloudPoints | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const payload = resultId
        ? await api.getResultPoints(resultId)
        : await api.getExperimentPoints(experimentId!, source!);
      if (!cancelled) setPoints(payload);
    })();
    return () => {
      cancelled = true;
    };
  }, [experimentId, source, resultId]);

  const geometry = usePointCloudGeometry(points);

  return <Viewer3D geometry={geometry} label={label} syncCameras={syncCameras} height={320} />;
}
