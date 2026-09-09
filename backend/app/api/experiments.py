"""Experiment lifecycle: create, upload, ROI, ground truth, slope analysis."""
import csv
import io
import json
from typing import List, Literal, Optional

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import Response

from app.config import get_settings
from app.core.store import store
from app.models.schemas import (
    AnalyzeSlopeIn,
    Experiment,
    ExperimentCreateIn,
    GroundTruthIn,
    PointCloudPoints,
    ProcessingResult,
    RoiIn,
)
from app.services import point_cloud_io, result_view
from app.services.pipeline import invalidate_baseline, recompute_baseline
from app.utils.logging import get_logger

router = APIRouter(tags=["experiments"])
logger = get_logger(__name__)


def _to_experiment_schema(exp) -> Experiment:
    return Experiment(
        id=exp.id,
        name=exp.name,
        created_at=exp.created_at,
        has_cloud=exp.original_cloud is not None,
        cloud_info=result_view.experiment_cloud_info(exp),
        ground_truth_slope_deg=exp.ground_truth_slope_deg,
        roi=exp.roi,
        result_ids=list(exp.results.keys()),
    )


@router.post("/experiments", response_model=Experiment)
def create_experiment(payload: ExperimentCreateIn):
    exp = store.create(payload.name)
    return _to_experiment_schema(exp)


@router.get("/experiments", response_model=List[Experiment])
def list_experiments():
    return [_to_experiment_schema(e) for e in store.list()]


@router.get("/experiments/{experiment_id}", response_model=Experiment)
def get_experiment(experiment_id: str):
    exp = store.get(experiment_id)
    if exp is None:
        raise HTTPException(404, "Experiment not found")
    return _to_experiment_schema(exp)


@router.delete("/experiments/{experiment_id}")
def delete_experiment(experiment_id: str):
    """Frees the original cloud and every in-memory result."""
    store.delete(experiment_id)
    return {"deleted": True}


@router.post("/experiments/{experiment_id}/reset")
def reset_experiment_results(experiment_id: str):
    """Clears all processing results but keeps the original uploaded cloud."""
    exp = store.require(experiment_id)
    store.reset_results(experiment_id)
    return _to_experiment_schema(exp)


@router.post("/experiments/{experiment_id}/upload", response_model=Experiment)
async def upload_point_cloud(experiment_id: str, file: UploadFile = File(...)):
    exp = store.require(experiment_id)
    raw = await file.read()
    settings = get_settings()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(raw) > max_bytes:
        raise HTTPException(413, f"File exceeds {settings.max_upload_mb}MB limit")

    try:
        loaded = point_cloud_io.load_point_cloud(raw, file.filename)
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    exp.original_cloud = loaded.cloud
    exp.original_intensity = loaded.intensity
    exp.file_name = file.filename
    exp.file_format = loaded.file_format
    exp.roi = None
    exp.results.clear()
    logger.info("Experiment %s: loaded %s (%d points)", exp.id, file.filename, len(loaded.cloud.points))
    return _to_experiment_schema(exp)


@router.get("/experiments/{experiment_id}/points", response_model=PointCloudPoints)
def get_experiment_points(
    experiment_id: str,
    source: Literal["original", "roi"] = Query("original"),
    max_points: Optional[int] = Query(None),
):
    exp = store.require(experiment_id)
    if exp.original_cloud is None:
        raise HTTPException(400, "No cloud uploaded yet")

    settings = get_settings()
    cap = max_points or settings.viz_max_points

    if source == "roi":
        if exp.roi is None:
            raise HTTPException(400, "No ROI set")
        cloud, _ = point_cloud_io.crop_to_roi(
            exp.original_cloud, tuple(exp.roi["min"]), tuple(exp.roi["max"])
        )
    else:
        cloud = exp.original_cloud

    return point_cloud_io.build_points_payload(cloud, cap)


@router.post("/experiments/{experiment_id}/roi", response_model=Experiment)
def set_roi(experiment_id: str, roi: RoiIn):
    exp = store.require(experiment_id)
    if exp.original_cloud is None:
        raise HTTPException(400, "Upload a point cloud before setting an ROI")
    exp.roi = {"min": roi.min, "max": roi.max}
    invalidate_baseline(exp)
    return _to_experiment_schema(exp)


@router.delete("/experiments/{experiment_id}/roi", response_model=Experiment)
def clear_roi(experiment_id: str):
    exp = store.require(experiment_id)
    exp.roi = None
    invalidate_baseline(exp)
    return _to_experiment_schema(exp)


@router.post("/experiments/{experiment_id}/ground-truth", response_model=Experiment)
def set_ground_truth(experiment_id: str, payload: GroundTruthIn):
    exp = store.require(experiment_id)
    exp.ground_truth_slope_deg = payload.slope_deg
    return _to_experiment_schema(exp)


@router.post("/experiments/{experiment_id}/analyze-slope", response_model=ProcessingResult)
def analyze_slope(experiment_id: str, payload: AnalyzeSlopeIn):
    """Computes/refreshes the baseline slope for the Original (or ROI) cloud.
    This is the pseudo-result every processed result is compared against.
    """
    exp = store.require(experiment_id)
    if exp.original_cloud is None:
        raise HTTPException(400, "Upload a point cloud before analyzing slope")
    try:
        record = recompute_baseline(exp, payload.source, payload.params)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return result_view.to_result_schema(exp, record)


@router.get("/experiments/{experiment_id}/results", response_model=List[ProcessingResult])
def list_results(experiment_id: str):
    exp = store.require(experiment_id)
    return [result_view.to_result_schema(exp, r) for r in exp.results.values()]


_METRICS_COLUMNS = [
    "name", "algorithm_name", "point_count", "calculated_slope", "ground_truth_slope",
    "slope_error", "improvement_pct", "plane_rmse", "mean_point_to_plane_distance",
    "inlier_count", "outlier_count", "points_removed_pct", "processing_time_ms", "created_at",
]


@router.get("/experiments/{experiment_id}/results/export")
def export_results_table(experiment_id: str, format: Literal["csv", "json"] = Query("csv")):
    """Exports the comparison table (not a point cloud) as CSV or JSON --
    triggered only when the user explicitly asks to export results."""
    exp = store.require(experiment_id)
    rows = [result_view.to_result_schema(exp, r).model_dump() for r in exp.results.values()]

    if format == "json":
        content = json.dumps(rows, indent=2, default=str)
        media_type = "application/json"
        filename = f"{exp.name.replace(' ', '_')}_results.json"
    else:
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=_METRICS_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
        content = buffer.getvalue()
        media_type = "text/csv"
        filename = f"{exp.name.replace(' ', '_')}_results.csv"

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
