"""Unit tests for comparison metrics (app/services/metrics.py)."""
import pytest

from app.services.metrics import (
    absolute_slope_error,
    improvement_percentage,
    points_removed_percentage,
)


def test_absolute_slope_error_basic():
    assert absolute_slope_error(7.80, 7.00) == pytest.approx(0.80)
    assert absolute_slope_error(7.00, 7.80) == pytest.approx(0.80)  # symmetric


def test_improvement_percentage_spec_example():
    # Straight from the product spec's worked example.
    original_error = absolute_slope_error(7.80, 7.00)  # 0.80
    processed_error = absolute_slope_error(7.15, 7.00)  # 0.15
    improvement = improvement_percentage(original_error, processed_error)
    assert improvement == pytest.approx(81.25, abs=0.01)


def test_improvement_percentage_negative_when_worse():
    original_error = 0.20
    processed_error = 0.50
    improvement = improvement_percentage(original_error, processed_error)
    assert improvement < 0


def test_improvement_percentage_handles_zero_original_error():
    assert improvement_percentage(0.0, 0.10) is None


def test_points_removed_percentage():
    assert points_removed_percentage(1000, 800) == pytest.approx(20.0)
    assert points_removed_percentage(1000, 1000) == pytest.approx(0.0)
    assert points_removed_percentage(0, 0) == pytest.approx(0.0)  # no div-by-zero
