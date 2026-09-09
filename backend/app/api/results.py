"""Single-result endpoints: fetch, fetch geometry, diff, export, delete."""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from app.config import get_settings
from app.core.store import store
from app.models.schemas import ExportIn, PointCloudPoints, ProcessingResult
from app.services import point_cloud_io, result_view
from app.services.difference import compute_diff_payload
from app.utils.logging import get_logger

router = APIRouter(prefix="/results", tags=["results"])
logger = get_logger(__name__)


def _require_result_and_experiment(result_id: str):
    record = store.get_result(result_id)
    if record is None:
        raise HTTPException(404, "Result not found")
    exp = store.require(record.experiment_id)
    return record, exp


@router.get("/{result_id}", response_model=ProcessingResult)
def get_result(result_id: str):
    record, exp = _require_result_and_experiment(result_id)
    return result_view.to_result_schema(exp, record)


@router.get("/{result_id}/points", response_model=PointCloudPoints)
def get_result_points(result_id: str, max_points: Optional[int] = Query(None)):
    record, _exp = _require_result_and_experiment(result_id)
    cap = max_points or get_settings().viz_max_points
    return point_cloud_io.build_points_payload(record.cloud, cap)


@router.get("/{result_id}/diff")
def get_result_diff(
    result_id: str,
    other_result_id: Optional[str] = Query(None),
    min_mm: float = Query(0.0),
    max_mm: float = Query(10.0),
    max_points: Optional[int] = Query(None),
):
    """Cloud-to-cloud distance heatmap comparing `result_id` against either
    `other_result_id` or (if omitted) the experiment's Original cloud."""
    record, exp = _require_result_and_experiment(result_id)

    if other_result_id:
        other = store.get_result(other_result_id)
        if other is None:
            raise HTTPException(404, "Comparison result not found")
        target_cloud = other.cloud
    else:
        if exp.original_cloud is None:
            raise HTTPException(400, "No original cloud to compare against")
        target_cloud = exp.original_cloud

    cap = max_points or get_settings().viz_max_points
    payload = compute_diff_payload(record.cloud, target_cloud, min_mm, max_mm, cap)
    return payload.__dict__


@router.post("/{result_id}/export")
def export_result(result_id: str, payload: ExportIn):
    """The ONLY place a processing result is ever written to a real file --
    only invoked when the user explicitly clicks Export/Download."""
    record, _exp = _require_result_and_experiment(result_id)
    try:
        data = point_cloud_io.save_point_cloud(record.cloud, payload.format)
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    media_type = "application/octet-stream"
    filename = f"{record.name.replace(' ', '_')}.{payload.format}"
    logger.info("Exporting result %s as %s (%d bytes)", result_id, payload.format, len(data))
    return Response(
        content=data,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/{result_id}")
def delete_result(result_id: str):
    deleted = store.delete_result(result_id)
    if not deleted:
        raise HTTPException(404, "Result not found")
    return {"deleted": True}
