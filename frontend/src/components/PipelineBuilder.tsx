import { useState } from "react";
import { api } from "../api/client";
import { useAppStore } from "../state/appStore";

interface Props {
  experimentId: string;
  source: "original" | "roi";
  onResult: (resultId: string) => void;
}

/** Mode A -- Pipeline: sequential algorithm chain with add/remove/reorder and
 * per-step parameter editing (spec section 10). */
export default function PipelineBuilder({ experimentId, source, onResult }: Props) {
  const algorithms = useAppStore((s) => s.algorithms);
  const steps = useAppStore((s) => s.pipelineSteps);
  const removeStep = useAppStore((s) => s.removePipelineStep);
  const moveStep = useAppStore((s) => s.movePipelineStep);
  const updateStepParams = useAppStore((s) => s.updatePipelineStepParams);
  const clearPipeline = useAppStore((s) => s.clearPipeline);
  const upsertResult = useAppStore((s) => s.upsertResult);

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const algoName = (id: string) => algorithms.find((a) => a.id === id)?.name ?? id;
  const algoParams = (id: string) => algorithms.find((a) => a.id === id)?.parameters ?? [];

  const run = async () => {
    if (steps.length === 0) return;
    setBusy(true);
    setError(null);
    try {
      const result = await api.runPipeline({ experiment_id: experimentId, source, steps });
      upsertResult(result);
      onResult(result.id);
    } catch (e: any) {
      setError(e.message ?? "Pipeline run failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="panel">
      <h3>Pipeline Builder</h3>
      <p className="muted small">
        Original {source === "roi" ? "(ROI)" : ""} → {steps.length === 0 ? "…" : steps.map((s) => algoName(s.algorithm_id)).join(" → ")}
      </p>
      {steps.length === 0 && (
        <div className="muted">Add algorithms from the library on the left ("+ Pipeline").</div>
      )}
      <ol className="pipeline-list">
        {steps.map((step, i) => (
          <li key={i} className="pipeline-step">
            <div className="pipeline-step-header">
              <span>
                {i + 1}. {algoName(step.algorithm_id)}
              </span>
              <span className="pipeline-step-controls">
                <button disabled={i === 0} onClick={() => moveStep(i, -1)} title="Move up">
                  ↑
                </button>
                <button disabled={i === steps.length - 1} onClick={() => moveStep(i, 1)} title="Move down">
                  ↓
                </button>
                <button onClick={() => removeStep(i)} title="Remove">
                  ✕
                </button>
              </span>
            </div>
            {algoParams(step.algorithm_id).map((p) => (
              <label key={p.key} className="param-row small">
                <span>{p.label}</span>
                <input
                  type="number"
                  step={p.step}
                  value={step.parameters[p.key] ?? p.default}
                  onChange={(e) =>
                    updateStepParams(i, { ...step.parameters, [p.key]: parseFloat(e.target.value) })
                  }
                />
              </label>
            ))}
          </li>
        ))}
      </ol>
      {error && <div className="error-text">{error}</div>}
      <div className="algo-actions">
        <button disabled={busy || steps.length === 0} onClick={run}>
          {busy ? "Running…" : "Run Pipeline"}
        </button>
        <button disabled={steps.length === 0} onClick={clearPipeline}>
          Clear
        </button>
      </div>
    </div>
  );
}
