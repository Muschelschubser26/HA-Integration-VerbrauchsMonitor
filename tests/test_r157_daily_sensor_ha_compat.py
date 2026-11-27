from pathlib import Path

ROOT = Path(__file__).parents[1]
SOURCE = (ROOT / "custom_components/verbrauchsmonitor/sensor.py").read_text(encoding="utf-8")

def test_daily_energy_uses_supported_energy_state_class():
    block = SOURCE.split("class VerbrauchsMonitorDailyEnergySensor", 1)[1].split("class VerbrauchsMonitorBalanceSensor", 1)[0]
    assert '_attr_state_class = "total_increasing"' in block
    assert '_attr_device_class = "energy"' in block

def test_daily_recorder_query_uses_recorder_executor():
    block = SOURCE.split("async def _restore_midnight_baseline", 1)[1].split("async def _save_baseline", 1)[0]
    assert "from homeassistant.components.recorder import get_instance, history" in block
    assert "recorder_instance = get_instance(self.hass)" in block
    assert "recorder_instance.async_add_executor_job(" in block
    assert "self.hass.async_add_executor_job(" not in block

def test_only_known_generated_short_registry_name_is_corrected():
    block = SOURCE.split("class VerbrauchsMonitorDailyEnergySensor", 1)[1].split("class VerbrauchsMonitorBalanceSensor", 1)[0]
    assert '_is_legacy_daily_entity_name(' in block
    assert 'def _is_legacy_daily_entity_name' in SOURCE
    assert '_daily_sensor_display_name(self._direction)' in block
