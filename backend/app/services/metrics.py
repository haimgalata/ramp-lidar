"""Comparison metrics: slope error and the headline "did this help?" number.

These are pure functions over plain floats so they are trivial to unit test
independently of Open3D / the point cloud store.
"""
from typing import Optional


def absolute_slope_error(calculated_slope_deg: float, ground_truth_deg: float) -> float:
    """|Calculated Slope - Ground Truth|"""
    return abs(calculated_slope_deg - ground_truth_deg)


def improvement_percentage(original_error_deg: float, processed_error_deg: float) -> Optional[float]:
    """((Original Error - Processed Error) / Original Error) * 100

    Returns None when the original error is 0 (division by zero is undefined --
    there is nothing left to improve, so a percentage is not meaningful).
    """
    if original_error_deg == 0:
        return None
    return ((original_error_deg - processed_error_deg) / original_error_deg) * 100.0


def points_removed_percentage(original_count: int, result_count: int) -> float:
    if original_count == 0:
        return 0.0
    removed = original_count - result_count
    return (removed / original_count) * 100.0
