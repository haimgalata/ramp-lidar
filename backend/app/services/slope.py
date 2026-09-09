"""Ramp slope calculation via RANSAC plane fitting.

Geometry recap
---------------
A plane is defined by:               A*x + B*y + C*z + D = 0
Its unit normal vector is:           n = (A, B, C) / ||(A, B, C)||

The "slope" of a ramp is the tilt of its surface plane relative to the
horizontal (world XY) plane. A perfectly flat/horizontal surface has a
normal pointing straight up, n = (0, 0, 1) -- slope 0 degrees. A vertical
wall has a normal lying in the XY plane (C = 0) -- slope 90 degrees.

The angle between the plane's normal and the world "up" vector (0, 0, 1)
therefore *is* the slope of the surface:

    slope_deg = arccos( |C| / ||n|| )

`|C|` (absolute value) is used because Open3D's RANSAC may return a normal
pointing up or down depending on point order -- the ramp's tilt is the same
either way.

Point-to-plane distance for a point p = (x, y, z) is:

    distance(p) = |A*x + B*y + C*z + D| / ||n||

which is used both to select RANSAC inliers/outliers and to report fit
quality (RMSE, mean distance) for the UI.
"""
from dataclasses import dataclass
from typing import List

import numpy as np
import open3d as o3d


@dataclass
class SlopeCalculation:
    slope_deg: float
    a: float
    b: float
    c: float
    d: float
    normal: List[float]
    inlier_indices: List[int]
    outlier_indices: List[int]
    inlier_count: int
    outlier_count: int
    rmse: float
    mean_distance: float


def slope_deg_from_normal(a: float, b: float, c: float) -> float:
    """Angle (degrees) between a plane's normal (a, b, c) and the world
    vertical axis -- i.e. how tilted the plane is relative to horizontal."""
    norm = float(np.sqrt(a * a + b * b + c * c))
    if norm == 0.0:
        raise ValueError("Degenerate plane normal (0, 0, 0)")
    cos_angle = abs(c) / norm
    # Guard against floating point drift pushing slightly outside [-1, 1].
    cos_angle = max(-1.0, min(1.0, cos_angle))
    return float(np.degrees(np.arccos(cos_angle)))


def point_to_plane_distances(points: np.ndarray, a: float, b: float, c: float, d: float) -> np.ndarray:
    """Perpendicular distance of each point to the plane A x + B y + C z + D = 0."""
    norm = float(np.sqrt(a * a + b * b + c * c))
    return np.abs(points @ np.array([a, b, c]) + d) / norm


def fit_plane_and_slope(
    cloud: o3d.geometry.PointCloud,
    distance_threshold: float,
    num_iterations: int,
) -> SlopeCalculation:
    """Fit the dominant plane in `cloud` with RANSAC and derive the ramp slope.

    Raises ValueError if the cloud has fewer than 3 points (cannot define a plane).
    """
    n_points = len(cloud.points)
    if n_points < 3:
        raise ValueError("Need at least 3 points to fit a plane")

    plane_model, inliers = cloud.segment_plane(
        distance_threshold=distance_threshold,
        ransac_n=3,
        num_iterations=num_iterations,
    )
    a, b, c, d = plane_model
    slope_deg = slope_deg_from_normal(a, b, c)

    all_indices = np.arange(n_points)
    inlier_mask = np.zeros(n_points, dtype=bool)
    inlier_mask[np.asarray(inliers, dtype=int)] = True
    outlier_indices = all_indices[~inlier_mask].tolist()

    points = np.asarray(cloud.points)
    inlier_points = points[inlier_mask]
    distances = point_to_plane_distances(inlier_points, a, b, c, d)
    rmse = float(np.sqrt(np.mean(distances ** 2))) if len(distances) else 0.0
    mean_distance = float(np.mean(distances)) if len(distances) else 0.0

    norm = float(np.sqrt(a * a + b * b + c * c))
    normal = [a / norm, b / norm, c / norm]

    return SlopeCalculation(
        slope_deg=slope_deg,
        a=float(a), b=float(b), c=float(c), d=float(d),
        normal=normal,
        inlier_indices=np.asarray(inliers, dtype=int).tolist(),
        outlier_indices=outlier_indices,
        inlier_count=int(inlier_mask.sum()),
        outlier_count=int((~inlier_mask).sum()),
        rmse=rmse,
        mean_distance=mean_distance,
    )
