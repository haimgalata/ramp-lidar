"""Voxel Grid Downsampling.

Buckets points into a 3D grid of `voxel_size` cubes and replaces every voxel's
points with their centroid. Reduces point count (and noise) but changes point
identity, so per-point intensity cannot be carried through with a simple index
map -- it is intentionally dropped here (documented limitation; colors and
normals ARE preserved because Open3D averages them per-voxel automatically).
"""
from typing import Dict

from app.algorithms.base import Algorithm, AlgorithmContext, AlgorithmOutput
from app.models.schemas import ParameterSpec


class VoxelDownsample(Algorithm):
    id = "voxel"
    name = "Voxel Downsampling"
    description = (
        "Reduces point density by averaging points inside each voxel cell "
        "(faster downstream processing, some noise smoothing)."
    )
    parameters = [
        ParameterSpec(key="voxel_size", label="Voxel Size (m)", type="float",
                      default=0.01, min=0.001, max=1.0, step=0.001),
    ]

    def process(self, ctx: AlgorithmContext, params: Dict[str, float]) -> AlgorithmOutput:
        voxel_size = float(params["voxel_size"])
        new_cloud = ctx.cloud.voxel_down_sample(voxel_size=voxel_size)
        removed = len(ctx.cloud.points) - len(new_cloud.points)
        return AlgorithmOutput(
            cloud=new_cloud,
            intensity=None,  # see module docstring
            extra={"points_removed": removed},
        )
