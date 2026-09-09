"""Processing endpoints: single algorithm, sequential pipeline, parallel comparison.

Every result produced here is an in-memory ProcessingResult -- no file is ever
written to disk from this module (see app/core/store.py docstring).
"""
from typing import List

from fastapi import APIRouter, HTTPException

from app.core.store import store
from app.models.schemas import ParallelProcessIn, PipelineProcessIn, ProcessingResult, SingleProcessIn
from app.services import pipeline as pipeline_service
from app.services import result_view
from app.services.pipeline import DEFAULT_SLOPE_PARAMS
from app.utils.logging import get_logger

router = APIRouter(prefix="/processing", tags=["processing"])
logger = get_logger(__name__)


@router.post("/single", response_model=ProcessingResult)
def process_single(payload: SingleProcessIn):
    exp = store.require(payload.experiment_id)
    try:
        record = pipeline_service.run_single(exp, payload, payload.slope_params or DEFAULT_SLOPE_PARAMS)
    except (KeyError, ValueError) as exc:
        raise HTTPException(400, str(exc))
    logger.info("Single run %s on %s -> %s points", payload.algorithm_id, payload.experiment_id, record.point_count)
    return result_view.to_result_schema(exp, record)


@router.post("/pipeline", response_model=ProcessingResult)
def process_pipeline(payload: PipelineProcessIn):
    exp = store.require(payload.experiment_id)
    try:
        record = pipeline_service.run_pipeline(exp, payload, payload.slope_params or DEFAULT_SLOPE_PARAMS)
    except (KeyError, ValueError) as exc:
        raise HTTPException(400, str(exc))
    logger.info("Pipeline (%d steps) on %s -> %s points", len(payload.steps), payload.experiment_id, record.point_count)
    return result_view.to_result_schema(exp, record)


@router.post("/parallel", response_model=List[ProcessingResult])
def process_parallel(payload: ParallelProcessIn):
    exp = store.require(payload.experiment_id)
    try:
        records = pipeline_service.run_parallel(exp, payload, payload.slope_params or DEFAULT_SLOPE_PARAMS)
    except (KeyError, ValueError) as exc:
        raise HTTPException(400, str(exc))
    logger.info("Parallel run (%d algorithms) on %s", len(payload.algorithms), payload.experiment_id)
    return [result_view.to_result_schema(exp, r) for r in records]
