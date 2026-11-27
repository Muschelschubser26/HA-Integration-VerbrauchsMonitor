from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
import ast
import json
import sys
from importlib.util import module_from_spec, spec_from_file_location

ROOT = Path(__file__).parents[1] / "custom_components" / "verbrauchsmonitor"


def load_module(name, filename):
    spec = spec_from_file_location(name, ROOT / filename)
    module = module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_forecast_menu_and_optional_environment_selectors_are_configured():
    source = (ROOT / "config_flow.py").read_text()
    assert "CONF_OUTDOOR_TEMPERATURE_ENTITY" in source
    assert "CONF_OUTDOOR_ILLUMINANCE_ENTITY" in source
    assert "CONF_OUTDOOR_WIND_DIRECTION_ENTITY" in source
    assert "CONF_DAILY_PRECIPITATION_ENTITY" in source
    assert "CONF_OUTDOOR_HUMIDITY_ENTITY" in source
    assert 'selector.EntitySelectorConfig(domain="sensor")' in source
    assert 'options_update.pop(key, None)' in source
    assert '"forecast": "Prognose & Zuverlässigkeit"' in (ROOT / "strings.json").read_text()


def test_optional_environment_sensor_quality_factors_are_omitted_or_scored():
    sensor = load_module("vm_r150_reliability_helper", "reliability.py")
    now = datetime(2026, 11, 26, 12, 0, tzinfo=timezone.utc)

    states = {
        "sensor.outdoor_temp": SimpleNamespace(state="8.5", last_updated=now - timedelta(hours=2)),
        "sensor.outdoor_brightness": SimpleNamespace(state="12000", last_updated=now - timedelta(hours=1)),
        "sensor.wind_direction": SimpleNamespace(state="SW", last_updated=now - timedelta(hours=1)),
        "sensor.rain_today": SimpleNamespace(state="1.2", last_updated=now - timedelta(hours=3)),
        "sensor.humidity": SimpleNamespace(state="82", last_updated=now - timedelta(hours=4)),
        "sensor.invalid_humidity": SimpleNamespace(state="150", last_updated=now),
    }
    hass = SimpleNamespace(states=SimpleNamespace(get=lambda entity_id: states.get(entity_id)))
    configured = {
        "outdoor_temperature_entity": "sensor.outdoor_temp",
        "outdoor_illuminance_entity": "sensor.outdoor_brightness",
        "outdoor_wind_direction_entity": "sensor.wind_direction",
        "daily_precipitation_entity": "sensor.rain_today",
        "outdoor_humidity_entity": "sensor.humidity",
    }
    result = sensor.environmental_reliability_factors(hass, configured, now)
    assert set(result) == {
        "outdoor_temperature", "outdoor_illuminance", "wind_direction",
        "daily_precipitation", "outdoor_humidity",
    }
    assert all(0 <= value <= 100 for value in result.values())
    assert result["outdoor_temperature"] < 100
    assert sensor.environmental_reliability_factors(hass, {}, now) == {}
    assert sensor.environmental_reliability_factors(
        hass, {"outdoor_humidity_entity": "sensor.invalid_humidity"}, now
    ) == {}


def test_environmental_factor_refresh_is_triggered_by_optional_entity_changes():
    source = (ROOT / "sensor.py").read_text()
    assert "tracked_entities = list(dict.fromkeys([self._source, *self._environment_entities]))" in source
    assert "async_track_state_change_event(hass, tracked_entities, self._changed)" in source


def test_de_and_en_forecast_reliability_translations_are_synchronized():
    de = json.loads((ROOT / "translations" / "de.json").read_text())
    en = json.loads((ROOT / "translations" / "en.json").read_text())
    for key in (
        "outdoor_temperature_entity", "outdoor_illuminance_entity",
        "outdoor_wind_direction_entity", "daily_precipitation_entity",
        "outdoor_humidity_entity",
    ):
        assert key in de["options"]["step"]["forecast"]["data"]
        assert key in en["options"]["step"]["forecast"]["data"]
