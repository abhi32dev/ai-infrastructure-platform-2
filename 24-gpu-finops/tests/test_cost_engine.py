"""Deterministic tests of the cost-governance engine using constructed
telemetry with known, designed-in idle/busy patterns — the real code
under test, independent of the (explicitly synthetic) data generator.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from cost_engine import find_sustained_idle_windows, analyze_instance, run_analysis, cost_per_point, SUSTAINED_IDLE_POINTS
from config import TELEMETRY_INTERVAL_MINUTES


def make_points(utils: list[float], instance_id="test-1", gpu_type="A100", team="test-team"):
    start = datetime(2026, 1, 1)
    return [
        {
            "instance_id": instance_id, "gpu_type": gpu_type, "team": team,
            "timestamp": start + timedelta(minutes=i * TELEMETRY_INTERVAL_MINUTES),
            "utilization_pct": u,
        }
        for i, u in enumerate(utils)
    ]


def test_momentary_dip_below_threshold_is_not_flagged_as_idle():
    """Negative case: a SHORT dip below the idle threshold (shorter than
    SUSTAINED_IDLE_POINTS) must not count as wasted spend — this is the
    difference between a real dip during training (e.g. between batches)
    and genuinely idle time."""
    utils = [90.0] * 5 + [5.0] * (SUSTAINED_IDLE_POINTS - 1) + [90.0] * 5
    points = make_points(utils)
    windows = find_sustained_idle_windows(points)
    assert windows == []


def test_sustained_low_utilization_is_flagged_as_idle():
    utils = [90.0] * 5 + [5.0] * (SUSTAINED_IDLE_POINTS + 3) + [90.0] * 5
    points = make_points(utils)
    windows = find_sustained_idle_windows(points)
    assert len(windows) == 1
    assert len(windows[0]) == SUSTAINED_IDLE_POINTS + 3


def test_fully_busy_instance_has_zero_idle_cost():
    utils = [95.0] * 20
    points = make_points(utils)
    report = analyze_instance("test-1", points)
    assert report["idle_cost_usd"] == 0.0
    assert report["alert"] is False


def test_fully_idle_instance_has_alert_triggered():
    utils = [2.0] * 20  # well below threshold, well beyond sustained duration
    points = make_points(utils)
    report = analyze_instance("test-1", points)
    assert report["idle_cost_usd"] > 0
    assert report["alert"] is True


def test_cost_allocation_sums_correctly_across_teams():
    telemetry = (
        make_points([95.0] * 10, instance_id="a", team="team-x")
        + make_points([95.0] * 10, instance_id="b", team="team-x")
        + make_points([95.0] * 10, instance_id="c", team="team-y")
    )
    result = run_analysis(telemetry)
    assert abs(result["by_team"]["team-x"]["total_cost_usd"] - 2 * result["by_team"]["team-y"]["total_cost_usd"]) < 0.01


def test_cost_per_point_reflects_gpu_type_rate_differences():
    """Regression guard: different GPU types must produce different
    per-point costs proportional to their configured hourly rate — a
    hardcoded rate here would silently break cost accuracy for any
    non-default GPU type."""
    a100_cost = cost_per_point("A100")
    l4_cost = cost_per_point("L4")
    assert a100_cost > l4_cost  # A100 is the more expensive GPU in config.py


def test_unknown_gpu_type_raises_instead_of_silently_defaulting():
    """Negative/edge case: an instance tagged with a GPU type not in the
    rate card must raise, not silently compute cost as $0 or some
    default — a silent default would corrupt the cost report without
    any visible error."""
    import pytest
    with pytest.raises(KeyError):
        cost_per_point("UNKNOWN_GPU_TYPE")
