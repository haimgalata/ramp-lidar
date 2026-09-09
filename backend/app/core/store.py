"""In-memory experiment & result store.

This is the single source of truth that separates the four concepts the
product spec calls out explicitly:

  Uploaded File  -->  ExperimentRecord.original_cloud (Open3D object, RAM only,
                       NEVER mutated after upload)
              -->  ResultRecord.cloud (Open3D object, RAM only, produced by
                       running an algorithm or pipeline)
              -->  Exported File (written to disk ONLY inside the /export
                       endpoint, on explicit user request)

There is no database and no implicit disk I/O. Everything lives in a plain
process-local dict guarded by a lock (fine for a local single-user prototype;
swapping in Redis/SQLite later would only touch this module).
"""
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import numpy as np
import open3d as o3d


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ResultRecord:
    """A single processing result (single algorithm, pipeline, or parallel
    branch). This is an in-memory object, not a file -- see module docstring.
    """

    id: str
    experiment_id: str
    parent_result_id: Optional[str]
    name: str
    source_type: str  # "original" | "roi" | "result"
    algorithm_name: Optional[str]
    algorithm_parameters: Dict[str, float]
    pipeline_steps: List[dict]
    cloud: o3d.geometry.PointCloud
    intensity: Optional[np.ndarray] = None

    calculated_slope: Optional[float] = None
    plane_equation: Optional[Tuple[float, float, float, float]] = None
    ground_truth_slope: Optional[float] = None
    slope_error: Optional[float] = None
    plane_rmse: Optional[float] = None
    mean_point_to_plane_distance: Optional[float] = None
    inlier_count: Optional[int] = None
    outlier_count: Optional[int] = None
    points_removed_pct: Optional[float] = None
    improvement_pct: Optional[float] = None
    processing_time_ms: Optional[float] = None
    created_at: str = field(default_factory=now_iso)

    @property
    def point_count(self) -> int:
        return len(self.cloud.points)


@dataclass
class ExperimentRecord:
    id: str
    name: str
    created_at: str
    file_name: Optional[str] = None
    file_format: Optional[str] = None
    original_cloud: Optional[o3d.geometry.PointCloud] = None
    original_intensity: Optional[np.ndarray] = None
    ground_truth_slope_deg: Optional[float] = None
    roi: Optional[dict] = None  # {"min": [x,y,z], "max": [x,y,z]}
    results: Dict[str, ResultRecord] = field(default_factory=dict)
    # id used for the pseudo "original" result row shown in comparison tables
    original_pseudo_id: str = ""


class ExperimentStore:
    """Thread-safe in-memory registry of experiments."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._experiments: Dict[str, ExperimentRecord] = {}

    def create(self, name: str) -> ExperimentRecord:
        exp_id = new_id("exp")
        with self._lock:
            record = ExperimentRecord(
                id=exp_id,
                name=name,
                created_at=now_iso(),
                original_pseudo_id=f"{exp_id}_original",
            )
            self._experiments[exp_id] = record
            return record

    def get(self, experiment_id: str) -> Optional[ExperimentRecord]:
        return self._experiments.get(experiment_id)

    def require(self, experiment_id: str) -> ExperimentRecord:
        exp = self.get(experiment_id)
        if exp is None:
            raise KeyError(f"Experiment '{experiment_id}' not found")
        return exp

    def delete(self, experiment_id: str) -> None:
        """Frees the original cloud and every result -- releases all RAM
        associated with the experiment."""
        with self._lock:
            self._experiments.pop(experiment_id, None)

    def list(self) -> List[ExperimentRecord]:
        return list(self._experiments.values())

    def add_result(self, experiment_id: str, result: ResultRecord) -> None:
        with self._lock:
            self.require(experiment_id).results[result.id] = result

    def get_result(self, result_id: str) -> Optional[ResultRecord]:
        for exp in self._experiments.values():
            if result_id in exp.results:
                return exp.results[result_id]
        return None

    def delete_result(self, result_id: str) -> bool:
        with self._lock:
            for exp in self._experiments.values():
                if result_id in exp.results:
                    del exp.results[result_id]
                    return True
        return False

    def reset_results(self, experiment_id: str) -> None:
        """Clears every processing result but keeps the original cloud."""
        with self._lock:
            self.require(experiment_id).results.clear()


# Single process-wide store instance (imported by API routers).
store = ExperimentStore()
