"""Central registry of all available algorithms.

Adding a new algorithm to the system means writing one class (implementing
`Algorithm.process`) and adding one line here -- nothing else needs to change.
"""
from typing import Dict, List

from app.algorithms.base import Algorithm
from app.algorithms.normal_estimation import NormalEstimation
from app.algorithms.radius_outlier import RadiusOutlierRemoval
from app.algorithms.ransac_plane import RansacPlaneFit
from app.algorithms.smoothing import NeighborAverageSmoothing
from app.algorithms.statistical_outlier import StatisticalOutlierRemoval
from app.algorithms.voxel_downsample import VoxelDownsample

_ALGORITHMS: List[Algorithm] = [
    StatisticalOutlierRemoval(),
    RadiusOutlierRemoval(),
    VoxelDownsample(),
    RansacPlaneFit(),
    NormalEstimation(),
    NeighborAverageSmoothing(),
]

_REGISTRY: Dict[str, Algorithm] = {a.id: a for a in _ALGORITHMS}


def list_algorithms() -> List[Algorithm]:
    return list(_ALGORITHMS)


def get_algorithm(algorithm_id: str) -> Algorithm:
    if algorithm_id not in _REGISTRY:
        raise KeyError(f"Unknown algorithm id '{algorithm_id}'")
    return _REGISTRY[algorithm_id]
