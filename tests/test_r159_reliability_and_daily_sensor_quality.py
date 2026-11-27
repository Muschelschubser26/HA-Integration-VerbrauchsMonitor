from datetime import datetime, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

ROOT = Path(__file__).parents[1]
INTEGRATION = ROOT / "custom_components" / "verbrauchsmonitor"
spec = spec_from_file_location("vm_r159_forecast_model", INTEGRATION / "forecast_model.py")
model = module_from_spec(spec)
sys.modules[spec.name] = model
spec.loader.exec_module(model)


def test_initial_history_score_is_confidence_adjusted_and_below_92_for_high_quality_history():
    now = datetime(2026, 11, 26, 17, 0, tzinfo=timezone.utc)
    result = model.resolve_forecast_reliability(
        initial_score=None, initial_created_at=now, now=now, evaluations=[],
        history={"usable": True, "history_months": 24, "sample_count": 700,
                 "coverage_percent": 100, "gap_days_max": 1, "quality": 100},
        method="seasonal_24m",
        reliability_context={"billing_period_start": "2026-08-01", "billing_period_end": "2026-12-31"},
    )
    assert result["forecast_reliability_percent"] < 92
    assert result["forecast_reliability_is_initial"] is True
    assert result["forecast_reliability_initial_evidence_confidence_percent"] == 100
    assert result["forecast_reliability_basis"] == "recorder_history_quality_and_billing_period_coverage"


def test_distinct_meter_history_produces_distinct_initial_scores_without_forced_equal_cap():
    now = datetime(2026, 11, 26, 17, 0, tzinfo=timezone.utc)
    common = {"billing_period_start": "2026-08-01", "billing_period_end": "2026-12-31"}
    consumption = model.resolve_forecast_reliability(
        initial_score=None, initial_created_at=now, now=now, evaluations=[],
        history={"usable": True, "history_months": 24, "sample_count": 600,
                 "coverage_percent": 98, "gap_days_max": 2, "quality": 96},
        method="seasonal_24m", reliability_context=common,
    )
    feed_in = model.resolve_forecast_reliability(
        initial_score=None, initial_created_at=now, now=now, evaluations=[],
        history={"usable": True, "history_months": 12, "sample_count": 180,
                 "coverage_percent": 78, "gap_days_max": 12, "quality": 75},
        method="seasonal_12m", reliability_context=common,
    )
    assert consumption["forecast_reliability_percent"] != feed_in["forecast_reliability_percent"]
    assert consumption["forecast_reliability_percent"] > feed_in["forecast_reliability_percent"]


def test_weighted_error_is_not_dominated_by_zero_export_night_hours():
    evaluations = [
        {"actual": 0.0, "predicted": 0.0, "absolute_error": 0.0, "error": 0.0},
        {"actual": 4.0, "predicted": 3.6, "absolute_error": 0.4, "error": -0.4},
    ] + [
        {"actual": 0.0, "predicted": 0.0, "absolute_error": 0.0, "error": 0.0}
        for _ in range(22)
    ]
    result = model.summarize_evaluations(evaluations)
    assert result["relative_error_percent"] < 10
    assert result["absolute_error_total"] == 0.4


def test_legacy_evaluations_remain_compatible_after_error_metric_change():
    evaluations = [
        {"absolute_error": 0.1, "relative_error_percent": 5.0, "error": 0.1}
        for _ in range(24)
    ]
    result = model.reliability_from_hourly_evaluations(evaluations)
    assert result["available"] is True
    assert result["score"] == 95.0


def test_daily_delta_increases_with_source_reading_and_resets_at_new_baseline():
    delta = INTEGRATION / "sensor.py"
    source = delta.read_text(encoding="utf-8")
    assert '_attr_state_class = "total_increasing"' in source.split(
        "class VerbrauchsMonitorDailyEnergySensor", 1
    )[1].split("class VerbrauchsMonitorBalanceSensor", 1)[0]
    # Daily counter is the cumulative source value minus a persisted local-midnight baseline.
    assert "return round(delta, 3) if delta >= 0 else None" in source
    assert "self._baseline = value" in source
    assert 'self._baseline_date = dt_util.now().date().isoformat()' in source


def test_legacy_short_entity_registry_name_is_migrated_but_custom_name_is_not_overwritten():
    source = (INTEGRATION / "sensor.py").read_text(encoding="utf-8")
    block = source.split("class VerbrauchsMonitorDailyEnergySensor", 1)[1].split(
        "class VerbrauchsMonitorBalanceSensor", 1
    )[0]
    assert '_is_legacy_daily_entity_name(' in block
    assert 'registry.async_update_entity(self.entity_id, name=expected_name)' in block
    assert 'expected_name = _daily_sensor_display_name(self._direction)' in block


def test_daily_delta_helper_returns_rising_values_and_zero_after_new_midnight_baseline():
    import ast
    source = (INTEGRATION / "sensor.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_daily_energy_delta")
    isolated = ast.Module(body=[function], type_ignores=[])
    namespace = {}
    exec(compile(isolated, "sensor_daily_delta_test", "exec"), namespace)
    delta = namespace["_daily_energy_delta"]
    assert delta(120.125, 120.000) == 0.125
    assert delta(120.500, 120.000) == 0.5
    assert delta(120.500, 120.500) == 0.0
    assert delta(119.900, 120.500) is None


def test_forecast_evaluation_records_actual_prediction_horizon():
    created = datetime(2026, 11, 26, 10, 0, tzinfo=timezone.utc)
    target = datetime(2026, 11, 26, 14, 0, tzinfo=timezone.utc)
    record = model.create_hourly_forecast("meter-a", "feed_in", target, 1.2, created_at=created)
    result = model.evaluate_hourly_forecast(record, 1.0)
    assert result["forecast_horizon_hours"] == 4.0


def test_near_term_errors_have_more_influence_than_long_horizon_errors():
    near = {"actual": 1.0, "predicted": 0.2, "absolute_error": 0.8,
            "error": -0.8, "forecast_horizon_hours": 1}
    far = {"actual": 1.0, "predicted": 0.9, "absolute_error": 0.1,
           "error": -0.1, "forecast_horizon_hours": 24}
    near_only = model.summarize_evaluations([near])
    far_only = model.summarize_evaluations([far])
    combined = model.summarize_evaluations([near, far])
    assert combined["relative_error_percent"] > far_only["relative_error_percent"]
    assert combined["relative_error_percent"] > 50
