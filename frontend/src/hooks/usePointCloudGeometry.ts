import { useMemo } from "react";
import type { PointCloudPoints } from "../api/types";

export interface PointCloudGeometryData {
  positions: Float32Array;
  colors: Float32Array | null;
  // True only when `colors` came from real per-point RGB data in the API
  // payload, as opposed to the uniform fallback tint used just for
  // rendering. The point inspector uses this to avoid showing a fake RGB
  // value for clouds that don't actually have a color channel.
  hasRealColor: boolean;
  count: number;
  bounds: { min: [number, number, number]; max: [number, number, number] } | null;
}

const DEFAULT_COLOR: [number, number, number] = [0.55, 0.75, 1.0];

/** Converts the flat-array API payload into typed arrays ready for a
 * three.js BufferGeometry, and computes bounds once (used for camera framing
 * and picking-threshold sizing). */
export function usePointCloudGeometry(
  payload: PointCloudPoints | null | undefined,
  fallbackColor: [number, number, number] = DEFAULT_COLOR
): PointCloudGeometryData {
  return useMemo(() => {
    if (!payload || payload.positions.length === 0) {
      return { positions: new Float32Array(0), colors: null, hasRealColor: false, count: 0, bounds: null };
    }
    const positions = Float32Array.from(payload.positions);
    let colors: Float32Array | null = null;
    const hasRealColor = !!(payload.colors && payload.colors.length === payload.positions.length);
    if (hasRealColor) {
      colors = Float32Array.from(payload.colors!);
    } else {
      const count = positions.length / 3;
      colors = new Float32Array(count * 3);
      for (let i = 0; i < count; i++) {
        colors[i * 3] = fallbackColor[0];
        colors[i * 3 + 1] = fallbackColor[1];
        colors[i * 3 + 2] = fallbackColor[2];
      }
    }

    const min: [number, number, number] = [Infinity, Infinity, Infinity];
    const max: [number, number, number] = [-Infinity, -Infinity, -Infinity];
    for (let i = 0; i < positions.length; i += 3) {
      for (let a = 0; a < 3; a++) {
        const v = positions[i + a];
        if (v < min[a]) min[a] = v;
        if (v > max[a]) max[a] = v;
      }
    }

    return { positions, colors, hasRealColor, count: positions.length / 3, bounds: { min, max } };
  }, [payload, fallbackColor]);
}
