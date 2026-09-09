"""Orchestrates single-algorithm, pipeline, and parallel processing runs.

This is the one place that turns "an algorithm + some input cloud" into a
ResultRecord living in the in-memory store (see app/core/store.py). Single,
pipeline and parallel runs all funnel through `_execute_step`, so the three
processing modes only differ in how they chain (or don't chain) results --
not in how a single algorithm actually executes.
"""
import time
from typing import List, Optional, Tuple

import numpy as np
import open3d as o3d

from app.algorithms.base import AlgorithmContext
from app.algorithms.registry import get_algorithm
from app.core.store import ExperimentRecord, ResultRecord, new_id, now_iso, store
from app.models.schemas import (
    AlgorithmStep,
    ParallelProcessIn,
    PipelineProcessIn,
    PlaneFitParams,
    SingleProcessIn,
)
from app.services import metrics, point_cloud_io
from app.services.slope import fit_plane_and_slope

DEFAULT_SLOPE_PARAMS = PlaneFitParams()


# --------------------------------------------------------------------------
# Source resolution
# --------------------------------------------------------------------------


def resolve_source(
    exp: ExperimentRecord,
    source: str,
    source_result_id: Optional[str] = None,
) -> Tuple[o3d.geometry.PointCloud, Optional[np.ndarray], str]:
    """Returns (cloud, intensity, source_type) for a processing/analysis request."""
    if source_result_id:
        rec = store.get_result(source_result_id)
        if rec is None:
            raise KeyError(f"Source result '{source_result_id}' not found")
        return rec.cloud, rec.intensity, "result"

    if exp.original_cloud is None:
        raise ValueError("Experiment has no uploaded point cloud yet")

    if source == "roi":
        if exp.roi is None:
            raise ValueError("No ROI has been set for this experiment")
        cropped, cropped_intensity = point_cloud_io.crop_to_roi(
            exp.original_cloud, tuple(exp.roi["min"]), tuple(exp.roi["max"]), exp.original_intensity
        )
        if len(cropped.points) < 3:
            raise ValueError("ROI contains fewer than 3 points -- cannot analyze")
        return cropped, cropped_intensity, "roi"

    return exp.original_cloud, exp.original_intensity, "original"


# --------------------------------------------------------------------------
# Baseline ("Original") pseudo-result -- the comparison anchor
# --------------------------------------------------------------------------


def get_or_create_baseline(
    exp: ExperimentRecord, source: str, slope_params: Optional[PlaneFitParams] = None
) -> ResultRecord:
    existing = exp.results.get(exp.original_pseudo_id)
    if existing is not None:
        return existing
    return recompute_baseline(exp, source, slope_params or DEFAULT_SLOPE_PARAMS)


def recompute_baseline(
    exp: ExperimentRecord, source: str, slope_params: PlaneFitParams
) -> ResultRecord:
    cloud, intensity, source_type = resolve_source(exp, source)
    calc = fit_plane_and_slope(cloud, slope_params.distance_threshold, slope_params.num_iterations)

    record = ResultRecord(
        id=exp.original_pseudo_id,
        experiment_id=exp.id,
        parent_result_id=None,
        name="Original" if source_type == "original" else "Original (ROI)",
        source_type=source_type,
        algorithm_name=None,
        algorithm_parameters={},
        pipeline_steps=[],
        cloud=cloud,
        intensity=intensity,
        calculated_slope=calc.slope_deg,
        plane_equation=(calc.a, calc.b, calc.c, calc.d),
        plane_rmse=calc.rmse,
        mean_point_to_plane_distance=calc.mean_distance,
        inlier_count=calc.inlier_count,
        outlier_count=calc.outlier_count,
        points_removed_pct=0.0,
        processing_time_ms=None,
    )
    exp.results[exp.original_pseudo_id] = record
    return record


def invalidate_baseline(exp: ExperimentRecord) -> None:
    """Called whenever the underlying source data changes (new upload, ROI
    edited) so a stale baseline is never compared against."""
    exp.results.pop(exp.original_pseudo_id, None)


# --------------------------------------------------------------------------
# Core step execution (shared by single / pipeline / parallel)
# --------------------------------------------------------------------------


def _execute_step(
    cloud: o3d.geometry.PointCloud,
    intensity: Optional[np.ndarray],
    algorithm_id: str,
    parameters: dict,
) -> Tuple[o3d.geometry.PointCloud, Optional[np.ndarray], dict, dict, float]:
    """Runs one algorithm. Returns (cloud, intensity, resolved_params, extra, elapsed_ms)."""
    algorithm = get_algorithm(algorithm_id)
    resolved_params = algorithm.resolve_parameters(parameters)
    ctx = AlgorithmContext(cloud=cloud, intensity=intensity)

    t0 = time.perf_counter()
    output = algorithm.process(ctx, resolved_params)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    return output.cloud, output.intensity, resolved_params, output.extra, elapsed_ms


