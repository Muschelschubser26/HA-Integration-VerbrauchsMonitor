"""Behavioral regression tests for daily energy sensor naming and baselines."""
from pathlib import Path

ROOT = Path(__file__).parents[1]
SOURCE = (ROOT / "custom_components/verbrauchsmonitor/sensor.py").read_text(encoding="utf-8")


def _load_helpers():
    start = SOURCE.index("def _daily_sensor_display_name")
    end = SOURCE.index("def _infer_daily_baseline_from_statistics", start)
    namespace = {}
    exec("from __future__ import annotations\n" + SOURCE[start:end], namespace)
    return namespace


def test_daily_sensor_names_are_exactly_requested_without_today_suffix():
    helpers = _load_helpers()
    assert helpers["_daily_sensor_display_name"]("consumption") == "TagesVerbrauch"
    assert helpers["_daily_sensor_display_name"]("feed_in") == "TagesEinspeisung"


def test_known_r160_registry_names_are_migrated_to_exact_names():
    block = SOURCE.split("class VerbrauchsMonitorDailyEnergySensor", 1)[1].split(
        "class VerbrauchsMonitorBalanceSensor", 1
    )[0]
    assert '_is_legacy_daily_entity_name(' in block
    assert 'registry.async_update_entity(self.entity_id, name=expected_name)' in block
    assert "expected_name = _daily_sensor_display_name(self._direction)" in block


def test_current_meter_reading_can_initialize_a_disclosed_partial_day_baseline():
    helpers = _load_helpers()
    baseline, partial = helpers["_daily_initial_baseline"](5037.085)
    assert baseline == 5037.085
    assert partial is True
    assert helpers["_daily_initial_baseline"](None) == (None, False)
    assert helpers["_daily_initial_baseline"](-1) == (None, False)


def test_daily_value_rises_with_cumulative_meter_and_survives_baseline_restore():
    helpers = _load_helpers()
    delta = helpers["_daily_energy_delta"]
    baseline, partial = helpers["_daily_initial_baseline"](5037.085)
    assert partial is True
    assert delta(5037.085, baseline) == 0.0
    assert delta(5037.125, baseline) == 0.04
    assert delta(5037.500, baseline) == 0.415
    # The same persisted baseline yields the same value after an HA restart.
    restored_baseline = float(baseline)
    assert delta(5037.500, restored_baseline) == 0.415


def test_daily_baseline_persists_partial_day_flag_and_discloses_it():
    block = SOURCE.split("class VerbrauchsMonitorDailyEnergySensor", 1)[1].split(
        "class VerbrauchsMonitorBalanceSensor", 1
    )[0]
    assert '"partial_day": self._baseline_partial' in block
    assert 'self._baseline_partial = bool(stored.get("partial_day", False))' in block
    assert '"partial_day": self._baseline_partial' in block
    assert '"partial_day": self._baseline_partial' in SOURCE
    assert '"partial_day": self._baseline_partial,' in block
    assert '"unavailable_reason": None if self._ready else "midnight_baseline_not_recovered"' in block


def test_daily_sensor_remains_energy_total_increasing_and_midnight_starts_new_baseline():
    block = SOURCE.split("class VerbrauchsMonitorDailyEnergySensor", 1)[1].split(
        "class VerbrauchsMonitorBalanceSensor", 1
    )[0]
    assert '_attr_device_class = "energy"' in block
    assert '_attr_state_class = "total_increasing"' in block
    assert 'self._baseline_partial = False' in block
    assert 'self._baseline_date = dt_util.now().date().isoformat()' in block


def test_registry_migration_targets_only_known_legacy_names_and_keeps_custom_names():
    helpers = _load_helpers()
    is_legacy = helpers["_is_legacy_daily_entity_name"]
    assert is_legacy("(heute)")
    assert is_legacy(None, "heute")
    assert is_legacy("Verbrauch (heute)")
    assert is_legacy("Tagesverbrauch (heute)")
    assert is_legacy("Tages-Einspeisung (heute)")
    assert not is_legacy("Mein Tagesverbrauch")
    assert not is_legacy("PV-Ertrag heute")


def test_partial_day_baseline_is_persisted_and_restored_without_resetting_progress():
    block = SOURCE.split("class VerbrauchsMonitorDailyEnergySensor", 1)[1].split(
        "class VerbrauchsMonitorBalanceSensor", 1
    )[0]
    assert '"partial_day": self._baseline_partial' in block
    assert 'self._baseline_partial = bool(stored.get("partial_day", False))' in block
    assert 'self._baseline = baseline' in block
    assert 'await self._save_baseline()' in block
