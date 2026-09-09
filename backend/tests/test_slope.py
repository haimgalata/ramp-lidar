"""Unit tests for plane fitting / slope geometry (app/services/slope.py)."""
import numpy as np
import open3d as o3d
import pytest

from app.services.slope import fit_plane_and_slope, point_to_plane_distances, slope_deg_from_normal


def test_slope_from_normal_horizontal_plane():
    # Normal straight up -> perfectly flat surface -> 0 degrees.
    assert slope_deg_from_normal(0, 0, 1) == pytest.approx(0.0, abs=1e-9)


def test_slope_from_normal_vertical_plane():
    # Normal lying flat in XY -> vertical wall -> 90 degrees.
    assert slope_deg_from_normal(1, 0, 0) == pytest.approx(90.0, abs=1e-9)


def test_slope_from_normal_sign_independent():
    # A downward-pointing normal should give the same slope as an upward one.
    assert slope_deg_from_normal(0, 0, -1) == pytest.approx(0.0, abs=1e-9)


def test_slope_from_normal_known_angle():
    theta = np.radians(7.0)
    a, b, c = np.sin(theta), 0.0, -np.cos(theta)
    assert slope_deg_from_normal(a, b, c) == pytest.approx(7.0, abs=1e-6)


def test_point_to_plane_distances_zero_on_plane():
    # Points on z = 0 plane (A=0,B=0,C=1,D=0) have zero distance.
    points = np.array([[1.0, 2.0, 0.0], [3.0, -1.0, 0.0]])
    dist = point_to_plane_distances(points, 0, 0, 1, 0)
    assert np.allclose(dist, 0.0)


def _make_tilted_ramp_cloud(theta_deg: float, n_points: int = 2000, noise_std: float = 0.001,
                             n_outliers: int = 50, seed: int = 0) -> o3d.geometry.PointCloud:
    """Builds a synthetic ramp: a tilted plane with small Gaussian noise plus
    a handful of outlier points well off the plane (simulating a wall/railing)."""
    rng = np.random.default_rng(seed)
    theta = np.radians(theta_deg)

    x = rng.uniform(-1.0, 1.0, n_points)
    y = rng.uniform(-1.0, 1.0, n_points)
    z = x * np.tan(theta) + rng.normal(0, noise_std, n_points)
    plane_points = np.stack([x, y, z], axis=1)

    outliers = rng.uniform(-1.0, 1.0, (n_outliers, 3))
    outliers[:, 2] += 0.5  # push well off the ramp plane

    all_points = np.vstack([plane_points, outliers])
    cloud = o3d.geometry.PointCloud()
    cloud.points = o3d.utility.Vector3dVector(all_points)
    return cloud


@pytest.mark.parametrize("theta_deg", [0.0, 7.0, 15.0, 30.0])
def test_fit_plane_and_slope_recovers_known_angle(theta_deg):
    cloud = _make_tilted_ramp_cloud(theta_deg)
    result = fit_plane_and_slope(cloud, distance_threshold=0.01, num_iterations=500)
    assert result.slope_deg == pytest.approx(theta_deg, abs=0.5)
    # RANSAC should reject the injected outliers as outliers.
    assert result.outlier_count >= 40
    assert result.rmse < 0.01


def test_fit_plane_requires_minimum_points():
    cloud = o3d.geometry.PointCloud()
    cloud.points = o3d.utility.Vector3dVector(np.array([[0, 0, 0], [1, 0, 0]]))
    with pytest.raises(ValueError):
        fit_plane_and_slope(cloud, 0.01, 100)
