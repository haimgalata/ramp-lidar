import { useMemo, useState } from "react";
import { api } from "../api/client";
import type { AlgorithmDef } from "../api/types";
import { useAppStore } from "../state/appStore";

interface Props {
  source: "original" | "roi";
  onSingleRunStart?: () => void;
  onSingleRunResult?: (resultId: string) => void;
}

/** Left sidebar: one card per algorithm with editable parameters and three
 * actions -- Run Now (Mode: single), Add to Pipeline (Mode A), Add to
 * Parallel Set (Mode B). */
export default function AlgorithmLibrary({ source, onSingleRunStart, onSingleRunResult }: Props) {
  const algorithms = useAppStore((s) => s.algorithms);
  const experiment = useAppStore((s) => s.experiment);
  const addPipelineStep = useAppStore((s) => s.addPipelineStep);
  const parallelStepIds = useAppStore((s) => s.parallelStepIds);
  const toggleParallelAlgo = useAppStore((s) => s.toggleParallelAlgo);
  const setParallelAlgoParams = useAppStore((s) => s.setParallelAlgoParams);
  const upsertResult = useAppStore((s) => s.upsertResult);

  const [paramState, setParamState] = useState<Record<string, Record<string, number>>>({});
  const [running, setRunning] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const getParams = (algo: AlgorithmDef) =>
    paramState[algo.id] ?? Object.fromEntries(algo.parameters.map((p) => [p.key, p.default]));

  const setParam = (algo: AlgorithmDef, key: string, value: number) => {
    const current = getParams(algo);
    const next = { ...current, [key]: value };
    setParamState((s) => ({ ...s, [algo.id]: next }));
    setParallelAlgoParams(algo.id, next);
  };

  const runNow = async (algo: AlgorithmDef) => {
    if (!experiment) return;
    setError(null);
    setRunning(algo.id);
    onSingleRunStart?.();
    try {
      const result = await api.runSingle({
        experiment_id: experiment.id,
        source,
        algorithm_id: algo.id,
        parameters: getParams(algo),
      });
      upsertResult(result);
      onSingleRunResult?.(result.id);
    } catch (e: any) {
      setError(e.message ?? "Failed to run algorithm");
    } finally {
      setRunning(null);
    }
  };

  return (
    <div className="panel algorithm-library">
      <h3>Algorithm Library</h3>
      {error && <div className="error-text">{error}</div>}
      {algorithms.length === 0 && <div className="muted">Loading algorithms…</div>}
      {algorithms.map((algo) => {
        const params = getParams(algo);
        const inParallel = parallelStepIds.includes(algo.id);
        return (
          <div key={algo.id} className="algo-card">
            <div className="algo-card-header">
              <strong>{algo.name}</strong>
            </div>
            <p className="algo-desc">{algo.description}</p>
            {algo.parameters.map((p) => (
              <label key={p.key} className="param-row">
                <span>{p.label}</span>
                <input
                  type="number"
                  min={p.min}
                  max={p.max}
                  step={p.step}
                  value={params[p.key]}
                  onChange={(e) => setParam(algo, p.key, parseFloat(e.target.value))}
                />
              </label>
            ))}
            <div className="algo-actions">
              <button disabled={!experiment || running === algo.id} onClick={() => runNow(algo)}>
                {running === algo.id ? "Running…" : "Run Now"}
              </button>
              <button
                disabled={!experiment}
                onClick={() => addPipelineStep({ algorithm_id: algo.id, parameters: params })}
              >
                + Pipeline
              </button>
              <button
                disabled={!experiment}
                className={inParallel ? "toggle-on" : ""}
                onClick={() => toggleParallelAlgo(algo.id)}
              >
                {inParallel ? "✓ Parallel Set" : "+ Parallel Set"}
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
