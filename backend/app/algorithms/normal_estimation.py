"""Normal Estimation.

Estimates a per-point surface normal using a local neighborhood (hybrid
KNN + radius search). Does not remove or move any points -- purely adds a
`normals` attribute so downstream viewers/algorithms can use it.
"""
from typing import Dict

from app.algorithms.base import Algorithm, AlgorithmContext, AlgorithmOutput
from app.models.schemas import ParameterSpec


class NormalEstimation(Algorithm):
    id = "normals"
    name = "Normal Estimation"
    description = (
        "Estimates a surface normal at every point from its local neighborhood. "
        "Does not remove points; enables normal-aware inspection/visualization."
    )
    parameters = [
        ParameterSpec(key="radius", label="Search Radius (m)", type="float",
                      default=0.05, min=0.001, max=1.0, step=0.001),
        ParameterSpec(key="max_nn", label="Max Neighbors", type="int",
                      default=30, min=3, max=200, step=1),
    ]

    def process(self, ctx: AlgorithmContext, params: Dict[str, float]) -> AlgorithmOutput:
        import open3d as o3d

        radius = float(params["radius"])
        max_nn = int(params["max_nn"])
        # PointCloud has no explicit copy(); construct a clone via the copy
        # constructor so the input this step reads from is never mutated.
        cloned = type(ctx.cloud)(ctx.cloud)
        cloned.estimate_normals(
            search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=radius, max_nn=max_nn)
        )
        return AlgorithmOutput(
            cloud=cloned,
            intensity=ctx.intensity,
            extra={"points_removed": 0},
        )
