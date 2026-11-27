"""Regression tests for Beta R123 forecast lifecycle and requested card layout."""
import ast
import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
SENSOR = ROOT / "custom_components/verbrauchsmonitor/sensor.py"
CARD = ROOT / "custom_components/verbrauchsmonitor/frontend/verbrauchsmonitor-card.js"


def _forecast_class():
    tree = ast.parse(SENSOR.read_text(encoding="utf-8"))
    return next(node for node in tree.body if isinstance(node, ast.ClassDef)
                and node.name == "VerbrauchsMonitorForecastSensor")


def test_monthly_forecast_entity_owns_its_learning_refresh_callbacks():
    methods = {node.name for node in _forecast_class().body
               if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    assert "_periodic_learning_state_refresh" in methods
    assert "_async_refresh_learning_state" in methods
    source = SENSOR.read_text(encoding="utf-8")
    assert "self._periodic_learning_state_refresh, timedelta(hours=1)" in source
    assert '"forecasts": {}, "evaluations": {}, "model_version": 1' in source


def test_forecast_setup_never_passes_none_to_home_assistant_event_helpers():
    source = SENSOR.read_text(encoding="utf-8")
    forecast = source.split("class VerbrauchsMonitorForecastSensor", 1)[1]
    setup = forecast.split("@callback\n    def _periodic_learning_state_refresh", 1)[0]
    assert 'hass = self.hass or getattr(self.platform, "hass", None)' in setup
    assert 'if hass is None:' in setup
    assert 'async_track_state_change_event(hass, tracked_entities, self._changed)' in setup
    assert '_async_migrate_entity_id(self, hass)' in setup


def test_forecast_card_places_heading_then_reliability_after_season():
    source = CARD.read_text(encoding="utf-8")
    block = source.split('const forecastBox = `', 1)[1].split('</section>`;', 1)[0]
    positions = [block.index(token) for token in (
        'class="forecast-season"', 'class="forecast-heading"',
        'class="forecast-reliability"', 'class="forecast-balance"',
        'class="forecast-advance',
    )]
    assert positions == sorted(positions)


def test_current_power_row_is_after_billing_period_and_uses_small_compact_style():
    source = CARD.read_text(encoding="utf-8")
    billing = source.split("class VerbrauchsMonitorBillingCard", 1)[1]
    period = billing.index('class="row period-row"')
    power = billing.index('class="current-power"')
    tariff = billing.index('"tariff-row"')
    assert period < power < tariff
    assert '.current-power{display:inline-flex;justify-content:flex-end' in source
    assert 'gap:8px;font-size:10px;line-height:12px' in source
    assert '.period-meta-row{display:flex;align-items:center;justify-content:space-between' in source


def test_tariff_row_has_no_redundant_thin_divider_before_finance_section():
    source = CARD.read_text(encoding="utf-8")
    assert '.tariff-row{border-bottom:0;padding-bottom:2px}' in source


def test_directional_selector_remains_multi_select_and_translated():
    source = (ROOT / "custom_components/verbrauchsmonitor/config_flow.py").read_text(encoding="utf-8")
    assert 'mode=selector.SelectSelectorMode.LIST, multiple=True' in source
    for language in ("de", "en"):
        data = json.loads((ROOT / f"custom_components/verbrauchsmonitor/translations/{language}.json").read_text(encoding="utf-8"))
        labels = data["options"]["step"]["meter_edit"]["data"]
        assert labels["feed_in_directions"]
        assert "Mehrfachauswahl" in labels["feed_in_directions"] if language == "de" else "multiple selection" in labels["feed_in_directions"]
