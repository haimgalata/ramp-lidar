"""Point cloud file I/O and format-agnostic helpers.

Open3D's readers/writers work off file paths, so uploaded bytes are written
to a short-lived temp file purely to satisfy that API -- this is NOT the
"exported result file" concept from the product spec (see app/core/store.py
docstring); the temp file is deleted immediately after parsing and nothing
here is ever written as a side effect of running an algorithm.
"""
import os
import tempfile
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np
import open3d as o3d

from app.models.schemas import BoundingBox, CloudInfo, PointCloudPoints
from app.utils.logging import get_logger

logger = get_logger(__name__)

SUPPORTED_FORMATS = {".ply", ".pcd"}


@dataclass
class LoadedCloud:
    cloud: o3d.geometry.PointCloud
    intensity: Optional[np.ndarray]
    file_format: str


def load_point_cloud(raw_bytes: bytes, file_name: str) -> LoadedCloud:
    """Parses uploaded PLY/PCD bytes into an Open3D PointCloud (+ intensity
    if the file provides it). Raises ValueError on unsupported formats or
    empty clouds.
    """
    ext = os.path.splitext(file_name)[1].lower()
    if ext not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported file format '{ext}'. Supported: {sorted(SUPPORTED_FORMATS)}")

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(raw_bytes)
            tmp_path = tmp.name

        cloud = o3d.io.read_point_cloud(tmp_path)
        if len(cloud.points) == 0:
            raise ValueError("Point cloud is empty or could not be parsed")

        intensity = _try_read_intensity(tmp_path, expected_count=len(cloud.points))
        return LoadedCloud(cloud=cloud, intensity=intensity, file_format=ext.lstrip("."))
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


def _try_read_intensity(path: str, expected_count: int) -> Optional[np.ndarray]:
    """Best-effort extraction of a per-point 'intensity' scalar field, common
    in PCD scans, via Open3D's tensor-based reader. Returns None if absent or
    unreadable -- intensity is an optional, format-dependent attribute.
    """
    try:
        t_cloud = o3d.t.io.read_point_cloud(path)
        if "intensity" in t_cloud.point:
            values = t_cloud.point["intensity"].numpy().reshape(-1).astype(float)
            if len(values) == expected_count:
                return values
    except Exception as exc:  # pragma: no cover - defensive, format dependent
        logger.debug("No intensity field readable from %s: %s", path, exc)
    return None


def save_point_cloud(cloud: o3d.geometry.PointCloud, file_format: str) -> bytes:
    """Writes a cloud to bytes in the given format ('ply' or 'pcd'). This is
    the ONLY place in the app that produces a downloadable file, and it is
    only ever invoked from the explicit /results/{id}/export endpoint.
    """
    ext = f".{file_format.lower()}"
    if ext not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported export format '{file_format}'")

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp_path = tmp.name
        o3d.io.write_point_cloud(tmp_path, cloud, write_ascii=False)
        with open(tmp_path, "rb") as f:
            return f.read()
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


def compute_cloud_info(
    cloud: o3d.geometry.PointCloud,
    file_name: Optional[str] = None,
    file_format: Optional[str] = None,
) -> CloudInfo:
    points = np.asarray(cloud.points)
    mins = points.min(axis=0)
    maxs = points.max(axis=0)
    width = float(maxs[0] - mins[0])
    length = float(maxs[1] - mins[1])
    height_range = float(maxs[2] - mins[2])

    footprint_area = width * length
    density = (len(points) / footprint_area) if footprint_area > 1e-9 else None

    return CloudInfo(
        file_name=file_name,
        file_format=file_format,
        point_count=len(points),
        min_x=float(mins[0]), max_x=float(maxs[0]),
        min_y=float(mins[1]), max_y=float(maxs[1]),
        min_z=float(mins[2]), max_z=float(maxs[2]),
        width=width, length=length, height_range=height_range,
        bounding_box=BoundingBox(min=mins.tolist(), max=maxs.tolist()),
        has_color=cloud.has_colors(),
        has_intensity=False,  # overridden by caller when intensity array is known
        has_normals=cloud.has_normals(),
        point_density=density,
    )


def crop_to_roi(
    cloud: o3d.geometry.PointCloud,
    roi_min: Tuple[float, float, float],
    roi_max: Tuple[float, float, float],
    intensity: Optional[np.ndarray] = None,
) -> Tuple[o3d.geometry.PointCloud, Optional[np.ndarray]]:
    """Crops a cloud to an axis-aligned bounding box. This never mutates the
    input cloud -- it builds a new PointCloud from a boolean mask, which is
    the "derived selection" the ROI spec calls for.
    """
    points = np.asarray(cloud.points)
    mask = np.all((points >= np.array(roi_min)) & (points <= np.array(roi_max)), axis=1)
    indices = np.where(mask)[0].tolist()
    cropped = cloud.select_by_index(indices)
    cropped_intensity = intensity[mask] if intensity is not None else None
    return cropped, cropped_intensity


def build_points_payload(
    cloud: o3d.geometry.PointCloud,
    max_points: int,
    highlight_color: Optional[Tuple[float, float, float]] = None,
) -> PointCloudPoints:
    """Builds the flat-array JSON payload sent to the frontend viewer.

    This is the "Visualization Resolution" referenced in the spec: if the
    cloud has more points than `max_points`, a random subsample is sent to
    the browser purely for rendering, while every backend calculation always
    runs on the full-resolution cloud (never on this subsample).
    """
    points = np.asarray(cloud.points)
    full_count = points.shape[0]

    if full_count > max_points:
        rng = np.random.default_rng(seed=42)  # deterministic subsample per session
        idx = rng.choice(full_count, size=max_points, replace=False)
        idx.sort()
        subsampled = True
    else:
        idx = np.arange(full_count)
        subsampled = False

    sent_points = points[idx]

    colors_flat = None
    if highlight_color is not None:
        colors = np.tile(np.array(highlight_color), (len(idx), 1))
        colors_flat = colors.astype(np.float32).ravel().tolist()
    elif cloud.has_colors():
        colors = np.asarray(cloud.colors)[idx]
        colors_flat = colors.astype(np.float32).ravel().tolist()

    return PointCloudPoints(
        positions=sent_points.astype(np.float32).ravel().tolist(),
        colors=colors_flat,
        full_point_count=full_count,
        sent_point_count=len(idx),
        subsampled=subsampled,
    )
