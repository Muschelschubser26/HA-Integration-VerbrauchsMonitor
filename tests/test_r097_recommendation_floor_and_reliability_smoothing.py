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


def test_final_payment_month_does_not_generate_a_new_monthly_advance_recommendation():
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
    assert result["advance_recommendation_minimum_eur"] == 0.0
    assert result["recommended_monthly_advance_eur"] == 0.0
    assert result["forecast_recommendation_available"] is False


def test_recommendation_never_uses_an_artificial_minimum_floor():
    forecast = _load_forecast()
    result = forecast.calculate_forecast(
        direction="consumption", current_reading="2000", baseline_reading="1000",
        period_start="2026-08-01", today=date(2026, 11, 23),
        price_net="30", vat_rate=19, annual_base_price_net="240",
        monthly_advance_net="100", period_months=5,
        booked_advances="400", future_scheduled_advances="100",
    )
    assert result["advance_recommendation_minimum_eur"] == 0.0
    assert result["recommended_monthly_advance_eur"] == 0.0
    assert result["forecast_recommendation_available"] is False


def test_reliability_is_unavailable_without_sufficient_history():
    forecast = _load_forecast()
    result = forecast.reliability_score(history={
        "history_months": 0, "coverage_percent": 0, "gap_days_max": 999,
        "quality": 0, "usable": False,
    }, method="linear_elapsed_period_average")
    assert result["forecast_reliability_percent"] is None


def test_reliability_recomputes_directly_from_current_evidence():
    forecast = _load_forecast()
    start = datetime(2026, 11, 1, tzinfo=timezone.utc)
    history = {"history_months": 24, "coverage_percent": 100, "gap_days_max": 1,
               "quality": 100, "usable": True, "sample_count": 300}
    state = forecast.update_reliability_state(
        {"score": 43.6, "last_evaluated": start.isoformat()},
        history=history, method="seasonal_24m", now=start,
    )
    assert state["score"] == forecast.reliability_score(history=history, method="seasonal_24m")["forecast_reliability_percent"]


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
