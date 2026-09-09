import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { PointCloudPoints } from "../api/types";
import { usePointCloudGeometry } from "../hooks/usePointCloudGeometry";
import Viewer3D from "./Viewer3D";

interface Props {
  experimentId: string;
  source: "original" | "roi";
  resultId: string | null;
}

/** Before/After view for Pipeline Mode (spec section 13): side-by-side by
 * default, with an Overlay mode that renders both clouds in one viewer using
 * distinct colors so the shift is visible directly. */
export default function BeforeAfterViewer({ experimentId, source, resultId }: Props) {
  const [beforePoints, setBeforePoints] = useState<PointCloudPoints | null>(null);
  const [afterPoints, setAfterPoints] = useState<PointCloudPoints | null>(null);
  const [overlay, setOverlay] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api.getExperimentPoints(experimentId, source).then((p) => !cancelled && setBeforePoints(p));
    return () => {
      cancelled = true;
    };
  }, [experimentId, source]);

  useEffect(() => {
    if (!resultId) {
      setAfterPoints(null);
      return;
    }
    let cancelled = false;
    api.getResultPoints(resultId).then((p) => !cancelled && setAfterPoints(p));
    return () => {
      cancelled = true;
    };
  }, [resultId]);

  const beforeGeom = usePointCloudGeometry(beforePoints, [0.4, 0.55, 0.95]);
  const afterGeom = usePointCloudGeometry(afterPoints, [0.95, 0.45, 0.25]);

  const overlayGeom = {
    positions: Float32Array.from([...beforeGeom.positions, ...afterGeom.positions]),
    colors: Float32Array.from([...(beforeGeom.colors ?? []), ...(afterGeom.colors ?? [])]),
    // These are the deliberate before/after tint colors, not real per-point
    // RGB, but overlay mode isn't used with point-picking so this is inert.
    hasRealColor: true,
    count: beforeGeom.count + afterGeom.count,
    bounds: beforeGeom.bounds ?? afterGeom.bounds,
  };

  if (!resultId) {
    return (
      <div className="panel">
        <h3>Before / After</h3>
        <div className="muted">Run a pipeline to compare its result against the original cloud.</div>
      </div>
    );
  }

  return (
    <div className="panel">
      <div className="panel-header-row">
        <h3>Before / After</h3>
        <label className="checkbox-row">
          <input type="checkbox" checked={overlay} onChange={(e) => setOverlay(e.target.checked)} />
          Overlay mode
        </label>
      </div>
      {overlay ? (
        <Viewer3D geometry={overlayGeom} label="Overlay (blue=original, orange=processed)" height={420} />
      ) : (
        <div className="side-by-side">
          <Viewer3D geometry={beforeGeom} label="Original" height={380} />
          <Viewer3D geometry={afterGeom} label="Processed" height={380} />
        </div>
      )}
    </div>
  );
}
