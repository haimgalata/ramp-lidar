"""Pydantic request/response models for the API.

Naming convention: `*In` = request body, plain name = response model.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

# --------------------------------------------------------------------------
# Experiments
# --------------------------------------------------------------------------


class ExperimentCreateIn(BaseModel):
    name: str = Field(..., description="Human readable experiment name, e.g. 'Ramp Test 001'")


class BoundingBox(BaseModel):
    min: List[float] = Field(..., min_length=3, max_length=3)
    max: List[float] = Field(..., min_length=3, max_length=3)


class CloudInfo(BaseModel):
    """Descriptive statistics about a point cloud (original or a result)."""

    file_name: Optional[str] = None
    file_format: Optional[str] = None
    point_count: int
    min_x: float
    max_x: float
    min_y: float
    max_y: float
    min_z: float
    max_z: float
    width: float  # X extent
    length: float  # Y extent
    height_range: float  # Z extent
    bounding_box: BoundingBox
    has_color: bool = False
    has_intensity: bool = False
    has_normals: bool = False
    point_density: Optional[float] = None  # points per unit^2, footprint-based estimate


class Experiment(BaseModel):
    id: str
    name: str
    created_at: str
    has_cloud: bool = False
    cloud_info: Optional[CloudInfo] = None
    ground_truth_slope_deg: Optional[float] = None
    roi: Optional[BoundingBox] = None
    result_ids: List[str] = []


class GroundTruthIn(BaseModel):
    slope_deg: float


class RoiIn(BaseModel):
    min: List[float] = Field(..., min_length=3, max_length=3)
    max: List[float] = Field(..., min_length=3, max_length=3)


# --------------------------------------------------------------------------
# Point cloud geometry payload (for the 3D viewer)
# --------------------------------------------------------------------------


class PointCloudPoints(BaseModel):
    """Flat arrays are used (not array-of-objects) to keep payloads small."""

    positions: List[float]  # flattened [x0,y0,z0, x1,y1,z1, ...]
    colors: Optional[List[float]] = None  # flattened [r0,g0,b0, ...] in 0..1
    full_point_count: int
    sent_point_count: int
    subsampled: bool


# --------------------------------------------------------------------------
# Slope analysis
# --------------------------------------------------------------------------


class PlaneFitParams(BaseModel):
    distance_threshold: float = 0.01
    num_iterations: int = 1000
    min_inliers: int = 50


class SlopeResult(BaseModel):
    slope_deg: float
    plane_a: float
    plane_b: float
    plane_c: float
    plane_d: float
    normal: List[float]
    inlier_count: int
    outlier_count: int
    rmse: float
    mean_point_to_plane_distance: float


class AnalyzeSlopeIn(BaseModel):
    source: Literal["original", "roi"] = "roi"
    params: PlaneFitParams = PlaneFitParams()


# --------------------------------------------------------------------------
# Algorithms
# --------------------------------------------------------------------------


class ParameterSpec(BaseModel):
    key: str
    label: str
    type: Literal["float", "int"]
    default: float
    min: float
    max: float
    step: float


class AlgorithmDef(BaseModel):
    id: str
    name: str
    description: str
    parameters: List[ParameterSpec]


class AlgorithmStep(BaseModel):
    algorithm_id: str
    parameters: Dict[str, float] = {}


class SingleProcessIn(BaseModel):
    experiment_id: str
    source: Literal["original", "roi"] = "roi"
    source_result_id: Optional[str] = None
    algorithm_id: str
    parameters: Dict[str, float] = {}
    name: Optional[str] = None
    slope_params: Optional[PlaneFitParams] = None


class PipelineProcessIn(BaseModel):
    experiment_id: str
    source: Literal["original", "roi"] = "roi"
    steps: List[AlgorithmStep]
    name: Optional[str] = None
    slope_params: Optional[PlaneFitParams] = None


class ParallelProcessIn(BaseModel):
    experiment_id: str
    source: Literal["original", "roi"] = "roi"
    algorithms: List[AlgorithmStep]
    slope_params: Optional[PlaneFitParams] = None


# --------------------------------------------------------------------------
# Processing results
# --------------------------------------------------------------------------


class ProcessingResult(BaseModel):
    id: str
    experiment_id: str
    parent_result_id: Optional[str] = None
    name: str
    source_type: Literal["original", "roi", "result"]
    algorithm_name: Optional[str] = None
    algorithm_parameters: Dict[str, float] = {}
    pipeline_steps: List[AlgorithmStep] = []
    point_count: int
    calculated_slope: Optional[float] = None
    plane_a: Optional[float] = None
    plane_b: Optional[float] = None
    plane_c: Optional[float] = None
    plane_d: Optional[float] = None
    plane_normal: Optional[List[float]] = None
    ground_truth_slope: Optional[float] = None
    slope_error: Optional[float] = None
    plane_rmse: Optional[float] = None
    mean_point_to_plane_distance: Optional[float] = None
    inlier_count: Optional[int] = None
    outlier_count: Optional[int] = None
    points_removed_pct: Optional[float] = None
    improvement_pct: Optional[float] = None
    processing_time_ms: Optional[float] = None
    created_at: str


class ExportIn(BaseModel):
    format: Literal["ply", "pcd"] = "ply"


class MetricsExportIn(BaseModel):
    format: Literal["csv", "json"] = "csv"


class DiffRequest(BaseModel):
    other_result_id: Optional[str] = None  # None => compare against original
    min_mm: float = 0.0
    max_mm: float = 10.0
