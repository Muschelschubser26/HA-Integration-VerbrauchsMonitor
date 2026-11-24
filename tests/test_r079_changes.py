import json
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_forecast_reset_scope_is_present_and_localized():
    flow = (ROOT / "custom_components/verbrauchsmonitor/config_flow.py").read_text()
    assert '"forecasts"' in flow
    assert 'meter["forecast_consumption_enabled"] = False' in flow
    de = json.loads((ROOT / "custom_components/verbrauchsmonitor/translations/de.json").read_text())
    en = json.loads((ROOT / "custom_components/verbrauchsmonitor/translations/en.json").read_text())
    assert de["options"]["step"]["data_management"]["data"]["forecasts"] == "Prognose zurücksetzen"
    assert en["options"]["step"]["data_management"]["data"]["forecasts"] == "Reset forecasts"


def test_forecast_card_order_and_start_month():
    card = (ROOT / "custom_components/verbrauchsmonitor/frontend/verbrauchsmonitor-card.js").read_text()
    assert 'class="forecast-trend ${advanceTrend}"' in card
    assert 'Möglicher Monatsabschlag:' in card
    assert 'forecast-start-month' in card
    assert 'forecastReliability >= 80' in card
    assert 'forecastReliability >= 50' in card


def test_season_is_automatically_calculated_from_home_assistant_location():
    flow = (ROOT / "custom_components/verbrauchsmonitor/config_flow.py").read_text()
    sensor = (ROOT / "custom_components/verbrauchsmonitor/sensor.py").read_text()
    assert "current_ha_season" in flow
    assert "current_ha_season" in sensor
    forecast_start = flow.index("    async def async_step_forecast(")
    forecast_end = flow.index("    async def async_step_billing(", forecast_start)
    forecast_flow = flow[forecast_start:forecast_end]
    assert 'vol.Required("season_mode"' not in forecast_flow
    assert 'vol.Required("manual_season"' not in forecast_flow
