from datetime import datetime, timezone
from pathlib import Path
from importlib.util import module_from_spec, spec_from_file_location
import sys

ROOT = Path(__file__).parents[1] / "custom_components" / "verbrauchsmonitor"


def load(name, filename):
    spec = spec_from_file_location(name, ROOT / filename)
    module = module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_temporal_ceiling_is_95_only_in_final_hour_and_requires_measured_accuracy():
    model = load("vm_r151_model", "forecast_model.py")
    evaluations = [
        {"absolute_error": 0.0, "relative_error_percent": 0.0, "error": 0.0}
        for _ in range(24)
    ]
    common = dict(
        initial_score=None,
        initial_created_at=datetime(2026, 12, 31, 0, 0, tzinfo=timezone.utc),
        evaluations=evaluations, history={}, method="linear_elapsed_period_average",
        reliability_context={"forecast_impact_weight": 1,
                             "billing_period_start": "2026-01-01",
                             "billing_period_end": "2026-12-31"},
    )
    before_final_hour = model.resolve_forecast_reliability(
        **common, now=datetime(2026, 12, 31, 22, 59, tzinfo=timezone.utc)
    )
    final_hour = model.resolve_forecast_reliability(
        **common, now=datetime(2026, 12, 31, 23, 30, tzinfo=timezone.utc)
    )
    assert before_final_hour["forecast_reliability_temporal_ceiling"] == 94.0
    assert before_final_hour["forecast_reliability_percent"] <= 94.0
    assert final_hour["forecast_reliability_temporal_ceiling"] == 95.0
    assert final_hour["forecast_reliability_percent"] == 95.0


def test_live_validated_inputs_can_initialize_a_non_accuracy_reliability_score():
    model = load("vm_r151_no_fabricated", "forecast_model.py")
    now = datetime(2026, 12, 31, 23, 30, tzinfo=timezone.utc)
    result = model.resolve_forecast_reliability(
        initial_score=None, initial_created_at=now, now=now, evaluations=[],
        history={}, method="linear_elapsed_period_average",
        reliability_context={
            "forecast_factors": {"meter_freshness": 100, "solar": 100},
            "financial_factors": {"tariff": 100, "vat": 100},
            "forecast_impact_weight": 100, "financial_impact_weight": 100,
            "billing_period_start": "2026-01-01", "billing_period_end": "2026-12-31",
        },
    )
    assert result["forecast_reliability_percent"] is not None
    assert 0 < result["forecast_reliability_percent"] <= 95
    assert result["forecast_reliability_basis"] == "live_input_and_configuration_quality_and_billing_period_coverage"
    assert result["forecast_reliability_measured_accuracy_percent"] is None


def test_temporal_factor_reduces_score_early_and_never_increases_measured_accuracy():
    model = load("vm_r151_temporal", "forecast_model.py")
    early = model.temporal_reliability_factor(
        now=datetime(2026, 4, 1, tzinfo=timezone.utc),
        period_start="2026-01-01", period_end="2026-12-31",
    )
    late = model.temporal_reliability_factor(
        now=datetime(2026, 12, 31, 0, 30, tzinfo=timezone.utc),
        period_start="2026-01-01", period_end="2026-12-31",
    )
    assert 0 < early["factor"] < late["factor"] < 1
    assert early["ceiling"] == 92.0
    assert late["ceiling"] == 94.0


def test_learning_history_retention_is_three_years_and_adaptation_uses_recent_window():
    source = (ROOT / "sensor.py").read_text(encoding="utf-8")
    assert "timedelta(days=365 * 3)" in source
    assert "recent_evaluations = [item for item in evaluations.values()" in source
    assert '"billing_period_start": period_start_date' in source
    assert '"billing_period_end": end_date' in source


def test_learning_state_normalization_preserves_valid_history_and_metadata():
    import ast
    source = (ROOT / "sensor.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    node = next(item for item in tree.body if isinstance(item, ast.FunctionDef) and item.name == "_normalize_learning_state")
    namespace = {}
    exec(compile(ast.Module(body=[node], type_ignores=[]), "sensor.py", "exec"), namespace)
    normalize = namespace["_normalize_learning_state"]
    saved = {
        "forecasts": {"f1": {"target_hour": "2026-11-26T10:00:00+00:00", "meter_id": "m1", "direction": "consumption"}},
        "evaluations": {"e1": {"target_hour": "2026-11-26T09:00:00+00:00", "meter_id": "m1", "direction": "consumption", "predicted": 1.2, "actual": 1.1}},
        "model_version": 4, "model_scale": 1.03, "custom_metadata": {"keep": True},
    }
    restored = normalize(saved)
    assert restored["forecasts"] == saved["forecasts"]
    assert restored["evaluations"] == saved["evaluations"]
    assert restored["model_version"] == 4
    assert restored["model_scale"] == 1.03
    assert restored["custom_metadata"] == {"keep": True}


def test_learning_state_normalization_drops_only_malformed_rows_not_whole_history():
    import ast
    source = (ROOT / "sensor.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    node = next(item for item in tree.body if isinstance(item, ast.FunctionDef) and item.name == "_normalize_learning_state")
    namespace = {}
    exec(compile(ast.Module(body=[node], type_ignores=[]), "sensor.py", "exec"), namespace)
    restored = namespace["_normalize_learning_state"]({
        "forecasts": {
            "good": {"target_hour": "2026-11-26T10:00:00+00:00", "meter_id": "m1", "direction": "feed_in"},
            "bad": {"meter_id": "m1", "direction": "feed_in"},
        },
        "evaluations": {
            "good": {"target_hour": "2026-11-26T09:00:00+00:00", "meter_id": "m1", "direction": "feed_in", "predicted": 2, "actual": 2},
            "bad": {"target_hour": "2026-11-26T08:00:00+00:00", "meter_id": "m1", "direction": "feed_in"},
        },
    })
    assert list(restored["forecasts"]) == ["good"]
    assert list(restored["evaluations"]) == ["good"]


def test_learning_store_is_stable_across_restarts_and_updates():
    source = (ROOT / "sensor.py").read_text(encoding="utf-8")
    assert 'learning_key = f"{DOMAIN}_{self._entry_id}_{self._direction}_hourly_learning"' in source
    assert 'self._learning_store = Store(hass, 1, learning_key)' in source
    assert "self._learning_state = await self._async_load_learning_state()" in source
    assert "self._learning_state = await self._async_load_learning_state()" in source
    assert 'self._learning_state = {' in source and '"evaluations": evaluations' in source
    assert 'await self._learning_store.async_save(self._learning_state)' in source
    assert 'self._learning_backup_store = Store(hass, 1, f"{learning_key}_backup")' in source
    assert 'await self._learning_backup_store.async_save(self._learning_state)' in source
    assert 'if not primary_has_history and backup_has_history:' in source


def test_recommendation_is_not_gated_by_reliability_and_no_new_entities_are_added():
    source = (ROOT / "sensor.py").read_text(encoding="utf-8")
    card = (ROOT / "frontend" / "verbrauchsmonitor-card.js").read_text(encoding="utf-8")
    assert 'result.get("forecast_recommendation_available")\n                    ),' in source
    assert "and reliability.get(\"forecast_reliability_available\")" not in source
    assert 'const recommendationAvailable = valid(forecastAdvance) && Number.isFinite(Number(forecastAdvance.state)) && recommendationAttributes.forecast_recommendation_available !== false;' in card
    assert 'insufficient_reliability" if result.get("forecast_recommendation_available")' not in source
