from pathlib import Path

ROOT = Path(__file__).parents[1]
FLOW = (ROOT / "custom_components/verbrauchsmonitor/config_flow.py").read_text(encoding="utf-8")
SENSOR = (ROOT / "custom_components/verbrauchsmonitor/sensor.py").read_text(encoding="utf-8")


def test_reset_store_keys_match_sensor_store_keys():
    # Meter sensor instances use meter.id as their synthetic entry_id.
    assert 'entry_id=meter.get("id", entry.entry_id)' in SENSOR
    assert 'f"{DOMAIN}_daily_{self._entry_id}_{self._direction}"' in SENSOR
    assert 'f"{DOMAIN}_{self._period}_{self._entry_id}_{self._direction}"' in SENSOR
    assert 'f"verbrauchsmonitor_daily_{meter_id}_{direction}"' in FLOW
    assert 'f"verbrauchsmonitor_{period}_{meter_id}_{direction}"' in FLOW


def test_period_reset_forces_config_entry_options_change_for_sensor_reload():
    assert 'options["_period_reset_generation"] = dt_util.utcnow().isoformat()' in FLOW
    assert "forces Home Assistant to reload the" in FLOW


def test_period_reset_persists_previous_store_snapshot_before_writes():
    backup = FLOW.index('f"{DOMAIN}_period_reset_backup"')
    first_write = FLOW.index('await Store(self.hass, 1, key).async_save(payload)', backup)
    assert backup < first_write
    assert '"stores": old_payloads' in FLOW


def test_dependency_description_checks_shared_source_entities():
    assert "def _period_reset_dependency_text" in FLOW
    assert 'meter.get("consumption_entity") == source' in FLOW
    assert 'meter.get("feed_in_entity") == source' in FLOW
    assert "Gemeinsam verwendete Messquellen erkannt" in FLOW
