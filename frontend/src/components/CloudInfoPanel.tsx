import type { CloudInfo } from "../api/types";

function fmt(n: number | null | undefined, digits = 3): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return n.toFixed(digits);
}

/** Displays the descriptive statistics from spec section 5 (file name,
 * point count, extents, bounding box, density, available attributes). */
export default function CloudInfoPanel({ info }: { info: CloudInfo | null }) {
  if (!info) {
    return (
      <div className="panel">
        <h3>Point Cloud Info</h3>
        <div className="muted">No point cloud loaded yet.</div>
      </div>
    );
  }

  return (
    <div className="panel">
      <h3>Point Cloud Info</h3>
      <div className="kv-grid">
        <span>File</span>
        <span>{info.file_name ?? "—"}</span>
        <span>Format</span>
        <span>{info.file_format?.toUpperCase() ?? "—"}</span>
        <span># Points</span>
        <span>{info.point_count.toLocaleString()}</span>
        <span>X range</span>
        <span>{fmt(info.min_x)} … {fmt(info.max_x)}</span>
        <span>Y range</span>
        <span>{fmt(info.min_y)} … {fmt(info.max_y)}</span>
        <span>Z range</span>
        <span>{fmt(info.min_z)} … {fmt(info.max_z)}</span>
        <span>Width (X)</span>
        <span>{fmt(info.width)} m</span>
        <span>Length (Y)</span>
        <span>{fmt(info.length)} m</span>
        <span>Height range (Z)</span>
        <span>{fmt(info.height_range)} m</span>
        <span>Density</span>
        <span>{info.point_density ? `${fmt(info.point_density, 1)} pts/m²` : "—"}</span>
      </div>
      <div className="attr-badges">
        <span className={`badge ${info.has_color ? "on" : "off"}`}>RGB</span>
        <span className={`badge ${info.has_intensity ? "on" : "off"}`}>Intensity</span>
        <span className={`badge ${info.has_normals ? "on" : "off"}`}>Normals</span>
      </div>
    </div>
  );
}
