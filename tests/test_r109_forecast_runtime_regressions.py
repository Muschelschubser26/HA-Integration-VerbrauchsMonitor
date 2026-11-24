"""Regression checks for forecast entity creation, state updates and diagnostics."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SENSOR = ROOT / "custom_components/verbrauchsmonitor/sensor.py"
CARD = ROOT / "custom_components/verbrauchsmonitor/frontend/verbrauchsmonitor-card.js"


def test_forecast_sensor_entity_is_created_for_enabled_consumption_by_default():
    source = SENSOR.read_text(encoding="utf-8")
    assert 'if entry.data.get("forecast_consumption_enabled", True):' in source
    assert 'entities.extend(_build_forecast_entities(entry, "consumption"))' in source


def test_forecast_sensor_entity_roles_match_dashboard_lookup():
    source = SENSOR.read_text(encoding="utf-8")
    card = CARD.read_text(encoding="utf-8")
    assert 'f"{direction}_forecast_{metric}"' in source
    for role in ("consumption_forecast_annual_balance", "consumption_forecast_monthly_advance"):
        assert role in card
    assert 'forecast_status"] = "source_unavailable"' in source
    assert 'forecast_status"] = "calculation_error"' in source


def test_forecast_sensor_refreshes_after_startup_and_on_source_change():
    source = SENSOR.read_text(encoding="utf-8")
    assert "await self._async_refresh_history()" in source
    assert "self.async_write_ha_state()" in source
    assert "async_track_state_change_event(self.hass, [self._source], self._changed)" in source


def test_forecast_runtime_rounding_constant_is_imported_at_module_scope():
    tree = ast.parse(SENSOR.read_text(encoding="utf-8"))
    assert any(
        isinstance(node, ast.ImportFrom)
        and node.module == "decimal"
        and any(alias.name == "ROUND_HALF_UP" for alias in node.names)
        for node in tree.body
    )


def test_forecast_runtime_errors_are_logged_and_exposed_in_sensor_attributes():
    source = SENSOR.read_text(encoding="utf-8")
    assert 'Prognoseberechnung fehlgeschlagen' in source
    assert 'forecast_error"] = f"{type(err).__name__}: {err}"' in source
