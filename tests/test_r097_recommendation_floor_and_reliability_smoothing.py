from datetime import date, datetime, timezone
from decimal import Decimal
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

ROOT = Path(__file__).parents[1]
FORECAST_PATH = ROOT / "custom_components" / "verbrauchsmonitor" / "forecast.py"


def _load_forecast():
    spec = spec_from_file_location("vm_r097_forecast", FORECAST_PATH)
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_final_three_payment_dates_keep_at_least_70_percent_of_configured_advance():
    forecast = _load_forecast()
    result = forecast.calculate_forecast(
        direction="consumption", current_reading="1000", baseline_reading="1000",
        period_start="2026-08-01", today=date(2026, 11, 23),
        price_net="0", vat_rate=19, annual_base_price_net="0",
        monthly_advance_net="168.06722689", period_months=5,
        booked_advances="800", future_scheduled_advances="200",
    )
    assert result["months_remaining"] == 1
    assert result["configured_monthly_advance_eur"] == 200.0
    assert result["advance_recommendation_final_period_protection"] is True
    assert result["advance_recommendation_minimum_eur"] == 140.0
    assert result["recommended_monthly_advance_eur"] == 140.0


def test_recommendation_is_not_reduced_below_70_percent_of_average_total_costs():
    forecast = _load_forecast()
    result = forecast.calculate_forecast(
        direction="consumption", current_reading="2000", baseline_reading="1000",
        period_start="2026-08-01", today=date(2026, 11, 23),
        price_net="30", vat_rate=19, annual_base_price_net="240",
        monthly_advance_net="100", period_months=5,
        booked_advances="400", future_scheduled_advances="100",
    )
    assert result["recommended_monthly_advance_eur"] >= result["advance_recommendation_minimum_eur"]
    assert result["advance_recommendation_minimum_eur"] >= 0.70 * (
        result["accrued_energy_cost_eur"] + result["accrued_base_price_eur"]
    ) / (result["basis_days"] / 30.436875) - 0.01


def test_reliability_target_has_at_least_40_percent_foundation():
    forecast = _load_forecast()
    result = forecast.reliability_score(history={
        "history_months": 0, "coverage_percent": 0, "gap_days_max": 999,
        "quality": 0, "usable": False,
    }, method="linear_elapsed_period_average")
    assert result["forecast_reliability_percent"] >= 40


def test_reliability_moves_gradually_and_respects_one_point_per_day():
    forecast = _load_forecast()
    start = datetime(2026, 11, 1, tzinfo=timezone.utc)
    state = {"score": 43.6, "last_evaluated": start.isoformat()}
    history = {
        "history_months": 24, "coverage_percent": 100, "gap_days_max": 0,
        "quality": 100, "usable": True, "two_cycle_months": 12,
    }
    after_one_hour = forecast.update_reliability_state(
        state, history=history, method="seasonal_24m",
        now=datetime(2026, 11, 1, 1, tzinfo=timezone.utc),
    )
    assert 43.6 <= after_one_hour["score"] <= 43.7
    after_ten_days = forecast.update_reliability_state(
        state, history=history, method="seasonal_24m",
        now=datetime(2026, 11, 11, tzinfo=timezone.utc),
    )
    assert after_ten_days["score"] <= 53.6
    assert after_ten_days["score"] > 43.6
    after_one_day = forecast.update_reliability_state(
        state, history=history, method="seasonal_24m",
        now=datetime(2026, 11, 2, tzinfo=timezone.utc),
    )
    assert after_one_day["score"] == 44.6


def test_meter_state_change_does_not_reload_full_recorder_history():
    source = (ROOT / "custom_components" / "verbrauchsmonitor" / "sensor.py").read_text()
    import ast
    tree = ast.parse(source)
    callback_node = next(
        node for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "_changed"
    )
    callback = ast.get_source_segment(source, callback_node)
    assert "async_write_ha_state()" in callback
    assert "_async_refresh_history" not in callback
