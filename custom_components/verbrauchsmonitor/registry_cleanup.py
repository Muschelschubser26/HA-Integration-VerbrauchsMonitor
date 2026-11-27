"""Helpers for pruning obsolete entities after meter renames or feature removal."""
from __future__ import annotations

from .const import ROLE_CONFIG, CONF_OUTDOOR_ILLUMINANCE_ENTITY
from .naming import slugify_meter_name, meter_entity_object_ids


def expected_sensor_unique_ids(options: dict, fallback_entry_id: str) -> set[str]:
    """Return every sensor unique_id that the current configuration creates."""
    expected: set[str] = set()
    for meter in options.get("meters", []):
        meter_id = str(meter.get("id") or fallback_entry_id)
        name = str(meter.get("name") or "Stromzähler")
        slug = slugify_meter_name(name)
        for config_key, (role, _label, _icon) in ROLE_CONFIG.items():
            if meter.get(config_key):
                expected.add(f"{meter_id}_{role}")
        expected.update(
            {
                f"{meter_id}_{slug}_verbrauch_kontostand",
            }
        )
        if meter.get("feed_in_entity"):
            expected.add(f"{meter_id}_{slug}_einspeisung_kontostand")

        # Forecast sensors are real entities owned by this logical meter.
        # Keep their registry entries while the corresponding forecast is
        # enabled; otherwise a reload would delete them before the sensor
        # platform can restore their states and reliability history.
        if meter.get("forecast_consumption_enabled", True):
            expected.update({
                f"{meter_id}_consumption_prognose_annual_balance",
                f"{meter_id}_consumption_prognose_monthly_advance",
            })
        if meter.get("feed_in_entity") and meter.get("forecast_feed_in_enabled", False):
            expected.update({
                f"{meter_id}_feed_in_prognose_annual_balance",
                f"{meter_id}_feed_in_prognose_monthly_advance",
            })
    return expected


def expected_entity_ids(options: dict) -> dict[str, str]:
    """Map active unique IDs to canonical entity IDs for configured meters."""
    expected: dict[str, str] = {}
    for meter in options.get("meters", []):
        meter_id = str(meter.get("id") or "")
        if not meter_id:
            continue
        ids = meter_entity_object_ids(str(meter.get("name") or "Stromzähler"))
        for config_key, (role, _label, _icon) in ROLE_CONFIG.items():
            if meter.get(config_key):
                expected[f"{meter_id}_{role}"] = f"sensor.{ids[role]}"
        # BalanceSensor unique IDs use the German role suffix. Keep these keys
        # exactly aligned with sensor.py so legacy entity IDs are migrated.
        expected[f"{meter_id}_{slugify_meter_name(str(meter.get('name') or 'Stromzähler'))}_verbrauch_kontostand"] = f"sensor.{ids['consumption_balance']}"
        if meter.get("feed_in_entity"):
            expected[f"{meter_id}_{slugify_meter_name(str(meter.get('name') or 'Stromzähler'))}_einspeisung_kontostand"] = f"sensor.{ids['feed_in_balance']}"
        slug = slugify_meter_name(str(meter.get("name") or "Stromzähler"))
        if meter.get("forecast_consumption_enabled", True):
            expected[f"{meter_id}_consumption_prognose_annual_balance"] = f"sensor.verbrauchsmonitor_{slug}_consumption_prognose_annual_balance"
            expected[f"{meter_id}_consumption_prognose_monthly_advance"] = f"sensor.verbrauchsmonitor_{slug}_consumption_prognose_monthly_advance"
        if meter.get("feed_in_entity") and meter.get("forecast_feed_in_enabled", False):
            expected[f"{meter_id}_feed_in_prognose_annual_balance"] = f"sensor.verbrauchsmonitor_{slug}_feed_in_prognose_annual_balance"
            expected[f"{meter_id}_feed_in_prognose_monthly_advance"] = f"sensor.verbrauchsmonitor_{slug}_feed_in_prognose_monthly_advance"
    return expected
