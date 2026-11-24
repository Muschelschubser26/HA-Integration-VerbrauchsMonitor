import json
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_dynamic_month_fields_use_localized_month_and_year_labels():
    flow = (ROOT / "custom_components/verbrauchsmonitor/config_flow.py").read_text()
    assert "def _month_field_label(month: str, hass) -> str" in flow
    assert 'return f"{names[parsed.month - 1]} {parsed.year}"' in flow
    assert "_month_field_label(month, self.hass)" in flow
    assert 'user_input[field_label]' in flow


def test_forecast_card_matches_confirmed_layout():
    card = (ROOT / "custom_components/verbrauchsmonitor/frontend/verbrauchsmonitor-card.js").read_text()
    assert 'Prognose zum Abrechnungsende am' in card
    assert 'class="forecast-reliability"' in card
    assert 'Zuverlässigkeit:' in card
    assert 'background:#fff' in card
    assert 'border:1.5px solid #d5d5d5' in card
    assert 'forecast-separator' not in card
    assert 'per month' in card


def test_device_manufacturer_and_package_metadata():
    sensor = (ROOT / "custom_components/verbrauchsmonitor/sensor.py").read_text()
    assert sensor.count('"manufacturer": "Muschelschubser26 & ChatGPT"') == 3
    manifest = json.loads((ROOT / "custom_components/verbrauchsmonitor/manifest.json").read_text())
    hacs = json.loads((ROOT / "hacs.json").read_text())
    assert manifest["domain"] == "verbrauchsmonitor"
    assert manifest["documentation"] == "https://github.com/Muschelschubser26/HA-Integration-VerbrauchsMonitor-Beta"
    assert hacs["name"] == "VerbrauchsMonitor"


def test_reliability_uses_history_quality_and_method():
    forecast = (ROOT / "custom_components/verbrauchsmonitor/forecast.py").read_text()
    sensor = (ROOT / "custom_components/verbrauchsmonitor/sensor.py").read_text()
    assert "def reliability_score" in forecast
    assert "history.get_significant_states" in sensor
    assert "forecast_reliability_basis" in forecast
    assert "forecast_history_used" in sensor
