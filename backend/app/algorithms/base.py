"""Common interface every processing algorithm implements.

Keeping this contract tiny (one `process` method) is what lets the pipeline
runner, the parallel runner and the single-run endpoint all share the same
execution code path (see app/services/pipeline.py).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
import open3d as o3d

from app.models.schemas import ParameterSpec


@dataclass
class AlgorithmContext:
    """Input to an algorithm run."""

    cloud: o3d.geometry.PointCloud
    # Per-point intensity aligned with `cloud.points`, if the source cloud had
    # an intensity channel. Not every algorithm can preserve it (see docstring
    # on VoxelDownsampleAlgorithm) -- that is a documented, deliberate
    # simplification rather than a bug.
    intensity: Optional[np.ndarray] = None


@dataclass
class AlgorithmOutput:
    cloud: o3d.geometry.PointCloud
    intensity: Optional[np.ndarray] = None
    # Algorithm-specific extra info (e.g. RANSAC inlier/outlier counts) that
    # the pipeline runner folds into the ResultRecord.
    extra: Dict[str, float] = None

    def __post_init__(self):
        if self.extra is None:
            self.extra = {}


class Algorithm(ABC):
    id: str
    name: str
    description: str
    parameters: List[ParameterSpec]

    def default_parameters(self) -> Dict[str, float]:
        return {p.key: p.default for p in self.parameters}

    def resolve_parameters(self, provided: Dict[str, float]) -> Dict[str, float]:
        """Merge user-provided parameters over defaults, ignoring unknown keys."""
        params = self.default_parameters()
        for spec in self.parameters:
            if spec.key in provided:
                value = provided[spec.key]
                params[spec.key] = int(value) if spec.type == "int" else float(value)
        return params

    @abstractmethod
    def process(self, ctx: AlgorithmContext, params: Dict[str, float]) -> AlgorithmOutput:
        ...
