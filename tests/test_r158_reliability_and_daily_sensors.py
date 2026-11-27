from datetime import datetime, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

ROOT = Path(__file__).parents[1] / "custom_components" / "verbrauchsmonitor"

def load(name, filename):
    spec = spec_from_file_location(name, ROOT / filename)
    module = module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

model = load("vm_r158_forecast_model", "forecast_model.py")


def test_live_meter_and_financial_evidence_produces_initial_score_without_long_recorder_history():
    now = datetime(2026, 11, 26, 17, 0, tzinfo=timezone.utc)
    result = model.resolve_forecast_reliability(
        initial_score=None, initial_created_at=now, now=now, evaluations=[],
        history={"usable": False, "history_months": 0, "sample_count": 0,
                 "coverage_percent": 0, "gap_days_max": 0, "quality": 0},
        method="linear_elapsed_period_average",
        reliability_context={
            "billing_period_start": "2026-08-01",
            "billing_period_end": "2026-12-31",
            "forecast_factors": {"meter_freshness": 99.0},
            "financial_factors": {"valid_energy_tariff": 100.0,
                                  "valid_billing_period": 100.0,
                                  "valid_vat": 100.0},
        },
    )
    assert result["forecast_reliability_available"] is True
    assert 0 < result["forecast_reliability_percent"] <= 92
    assert result["forecast_reliability_basis"] == "live_input_and_configuration_quality_and_billing_period_coverage"
    assert result["forecast_reliability_measured_accuracy_percent"] is None


def test_missing_optional_weather_inputs_do_not_create_or_reduce_score():
    now = datetime(2026, 11, 26, 17, 0, tzinfo=timezone.utc)
    context = {"billing_period_start": "2026-08-01", "billing_period_end": "2026-12-31",
               "forecast_factors": {"meter_freshness": 90.0},
               "financial_factors": {"valid_energy_tariff": 100.0}}
    result = model.resolve_forecast_reliability(
        initial_score=None, initial_created_at=now, now=now, evaluations=[],
        history={}, method="linear_elapsed_period_average", reliability_context=context)
    assert result["forecast_reliability_available"] is True
    assert result["forecast_reliability_percent"] > 0


def test_reliability_does_not_exceed_time_dependent_ceiling():
    now = datetime(2026, 12, 31, 22, 30, tzinfo=timezone.utc)
    result = model.resolve_forecast_reliability(
        initial_score=None, initial_created_at=now, now=now, evaluations=[],
        history={}, method="linear_elapsed_period_average",
        reliability_context={"billing_period_start": "2026-01-01",
                             "billing_period_end": "2026-12-31",
                             "forecast_factors": {"meter_freshness": 100.0},
                             "financial_factors": {"valid_energy_tariff": 100.0}})
    assert result["forecast_reliability_percent"] <= 95
    assert result["forecast_reliability_temporal_ceiling"] == 94


def test_daily_sensor_corrects_known_generated_registry_name_variants_and_preserves_manual_names():
    source = (ROOT / "sensor.py").read_text(encoding="utf-8")
    block = source.split("class VerbrauchsMonitorDailyEnergySensor", 1)[1].split("class VerbrauchsMonitorBalanceSensor", 1)[0]
    assert '_is_legacy_daily_entity_name(' in block
    assert 'def _is_legacy_daily_entity_name' in source
    assert '_daily_sensor_display_name(self._direction)' in block
    assert 'registry.async_update_entity(self.entity_id, name=expected_name)' in block


def test_daily_baseline_has_long_term_statistics_fallback_and_never_invents_zero():
    source = (ROOT / "sensor.py").read_text(encoding="utf-8")
    block = source.split("async def _restore_midnight_baseline", 1)[1].split("async def _save_baseline", 1)[0]
    assert "statistics.statistics_during_period" in block
    assert '"sum"' in block
    assert "_infer_daily_baseline_from_statistics(current_reading, points)" in block
    assert "never invent" in block.lower()


def test_daily_baseline_inference_requires_two_monotonic_statistics_points():
    sensor_source = (ROOT / "sensor.py").read_text(encoding="utf-8")
    assert "def _infer_daily_baseline_from_statistics" in sensor_source
    # Exercise the pure helper without importing Home Assistant.
    namespace = {}
    start = sensor_source.index("def _infer_daily_baseline_from_statistics")
    end = sensor_source.index("class VerbrauchsMonitorDailyEnergySensor", start)
    block = sensor_source[start:end]
    exec("from __future__ import annotations\n" + block, namespace)
    helper = namespace["_infer_daily_baseline_from_statistics"]
    from datetime import datetime, timezone
    t1 = datetime(2026, 11, 26, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 11, 26, 17, 0, tzinfo=timezone.utc)
    assert helper(5036.761, [(t1, 1200.0), (t2, 1201.761)]) == 5035.0
    assert helper(5036.761, [(t1, 1200.0)]) is None
    assert helper(5036.761, [(t1, 1201.0), (t2, 1200.0)]) is None
    assert helper(0.5, [(t1, 1200.0), (t2, 1201.0)]) is None