def _finalize_result(
    exp: ExperimentRecord,
    cloud: o3d.geometry.PointCloud,
    intensity: Optional[np.ndarray],
    *,
    name: str,
    source_type: str,
    algorithm_name: Optional[str],
    algorithm_parameters: dict,
    pipeline_steps: List[dict],
    parent_result_id: Optional[str],
    processing_time_ms: float,
    source_point_count: int,
    last_step_extra: dict,
    slope_params: PlaneFitParams,
) -> ResultRecord:
    """Runs slope analysis on the produced cloud (re-using a RANSAC step's own
    fit instead of re-running RANSAC when the last algorithm already was one)
    and wraps everything into a ResultRecord.
    """
    if "calculated_slope" in last_step_extra:
        # The last algorithm in the chain was RANSAC Plane Fitting itself --
        # reuse its fit instead of running RANSAC a second time.
        calculated_slope = last_step_extra["calculated_slope"]
        plane_eq = (
            last_step_extra["plane_a"], last_step_extra["plane_b"],
            last_step_extra["plane_c"], last_step_extra["plane_d"],
        )
        rmse = last_step_extra["rmse"]
        mean_dist = last_step_extra["mean_point_to_plane_distance"]
        inliers = int(last_step_extra["inlier_count"])
        outliers = int(last_step_extra["outlier_count"])
    elif len(cloud.points) >= 3:
        calc = fit_plane_and_slope(cloud, slope_params.distance_threshold, slope_params.num_iterations)
        calculated_slope = calc.slope_deg
        plane_eq = (calc.a, calc.b, calc.c, calc.d)
        rmse = calc.rmse
        mean_dist = calc.mean_distance
        inliers = calc.inlier_count
        outliers = calc.outlier_count
    else:
        calculated_slope = plane_eq = rmse = mean_dist = None
        inliers = outliers = None

    result = ResultRecord(
        id=new_id("res"),
        experiment_id=exp.id,
        parent_result_id=parent_result_id,
        name=name,
        source_type=source_type,
        algorithm_name=algorithm_name,
        algorithm_parameters=algorithm_parameters,
        pipeline_steps=pipeline_steps,
        cloud=cloud,
        intensity=intensity,
        calculated_slope=calculated_slope,
        plane_equation=plane_eq,
        plane_rmse=rmse,
        mean_point_to_plane_distance=mean_dist,
        inlier_count=inliers,
        outlier_count=outliers,
        points_removed_pct=metrics.points_removed_percentage(source_point_count, len(cloud.points)),
        processing_time_ms=processing_time_ms,
    )
    store.add_result(exp.id, result)
    return result


# --------------------------------------------------------------------------
# Public entry points (called by API routes)
# --------------------------------------------------------------------------


def run_single(exp: ExperimentRecord, req: SingleProcessIn, slope_params: PlaneFitParams) -> ResultRecord:
    get_or_create_baseline(exp, req.source, slope_params)
    cloud, intensity, source_type = resolve_source(exp, req.source, req.source_result_id)
    algorithm = get_algorithm(req.algorithm_id)

    new_cloud, new_intensity, resolved_params, extra, elapsed_ms = _execute_step(
        cloud, intensity, req.algorithm_id, req.parameters
    )
    return _finalize_result(
        exp, new_cloud, new_intensity,
        name=req.name or algorithm.name,
        source_type="result" if req.source_result_id else source_type,
        algorithm_name=algorithm.name,
        algorithm_parameters=resolved_params,
        pipeline_steps=[{"algorithm_id": req.algorithm_id, "parameters": resolved_params}],
        parent_result_id=req.source_result_id,
        processing_time_ms=elapsed_ms,
        source_point_count=len(cloud.points),
        last_step_extra=extra,
        slope_params=slope_params,
    )


def run_pipeline(exp: ExperimentRecord, req: PipelineProcessIn, slope_params: PlaneFitParams) -> ResultRecord:
    if not req.steps:
        raise ValueError("Pipeline must contain at least one algorithm step")

    get_or_create_baseline(exp, req.source, slope_params)
    cloud, intensity, source_type = resolve_source(exp, req.source)
    source_point_count = len(cloud.points)

    steps_meta: List[dict] = []
    total_time_ms = 0.0
    last_extra: dict = {}
    names: List[str] = []

    for step in req.steps:
        algorithm = get_algorithm(step.algorithm_id)
        cloud, intensity, resolved_params, extra, elapsed_ms = _execute_step(
            cloud, intensity, step.algorithm_id, step.parameters
        )
        total_time_ms += elapsed_ms
        last_extra = extra
        names.append(algorithm.name)
        steps_meta.append({
            "algorithm_id": step.algorithm_id,
            "algorithm_name": algorithm.name,
            "parameters": resolved_params,
        })

    return _finalize_result(
        exp, cloud, intensity,
        name=req.name or " -> ".join(names),
        source_type=source_type,
        algorithm_name="Pipeline",
        algorithm_parameters={},
        pipeline_steps=steps_meta,
        parent_result_id=None,
        processing_time_ms=total_time_ms,
        source_point_count=source_point_count,
        last_step_extra=last_extra,
        slope_params=slope_params,
    )


def run_parallel(exp: ExperimentRecord, req: ParallelProcessIn, slope_params: PlaneFitParams) -> List[ResultRecord]:
    if not req.algorithms:
        raise ValueError("Must select at least one algorithm to run in parallel")

    get_or_create_baseline(exp, req.source, slope_params)
    base_cloud, base_intensity, source_type = resolve_source(exp, req.source)
    source_point_count = len(base_cloud.points)

    results: List[ResultRecord] = []
    for step in req.algorithms:
        algorithm = get_algorithm(step.algorithm_id)
        new_cloud, new_intensity, resolved_params, extra, elapsed_ms = _execute_step(
            base_cloud, base_intensity, step.algorithm_id, step.parameters
        )
        result = _finalize_result(
            exp, new_cloud, new_intensity,
            name=algorithm.name,
            source_type=source_type,
            algorithm_name=algorithm.name,
            algorithm_parameters=resolved_params,
            pipeline_steps=[{"algorithm_id": step.algorithm_id, "parameters": resolved_params}],
            parent_result_id=None,
            processing_time_ms=elapsed_ms,
            source_point_count=source_point_count,
            last_step_extra=extra,
            slope_params=slope_params,
        )
        results.append(result)
    return results
