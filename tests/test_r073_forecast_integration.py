from pathlib import Path

ROOT = Path(__file__).parents[1]
INTEGRATION = ROOT / "custom_components" / "verbrauchsmonitor"

def test_forecast_is_individually_configurable_and_displayed():
    flow = (INTEGRATION / "config_flow.py").read_text()
    sensor = (INTEGRATION / "sensor.py").read_text()
    card = (INTEGRATION / "frontend" / "verbrauchsmonitor-card.js").read_text()
    assert '"forecast", "settlement", "billing"' in flow
    assert '"forecast_consumption_enabled"' in flow
    assert '"forecast_feed_in_enabled"' in flow
    assert 'mode=selector.SelectSelectorMode.LIST, multiple=True' in flow
    assert 'feed_in_monthly_advance' in flow
    assert 'VerbrauchsMonitorForecastSensor' in sensor
    assert "_jahresbilanz_prognose" in sensor and "_monatsabschlag_prognose" in sensor
    assert 'consumption_forecast_annual_balance' in card
    assert 'feed_in_forecast_monthly_advance' in card

def test_forecast_translation_files_are_complete_and_german_fallback_matches():
    import json
    strings = json.loads((INTEGRATION / "strings.json").read_text())
    german = json.loads((INTEGRATION / "translations/de.json").read_text())
    english = json.loads((INTEGRATION / "translations/en.json").read_text())
    assert strings == german
    for lang in (german, english):
        assert "forecast" in lang["options"]["step"]
        assert "enabled_forecasts" in lang["options"]["step"]["forecast"]["data"]
