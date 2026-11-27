from pathlib import Path


def test_period_reset_scope_and_selection_are_available():
    root = Path(__file__).parents[1]
    flow = (root / "custom_components/verbrauchsmonitor/config_flow.py").read_text(encoding="utf-8")
    assert '"periods"' in flow
    assert "async_step_period_reset_select" in flow
    assert '"selected_periods"' in flow
    assert "verbrauchsmonitor_daily_" in flow
    for period in ("week", "month", "year"):
        assert f"verbrauchsmonitor_{{period}}_" in flow


def test_period_reset_preserves_meter_and_billing_history():
    root = Path(__file__).parents[1]
    flow = (root / "custom_components/verbrauchsmonitor/config_flow.py").read_text(encoding="utf-8")
    method = flow.split("async def _async_reset_period_stores", 1)[1].split("async def async_step_forecast_reset_select", 1)[0]
    assert "physical_meter_periods" not in method
    assert 'data["bookings"]' not in method
    assert '"offset": 0.0' in method
    assert '"last_current": reading' in method
