"""Generates a synthetic ramp point cloud (PLY) for trying out the app without
needing a real LiDAR scan.

Produces a ~7 degree ramp surface plus a side wall, a railing, and some sensor
noise/outliers -- so the ROI selection and outlier-removal algorithms in the
app actually have something to do.

Usage (from the sample_data/ directory, with the backend venv active):
    python generate_sample_ramp.py
"""
import numpy as np
import open3d as o3d

RNG = np.random.default_rng(7)
TRUE_SLOPE_DEG = 7.0


def make_ramp_surface(n=15000):
    theta = np.radians(TRUE_SLOPE_DEG)
    x = RNG.uniform(0, 3.0, n)          # ramp runs 3m along X
    y = RNG.uniform(0, 1.2, n)          # 1.2m wide
    z = x * np.tan(theta) + RNG.normal(0, 0.003, n)  # small sensor noise
    colors = np.tile([0.55, 0.55, 0.58], (n, 1)) + RNG.normal(0, 0.02, (n, 3))
    return x, y, z, colors


def make_side_wall(n=4000):
    # A vertical wall running alongside the ramp at y = 1.2
    x = RNG.uniform(0, 3.0, n)
    z = RNG.uniform(0, 1.0, n)
    y = np.full(n, 1.2) + RNG.normal(0, 0.005, n)
    colors = np.tile([0.35, 0.4, 0.45], (n, 1))
    return x, y, z, colors


def make_railing(n=1500):
    # A thin railing above the ramp edge (y ~= 1.25, z offset above the surface)
    theta = np.radians(TRUE_SLOPE_DEG)
    x = RNG.uniform(0, 3.0, n)
    z = x * np.tan(theta) + 0.9 + RNG.normal(0, 0.01, n)
    y = np.full(n, 1.25) + RNG.normal(0, 0.01, n)
    colors = np.tile([0.6, 0.5, 0.3], (n, 1))
    return x, y, z, colors


def make_noise_outliers(n=200):
    x = RNG.uniform(-0.3, 3.3, n)
    y = RNG.uniform(-0.3, 1.5, n)
    z = RNG.uniform(-0.3, 1.5, n)
    colors = RNG.uniform(0, 1, (n, 3))
    return x, y, z, colors


def main():
    parts = [make_ramp_surface(), make_side_wall(), make_railing(), make_noise_outliers()]
    xs = np.concatenate([p[0] for p in parts])
    ys = np.concatenate([p[1] for p in parts])
    zs = np.concatenate([p[2] for p in parts])
    colors = np.clip(np.concatenate([p[3] for p in parts]), 0, 1)

    points = np.stack([xs, ys, zs], axis=1)
    cloud = o3d.geometry.PointCloud()
    cloud.points = o3d.utility.Vector3dVector(points)
    cloud.colors = o3d.utility.Vector3dVector(colors)

    out_path = "ramp_sample.ply"
    o3d.io.write_point_cloud(out_path, cloud)
    print(f"Wrote {len(points)} points to {out_path}")
    print(f"True ramp slope used to generate this file: {TRUE_SLOPE_DEG} degrees")
    print("Suggested ROI (excludes wall/railing/outliers): X[0,3] Y[0,1.15] Z[-1,1.2]")


if __name__ == "__main__":
    main()
