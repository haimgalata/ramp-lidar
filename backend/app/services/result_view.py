"""Converts internal store records into API (Pydantic) response models.

Ground-truth-dependent fields (slope_error, improvement_pct) are computed
HERE, at serve time, rather than cached on the ResultRecord -- that way,
editing the Ground Truth value always immediately updates every result's
error/improvement numbers without needing to re-run any processing.
"""
from typing import List, Optional

from app.core.store import ExperimentRecord, ResultRecord
from app.models.schemas import AlgorithmStep, BoundingBox, CloudInfo, ProcessingResult
from app.services import metrics
from app.services.point_cloud_io import compute_cloud_info


def _slope_error_and_improvement(exp: ExperimentRecord, record: ResultRecord):
    gt = exp.ground_truth_slope_deg
    if gt is None or record.calculated_slope is None:
        return gt, None, None

    slope_error = metrics.absolute_slope_error(record.calculated_slope, gt)

    improvement_pct = None
    baseline = exp.results.get(exp.original_pseudo_id)
    if baseline is not None and baseline.calculated_slope is not None and record.id != baseline.id:
        baseline_error = metrics.absolute_slope_error(baseline.calculated_slope, gt)
        improvement_pct = metrics.improvement_percentage(baseline_error, slope_error)

    return gt, slope_error, improvement_pct


def to_result_schema(exp: ExperimentRecord, record: ResultRecord) -> ProcessingResult:
    gt, slope_error, improvement_pct = _slope_error_and_improvement(exp, record)
    plane = record.plane_equation
    if plane is not None:
        a, b, c, d = plane
        norm = (a ** 2 + b ** 2 + c ** 2) ** 0.5 or 1.0
        normal = [a / norm, b / norm, c / norm]
    else:
        a = b = c = d = None
        normal = None
    return ProcessingResult(
        id=record.id,
        experiment_id=record.experiment_id,
        parent_result_id=record.parent_result_id,
        name=record.name,
        source_type=record.source_type,
        algorithm_name=record.algorithm_name,
        algorithm_parameters=record.algorithm_parameters,
        pipeline_steps=[AlgorithmStep(**s) if not isinstance(s, AlgorithmStep) else s
                        for s in _normalize_steps(record.pipeline_steps)],
        point_count=record.point_count,
        calculated_slope=record.calculated_slope,
        plane_a=a, plane_b=b, plane_c=c, plane_d=d, plane_normal=normal,
        ground_truth_slope=gt,
        slope_error=slope_error,
        plane_rmse=record.plane_rmse,
        mean_point_to_plane_distance=record.mean_point_to_plane_distance,
        inlier_count=record.inlier_count,
        outlier_count=record.outlier_count,
        points_removed_pct=record.points_removed_pct,
        improvement_pct=improvement_pct,
        processing_time_ms=record.processing_time_ms,
        created_at=record.created_at,
    )


def _normalize_steps(steps: List[dict]) -> List[dict]:
    """Pipeline steps store extra metadata (algorithm_name); AlgorithmStep only
    models algorithm_id/parameters, so strip anything extra before validating.
    """
    normalized = []
    for s in steps:
        normalized.append({"algorithm_id": s["algorithm_id"], "parameters": s.get("parameters", {})})
    return normalized


def experiment_cloud_info(exp: ExperimentRecord) -> Optional[CloudInfo]:
    if exp.original_cloud is None:
        return None
    info = compute_cloud_info(exp.original_cloud, exp.file_name, exp.file_format)
    info.has_intensity = exp.original_intensity is not None
    return info
