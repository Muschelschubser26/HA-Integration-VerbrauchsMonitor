from datetime import datetime, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

PATH = Path(__file__).parents[1] / "custom_components" / "verbrauchsmonitor" / "forecast_model.py"
spec = spec_from_file_location("vm_r135_forecast_model", PATH)
model = module_from_spec(spec)
sys.modules[spec.name] = model
spec.loader.exec_module(model)

def test_reliability_waits_for_measured_forecast_comparisons():
    now = datetime(2026, 11, 26, 12, 0, tzinfo=timezone.utc)
    result = model.resolve_forecast_reliability(
        initial_score=None, initial_created_at=now, now=now, evaluations=[],
        history={"history_months": 0, "coverage_percent": 0, "quality": 0, "sample_count": 0, "context_coverage_percent": 0},
        reliability_context={"forecast_factors": {"meter": 80}, "forecast_impact_weight": 1},
        method="linear_elapsed_period_average", provisional_hours=0.25,
    )
    assert result["forecast_reliability_available"] is False
    assert result["forecast_reliability_pending"] is True
    assert result["forecast_reliability_percent"] is None

def test_reliability_stops_loading_after_15_minutes_without_fabricating_score():
    created = datetime(2026, 11, 26, 12, 0, tzinfo=timezone.utc)
    now = datetime(2026, 11, 26, 12, 16, tzinfo=timezone.utc)
    result = model.resolve_forecast_reliability(
        initial_score=None, initial_created_at=created, now=now, evaluations=[],
        history={}, reliability_context={"forecast_factors": {"meter": 80}, "forecast_impact_weight": 1}, method="linear_elapsed_period_average", provisional_hours=0.25,
    )
    assert result["forecast_reliability_available"] is False
    assert result["forecast_reliability_pending"] is False
    assert result["forecast_reliability_percent"] is None
