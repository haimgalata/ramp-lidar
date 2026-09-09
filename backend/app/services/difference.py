"""Cloud-to-cloud difference visualization.

For every point in the "source" cloud, we find the distance to its nearest
neighbor in the "target" cloud (Open3D's compute_point_cloud_distance --
effectively a one-directional Cloud-to-Cloud / Hausdorff-style distance).
Distances are converted to millimetres and mapped onto a blue -> green ->
yellow -> red gradient between `min_mm` and `max_mm`, so the user can see at
a glance where processing changed the cloud the most.
"""
from dataclasses import dataclass
from typing import List, Tuple

import numpy as np
import open3d as o3d

# Fixed illustrative bins from the product spec, reported alongside the
# continuous gradient so the legend can show both a scale and concrete counts.
LEGEND_BINS_MM = [
    (0.0, 2.0, "small (0-2mm)"),
    (2.0, 5.0, "medium (2-5mm)"),
    (5.0, 10.0, "large (5-10mm)"),
    (10.0, float("inf"), "significant (>10mm)"),
]


@dataclass
class DiffPayload:
    positions: List[float]
    colors: List[float]
    distances_mm: List[float]
    point_count: int
    mean_distance_mm: float
    max_distance_mm: float
    min_mm: float
    max_mm: float
    bin_counts: List[dict]


def _gradient_color(t: float) -> Tuple[float, float, float]:
    """Maps t in [0, 1] to a blue -> green -> yellow -> red gradient."""
    t = max(0.0, min(1.0, t))
    stops = [
        (0.0, (0.10, 0.25, 0.90)),
        (0.33, (0.10, 0.75, 0.35)),
        (0.66, (0.95, 0.85, 0.10)),
        (1.0, (0.90, 0.15, 0.10)),
    ]
    for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
        if t0 <= t <= t1:
            local = (t - t0) / (t1 - t0) if t1 > t0 else 0.0
            return tuple(c0[i] + (c1[i] - c0[i]) * local for i in range(3))
    return stops[-1][1]


def compute_diff_payload(
    source_cloud: o3d.geometry.PointCloud,
    target_cloud: o3d.geometry.PointCloud,
    min_mm: float,
    max_mm: float,
    max_points: int,
) -> DiffPayload:
    distances_m = np.asarray(source_cloud.compute_point_cloud_distance(target_cloud))
    distances_mm = distances_m * 1000.0

    points = np.asarray(source_cloud.points)
    full_count = points.shape[0]
    if full_count > max_points:
        rng = np.random.default_rng(seed=42)
        idx = rng.choice(full_count, size=max_points, replace=False)
        idx.sort()
    else:
        idx = np.arange(full_count)

    sent_points = points[idx]
    sent_dist = distances_mm[idx]

    span = max(max_mm - min_mm, 1e-9)
    t_values = (sent_dist - min_mm) / span
    colors = np.array([_gradient_color(t) for t in t_values], dtype=np.float32)

    bin_counts = []
    for lo, hi, label in LEGEND_BINS_MM:
        count = int(np.sum((distances_mm >= lo) & (distances_mm < hi)))
        bin_counts.append({"label": label, "min_mm": lo, "max_mm": (hi if hi != float("inf") else None), "count": count})

    return DiffPayload(
        positions=sent_points.astype(np.float32).ravel().tolist(),
        colors=colors.ravel().tolist(),
        distances_mm=sent_dist.astype(np.float32).tolist(),
        point_count=len(idx),
        mean_distance_mm=float(np.mean(distances_mm)) if full_count else 0.0,
        max_distance_mm=float(np.max(distances_mm)) if full_count else 0.0,
        min_mm=min_mm,
        max_mm=max_mm,
        bin_counts=bin_counts,
    )
