from datetime import datetime, timedelta, timezone

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "vm_forecast_r086",
    Path(__file__).parents[1] / "custom_components" / "verbrauchsmonitor" / "forecast.py",
)
_forecast = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_forecast)
initial_reliability_state = _forecast.initial_reliability_state
update_reliability_state = _forecast.update_reliability_state


def test_initial_reliability_is_randomized_in_configured_range():
    now = datetime(2026, 11, 23, tzinfo=timezone.utc)
    values = [initial_reliability_state(now=now)["score"] for _ in range(200)]
    assert all(37.6 <= value <= 44.3 for value in values)
    assert len(set(values)) > 1


def test_reliability_does_not_change_before_hourly_review():
    now = datetime(2026, 11, 23, tzinfo=timezone.utc)
    state = {"score": 41.7, "last_evaluated": now.isoformat()}
    updated = update_reliability_state(
        state, history={"history_months": 24, "coverage_percent": 100,
                        "gap_days_max": 1, "quality": 100},
        method="seasonal_24m", now=now + timedelta(minutes=59),
    )
    assert updated == state


def test_reliability_moves_toward_evidence_based_target_with_40_percent_floor():
    now = datetime(2026, 11, 23, tzinfo=timezone.utc)
    state = {"score": 41.7, "last_evaluated": now.isoformat()}
    high = update_reliability_state(
        state, history={"history_months": 24, "coverage_percent": 100,
                        "gap_days_max": 1, "quality": 100},
        method="seasonal_24m", now=now + timedelta(days=7),
    )
    low = update_reliability_state(
        state, history={"history_months": 0, "coverage_percent": 0,
                        "gap_days_max": 999, "quality": 0},
        method="linear_elapsed_period_average", now=now + timedelta(days=7),
    )
    assert high["score"] > state["score"]
    assert low["score"] < state["score"]
    assert low["score"] >= 40.0
