"""Neighbor-Average Smoothing.

A simple, fast smoothing filter: each point is moved to the centroid of its
`k_neighbors` nearest neighbors (including itself), repeated `iterations`
times. This is a basic Laplacian-style smoothing -- not a full Moving-Least-
-Squares surface reconstruction -- chosen deliberately to keep behavior easy
to reason about and fast on ramp-sized clouds.
"""
from typing import Dict

import numpy as np
import open3d as o3d

from app.algorithms.base import Algorithm, AlgorithmContext, AlgorithmOutput
from app.models.schemas import ParameterSpec


class NeighborAverageSmoothing(Algorithm):
    id = "smooth"
    name = "Neighbor-Average Smoothing"
    description = (
        "Moves each point toward the centroid of its nearest neighbors to reduce "
        "high-frequency surface noise (simple Laplacian-style smoothing)."
    )
    parameters = [
        ParameterSpec(key="k_neighbors", label="Neighbors (k)", type="int",
                      default=8, min=3, max=50, step=1),
        ParameterSpec(key="iterations", label="Iterations", type="int",
                      default=1, min=1, max=10, step=1),
    ]

    def process(self, ctx: AlgorithmContext, params: Dict[str, float]) -> AlgorithmOutput:
        k = int(params["k_neighbors"])
        iterations = int(params["iterations"])

        points = np.asarray(ctx.cloud.points).copy()
        n = points.shape[0]
        if n == 0:
            return AlgorithmOutput(cloud=o3d.geometry.PointCloud(), intensity=ctx.intensity,
                                    extra={"points_removed": 0})

        k_eff = min(k, n - 1) if n > 1 else 0
        for _ in range(iterations):
            working = o3d.geometry.PointCloud()
            working.points = o3d.utility.Vector3dVector(points)
            tree = o3d.geometry.KDTreeFlann(working)
            smoothed = np.empty_like(points)
            for i in range(n):
                if k_eff == 0:
                    smoothed[i] = points[i]
                    continue
                _, idx, _ = tree.search_knn_vector_3d(points[i], k_eff + 1)
                smoothed[i] = points[np.asarray(idx)].mean(axis=0)
            points = smoothed

        new_cloud = type(ctx.cloud)(ctx.cloud)
        new_cloud.points = o3d.utility.Vector3dVector(points)
        return AlgorithmOutput(
            cloud=new_cloud,
            intensity=ctx.intensity,
            extra={"points_removed": 0},
        )
