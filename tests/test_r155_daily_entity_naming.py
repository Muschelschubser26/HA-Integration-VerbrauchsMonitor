import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "custom_components" / "verbrauchsmonitor" / "naming.py"
SPEC = importlib.util.spec_from_file_location("vm_naming_r155", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_daily_entity_ids_are_direction_specific_and_stable():
    ids = MODULE.meter_entity_object_ids("Hauszähler")
    assert ids["consumption_today"] == "verbrauchsmonitor_hauszahler_tagesverbrauch"
    assert ids["feed_in_today"] == "verbrauchsmonitor_hauszahler_tageseinspeisung"


def test_daily_delta_uses_cumulative_difference_and_rejects_counter_reset():
    sensor_path = Path(__file__).parents[1] / "custom_components" / "verbrauchsmonitor" / "sensor.py"
    source = sensor_path.read_text(encoding="utf-8")
    assert "def _daily_energy_delta(current: float | None, baseline: float | None)" in source
    assert "return round(delta, 3) if delta >= 0 else None" in source
    assert "Store(self.hass, 1, f\"{DOMAIN}_daily_" in source
