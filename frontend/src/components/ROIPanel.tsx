import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { CloudInfo, Experiment } from "../api/types";
import { useAppStore } from "../state/appStore";

interface Props {
  experiment: Experiment;
  cloudInfo: CloudInfo | null;
  onUpdated: (e: Experiment) => void;
}

/** Simple, reliable ROI mechanism (spec section 6): an axis-aligned bounding
 * box defined by numeric min/max per axis. The box renders live in the 3D
 * viewer (see roiDraft in appStore) so the user gets visual feedback while
 * typing, and "Apply ROI" is what actually creates the derived selection
 * server-side (the original cloud is never modified). */
export default function ROIPanel({ experiment, cloudInfo, onUpdated }: Props) {
  const roiDraft = useAppStore((s) => s.roiDraft);
  const setRoiDraft = useAppStore((s) => s.setRoiDraft);
  const showRoiBox = useAppStore((s) => s.showRoiBox);
  const toggleShowRoiBox = useAppStore((s) => s.toggleShowRoiBox);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!roiDraft && cloudInfo) {
      setRoiDraft({
        min: [cloudInfo.min_x, cloudInfo.min_y, cloudInfo.min_z],
        max: [cloudInfo.max_x, cloudInfo.max_y, cloudInfo.max_z],
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cloudInfo]);

  if (!cloudInfo || !roiDraft) {
    return (
      <div className="panel">
        <h3>Region of Interest</h3>
        <div className="muted">Upload a cloud first.</div>
      </div>
    );
  }

  const setVal = (bound: "min" | "max", axis: 0 | 1 | 2, value: number) => {
    const next = { ...roiDraft, [bound]: [...roiDraft[bound]] as [number, number, number] };
    next[bound][axis] = value;
    setRoiDraft(next);
  };

  const apply = async () => {
    setBusy(true);
    setError(null);
    try {
      const exp = await api.setRoi(experiment.id, roiDraft.min, roiDraft.max);
      onUpdated(exp);
    } catch (e: any) {
      setError(e.message ?? "Failed to set ROI");
    } finally {
      setBusy(false);
    }
  };

  const resetToFull = () => {
    setRoiDraft({
      min: [cloudInfo.min_x, cloudInfo.min_y, cloudInfo.min_z],
      max: [cloudInfo.max_x, cloudInfo.max_y, cloudInfo.max_z],
    });
  };

  const clear = async () => {
    setBusy(true);
    try {
      const exp = await api.clearRoi(experiment.id);
      onUpdated(exp);
    } finally {
      setBusy(false);
    }
  };

  const axisLabels = ["X", "Y", "Z"] as const;

  return (
    <div className="panel">
      <h3>Region of Interest</h3>
      <p className="muted small">
        Select the ramp surface only (exclude walls, railings, floor, people…) with a bounding box.
      </p>
      <table className="roi-table">
        <thead>
          <tr>
            <th></th>
            <th>Min</th>
            <th>Max</th>
          </tr>
        </thead>
        <tbody>
          {axisLabels.map((label, axis) => (
            <tr key={label}>
              <td>{label}</td>
              <td>
                <input
                  type="number"
                  step={0.01}
                  value={roiDraft.min[axis]}
                  onChange={(e) => setVal("min", axis as 0 | 1 | 2, parseFloat(e.target.value))}
                />
              </td>
              <td>
                <input
                  type="number"
                  step={0.01}
                  value={roiDraft.max[axis]}
                  onChange={(e) => setVal("max", axis as 0 | 1 | 2, parseFloat(e.target.value))}
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {error && <div className="error-text">{error}</div>}
      <div className="algo-actions">
        <button disabled={busy} onClick={apply}>
          Apply ROI
        </button>
        <button disabled={busy} onClick={resetToFull}>
          Reset Box
        </button>
        <button disabled={busy || !experiment.roi} onClick={clear}>
          Clear ROI
        </button>
      </div>
      <label className="checkbox-row">
        <input type="checkbox" checked={showRoiBox} onChange={toggleShowRoiBox} />
        Show ROI box in viewer
      </label>
      {experiment.roi && <div className="muted small">ROI active — analysis and processing default to the ROI selection.</div>}
    </div>
  );
}
