from pathlib import Path

ROOT = Path(__file__).parents[1]
INTEGRATION = ROOT / "custom_components" / "verbrauchsmonitor"


def test_each_configured_direction_builds_month_and_year_sensors():
    source = (INTEGRATION / "sensor.py").read_text(encoding="utf-8")
    assert 'VerbrauchsMonitorPeriodEnergySensor(entry, "consumption", "month")' in source
    assert 'VerbrauchsMonitorPeriodEnergySensor(entry, "consumption", "year")' in source
    assert 'VerbrauchsMonitorPeriodEnergySensor(entry, "feed_in", "month")' in source
    assert 'VerbrauchsMonitorPeriodEnergySensor(entry, "feed_in", "year")' in source


def test_period_sensors_persist_baselines_offsets_and_local_period_boundaries():
    source = (INTEGRATION / "sensor.py").read_text(encoding="utf-8")
    assert 'Store(self.hass, 1, f"{DOMAIN}_{self._period}_{self._entry_id}_{self._direction}")' in source
    assert 'hour=0, minute=0, second=5' in source
    assert 'replace(month=1, day=1)' in source
    assert 'replace(day=1)' in source
    assert '"offset": self._offset' in source
    assert "self._confirmed_meter_change(self._current)" in source
    assert "rückläufiger Messwert ignoriert" in source
    assert "end_key = \"consumption_reading\"" in source
    assert '"partial_period": self._partial' in source


def test_period_sensor_uses_energy_metadata_and_german_entity_ids():
    source = (INTEGRATION / "sensor.py").read_text(encoding="utf-8")
    naming = (INTEGRATION / "naming.py").read_text(encoding="utf-8")
    assert '_attr_device_class = "energy"' in source
    assert '_attr_state_class = "total_increasing"' in source
    for fragment in ("_monatsverbrauch", "_jahresverbrauch", "_monatseinspeisung", "_jahreseinspeisung"):
        assert fragment in naming
