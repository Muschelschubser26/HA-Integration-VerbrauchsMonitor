from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

ROOT = Path(__file__).parents[1] / "custom_components" / "verbrauchsmonitor"


def load_module(name, filename):
    spec = spec_from_file_location(name, ROOT / filename)
    module = module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_future_advance_notice_suppresses_same_amount_continuation():
    database = load_module("vm_r146_database_helper", "database.py")
    rows = [
        {"meter_id": "m1", "direction": "consumption", "source": "manual", "month": "2027-01", "amount": 220, "superseded": False},
        {"meter_id": "m1", "direction": "consumption", "source": "manual", "month": "2027-02", "amount": 220, "superseded": False},
        {"meter_id": "m1", "direction": "consumption", "source": "manual", "month": "2027-03", "amount": 250, "superseded": False},
        {"meter_id": "m1", "direction": "consumption", "source": "manual", "month": "2027-04", "amount": 250, "superseded": False},
    ]
    # Before January: announce the January transition.
    result = database.next_distinct_monthly_advance(
        rows, meter_id="m1", direction="consumption", after_month="2026-12", current_amount=200
    )
    assert result["month"] == "2027-01"
    # In January the same amount is now active: do not show a false February notice.
    result = database.next_distinct_monthly_advance(
        rows, meter_id="m1", direction="consumption", after_month="2027-01", current_amount=220
    )
    assert result["month"] == "2027-03"
    # Once March's amount is active, all repeated continuation rows disappear.
    assert database.next_distinct_monthly_advance(
        rows, meter_id="m1", direction="consumption", after_month="2027-03", current_amount=250
    ) is None


def test_live_input_quality_without_forecast_actual_comparisons_has_no_score():
    model = load_module("vm_r146_forecast_model", "forecast_model.py")
    created = __import__("datetime").datetime(2026, 11, 26, 12, 0, tzinfo=__import__("datetime").timezone.utc)
    result = model.resolve_forecast_reliability(
        initial_score=None,
        initial_created_at=created,
        now=created,
        evaluations=[],
        history={},
        method="linear_elapsed_period_average",
        reliability_context={
            "forecast_factors": {"meter_freshness": 92.0},
            "financial_factors": {"valid_energy_tariff": 100.0, "valid_billing_period": 100.0},
            "forecast_impact_weight": 529.14,
            "financial_impact_weight": 77.25,
        },
    )
    assert result["forecast_reliability_available"] is False
    assert result["forecast_reliability_percent"] is None
    assert result["forecast_hourly_evaluation_count"] == 0
    assert result["forecast_reliability_pending"] is True


def test_real_forecast_euro_components_produce_impact_weights_but_no_unverified_score():
    reliability = load_module("vm_r147_reliability_weights", "reliability.py")
    forecast_result = {
        "forecast_energy_cost_total_eur": 529.20,
        "annual_value_eur": 606.45,
        "booked_advances_eur": 734.00,
        "future_scheduled_advances_eur": 400.00,
        "additional_payments_eur": 0.0,
        "credits_eur": 0.0,
        "corrections_eur": -66.00,
    }
    weights = reliability.derive_impact_weights(forecast_result)
    assert weights["forecast_impact_weight"] == 529.20
    assert weights["financial_impact_weight"] == 1806.45

    model = load_module("vm_r147_forecast_model", "forecast_model.py")
    from datetime import datetime, timezone
    now = datetime(2026, 11, 26, 14, 0, tzinfo=timezone.utc)
    result = model.resolve_forecast_reliability(
        initial_score=None, initial_created_at=now, now=now,
        evaluations=[], history={}, method="linear_elapsed_period_average",
        reliability_context={
            "forecast_factors": {"meter_freshness": 92.0},
            "financial_factors": {
                "valid_energy_tariff": 100.0,
                "valid_billing_period": 100.0,
                "valid_vat": 100.0,
            },
            **weights,
        },
    )
    assert result["forecast_reliability_available"] is False
    assert result["forecast_reliability_percent"] is None
    assert result["forecast_reliability_modules"] == {}
    assert result["forecast_hourly_evaluation_count"] == 0


def test_reliability_impact_weights_do_not_invent_weights_for_zero_financial_impact():
    reliability = load_module("vm_r147_reliability_zero_weights", "reliability.py")
    weights = reliability.derive_impact_weights({
        "forecast_energy_cost_total_eur": 0,
        "annual_value_eur": 0,
        "booked_advances_eur": 0,
        "future_scheduled_advances_eur": 0,
    })
    assert weights == {"forecast_impact_weight": 0.0, "financial_impact_weight": 0.0}


def test_sensor_uses_shared_financial_impact_weight_derivation():
    source = (ROOT / "sensor.py").read_text(encoding="utf-8")
    assert "derive_impact_weights(result)" in source
    assert "**impact_weights" in source


def test_actual_forecast_result_flows_to_numeric_reliability_without_history():
    from datetime import date, datetime
    from zoneinfo import ZoneInfo
    forecast = load_module("vm_r147_real_forecast", "forecast.py")
    reliability = load_module("vm_r147_real_reliability", "reliability.py")
    model = load_module("vm_r147_real_model", "forecast_model.py")
    now = datetime(2026, 11, 26, 15, 0, tzinfo=ZoneInfo("Europe/Berlin"))
    calculated = forecast.calculate_forecast(
        direction="consumption",
        current_reading="5035.278",
        baseline_reading="3164.000",
        period_start="2026-08-01",
        today=date(2026, 11, 26),
        price_net="28.28",
        vat_rate="19",
        annual_base_price_net="239.62",
        booked_advances="734.00",
        future_scheduled_advances="200.00",
        as_of=now,
        period_end_override="2026-12-31",
    )
    weights = reliability.derive_impact_weights(calculated)
    resolved = model.resolve_forecast_reliability(
        initial_score=None,
        initial_created_at=now,
        now=now,
        evaluations=[],
        history={},
        method=calculated["method"],
        reliability_context={
            "forecast_factors": {"meter_freshness": 99.0},
            "financial_factors": {
                "valid_energy_tariff": 100.0,
                "valid_billing_period": 100.0,
                "valid_vat": 100.0,
            },
            **weights,
        },
    )
    assert calculated["forecast_energy_cost_total_eur"] > 0
    assert calculated["annual_value_eur"] > 0
    assert weights["forecast_impact_weight"] > 0
    assert weights["financial_impact_weight"] > 0
    assert resolved["forecast_reliability_available"] is False
    assert resolved["forecast_reliability_percent"] is None
    assert resolved["forecast_reliability_pending"] is True
