from datetime import datetime, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

ROOT = Path(__file__).parents[1] / "custom_components" / "verbrauchsmonitor"
spec = spec_from_file_location("vm_r156_forecast_model", ROOT / "forecast_model.py")
model = module_from_spec(spec)
sys.modules[spec.name] = model
spec.loader.exec_module(model)


def test_existing_usable_recorder_history_provides_initial_reliability_before_24_pairs():
    now = datetime(2026, 11, 26, 17, 0, tzinfo=timezone.utc)
    history = {
        "usable": True,
        "history_months": 24,
        "sample_count": 700,
        "coverage_percent": 98.0,
        "gap_days_max": 2.0,
        "quality": 97,
        "monthly_daily_kwh": {str(month): 10.0 for month in range(1, 13)},
        "two_cycle_months": 12,
    }
    result = model.resolve_forecast_reliability(
        initial_score=None,
        initial_created_at=now,
        now=now,
        evaluations=[],
        history=history,
        method="seasonal_24m",
        reliability_context={
            "billing_period_start": "2026-01-01",
            "billing_period_end": "2026-12-31",
        },
    )
    assert result["forecast_reliability_available"] is True
    assert result["forecast_reliability_percent"] is not None
    assert result["forecast_reliability_percent"] > 0
    assert result["forecast_reliability_basis"] == "recorder_history_quality_and_billing_period_coverage"
    assert result["forecast_reliability_history_quality_percent"] is not None
    assert result["forecast_reliability_measured_accuracy_percent"] is None


def test_measured_forecast_comparisons_take_precedence_over_recorder_bootstrap():
    now = datetime(2026, 12, 31, 23, 30, tzinfo=timezone.utc)
    evaluations = [
        {"absolute_error": 0.1, "relative_error_percent": 5.0, "error": 0.1}
        for _ in range(24)
    ]
    history = {
        "usable": True, "history_months": 24, "sample_count": 700,
        "coverage_percent": 98.0, "gap_days_max": 2.0, "quality": 97,
    }
    result = model.resolve_forecast_reliability(
        initial_score=None, initial_created_at=now, now=now,
        evaluations=evaluations, history=history,
        method="seasonal_24m",
        reliability_context={
            "forecast_impact_weight": 1,
            "billing_period_start": "2026-01-01",
            "billing_period_end": "2026-12-31",
        },
    )
    assert result["forecast_reliability_basis"] == "measured_forecast_accuracy_and_billing_period_coverage"
    assert result["forecast_reliability_measured_accuracy_percent"] == 95.0
    assert result["forecast_reliability_history_quality_percent"] is None
    assert result["forecast_reliability_percent"] <= 95.0
