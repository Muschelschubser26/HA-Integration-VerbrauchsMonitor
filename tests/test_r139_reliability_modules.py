from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

PATH = Path(__file__).parents[1] / "custom_components" / "verbrauchsmonitor" / "reliability.py"
spec = spec_from_file_location("vm_r139_reliability", PATH)
reliability = module_from_spec(spec)
sys.modules[spec.name] = reliability
spec.loader.exec_module(reliability)

def test_a_and_b_produce_one_percentage_and_are_inspectable():
    result = reliability.evaluate_reliability({
        "measured_forecast_score": 60,
        "measured_financial_score": 100,
        "forecast_impact_weight": 3, "financial_impact_weight": 1,
    })
    assert result["available"] is True
    assert result["score"] == 70.0
    assert set(result["modules"]) == {"A", "B"}

def test_missing_history_does_not_create_a_historical_penalty():
    result = reliability.evaluate_reliability({"forecast_factors": {"current_meter": 75}, "forecast_impact_weight": 1})
    assert result["available"] is False
    assert result["score"] is None

def test_modules_can_be_added_without_changing_aggregator():
    reliability.register_module("future_quality_module", lambda ctx: reliability.ReliabilityContribution("future_quality_module", 90, 2, {"source": "test"}))
    result = reliability.evaluate_reliability({"forecast_factors": {"time": 50}, "forecast_impact_weight": 1}, module_keys=("A", "future_quality_module"))
    assert result["score"] == 90.0
    assert "future_quality_module" in result["modules"]

def test_no_available_evidence_returns_no_fabricated_percentage():
    result = reliability.evaluate_reliability({"forecast_factors": {}, "financial_factors": {}}, module_keys=("A", "B"))
    assert result["available"] is False
    assert result["score"] is None

def test_scores_can_legitimately_be_below_ten_percent():
    result = reliability.evaluate_reliability({"measured_forecast_score": 4, "forecast_impact_weight": 1}, module_keys=("A",))
    assert result["score"] == 4.0


def test_module_without_financial_impact_weight_is_excluded():
    result = reliability.evaluate_reliability({"forecast_factors": {"freshness": 80}}, module_keys=("A", "B"))
    assert result["available"] is False
    assert result["score"] is None


def test_unavailable_reliability_shows_bounded_initialization_state():
    from datetime import datetime, timezone
    model_path = PATH.parent / "forecast_model.py"
    model_spec = spec_from_file_location("vm_reliability_forecast_model_pending", model_path)
    model = module_from_spec(model_spec)
    sys.modules[model_spec.name] = model
    model_spec.loader.exec_module(model)
    created = datetime(2026, 11, 26, 12, 0, tzinfo=timezone.utc)
    pending = model.resolve_forecast_reliability(
        initial_score=None, initial_created_at=created, now=created,
        evaluations=[], history={}, method="linear_elapsed_period_average",
        reliability_context={},
    )
    assert pending["forecast_reliability_pending"] is True
    finished = model.resolve_forecast_reliability(
        initial_score=None, initial_created_at=created,
        now=datetime(2026, 11, 26, 12, 16, tzinfo=timezone.utc),
        evaluations=[], history={}, method="linear_elapsed_period_average",
        reliability_context={},
    )
    assert finished["forecast_reliability_pending"] is False
    assert finished["forecast_reliability_percent"] is None
