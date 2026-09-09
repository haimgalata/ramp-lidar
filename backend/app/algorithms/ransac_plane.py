"""RANSAC Plane Fitting, used both as a pipeline algorithm (crop the cloud
down to the dominant planar surface -- i.e. the ramp) and, via
app/services/slope.py, as the slope-analysis engine.

See app/services/slope.py for the actual geometry (plane equation -> slope
in degrees); this module just wires RANSAC into the Algorithm interface so it
can be dropped into a pipeline like any other step.
"""
from typing import Dict

from app.algorithms.base import Algorithm, AlgorithmContext, AlgorithmOutput
from app.models.schemas import ParameterSpec
from app.services.slope import fit_plane_and_slope


class RansacPlaneFit(Algorithm):
    id = "ransac"
    name = "RANSAC Plane Fitting"
    description = (
        "Fits the dominant plane (the ramp surface) with RANSAC and keeps only "
        "the inlier points -- effectively removes anything that is not part of "
        "the flat ramp surface (walls, railings, stray objects)."
    )
    parameters = [
        ParameterSpec(key="distance_threshold", label="Distance Threshold (m)", type="float",
                      default=0.01, min=0.0005, max=0.5, step=0.0005),
        ParameterSpec(key="num_iterations", label="Iterations", type="int",
                      default=1000, min=50, max=5000, step=50),
        ParameterSpec(key="min_inliers", label="Minimum Inliers", type="int",
                      default=50, min=3, max=100000, step=1),
    ]

    def process(self, ctx: AlgorithmContext, params: Dict[str, float]) -> AlgorithmOutput:
        distance_threshold = float(params["distance_threshold"])
        num_iterations = int(params["num_iterations"])
        min_inliers = int(params["min_inliers"])

        slope_calc = fit_plane_and_slope(ctx.cloud, distance_threshold, num_iterations)
        new_cloud = ctx.cloud.select_by_index(slope_calc.inlier_indices)
        new_intensity = (
            ctx.intensity[slope_calc.inlier_indices] if ctx.intensity is not None else None
        )
        low_inliers_warning = 1.0 if slope_calc.inlier_count < min_inliers else 0.0

        return AlgorithmOutput(
            cloud=new_cloud,
            intensity=new_intensity,
            extra={
                "points_removed": len(ctx.cloud.points) - len(new_cloud.points),
                "calculated_slope": slope_calc.slope_deg,
                "plane_a": slope_calc.a,
                "plane_b": slope_calc.b,
                "plane_c": slope_calc.c,
                "plane_d": slope_calc.d,
                "inlier_count": slope_calc.inlier_count,
                "outlier_count": slope_calc.outlier_count,
                "rmse": slope_calc.rmse,
                "mean_point_to_plane_distance": slope_calc.mean_distance,
                "low_inliers_warning": low_inliers_warning,
            },
        )
