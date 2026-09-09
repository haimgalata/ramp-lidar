"""Smoke tests for each algorithm module: every algorithm should run without
error on a synthetic ramp-like cloud and behave sensibly (removes outliers,
reduces point count, etc.)."""
import numpy as np
import open3d as o3d
import pytest

from app.algorithms.base import AlgorithmContext
from app.algorithms.normal_estimation import NormalEstimation
from app.algorithms.radius_outlier import RadiusOutlierRemoval
from app.algorithms.ransac_plane import RansacPlaneFit
from app.algorithms.smoothing import NeighborAverageSmoothing
from app.algorithms.statistical_outlier import StatisticalOutlierRemoval
from app.algorithms.voxel_downsample import VoxelDownsample


def _synthetic_cloud_with_outliers(n_points=1000, n_outliers=30, seed=1):
    rng = np.random.default_rng(seed)
    plane = np.stack([
        rng.uniform(-1, 1, n_points),
        rng.uniform(-1, 1, n_points),
        rng.normal(0, 0.002, n_points),
    ], axis=1)
    outliers = rng.uniform(-1, 1, (n_outliers, 3))
    outliers[:, 2] += rng.uniform(0.3, 1.0, n_outliers)
    points = np.vstack([plane, outliers])
    cloud = o3d.geometry.PointCloud()
    cloud.points = o3d.utility.Vector3dVector(points)
    return cloud, n_points, n_outliers


def test_statistical_outlier_removal_reduces_points():
    cloud, n_plane, n_out = _synthetic_cloud_with_outliers()
    algo = StatisticalOutlierRemoval()
    out = algo.process(AlgorithmContext(cloud=cloud), algo.default_parameters())
    assert 0 < len(out.cloud.points) < len(cloud.points)


def test_radius_outlier_removal_reduces_points():
    cloud, n_plane, n_out = _synthetic_cloud_with_outliers()
    algo = RadiusOutlierRemoval()
    out = algo.process(AlgorithmContext(cloud=cloud), algo.default_parameters())
    assert 0 < len(out.cloud.points) < len(cloud.points)


def test_voxel_downsample_reduces_points_and_drops_intensity():
    cloud, n_plane, n_out = _synthetic_cloud_with_outliers()
    intensity = np.ones(len(cloud.points))
    algo = VoxelDownsample()
    params = algo.default_parameters()
    params["voxel_size"] = 0.2
    out = algo.process(AlgorithmContext(cloud=cloud, intensity=intensity), params)
    assert len(out.cloud.points) < len(cloud.points)
    assert out.intensity is None  # documented limitation


def test_ransac_plane_fit_keeps_only_inliers():
    cloud, n_plane, n_out = _synthetic_cloud_with_outliers()
    algo = RansacPlaneFit()
    params = algo.default_parameters()
    params["distance_threshold"] = 0.01
    out = algo.process(AlgorithmContext(cloud=cloud), params)
    # Should keep roughly the plane points and drop most/all outliers.
    assert len(out.cloud.points) <= len(cloud.points)
    assert len(out.cloud.points) >= n_plane * 0.9
    assert "calculated_slope" in out.extra
    assert out.extra["calculated_slope"] == pytest.approx(0.0, abs=1.0)


def test_normal_estimation_adds_normals_without_changing_point_count():
    cloud, _, _ = _synthetic_cloud_with_outliers()
    algo = NormalEstimation()
    out = algo.process(AlgorithmContext(cloud=cloud), algo.default_parameters())
    assert len(out.cloud.points) == len(cloud.points)
    assert out.cloud.has_normals()


def test_smoothing_preserves_point_count():
    cloud, _, _ = _synthetic_cloud_with_outliers()
    algo = NeighborAverageSmoothing()
    params = algo.default_parameters()
    params["iterations"] = 1
    out = algo.process(AlgorithmContext(cloud=cloud), params)
    assert len(out.cloud.points) == len(cloud.points)
