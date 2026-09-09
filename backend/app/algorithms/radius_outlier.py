"""Radius Outlier Removal (ROR).

Removes any point that does not have at least `min_neighbors` other points
within `radius` of it. Effective at removing sparse/isolated blobs (e.g. dust,
stray reflections) that Statistical Outlier Removal can miss.
"""
from typing import Dict

from app.algorithms.base import Algorithm, AlgorithmContext, AlgorithmOutput
from app.models.schemas import ParameterSpec


class RadiusOutlierRemoval(Algorithm):
    id = "ror"
    name = "Radius Outlier Removal"
    description = (
        "Removes points that have fewer than N neighbors within a given radius "
        "(good for isolated sparse noise blobs)."
    )
    parameters = [
        ParameterSpec(key="radius", label="Radius (m)", type="float",
                      default=0.05, min=0.001, max=2.0, step=0.001),
        ParameterSpec(key="min_neighbors", label="Min Neighbors", type="int",
                      default=5, min=1, max=100, step=1),
    ]

    def process(self, ctx: AlgorithmContext, params: Dict[str, float]) -> AlgorithmOutput:
        radius = float(params["radius"])
        min_neighbors = int(params["min_neighbors"])
        new_cloud, ind = ctx.cloud.remove_radius_outlier(
            nb_points=min_neighbors, radius=radius
        )
        new_intensity = ctx.intensity[ind] if ctx.intensity is not None else None
        removed = len(ctx.cloud.points) - len(new_cloud.points)
        return AlgorithmOutput(
            cloud=new_cloud,
            intensity=new_intensity,
            extra={"points_removed": removed},
        )
