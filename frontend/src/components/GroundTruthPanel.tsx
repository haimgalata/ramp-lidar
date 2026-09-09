import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Experiment } from "../api/types";

interface Props {
  experiment: Experiment;
  onUpdated: (e: Experiment) => void;
}

/** Manual Ground Truth entry (spec section 8). Every result's error and
 * improvement percentage are computed against this value on the backend. */
export default function GroundTruthPanel({ experiment, onUpdated }: Props) {
  const [value, setValue] = useState<string>(experiment.ground_truth_slope_deg?.toString() ?? "");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setValue(experiment.ground_truth_slope_deg?.toString() ?? "");
  }, [experiment.ground_truth_slope_deg]);

  const save = async () => {
    const parsed = parseFloat(value);
    if (Number.isNaN(parsed)) return;
    setBusy(true);
    try {
      const exp = await api.setGroundTruth(experiment.id, parsed);
      onUpdated(exp);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="panel">
      <h3>Ground Truth Slope</h3>
      <p className="muted small">Enter the manually-measured ramp slope for accuracy comparison.</p>
      <div className="param-row">
        <span>Ground Truth (°)</span>
        <input
          type="number"
          step={0.01}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="e.g. 7.00"
        />
      </div>
      <button disabled={busy} onClick={save}>
        Save Ground Truth
      </button>
    </div>
  );
}
