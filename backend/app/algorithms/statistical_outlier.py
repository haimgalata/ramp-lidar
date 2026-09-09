"""Statistical Outlier Removal (SOR).

For each point, Open3D computes the mean distance to its `nb_neighbors`
nearest neighbors. Points whose mean distance is further than
`mean + std_ratio * std_dev` (over the whole cloud) are removed as outliers
(typically stray/noisy points, e.g. sensor noise around the ramp edges).
"""
from typing import Dict

from app.algorithms.base import Algorithm, AlgorithmContext, AlgorithmOutput
from app.models.schemas import ParameterSpec


class StatisticalOutlierRemoval(Algorithm):
    id = "sor"
    name = "Statistical Outlier Removal"
    description = (
        "Removes points whose average distance to their nearest neighbors is "
        "statistically far from the cloud's mean (good for scattered sensor noise)."
    )
    parameters = [
        ParameterSpec(key="nb_neighbors", label="Number of Neighbors", type="int",
                      default=20, min=1, max=200, step=1),
        ParameterSpec(key="std_ratio", label="Std Dev Ratio", type="float",
                      default=2.0, min=0.1, max=5.0, step=0.1),
    ]

    def process(self, ctx: AlgorithmContext, params: Dict[str, float]) -> AlgorithmOutput:
        nb_neighbors = int(params["nb_neighbors"])
        std_ratio = float(params["std_ratio"])
        new_cloud, ind = ctx.cloud.remove_statistical_outlier(
            nb_neighbors=nb_neighbors, std_ratio=std_ratio
        )
        new_intensity = ctx.intensity[ind] if ctx.intensity is not None else None
        removed = len(ctx.cloud.points) - len(new_cloud.points)
        return AlgorithmOutput(
            cloud=new_cloud,
            intensity=new_intensity,
            extra={"points_removed": removed},
        )
