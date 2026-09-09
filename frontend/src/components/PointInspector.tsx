import type { PickedPoint } from "../state/appStore";

/** Shows the attributes of the last-clicked point (spec section 4: at
 * minimum XYZ, plus RGB when the cloud has color). */
export default function PointInspector({ point }: { point: PickedPoint | null }) {
  return (
    <div className="panel">
      <h3>Point Inspector</h3>
      {!point ? (
        <div className="muted">Click a point in the viewer to inspect it.</div>
      ) : (
        <div className="kv-grid">
          <span>Source</span>
          <span>{point.sourceLabel}</span>
          <span>X</span>
          <span>{point.x.toFixed(4)}</span>
          <span>Y</span>
          <span>{point.y.toFixed(4)}</span>
          <span>Z</span>
          <span>{point.z.toFixed(4)}</span>
          {point.color && (
            <>
              <span>RGB</span>
              <span className="color-swatch-row">
                <span
                  className="color-swatch"
                  style={{
                    background: `rgb(${Math.round(point.color[0] * 255)}, ${Math.round(
                      point.color[1] * 255
                    )}, ${Math.round(point.color[2] * 255)})`,
                  }}
                />
                {point.color.map((c) => c.toFixed(2)).join(", ")}
              </span>
            </>
          )}
        </div>
      )}
    </div>
  );
}
