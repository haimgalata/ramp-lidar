"""End-to-end smoke test hitting the real FastAPI app through every major
workflow step described in the product spec (upload -> ROI -> ground truth ->
slope -> single/pipeline/parallel processing -> results table -> export).
"""
import numpy as np
import open3d as o3d
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture
def ramp_ply_file(tmp_path):
    theta_deg = 7.0
    rng = np.random.default_rng(42)
    theta = np.radians(theta_deg)
    n_points = 3000
    x = rng.uniform(0, 2, n_points)
    y = rng.uniform(0, 1, n_points)
    z = x * np.tan(theta) + rng.normal(0, 0.001, n_points)
    ramp = np.stack([x, y, z], axis=1)
    wall = np.stack([
        np.full(100, 2.5),
        rng.uniform(0, 1, 100),
        rng.uniform(0, 1, 100),
    ], axis=1)
    points = np.vstack([ramp, wall])

    cloud = o3d.geometry.PointCloud()
    cloud.points = o3d.utility.Vector3dVector(points)
    path = tmp_path / "ramp.ply"
    o3d.io.write_point_cloud(str(path), cloud)
    return path, theta_deg


def test_full_workflow(ramp_ply_file):
    path, true_theta = ramp_ply_file

    # 1. Create experiment
    exp = client.post("/experiments", json={"name": "Ramp Test 001"}).json()
    exp_id = exp["id"]

    # 2. Upload
    with open(path, "rb") as f:
        r = client.post(f"/experiments/{exp_id}/upload", files={"file": ("ramp.ply", f, "application/octet-stream")})
    assert r.status_code == 200
    exp = r.json()
    assert exp["cloud_info"]["point_count"] == 3100

    # 3. Viz points
    r = client.get(f"/experiments/{exp_id}/points?source=original")
    assert r.status_code == 200
    assert r.json()["full_point_count"] == 3100

    # 4. Set ROI excluding the wall cluster (x in [0, 2])
    r = client.post(f"/experiments/{exp_id}/roi", json={"min": [0, 0, -1], "max": [2, 1, 1]})
    assert r.status_code == 200
    assert r.json()["roi"] is not None

    # 5. Ground truth
    r = client.post(f"/experiments/{exp_id}/ground-truth", json={"slope_deg": true_theta})
    assert r.status_code == 200

    # 6. Analyze slope on ROI
    r = client.post(
        f"/experiments/{exp_id}/analyze-slope",
        json={"source": "roi", "params": {"distance_threshold": 0.01, "num_iterations": 500, "min_inliers": 50}},
    )
    assert r.status_code == 200
    baseline = r.json()
    assert baseline["calculated_slope"] == pytest.approx(true_theta, abs=0.5)
    assert baseline["slope_error"] is not None

    # 7. Run a single algorithm (SOR) on the ROI
    r = client.post(
        "/processing/single",
        json={"experiment_id": exp_id, "source": "roi", "algorithm_id": "sor", "parameters": {}},
    )
    assert r.status_code == 200
    single_result = r.json()
    assert single_result["algorithm_name"] == "Statistical Outlier Removal"
    assert single_result["point_count"] <= 3000

    # 8. Run a pipeline (SOR -> Voxel -> RANSAC)
    r = client.post(
        "/processing/pipeline",
        json={
            "experiment_id": exp_id,
            "source": "roi",
            "steps": [
                {"algorithm_id": "sor", "parameters": {}},
                {"algorithm_id": "voxel", "parameters": {"voxel_size": 0.02}},
                {"algorithm_id": "ransac", "parameters": {"distance_threshold": 0.01}},
            ],
        },
    )
    assert r.status_code == 200
    pipeline_result = r.json()
    assert pipeline_result["calculated_slope"] == pytest.approx(true_theta, abs=1.0)
    result_id = pipeline_result["id"]

    # 9. Run parallel comparison (SOR, ROR, Voxel independently)
    r = client.post(
        "/processing/parallel",
        json={
            "experiment_id": exp_id,
            "source": "roi",
            "algorithms": [
                {"algorithm_id": "sor", "parameters": {}},
                {"algorithm_id": "ror", "parameters": {}},
                {"algorithm_id": "voxel", "parameters": {"voxel_size": 0.02}},
            ],
        },
    )
    assert r.status_code == 200
    assert len(r.json()) == 3

    # 10. Results table includes the baseline + all runs
    r = client.get(f"/experiments/{exp_id}/results")
    assert r.status_code == 200
    all_results = r.json()
    assert len(all_results) >= 1 + 1 + 1 + 3  # baseline + single + pipeline + 3 parallel

    # 11. Result points for viewer
    r = client.get(f"/results/{result_id}/points")
    assert r.status_code == 200
    assert r.json()["full_point_count"] > 0

    # 12. Diff visualization vs original
    r = client.get(f"/results/{result_id}/diff", params={"min_mm": 0, "max_mm": 10})
    assert r.status_code == 200
    diff = r.json()
    assert "bin_counts" in diff

    # 13. Export the pipeline result as PLY
    r = client.post(f"/results/{result_id}/export", json={"format": "ply"})
    assert r.status_code == 200
    assert len(r.content) > 0

    # 14. Export results table as CSV
    r = client.get(f"/experiments/{exp_id}/results/export", params={"format": "csv"})
    assert r.status_code == 200
    assert b"slope_error" in r.content

    # 15. Delete a result
    r = client.delete(f"/results/{single_result['id']}")
    assert r.status_code == 200

    # 16. Clean up experiment
    r = client.delete(f"/experiments/{exp_id}")
    assert r.status_code == 200
