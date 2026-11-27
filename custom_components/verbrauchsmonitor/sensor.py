"""Sensor mirrors for configured VerbrauchsMonitor source entities."""
from __future__ import annotations

import asyncio
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.storage import Store
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval, async_track_time_change
from homeassistant.util import dt as dt_util
from types import SimpleNamespace
import logging
from decimal import ROUND_HALF_UP

_LOGGER = logging.getLogger(__name__)

def _is_transient_unavailable_state(state) -> bool:
    """Return True for missing or temporarily unavailable source states.

    Home Assistant commonly exposes configured source entities as unknown or
    unavailable during startup/reload. These are not measurement failures and
    must not trigger warning spam or modify persisted meter references.
    """
    return state is None or getattr(state, "state", None) in ("unknown", "unavailable")

from .const import (
    DOMAIN,
    CONF_CONSUMPTION_ENTITY,
    CONF_METER_NAME,
    CONF_METER_NUMBER,
    CONF_FEED_IN_ENTITY,
    CONF_FEED_IN_POWER_ENTITY,
    CONF_OUTDOOR_ILLUMINANCE_ENTITY,
    CONF_OUTDOOR_TEMPERATURE_ENTITY,
    CONF_OUTDOOR_WIND_DIRECTION_ENTITY,
    CONF_DAILY_PRECIPITATION_ENTITY,
    CONF_OUTDOOR_HUMIDITY_ENTITY,
    CONF_OUTDOOR_TEMPERATURE_ENTITY,
    CONF_OUTDOOR_WIND_DIRECTION_ENTITY,
    CONF_DAILY_PRECIPITATION_ENTITY,
    CONF_OUTDOOR_HUMIDITY_ENTITY,
    CONF_CONTRACT_NAME,
    CONF_CONTRACT_NUMBER,
    CONF_CONTRACT_START,
    CONF_CONTRACT_END,
    CONF_PURCHASE_PRICE_NET,
    CONF_FEED_IN_PRICE_NET,
    CONF_VAT_RATE,
    CONF_BASE_PRICE_NET,
    CONF_BASE_PRICE_PERIOD,
    CONF_MONTHLY_ADVANCE,
    CONF_BILLING_START,
    CONF_BILLING_END,
    ROLE_CONFIG,
)
from .pricing import gross_from_net
from .reliability import environmental_reliability_factors
from .naming import slugify_meter_name, meter_entity_object_ids
from .measurement_validation import confirmed_meter_change, parse_reading, validate_reading



def _normalize_learning_state(value):
    """Validate persisted learning data without resetting valid history.

    Store payloads are versioned independently from the integration release.
    Unknown metadata is retained so future releases can extend the schema
    without discarding records written by a newer compatible implementation.
    """
    if not isinstance(value, dict):
        return {"forecasts": {}, "evaluations": {}, "model_version": 1, "model_scale": 1.0}
    state = dict(value)
    forecasts = state.get("forecasts")
    evaluations = state.get("evaluations")
    state["forecasts"] = forecasts if isinstance(forecasts, dict) else {}
    state["evaluations"] = evaluations if isinstance(evaluations, dict) else {}
    try:
        state["model_version"] = max(1, int(state.get("model_version", 1)))
    except (TypeError, ValueError):
        state["model_version"] = 1
    try:
        scale = float(state.get("model_scale", 1.0))
        state["model_scale"] = scale if 0.1 <= scale <= 10.0 else 1.0
    except (TypeError, ValueError):
        state["model_scale"] = 1.0
    # Keep only structurally valid records; do not discard the remaining history
    # because one damaged row exists. The original Store remains untouched until
    # the next successful, complete learning-cycle save.
    state["forecasts"] = {key: row for key, row in state["forecasts"].items()
                          if isinstance(key, str) and isinstance(row, dict)
                          and row.get("target_hour") and row.get("meter_id")
                          and row.get("direction") in ("consumption", "feed_in")}
    state["evaluations"] = {key: row for key, row in state["evaluations"].items()
                            if isinstance(key, str) and isinstance(row, dict)
                            and row.get("target_hour") and row.get("meter_id")
                            and row.get("direction") in ("consumption", "feed_in")
                            and row.get("predicted") is not None and row.get("actual") is not None}
    return state



async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create mirrors only for configured sources and enabled features."""
    contracts = {c.get("id"): c for c in entry.options.get("contracts", [])}
    from .database import load_data
    ledger = await hass.async_add_executor_job(load_data, hass)
    entities = []
    configured_meters = entry.options.get("meters", [])
    for meter in configured_meters:
        contract = contracts.get(meter.get("contract_id"), {})
        # Only explicitly assigned records for this logical meter and direction
        # are exposed to its calculation; unresolved legacy bookings are excluded.
        meter_bookings = [b for b in ledger.get("bookings", []) if b.get("status") == "assigned" and b.get("meter_id") == meter.get("id")]
        monthly_records = [r for r in ledger.get("monthly_advances", []) if r.get("meter_id") == meter.get("id") and not r.get("superseded")]
        merged = {
            **contract, **meter,
            CONF_METER_NAME: meter.get("name", "Stromzähler"),
            "bookings": meter_bookings,
            "monthly_advances": monthly_records,
            # Shared optional environmental entities are copied into each
            # logical meter's calculation context; their readings remain
            # read-only and are never persisted as meter measurements.
            **{
                key: entry.options.get(key)
                for key in (
                    CONF_OUTDOOR_TEMPERATURE_ENTITY,
                    CONF_OUTDOOR_ILLUMINANCE_ENTITY,
                    CONF_OUTDOOR_WIND_DIRECTION_ENTITY,
                    CONF_DAILY_PRECIPITATION_ENTITY,
                    CONF_OUTDOOR_HUMIDITY_ENTITY,
                )
                if entry.options.get(key)
            },
        }
        # Backward compatibility: older feed-in-only contracts stored their
        # payout advance in the generic monthly_advance field. Migrate it in
        # memory only when that field cannot belong to a consumption area.
        if (
            merged.get("primary_billing_type") == "feed_in"
            and merged.get("secondary_billing_type") != "consumption"
            and merged.get("feed_in_monthly_advance") in (None, "")
            and merged.get("monthly_advance") not in (None, "")
        ):
            merged["feed_in_monthly_advance"] = merged.get("monthly_advance")
        # Normalize legacy scalar/global orientation values into the
        # canonical per-meter multi-select. Empty is a valid explicit choice.
        legacy_directions = merged.get("feed_in_directions")
        if legacy_directions is None:
            legacy_directions = merged.get("compass_directions")
        if legacy_directions is None:
            legacy_single = merged.get("feed_in_orientation")
            legacy_directions = [legacy_single] if legacy_single in ("north", "east", "south", "west") else ["south"]
        if isinstance(legacy_directions, str):
            legacy_directions = [legacy_directions]
        merged["feed_in_directions"] = list(dict.fromkeys(
            value for value in (legacy_directions or [])
            if value in ("north", "east", "south", "west")
        ))
        merged.pop("feed_in_orientation", None)
        merged.pop("compass_directions", None)
        merged["hub_entry_id"] = entry.entry_id
        meter_entry = SimpleNamespace(entry_id=meter.get("id", entry.entry_id), data=merged)
        has_feed_in = bool(merged.get(CONF_FEED_IN_ENTITY))
        entities.extend(_build_meter_entities(meter_entry, has_feed_in))
    if entities:
        async_add_entities(entities)


def _feed_in_orientations(data: dict) -> list[str]:
    """Return all valid compass orientations configured for this feed-in meter."""
    directions = data.get("feed_in_directions")
    if directions is None:
        legacy = data.get("feed_in_orientation")
        directions = [legacy] if legacy in ("north", "east", "south", "west") else []
    if isinstance(directions, str):
        directions = [directions]
    return list(dict.fromkeys(
        value for value in (directions or [])
        if value in ("north", "east", "south", "west")
    ))


def _build_meter_entities(entry, has_feed_in):
    """Build the native sensor entity descriptions for all configured meters and directions."""
    entities = []
    for config_key, (role, label, icon) in ROLE_CONFIG.items():
        source = entry.data.get(config_key)
        if source:
            entities.append(VerbrauchsMonitorMirrorSensor(entry, source, role, label, icon))
    entities.append(VerbrauchsMonitorBalanceSensor(entry, "consumption"))
    entities.append(VerbrauchsMonitorDailyEnergySensor(entry, "consumption"))
    entities.append(VerbrauchsMonitorPeriodEnergySensor(entry, "consumption", "week"))
    entities.append(VerbrauchsMonitorPeriodEnergySensor(entry, "consumption", "month"))
    entities.append(VerbrauchsMonitorPeriodEnergySensor(entry, "consumption", "year"))
    if has_feed_in:
        entities.append(VerbrauchsMonitorBalanceSensor(entry, "feed_in"))
        entities.append(VerbrauchsMonitorDailyEnergySensor(entry, "feed_in"))
        entities.append(VerbrauchsMonitorPeriodEnergySensor(entry, "feed_in", "week"))
        entities.append(VerbrauchsMonitorPeriodEnergySensor(entry, "feed_in", "month"))
        entities.append(VerbrauchsMonitorPeriodEnergySensor(entry, "feed_in", "year"))
    if entry.data.get("forecast_consumption_enabled", True):
        entities.extend(_build_forecast_entities(entry, "consumption"))
    if (
        has_feed_in
        and entry.data.get("forecast_feed_in_enabled", False)
    ):
        entities.extend(_build_forecast_entities(entry, "feed_in"))
    return entities


def _build_forecast_entities(entry, direction):
    """Create annual-balance and monthly-advance forecast sensors per direction."""
    return [
        VerbrauchsMonitorForecastSensor(entry, direction, "annual_balance"),
        VerbrauchsMonitorForecastSensor(entry, direction, "monthly_advance"),
    ]


async def _async_migrate_entity_id(entity, hass=None) -> None:
    """Move a registered entity to its canonical suggested object ID safely.

    Home Assistant does not automatically rename an existing registry entry
    when ``suggested_object_id`` changes. This migration keeps the unique ID
    (and therefore the entity's registry identity) while correcting old IDs.
    A conflicting target is never overwritten.
    """
    from homeassistant.helpers import entity_registry as er

    suggested = getattr(entity, "entity_id", None)
    object_id = getattr(entity, "_attr_suggested_object_id", None)
    if not suggested or not object_id:
        return
    target = f"sensor.{object_id}"
    if suggested == target:
        return
    registry = er.async_get(hass or entity.hass)
    target_entry = registry.async_get(target)
    current_entry = registry.async_get(suggested)
    if current_entry is None:
        return
    if target_entry is not None and target_entry.unique_id != current_entry.unique_id:
        _LOGGER.error(
            "VerbrauchsMonitor: Entitäts-ID-Migration übersprungen; Ziel %s ist bereits durch eine andere Entität belegt",
            target,
        )
        return
    registry.async_update_entity(suggested, new_entity_id=target)



class VerbrauchsMonitorMirrorSensor(SensorEntity):
    """Live mirror retaining source metadata and exposing tariff attributes."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        entry: ConfigEntry,
        source_entity: str,
        role: str,
        label: str,
        icon: str,
    ) -> None:
        """Initialize the sensor entity with its config entry, meter data and sensor description."""
        self._source = source_entity
        self._attr_unique_id = f"{entry.entry_id}_{role}"
        meter_name = entry.data.get(CONF_METER_NAME, "Stromzähler")
        self._attr_suggested_object_id = meter_entity_object_ids(meter_name)[role]
        self._attr_name = label
        self._attr_icon = icon
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.data.get(CONF_METER_NAME, "Stromzähler"),
            "manufacturer": "Muschelschubser26 & ChatGPT",
            "model": "VerbrauchsMonitor",
        }
        self._attr_extra_state_attributes = {
            "vm_role": role,
            "source_entity": source_entity,
            "meter_number": entry.data.get(CONF_METER_NUMBER),
            "meter_name": entry.data.get(CONF_METER_NAME),
            "meter_id": entry.entry_id,
            "hub_entry_id": entry.data.get("hub_entry_id"),
            "contract_name": entry.data.get(CONF_CONTRACT_NAME),
            "contract_number": entry.data.get(CONF_CONTRACT_NUMBER),
            "contract_id": entry.data.get("contract_id"),
            "contract_start": entry.data.get(CONF_CONTRACT_START),
            "contract_end": entry.data.get(CONF_CONTRACT_END),
            "purchase_price_net_ct_kwh": entry.data.get(CONF_PURCHASE_PRICE_NET, 0),
            "purchase_price_gross_ct_kwh": gross_from_net(
                entry.data.get(CONF_PURCHASE_PRICE_NET, 0),
                entry.data.get(CONF_VAT_RATE, 19),
            ),
            "vat_rate_percent": entry.data.get(CONF_VAT_RATE, 19),
            "base_price_net": entry.data.get(CONF_BASE_PRICE_NET, 0),
            "base_price_gross": gross_from_net(
                entry.data.get(CONF_BASE_PRICE_NET, 0),
                entry.data.get(CONF_VAT_RATE, 19),
            ),
            "base_price_period": entry.data.get(CONF_BASE_PRICE_PERIOD, "annual"),
            "base_price_is_annual": True,
            "monthly_advance_net": entry.data.get(CONF_MONTHLY_ADVANCE, 0),
            "previous_consumption_reading": entry.data.get("previous_consumption_reading", 0),
            "previous_feed_in_reading": entry.data.get("previous_feed_in_reading", 0),
            "consumption_baseline_source": entry.data.get("consumption_baseline_source", "manual"),
            "consumption_baseline_updated_at": entry.data.get("consumption_baseline_updated_at"),
            "feed_in_baseline_source": entry.data.get("feed_in_baseline_source", "manual"),
            "feed_in_baseline_updated_at": entry.data.get("feed_in_baseline_updated_at"),
            "consumption_baseline_history": entry.data.get("consumption_baseline_history", []),
            "feed_in_baseline_history": entry.data.get("feed_in_baseline_history", []),
            "meter_changes": entry.data.get("meter_changes", []),
            "billing_period_start": entry.data.get("billing_period_start") or entry.data.get("billing_start"),
            "billing_period_months": entry.data.get("billing_period_months", 12),
            "forecast_consumption_enabled": entry.data.get("forecast_consumption_enabled", True),
            "forecast_feed_in_enabled": entry.data.get("forecast_feed_in_enabled", False),
            # The card reads one direction-specific gross monthly advance.
            # Feed-in payouts are stored separately from consumption advances.
            "monthly_advance_gross": gross_from_net(
                entry.data.get(
                    "feed_in_monthly_advance"
                    if self._source == entry.data.get(CONF_FEED_IN_ENTITY)
                    else CONF_MONTHLY_ADVANCE,
                    0,
                ),
                entry.data.get(CONF_VAT_RATE, 19),
            ),
            "bookings": [b for b in entry.data.get("bookings", []) if b.get("direction") == ("consumption" if self._source == entry.data.get(CONF_CONSUMPTION_ENTITY) else "feed_in")],
            "billing_start": entry.data.get(CONF_BILLING_START),
            "billing_end": entry.data.get(CONF_BILLING_END),
        }
        if (
            entry.data.get(CONF_FEED_IN_ENTITY)
            or entry.data.get(CONF_FEED_IN_POWER_ENTITY)
        ):
            self._attr_extra_state_attributes.update(
                {
                    "feed_in_price_net_ct_kwh": entry.data.get(
                        CONF_FEED_IN_PRICE_NET, 0
                    ),
                    "feed_in_price_gross_ct_kwh": gross_from_net(
                        entry.data.get(CONF_FEED_IN_PRICE_NET, 0),
                        entry.data.get(CONF_VAT_RATE, 19),
                    ),
                }
            )

    async def async_added_to_hass(self) -> None:
        """Subscribe to the selected source entity."""
        await super().async_added_to_hass()
        await _async_migrate_entity_id(self)
        self._copy_source_state()
        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [self._source], self._async_source_changed
            )
        )

    @callback
    def _async_source_changed(self, event) -> None:
        """Update the mirror when its source changes."""
        self._copy_source_state()
        self.async_write_ha_state()

    def _copy_source_state(self) -> None:
        """Copy state and measurement metadata without inventing fallback values."""
        state = self.hass.states.get(self._source)
        if state is None or state.state in ("unknown", "unavailable"):
            self._attr_native_value = None
            self._attr_extra_state_attributes["source_status"] = (
                "missing" if state is None else state.state
            )
            return
        try:
            self._attr_native_value = float(state.state)
        except (TypeError, ValueError):
            self._attr_native_value = None
            self._attr_extra_state_attributes["source_status"] = "invalid"
            return
        self._attr_native_unit_of_measurement = state.attributes.get(
            "unit_of_measurement"
        )
        self._attr_device_class = state.attributes.get("device_class")
        self._attr_state_class = state.attributes.get("state_class")
        self._attr_extra_state_attributes["source_status"] = "ok"


def _daily_sensor_display_name(direction: str) -> str:
    """Return a device-view-safe name that is not reduced to only '(heute)' by HA."""
    if direction == "consumption":
        return "TagesVerbrauch"
    if direction == "feed_in":
        return "TagesEinspeisung"
    raise ValueError(f"Unsupported daily energy direction: {direction}")


def _daily_initial_baseline(current: float | None) -> tuple[float | None, bool]:
    """Use a real current reading as a disclosed partial-day baseline if needed."""
    if current is None or current < 0 or current == float("inf"):
        return None, False
    return float(current), True


def _is_legacy_daily_entity_name(name: str | None, original_name: str | None = None) -> bool:
    """Identify only known generated placeholders; retain deliberate user names."""
    legacy_names = {
        "(heute)", "heute", "(today)", "today",
        "verbrauch (heute)", "einspeisung (heute)",
        "tagesverbrauch (heute)", "tages-einspeisung (heute)",
    }
    current = (name or "").strip().casefold()
    original = (original_name or "").strip().casefold()
    return current in legacy_names or (name is None and original in legacy_names)


def _daily_energy_delta(current: float | None, baseline: float | None) -> float | None:
    """Return a non-negative daily counter delta; reject missing/reset values."""
    if current is None or baseline is None:
        return None
    delta = current - baseline
    return round(delta, 3) if delta >= 0 else None


def _infer_daily_baseline_from_statistics(current_reading: float, statistic_points: list[tuple[object, float]]) -> float | None:
    """Infer the cumulative meter baseline from valid same-day statistics sums."""
    valid = [(stamp, value) for stamp, value in statistic_points
             if stamp is not None and value is not None and value >= 0]
    valid.sort(key=lambda item: item[0])
    if len(valid) < 2 or current_reading is None or current_reading < 0:
        return None
    daily_delta = valid[-1][1] - valid[0][1]
    if daily_delta < 0:
        return None
    baseline = current_reading - daily_delta
    return baseline if baseline >= 0 else None


class VerbrauchsMonitorDailyEnergySensor(SensorEntity):
    """Daily energy delta from a cumulative meter, with a persistent midnight baseline."""

    _attr_has_entity_name = False
    _attr_native_unit_of_measurement = "kWh"
    _attr_suggested_display_precision = 3
    # A daily cumulative energy value may reset at local midnight.
    # total_increasing is the supported energy state class; HA detects the reset.
    _attr_state_class = "total_increasing"
    _attr_device_class = "energy"
    _attr_icon = "mdi:counter"
    _attr_should_poll = False

    def __init__(self, entry, direction: str) -> None:
        self._data = entry.data
        self._entry_id = entry.entry_id
        self._direction = direction
        self._source = entry.data.get(CONF_CONSUMPTION_ENTITY if direction == "consumption" else CONF_FEED_IN_ENTITY)
        name = entry.data.get(CONF_METER_NAME, "Stromzähler")
        slug = slugify_meter_name(name)
        self._attr_unique_id = f"{entry.entry_id}_{slug}_{direction}_today"
        role = "consumption_today" if direction == "consumption" else "feed_in_today"
        self._attr_suggested_object_id = meter_entity_object_ids(name)[role]
        # Avoid the device-name prefix: HA strips matching prefixes in device views.
        self._attr_name = _daily_sensor_display_name(direction)
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": name,
            "manufacturer": "Muschelschubser26 & ChatGPT",
            "model": "VerbrauchsMonitor",
        }
        self._store = None
        self._baseline = None
        self._baseline_date = None
        self._current = None
        self._ready = False
        self._baseline_partial = False
        self._offset = 0.0
        self._last_current = None

    async def async_added_to_hass(self):
        """Restore baseline and subscribe to source and local-midnight events."""
        await super().async_added_to_hass()
        await _async_migrate_entity_id(self)
        # R155 initially registered the entity with an abbreviated registry name
        # on some HA versions. Correct only that known generated label; preserve
        # any deliberate user rename.
        from homeassistant.helpers import entity_registry as er
        registry = er.async_get(self.hass)
        registry_entry = registry.async_get(self.entity_id)
        expected_name = _daily_sensor_display_name(self._direction)
        if registry_entry is not None and _is_legacy_daily_entity_name(
            registry_entry.name, getattr(registry_entry, "original_name", None)
        ):
            # Correct only the known legacy generated placeholder. Explicit
            # user-defined names are deliberately left untouched.
            registry.async_update_entity(self.entity_id, name=expected_name)
        self._store = Store(self.hass, 1, f"{DOMAIN}_daily_{self._entry_id}_{self._direction}")
        stored = await self._store.async_load() or {}
        today = dt_util.now().date().isoformat()
        state = self.hass.states.get(self._source) if self._source else None
        self._current = self._valid_reading(state.state) if state else None
        self._baseline = self._valid_reading(stored.get("baseline"))
        self._baseline_date = stored.get("date")
        stored_last = self._valid_reading(stored.get("last_current"))
        if stored_last is None:
            stored_last = self._baseline
        self._last_current = stored_last
        if self._current is not None and stored_last is not None and self._current < stored_last:
            if not self._confirmed_meter_change(stored_last):
                _LOGGER.warning("VerbrauchsMonitor: rückläufiger Startwert ignoriert (%s): %s < %s", self._source, self._current, stored_last)
                self._current = stored_last
        if stored.get("date") == today and self._valid_reading(stored.get("baseline")) is not None:
            self._baseline = float(stored["baseline"])
            self._baseline_date = today
            self._baseline_partial = bool(stored.get("partial_day", False))
            self._offset = max(0.0, float(stored.get("offset", 0.0) or 0.0))
            self._last_current = self._valid_reading(stored.get("last_current"))
            if self._last_current is None:
                self._last_current = self._valid_reading(stored.get("baseline"))
            self._ready = True
            if self._current is not None and self._last_current is not None and self._current < self._last_current:
                if self._confirmed_meter_change(self._last_current):
                    self._apply_meter_change(self._current, self._last_current)
                    await self._save_baseline()
                else:
                    _LOGGER.warning("VerbrauchsMonitor: rückläufiger Messwert beim Start ignoriert (%s, %s)", self._source, self._current)
                    self._current = self._last_current
            elif self._current is not None:
                self._last_current = self._current
        else:
            await self._restore_midnight_baseline(today)
        if self._source:
            self.async_on_remove(async_track_state_change_event(self.hass, [self._source], self._changed))
        self.async_on_remove(async_track_time_change(self.hass, self._midnight, hour=0, minute=0, second=0))
        self.async_write_ha_state()

    @staticmethod
    def _valid_reading(value):
        """Compatibility float wrapper around the central strict parser."""
        reading = parse_reading(value)
        return float(reading) if reading is not None else None

    def _confirmed_meter_change(self, previous_reading):
        """Delegate meter-change confirmation to the shared validation module."""
        period_start = getattr(self, "_period_key", None) or getattr(self, "_baseline_date", None)
        return confirmed_meter_change(
            self._data.get("meter_changes", []), direction=self._direction,
            period_start=period_start, today=dt_util.now().date(),
            baseline=self._baseline, previous_reading=previous_reading,
        )

    async def _restore_midnight_baseline(self, today: str):
        """Recover today's first reading from Recorder; never invent a zero baseline."""
        if not self._source:
            return
        try:
            from homeassistant.components.recorder import get_instance, history
            from datetime import datetime, time
            midnight = dt_util.as_local(datetime.combine(dt_util.now().date(), time.min, tzinfo=dt_util.now().tzinfo))
            recorder_instance = get_instance(self.hass)
            rows = await recorder_instance.async_add_executor_job(
                history.get_significant_states,
                self.hass,
                midnight,
                None,
                [self._source],
                None,
                True,
                False,
                False,
                True,
                False,
            )
            states = rows.get(self._source, []) if isinstance(rows, dict) else []
            candidates = [self._valid_reading(item.state) for item in states]
            candidates = [value for value in candidates if value is not None]
            if self._last_current is not None:
                candidates = [value for value in candidates if value >= self._last_current]
            if candidates:
                self._baseline = candidates[0]
                self._baseline_date = today
                self._baseline_partial = False
                self._ready = True
                await self._save_baseline()
                return
            # Significant-state history can be empty for sources whose changes
            # are represented only in long-term statistics. Reconstruct the
            # midnight baseline from the cumulative statistics sum instead.
            try:
                from homeassistant.components.recorder import statistics
                rows = await recorder_instance.async_add_executor_job(
                    statistics.statistics_during_period,
                    self.hass, midnight, dt_util.utcnow(), {self._source},
                    "hour", None, {"sum"},
                )
                points = [
                    (item.get("start"), self._valid_reading(item.get("sum")))
                    for item in rows.get(self._source, [])
                    if isinstance(item, dict) and item.get("start") is not None
                ]
                current_state = self.hass.states.get(self._source)
                current_reading = self._valid_reading(current_state.state) if current_state else None
                inferred = _infer_daily_baseline_from_statistics(current_reading, points)
                if inferred is not None:
                    self._baseline = inferred
                    self._baseline_date = today
                    self._baseline_partial = False
                    self._current = current_reading
                    self._ready = True
                    await self._save_baseline()
            except Exception:  # noqa: BLE001 - statistics are an optional fallback.
                pass
        except Exception:  # Recorder may be disabled or history unavailable.
            pass

        # A real current meter reading is a safe partial-day baseline when no
        # midnight history exists. The sensor can then rise from this point;
        # attributes explicitly disclose that earlier usage today is missing.
        if not self._ready:
            baseline, partial = _daily_initial_baseline(self._current)
            if baseline is not None:
                self._baseline = baseline
                self._baseline_date = today
                self._baseline_partial = partial
                self._ready = True
                await self._save_baseline()

    async def _save_baseline(self):
        await self._store.async_save({
            "date": self._baseline_date,
            "baseline": self._baseline,
            "partial_day": self._baseline_partial,
            "offset": self._offset,
            "last_current": self._last_current,
        })

    @callback
    def _changed(self, event):
        state = event.data.get("new_state")
        if _is_transient_unavailable_state(state):
            return
        value, status = validate_reading(state.state, self._current)
        if status == "decreased":
            if self._confirmed_meter_change(self._current):
                value = parse_reading(state.state)
                self._apply_meter_change(float(value), self._current)
                self.hass.async_create_task(self._save_baseline())
            else:
                _LOGGER.warning("VerbrauchsMonitor: rückläufiger Messwert ignoriert (%s): %s < %s", self._source, state.state, self._current)
                return
        elif status == "accepted":
            self._current = float(value)
            self._last_current = float(value)
            self.hass.async_create_task(self._save_baseline())
        else:
            _LOGGER.warning("VerbrauchsMonitor: ungültiger Messwert ignoriert (%s): %r", self._source, state.state if state else None)
            return
        self.async_write_ha_state()

    def _apply_meter_change(self, new_reading, last_reading):
        """Close the previous daily meter segment using its recorded end reading."""
        if self._ready and self._baseline is not None:
            end_key = "consumption_reading" if self._direction == "consumption" else "feed_in_reading"
            today = dt_util.now().date().isoformat()
            ends = [self._valid_reading(item.get(end_key)) for item in self._data.get("meter_changes", [])
                    if str(item.get("date", ""))[:10] == today]
            ends = [value for value in ends if value is not None]
            end_reading = ends[-1] if ends else last_reading
            if end_reading >= self._baseline:
                self._offset += end_reading - self._baseline
        self._baseline = new_reading
        self._current = new_reading
        self._last_current = new_reading
        self._baseline_partial = True
        self._ready = True

    @callback
    def _midnight(self, now):
        """Start a new daily interval using the current cumulative meter reading."""
        state = self.hass.states.get(self._source) if self._source else None
        value, status = validate_reading(state.state if state else None, self._last_current)
        if status == "decreased":
            if self._confirmed_meter_change(self._last_current):
                value = parse_reading(state.state)
                self._apply_meter_change(float(value), self._last_current)
            else:
                _LOGGER.warning("VerbrauchsMonitor: rückläufiger Messwert beim Tageswechsel ignoriert (%s)", self._source)
                return
        elif status == "invalid":
            self._ready = False
            self.async_write_ha_state()
            return
        value = float(value)
        self._baseline = value
        self._current = value
        self._last_current = value
        self._offset = 0.0
        self._baseline_date = dt_util.now().date().isoformat()
        self._baseline_partial = False
        self._ready = True
        self.hass.async_create_task(self._save_baseline())
        self.async_write_ha_state()

    @property
    def native_value(self):
        if not self._ready or self._baseline is None or self._current is None:
            return None
        delta = _daily_energy_delta(self._current, self._baseline)
        return None if delta is None else round(self._offset + delta, 6)

    @property
    def extra_state_attributes(self):
        return {
            "source_entity": self._source,
            "direction": self._direction,
            "baseline_date": self._baseline_date,
            "baseline_reading": self._baseline,
            "baseline_available": self._ready,
            "partial_day": self._baseline_partial,
            "daily_value_increases_with_source_counter": True,
            "unavailable_reason": None if self._ready else "midnight_baseline_not_recovered",
        }


def _period_key_and_start(now, period: str):
    """Return the local calendar period key and its timezone-aware start."""
    from datetime import datetime, time, timedelta
    local_now = dt_util.as_local(now)
    if period == "week":
        start_date = local_now.date() - timedelta(days=local_now.date().weekday())
    elif period == "month":
        start_date = local_now.date().replace(day=1)
    elif period == "year":
        start_date = local_now.date().replace(month=1, day=1)
    else:
        raise ValueError(f"Unsupported energy period: {period}")
    start = dt_util.as_local(datetime.combine(start_date, time.min, tzinfo=local_now.tzinfo))
    return start_date.isoformat(), start


class VerbrauchsMonitorPeriodEnergySensor(SensorEntity):
    """Persistent calendar-month/year delta from a cumulative meter reading.

    Period baselines are stored independently for each meter and direction. A
    missed boundary is recovered from Recorder where possible; otherwise the
    sensor starts a disclosed partial period from the first available reading.
    """
    _attr_has_entity_name = False
    _attr_native_unit_of_measurement = "kWh"
    _attr_suggested_display_precision = 3
    _attr_state_class = "total_increasing"
    _attr_device_class = "energy"
    _attr_icon = "mdi:counter"
    _attr_should_poll = False

    def __init__(self, entry, direction: str, period: str) -> None:
        self._entry_id = entry.entry_id
        self._data = entry.data
        self._direction = direction
        self._period = period
        self._source = entry.data.get(CONF_CONSUMPTION_ENTITY if direction == "consumption" else CONF_FEED_IN_ENTITY)
        name = entry.data.get(CONF_METER_NAME, "Stromzähler")
        slug = slugify_meter_name(name)
        self._attr_unique_id = f"{entry.entry_id}_{slug}_{direction}_{period}"
        role = f"{direction}_{period}"
        self._attr_suggested_object_id = meter_entity_object_ids(name)[role]
        period_label = {"week": "Wochen", "month": "Monats", "year": "Jahres"}[period]
        self._attr_name = f"{period_label}Verbrauch" if direction == "consumption" else f"{period_label}Einspeisung"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)}, "name": name,
            "manufacturer": "Muschelschubser26 & ChatGPT", "model": "VerbrauchsMonitor",
        }
        self._store = Store(entry.hass, 1, f"{DOMAIN}_{period}_{entry.entry_id}_{direction}") if hasattr(entry, "hass") else None
        self._baseline = None
        self._current = None
        self._period_key = None
        self._partial = False
        self._offset = 0.0
        self._last_current = None
        self._ready = False

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        await _async_migrate_entity_id(self)
        self._store = Store(self.hass, 1, f"{DOMAIN}_{self._period}_{self._entry_id}_{self._direction}")
        today_key, period_start = _period_key_and_start(dt_util.now(), self._period)
        state = self.hass.states.get(self._source) if self._source else None
        self._current = self._valid_reading(state.state) if state else None
        stored = await self._store.async_load() or {}
        self._baseline = self._valid_reading(stored.get("baseline"))
        self._period_key = stored.get("period")
        stored_last = self._valid_reading(stored.get("last_current"))
        if stored_last is None:
            stored_last = self._baseline
        self._last_current = stored_last
        if self._current is not None and stored_last is not None and self._current < stored_last:
            if not self._confirmed_meter_change(stored_last):
                _LOGGER.warning("VerbrauchsMonitor: rückläufiger Startwert ignoriert (%s): %s < %s", self._source, self._current, stored_last)
                self._current = stored_last
        if stored.get("period") == today_key and self._valid_reading(stored.get("baseline")) is not None:
            self._baseline = float(stored["baseline"])
            self._period_key = today_key
            self._partial = bool(stored.get("partial", False))
            self._offset = max(0.0, float(stored.get("offset", 0.0) or 0.0))
            self._last_current = self._valid_reading(stored.get("last_current"))
            if self._last_current is None:
                self._last_current = self._valid_reading(stored.get("baseline"))
            self._ready = True
            if self._current is not None and self._last_current is not None and self._current < self._last_current:
                if self._confirmed_meter_change(self._last_current):
                    self._apply_meter_change(self._current, self._last_current)
                    await self._save()
                else:
                    _LOGGER.warning("VerbrauchsMonitor: rückläufiger Messwert beim Start ignoriert (%s, %s)", self._source, self._current)
                    self._current = self._last_current
            elif self._current is not None:
                self._last_current = self._current
        else:
            await self._restore_period_baseline(today_key, period_start)
        if self._source:
            self.async_on_remove(async_track_state_change_event(self.hass, [self._source], self._changed))
        # One lightweight check at local midnight; the persisted period key
        # decides whether this sensor actually needs a rollover.
        self.async_on_remove(async_track_time_change(self.hass, self._boundary, hour=0, minute=0, second=5))
        self.async_write_ha_state()

    @staticmethod
    def _valid_reading(value):
        """Compatibility float wrapper around the central strict parser."""
        reading = parse_reading(value)
        return float(reading) if reading is not None else None

    def _confirmed_meter_change(self, previous_reading):
        """Delegate meter-change confirmation to the shared validation module."""
        period_start = getattr(self, "_period_key", None) or getattr(self, "_baseline_date", None)
        return confirmed_meter_change(
            self._data.get("meter_changes", []), direction=self._direction,
            period_start=period_start, today=dt_util.now().date(),
            baseline=self._baseline, previous_reading=previous_reading,
        )

    async def _restore_period_baseline(self, period_key, period_start):
        if not self._source:
            return
        try:
            from homeassistant.components.recorder import get_instance, history
            recorder = get_instance(self.hass)
            rows = await recorder.async_add_executor_job(
                history.get_significant_states, self.hass, period_start, None,
                [self._source], None, True, False, False, True, False,
            )
            values = [self._valid_reading(item.state) for item in rows.get(self._source, [])]
            values = [value for value in values if value is not None]
            if self._last_current is not None:
                values = [value for value in values if value >= self._last_current]
            if values:
                self._baseline = values[0]
                self._period_key = period_key
                self._partial = False
                self._ready = True
                await self._save()
                return
        except Exception:  # Recorder can be disabled or history can be unavailable.
            pass
        if self._current is not None:
            self._baseline = self._current
            self._period_key = period_key
            self._partial = True
            self._ready = True
            await self._save()

    async def _save(self):
        await self._store.async_save({"period": self._period_key, "baseline": self._baseline, "partial": self._partial, "offset": self._offset, "last_current": self._last_current})

    @callback
    def _changed(self, event):
        state = event.data.get("new_state")
        if _is_transient_unavailable_state(state):
            return
        value, status = validate_reading(state.state, self._current)
        if status == "invalid":
            _LOGGER.warning("VerbrauchsMonitor: ungültiger Messwert ignoriert (%s): %r", self._source, state.state if state else None)
            return
        if status == "decreased":
            if self._confirmed_meter_change(self._current):
                value = float(parse_reading(state.state))
                current_key, _ = _period_key_and_start(dt_util.now(), self._period)
                if self._period_key != current_key:
                    self._baseline = value
                    self._current = value
                    self._last_current = value
                    self._period_key = current_key
                    self._offset = 0.0
                    self._partial = True
                    self._ready = True
                else:
                    self._apply_meter_change(value, self._current)
                self.hass.async_create_task(self._save())
                self.async_write_ha_state()
            else:
                _LOGGER.warning("VerbrauchsMonitor: rückläufiger Messwert ignoriert (%s): %s < %s", self._source, state.state, self._current)
            return
        value = float(value)
        current_key, _ = _period_key_and_start(dt_util.now(), self._period)
        if self._period_key != current_key:
            # A boundary may have passed while HA was down or the source was
            # unavailable. Start the new period at the first valid reading.
            self._baseline = value
            self._current = value
            self._last_current = value
            self._period_key = current_key
            self._offset = 0.0
            self._partial = True
            self._ready = True
            self.hass.async_create_task(self._save())
            self.async_write_ha_state()
            return
        self._current = value
        self._last_current = value
        self.hass.async_create_task(self._save())
        if not self._ready and self._baseline is None:
            key, _ = _period_key_and_start(dt_util.now(), self._period)
            self._baseline = value
            self._period_key = key
            self._partial = True
            self._ready = True
            self.hass.async_create_task(self._save())
        self.async_write_ha_state()

    def _apply_meter_change(self, new_reading, last_reading):
        """Close the previous meter segment and continue with the replacement."""
        if self._ready and self._baseline is not None:
            end_key = "consumption_reading" if self._direction == "consumption" else "feed_in_reading"
            from datetime import date as date_type
            today = dt_util.now().date()
            candidates = []
            for change in self._data.get("meter_changes", []):
                try:
                    change_date = date_type.fromisoformat(str(change.get("date", ""))[:10])
                    end_reading = self._valid_reading(change.get(end_key))
                    period_start_date = date_type.fromisoformat(self._period_key) if self._period_key else today
                    if period_start_date <= change_date <= today and end_reading is not None:
                        candidates.append((change_date, end_reading))
                except (TypeError, ValueError):
                    continue
            end_reading = sorted(candidates, key=lambda item: item[0])[-1][1] if candidates else last_reading
            if end_reading >= self._baseline:
                self._offset += end_reading - self._baseline
        self._baseline = new_reading
        self._current = new_reading
        self._last_current = new_reading
        self._partial = True
        self._ready = True

    @callback
    def _boundary(self, now):
        """Apply a calendar rollover once, without invalidating a sensor.

        If the source has no valid value at midnight, keep the last persisted
        state. The first later valid source update establishes the new baseline.
        """
        state = self.hass.states.get(self._source) if self._source else None
        value, status = validate_reading(state.state if state else None, self._last_current)
        key, _ = _period_key_and_start(dt_util.now(), self._period)
        if status == "decreased":
            if not self._confirmed_meter_change(self._last_current):
                _LOGGER.warning("VerbrauchsMonitor: rückläufiger Messwert beim Periodenwechsel ignoriert (%s)", self._source)
                return
            value = parse_reading(state.state)
        elif status == "invalid":
            return
        value = float(value)
        if key == self._period_key:
            return
        if value is None:
            # Do not erase the old baseline or mark the entity unavailable.
            # _changed() will complete the rollover on the next valid reading.
            return
        self._baseline = value
        self._current = value
        self._last_current = value
        self._period_key = key
        self._partial = False
        self._offset = 0.0
        self._ready = True
        self.hass.async_create_task(self._save())
        self.async_write_ha_state()

    @property
    def native_value(self):
        if not self._ready or self._baseline is None or self._current is None or self._current < self._baseline:
            return None
        return round(self._offset + self._current - self._baseline, 6)

    @property
    def extra_state_attributes(self):
        return {"source_entity": self._source, "direction": self._direction, "period": self._period,
                "period_key": self._period_key, "baseline_reading": self._baseline,
                "partial_period": self._partial, "completed_meter_segments_kwh": self._offset, "baseline_available": self._ready}


class VerbrauchsMonitorBalanceSensor(SensorEntity):
    """Calculated per-meter period balance based on the previous billing reading."""
    _attr_has_entity_name = False
    _attr_native_unit_of_measurement = "€"
    _attr_suggested_display_precision = 2
    _attr_icon = "mdi:cash"
    _attr_should_poll = False

    def __init__(self, entry, direction: str, has_feed_in: bool = False) -> None:
        """Initialize the sensor entity with its config entry, meter data and sensor description."""
        self._data = entry.data
        self._entry_id = entry.entry_id
        self._direction = direction
        name = entry.data.get(CONF_METER_NAME, "Stromzähler")
        slug = slugify_meter_name(name)
        self._source = entry.data.get(CONF_CONSUMPTION_ENTITY) if direction == "consumption" else entry.data.get(CONF_FEED_IN_ENTITY)
        self._baseline = float(entry.data.get("previous_consumption_reading" if direction == "consumption" else "previous_feed_in_reading", 0) or 0)
        self._attr_unique_id = f"{entry.entry_id}_{slug}_{direction}_kontostand"
        suffix = {"consumption": "Verbrauch", "feed_in": "Einspeisung"}[direction]
        object_id = meter_entity_object_ids(name)[f"{direction}_balance"]
        self._attr_suggested_object_id = object_id
        self._attr_name = f"Kontostand {suffix}"
        self._attr_device_info = {"identifiers": {(DOMAIN, entry.entry_id)}, "name": name, "manufacturer": "Muschelschubser26 & ChatGPT", "model": "VerbrauchsMonitor"}
        self._attr_extra_state_attributes = {
            "vm_role": f"{direction}_balance",
            "meter_id": entry.entry_id,
            "hub_entry_id": entry.data.get("hub_entry_id"),
            "direction": direction,
            "meter_name": name,
            "meter_number": entry.data.get(CONF_METER_NUMBER),
            "contract_name": entry.data.get(CONF_CONTRACT_NAME),
            "contract_number": entry.data.get(CONF_CONTRACT_NUMBER),
            "baseline_reading": self._baseline,
            "billing_status": "ok" if self._source else "missing_source",
        }

    async def async_added_to_hass(self):
        """Subscribe to the source entity updates after this sensor is added to Home Assistant."""
        await super().async_added_to_hass()
        await _async_migrate_entity_id(self)
        sources = [self._source] if self._source else []
        if sources:
            self.async_on_remove(async_track_state_change_event(self.hass, sources, self._changed))
        self.async_write_ha_state()

    @callback
    def _periodic_learning_state_refresh(self, now):
        """Reload shared hourly evaluations for the monthly recommendation entity."""
        self.hass.async_create_task(self._async_refresh_learning_state())

    async def _async_refresh_learning_state(self):
        """Reload the per-meter/direction learning store and refresh the entity."""
        if not hasattr(self, "_learning_store"):
            return
        self._learning_state = _normalize_learning_state(await self._learning_store.async_load())
        self.async_write_ha_state()

    @callback
    def _periodic_refresh(self, now):
        """Refresh history weekly; data changes can trigger an earlier refresh."""
        self.hass.async_create_task(self._async_refresh_history())

    @callback
    def _changed(self, event):
        """Handle a source-state change and refresh the derived sensor state."""
        self.async_write_ha_state()

    @property
    def native_value(self):
        """Calculate one independent meter balance (consumption OR feed-in)."""
        from datetime import date
        from decimal import Decimal
        from .ledger import calculate_advance_total, calculate_recorded_advance_total, build_monthly_advance_groups, apply_booking_corrections, signed_customer_balance
        from .pricing import gross_decimal_from_net
        from decimal import ROUND_HALF_UP

        cent = Decimal("0.01")
        def money_amount(value):
            """Round each accounting line to cents before totals are combined."""
            return Decimal(value).quantize(cent, rounding=ROUND_HALF_UP)

        source = self._source
        state = self.hass.states.get(source) if source else None
        if state is None or state.state in ("unknown", "unavailable"):
            self._attr_extra_state_attributes["forecast_status"] = "source_unavailable"
            return None
        try:
            current = Decimal(str(state.state))
            baseline = Decimal(str(self._data.get(
                "previous_consumption_reading" if self._direction == "consumption" else "previous_feed_in_reading", 0
            ) or 0))
            energy_delta = current - baseline
            if not energy_delta.is_finite() or energy_delta < 0:
                return None

            vat = Decimal(str(self._data.get(CONF_VAT_RATE, 19) or 0))
            if self._direction == "consumption":
                price = gross_decimal_from_net(self._data.get(CONF_PURCHASE_PRICE_NET, 0), vat)
            else:
                price = gross_decimal_from_net(self._data.get(CONF_FEED_IN_PRICE_NET, 0), vat)
            if price is None:
                return None

            # Tariffs retain their exact configured precision. Each monetary
            # line item is rounded once to cents before the account total is
            # formed, so displayed lines always add up to the displayed total.
            energy_amount = money_amount(energy_delta * price / Decimal(100))
            # A supplier base charge belongs to consumption only; feed-in
            # remuneration must never inherit that charge.
            base_net = (
                Decimal(str(self._data.get(CONF_BASE_PRICE_NET, 0) or 0))
                if self._direction == "consumption"
                else Decimal("0")
            )
            base_gross_annual = base_net * (Decimal(1) + vat / Decimal(100))

            start_text = self._data.get("billing_period_start") or self._data.get("billing_start") or self._data.get(CONF_CONTRACT_START)
            from homeassistant.util import dt as dt_util
            now_local = dt_util.now()
            today = now_local.date()
            base_gross = Decimal("0.00")
            if start_text:
                start_date = date.fromisoformat(str(start_text)[:10])
                if start_date > today:
                    return None
                from datetime import datetime, time
                billing_start_dt = datetime.combine(start_date, time.min, tzinfo=now_local.tzinfo)
                from .pricing import accrued_annual_base_price
                base_gross = accrued_annual_base_price(base_gross_annual, billing_start_dt, now_local)
                configured_duration = self._data.get("billing_period_months")
                if configured_duration not in (None, ""):
                    duration_months = max(1, int(configured_duration))
                    end_index = start_date.year * 12 + start_date.month - 1 + duration_months
                    from datetime import timedelta
                    period_end_date = date(end_index // 12, end_index % 12 + 1, 1)
                    period_end_dt = datetime.combine(period_end_date, time.min, tzinfo=now_local.tzinfo)
                    if now_local > period_end_dt:
                        # Freeze the continuously accrued base price at the
                        # exclusive billing-period boundary. Do not switch to
                        # a months/12 approximation after the period ends.
                        base_gross = accrued_annual_base_price(
                            base_gross_annual, billing_start_dt, period_end_dt
                        )
            # Consumption and feed-in advances are separate contractual
            # amounts. Both are automatically counted on each due month start.
            if self._direction == "consumption":
                monthly_advance = Decimal(str(self._data.get("monthly_advance", 0) or 0))
            else:
                monthly_advance = Decimal(str(self._data.get("feed_in_monthly_advance", 0) or 0))
            monthly_advance_gross = monthly_advance * (Decimal(1) + vat / Decimal(100))
            # Contractual advances are counted from their due month start.
            # Recorded advances replace the automatic amount for that month.
            period_end = self._data.get("billing_period_end") or self._data.get("billing_end") or self._data.get(CONF_CONTRACT_END)
            direction_bookings = [
                b for b in self._data.get("bookings", [])
                if b.get("direction") == self._direction
            ]
            # A contractual monthly advance is automatically treated as paid
            # on the first calendar day of each month in the billing period.
            # No confirmation or manual booking is required. An explicit
            # advance booking replaces that month's automatic amount.
            monthly_overrides = {
                str(item.get("month")): Decimal(str(item.get("amount", 0)))
                for item in self._data.get("monthly_advances", [])
                if item.get("direction") == self._direction and item.get("month") and not item.get("superseded")
            }
            # Monthly advances are actual account payments by project rule:
            # every first day of a month in the billing period counts once.
            # Explicit advance bookings replace, rather than duplicate, that
            # month's automatic amount.
            expected_advances = calculate_advance_total(
                monthly_advance_gross=monthly_advance_gross,
                bookings=direction_bookings,
                period_start=start_text,
                as_of=today,
                period_end=period_end,
                monthly_amounts=monthly_overrides,
            )
            expected_advance_amount = money_amount(expected_advances)
            paid_advances = calculate_recorded_advance_total(
                bookings=direction_bookings,
                period_start=start_text,
                as_of=today,
                period_end=period_end,
            )
            # Project rule: elapsed contractual monthly advances count as paid.
            # This includes the effective month-specific amount and avoids
            # treating future scheduled months as already paid.
            advances = money_amount(expected_advance_amount)
            self._attr_extra_state_attributes["recorded_advances_paid"] = float(money_amount(paid_advances))
            self._attr_extra_state_attributes["actual_advances_paid"] = float(advances)
            self._attr_extra_state_attributes["automatic_monthly_advances_paid"] = float(advances)
            self._attr_extra_state_attributes["expected_advances_total"] = float(expected_advance_amount)
            # Provide a backend-calculated, period-scoped breakdown by effective
            # monthly amount. These are due amounts, not payment evidence.
            self._attr_extra_state_attributes["monthly_advance_groups"] = build_monthly_advance_groups(
                period_start=start_text,
                as_of=today,
                period_end=period_end,
                monthly_advance_gross=monthly_advance_gross,
                monthly_amounts=monthly_overrides,
                bookings=direction_bookings,
            )

            from .ledger import calculate_booking_adjustments

            relevant_bookings = []
            for booking in self._data.get("bookings", []):
                booking_date = str(booking.get("date", ""))[:10]
                if start_text and booking_date and booking_date < str(start_text)[:10]:
                    continue
                if booking_date and booking_date > today.isoformat():
                    continue
                relevant_bookings.append(booking)

            credits, additional_payments, extra_charges, corrections = calculate_booking_adjustments(
                bookings=relevant_bookings,
                direction=self._direction,
            )
            credits = money_amount(credits)
            additional_payments = money_amount(additional_payments)
            extra_charges = money_amount(extra_charges)
            corrections = money_amount(corrections)

            # Every monetary line has already been rounded to cents.
            # Advances, additional payments and credits retain their established
            # direction-specific treatment. Corrections are account adjustments:
            # their signed value is applied AFTER sign conversion, identically
            # for every logical meter and billing direction. Thus -66 EUR reduces
            # the customer credit by 66 EUR for consumption and feed-in alike.
            credit_effect = credits if self._direction == "feed_in" else -credits
            result_before_correction = (
                energy_amount + base_gross + extra_charges
                - advances - additional_payments + credit_effect
            )
            result_before_correction = money_amount(result_before_correction)
            account_balance = signed_customer_balance(
                direction=self._direction, amount=result_before_correction
            )
            final_balance = money_amount(apply_booking_corrections(
                account_balance=account_balance, corrections=corrections
            ))
            # Expose the exact backend line items to the card. The frontend
            # must not independently recalculate tariffs or period costs.
            self._attr_extra_state_attributes.update({
                "vm_energy_amount": float(energy_amount),
                "vm_base_amount": float(base_gross),
                "vm_extra_charges": float(extra_charges),
                "vm_total_costs": float(energy_amount + base_gross + extra_charges),
                "vm_gross_tariff_ct_kwh": float(price),
                "vm_money_rounding": "ROUND_HALF_UP_per_line_item",
                "vm_credits": float(credits),
                "vm_additional_payments": float(additional_payments),
                "vm_corrections": float(corrections),
                "vm_advances": float(advances),
            })
            return float(final_balance)
        except (TypeError, ValueError, ArithmeticError):
            return None


class VerbrauchsMonitorForecastSensor(SensorEntity):
    """Expose one independent forecast value for one meter and direction."""
    _attr_has_entity_name = False
    _attr_native_unit_of_measurement = "€"
    _attr_suggested_display_precision = 2
    _attr_icon = "mdi:chart-timeline-variant"
    _attr_should_poll = False

    def __init__(self, entry, direction: str, metric: str) -> None:
        # Keep the logical meter ID: it is part of the persistent reliability
        # storage key and must exist before async_added_to_hass is called.
        """Initialize the sensor entity with its config entry, meter data and sensor description."""
        self._entry_id = entry.entry_id
        self._data = entry.data
        self._direction = direction
        self._metric = metric
        self._source = self._data.get(CONF_CONSUMPTION_ENTITY if direction == "consumption" else CONF_FEED_IN_ENTITY)
        self._environment_entities = [
            self._data.get(key) for key in (
                CONF_OUTDOOR_TEMPERATURE_ENTITY,
                CONF_OUTDOOR_ILLUMINANCE_ENTITY,
                CONF_OUTDOOR_WIND_DIRECTION_ENTITY,
                CONF_DAILY_PRECIPITATION_ENTITY,
                CONF_OUTDOOR_HUMIDITY_ENTITY,
            ) if self._data.get(key)
        ]
        # Home Assistant reads native_value synchronously while writing entity state.
        # Keep that property O(1): the forecast is calculated asynchronously and
        # the latest completed result is cached here.
        self._cached_native_value = None
        self._forecast_refresh_lock = asyncio.Lock()
        self._reliability_progress_percent = 0
        self._reliability_progress_pending = True
        self._forecast_refresh_requested = False
        name = self._data.get(CONF_METER_NAME, "Stromzähler")
        label = "Jahresprognose" if metric == "annual_balance" else "Monatlicher Abschlag empfohlen"
        suffix = "Verbrauch" if direction == "consumption" else "Einspeisung"
        self._attr_unique_id = f"{entry.entry_id}_{direction}_prognose_{metric}"
        self._attr_name = f"{label} {suffix}"
        self._attr_extra_state_attributes = {"meter_name": name, "card_meter_id": entry.entry_id, "card_meter_name": name, "meter_id": entry.entry_id, "direction": direction, "vm_role": f"{direction}_forecast_{metric}", "forecast_method": "linear_elapsed_period_average"}
        self._attr_suggested_object_id = (f"verbrauchsmonitor_{slugify_meter_name(name)}_{'verbrauch' if direction == 'consumption' else 'einspeisung'}_jahresbilanz_prognose" if metric == "annual_balance" else f"verbrauchsmonitor_{slugify_meter_name(name)}_{'verbrauch' if direction == 'consumption' else 'einspeisung'}_monatsabschlag_prognose")
        self._attr_device_info = {"identifiers": {(DOMAIN, entry.entry_id)}, "name": name, "manufacturer": "Muschelschubser26 & ChatGPT", "model": "VerbrauchsMonitor"}

    async def async_added_to_hass(self):
        """Initialize persistent forecast state and register live refresh callbacks."""
        await super().async_added_to_hass()
        # During platform startup the Entity.hass reference can briefly be
        # unset while the platform already owns the Home Assistant instance.
        # Prefer the entity reference, then use the owning platform as a safe
        # lifecycle fallback instead of passing None to HA event helpers.
        hass = self.hass or getattr(self.platform, "hass", None)
        if hass is None:
            raise RuntimeError("Forecast sensor was added without a Home Assistant instance")
        await _async_migrate_entity_id(self, hass)
        self._history = {}
        # Legacy synthetic reliability storage is intentionally no longer read.
        # A percentage is now derived from current evidence on every refresh.
        self._reliability_state = None
        from datetime import datetime, timezone
        self._reliability_started_at = datetime.now(timezone.utc)
        learning_key = f"{DOMAIN}_{self._entry_id}_{self._direction}_hourly_learning"
        self._learning_store = Store(hass, 1, learning_key)
        # Independent rolling copy protects the multi-year learning history if
        # the primary Store file is missing or cannot be decoded after an update.
        self._learning_backup_store = Store(hass, 1, f"{learning_key}_backup")
        self._learning_state = await self._async_load_learning_state()
        if self._source:
            from datetime import timedelta
            tracked_entities = list(dict.fromkeys([self._source, *self._environment_entities]))
            self.async_on_remove(async_track_state_change_event(hass, tracked_entities, self._changed))
            # Refresh the expensive Recorder history daily. The reliability
            # value itself is smoothed hourly from this cached evidence.
            self.async_on_remove(async_track_time_interval(
                hass, self._periodic_refresh, timedelta(days=1)
            ))
            # Reliability is recalculated by the hourly learning cycle below.
            # Do not register the removed history-only reliability callback.
            if self._metric == "annual_balance":
                self.async_on_remove(async_track_time_interval(
                    hass, self._periodic_hourly_learning, timedelta(hours=1)
                ))
            else:
                # The annual sensor owns the learning cycle. The recommendation
                # sensor reloads its shared results hourly so its attributes
                # and availability follow measured reliability without
                # running a duplicate learning job.
                self.async_on_remove(async_track_time_interval(
                    hass, self._periodic_learning_state_refresh, timedelta(hours=1)
                ))
            # Season boundaries can occur at any local time; refresh hourly.
            self.async_on_remove(async_track_time_interval(
                hass, self._periodic_season_refresh, timedelta(hours=1)
            ))
            await self._async_refresh_history()
        # No synthetic starting score is stored. Reliability is calculated
        # immediately from valid live evidence and completed comparisons only.
        if self._source and self._metric == "annual_balance":
            await self._async_hourly_learning()
        # Calculate once before the first published state. native_value itself
        # only returns the cached result and never performs forecast work.
        await self._async_refresh_forecast_value()
        self.async_write_ha_state()

    async def _async_load_learning_state(self):
        """Restore learning from primary storage, falling back to its backup."""
        primary_raw = await self._learning_store.async_load()
        primary = _normalize_learning_state(primary_raw)
        primary_has_history = bool(primary["forecasts"] or primary["evaluations"])
        backup_store = getattr(self, "_learning_backup_store", None)
        if backup_store is None:
            return primary
        backup_raw = await backup_store.async_load()
        backup = _normalize_learning_state(backup_raw)
        backup_has_history = bool(backup["forecasts"] or backup["evaluations"])
        if not primary_has_history and backup_has_history:
            _LOGGER.warning(
                "VerbrauchsMonitor: Stelle Lernhistorie aus Sicherung wieder her (%s, %s)",
                self._entry_id, self._direction,
            )
            await self._learning_store.async_save(backup)
            return backup
        return primary

    @callback
    def _periodic_learning_state_refresh(self, now):
        """Reload the shared hourly learning state for the monthly recommendation sensor."""
        self.hass.async_create_task(self._async_refresh_learning_state())

    async def _async_refresh_learning_state(self):
        """Reload the shared per-meter and per-direction learning store."""
        learning_store = getattr(self, "_learning_store", None)
        if learning_store is None:
            return
        self._learning_state = await self._async_load_learning_state()
        await self._async_refresh_forecast_value()
        self.async_write_ha_state()

    @callback
    def _periodic_refresh(self, now):
        """Refresh the two-year Recorder evidence once per day."""
        self.hass.async_create_task(self._async_refresh_history())

    def _periodic_hourly_learning(self, now):
        """Evaluate completed forecast hours and persist the next hourly horizon."""
        self.hass.async_create_task(self._async_hourly_learning())

    @callback
    def _periodic_season_refresh(self, now):
        """Refresh season- and solar-dependent forecast values at least hourly."""
        self.hass.async_create_task(self._async_refresh_forecast_and_write())

    @callback
    def _changed(self, event):
        """Refresh the live forecast when the source meter changes.

        Recorder history is deliberately not reloaded for every source update;
        its bounded daily refresh avoids repeated two-year history queries.
        """
        self._forecast_refresh_requested = True
        self.hass.async_create_task(self._async_refresh_forecast_and_write())

    async def _async_hourly_learning(self):
        """Persist immutable hourly predictions and compare them with Recorder actuals.

        This runs once per logical meter/direction (the annual forecast entity),
        keeping consumption and feed-in learning histories completely separate.
        """
        if not self._source or not getattr(self, "_learning_store", None):
            return
        try:
            from datetime import datetime, timedelta, timezone
            from homeassistant.components.recorder import statistics
            from homeassistant.util import dt as dt_util
            from .forecast_model import (
                build_hourly_forecasts, merge_forecast_records,
                merge_hourly_evaluations, evaluate_hourly_forecast,
                reliability_from_hourly_evaluations, learn_candidate_scale,
            )
            now = dt_util.now()
            utc_now = dt_util.utcnow()
            start = utc_now - timedelta(days=4)
            from homeassistant.components.recorder import get_instance
            recorder = get_instance(self.hass)
            rows = await recorder.async_add_executor_job(
                statistics.statistics_during_period, self.hass, start, utc_now,
                {self._source}, "hour", None, {"sum", "state"}
            )
            values = []
            for row in rows.get(self._source, []):
                stamp = row.get("start")
                value = row.get("sum") if row.get("sum") is not None else row.get("state")
                if stamp is not None and value is not None:
                    try:
                        values.append((stamp, float(value)))
                    except (TypeError, ValueError):
                        continue
            values.sort(key=lambda item: item[0])
            actual_by_hour = {}
            for (t1, v1), (t2, v2) in zip(values, values[1:]):
                interval_seconds = (t2 - t1).total_seconds()
                # Never attribute a multi-hour gap to one forecast hour.
                if abs(interval_seconds - 3600) <= 5 and v2 >= v1:
                    # The delta between consecutive cumulative samples belongs
                    # to the interval beginning at t1, not the ending timestamp.
                    target = t1
                    if getattr(target, "tzinfo", None) is None:
                        target = target.replace(tzinfo=timezone.utc)
                    target = target.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
                    actual_by_hour[target.isoformat()] = max(0.0, v2 - v1)

            forecasts = dict(self._learning_state.get("forecasts", {}))
            evaluations = dict(self._learning_state.get("evaluations", {}))
            additions = []
            for key, record in forecasts.items():
                target = datetime.fromisoformat(record["target_hour"])
                if target <= utc_now.replace(minute=0, second=0, microsecond=0) and record["target_hour"] in actual_by_hour:
                    additions.append(evaluate_hourly_forecast(record, actual_by_hour[record["target_hour"]]))
            evaluations = merge_hourly_evaluations(evaluations, additions)

            # Use this meter/direction's recent measured daily profile as scale.
            # The generic solar/household prior only distributes that energy by hour.
            daily_rates = list((self._history.get("monthly_daily_kwh") or {}).values())
            daily_energy = (sum(float(x) for x in daily_rates) / len(daily_rates)) if daily_rates else 0.0
            state = self.hass.states.get(self._source)
            if state and state.state not in ("unknown", "unavailable") and daily_energy <= 0:
                try:
                    # First-install scale: use elapsed billing-period energy only.
                    period_start = self._data.get("billing_period_start") or self._data.get("billing_start")
                    baseline = float(self._data.get("previous_consumption_reading" if self._direction == "consumption" else "previous_feed_in_reading", 0) or 0)
                    if period_start:
                        from datetime import date
                        days = max(1, (now.date() - date.fromisoformat(str(period_start)[:10])).days + 1)
                        daily_energy = max(0.0, (float(state.state) - baseline) / days)
                except (TypeError, ValueError):
                    daily_energy = 0.0
            new_records = []
            # Keep a multi-year evaluation record for long-term trend analysis.
            # Model adaptation remains bounded to recent data to avoid learning
            # obsolete household/plant behavior after structural changes.
            learning_cutoff = (utc_now - timedelta(days=90)).isoformat()
            recent_evaluations = [item for item in evaluations.values()
                                  if item.get("target_hour", "") >= learning_cutoff]
            learning = learn_candidate_scale(recent_evaluations)
            model_scale = float(self._learning_state.get("model_scale", 1.0) or 1.0)
            model_version = int(self._learning_state.get("model_version", 1))
            if learning.get("adopted"):
                # The learned value is a correction relative to the currently
                # applied scale because stored predictions already include it.
                model_scale *= float(learning["scale"])
                model_version += 1
            if daily_energy > 0:
                new_records = build_hourly_forecasts(
                    meter_id=self._entry_id, direction=self._direction, now=now,
                    daily_energy=daily_energy, latitude=self.hass.config.latitude,
                    longitude=self.hass.config.longitude, timezone_info=now.tzinfo,
                    orientations=_feed_in_orientations(self._data),
                    horizon_hours=24, model_version=model_version,
                )
                for record in new_records:
                    record["predicted_value"] *= model_scale
            forecasts = merge_forecast_records(forecasts, new_records)
            # Discard only expired predictions; completed evaluations remain for trend metrics.
            cutoff = (utc_now - timedelta(days=90)).isoformat()
            forecasts = {k: v for k, v in forecasts.items() if v.get("target_hour", "") >= cutoff}
            evaluation_cutoff = (utc_now - timedelta(days=365 * 3)).isoformat()
            evaluations = {
                key: item for key, item in evaluations.items()
                if item.get("target_hour", "") >= evaluation_cutoff
            }
            self._learning_state = {
                "forecasts": forecasts, "evaluations": evaluations,
                "model_version": model_version,
                "model_scale": model_scale,
                "last_learning_result": learning,
                "last_cycle": utc_now.isoformat(),
            }
            await self._learning_store.async_save(self._learning_state)
            # Keep a second persistent copy; both stores use Home Assistant's
            # atomic Store writes and remain independent of integration updates.
            await self._learning_backup_store.async_save(self._learning_state)
            measured = reliability_from_hourly_evaluations(list(evaluations.values()))
            self._attr_extra_state_attributes.update({
                "forecast_hourly_evaluation_count": measured["count"],
                "forecast_hourly_mae": measured["mae"],
                "forecast_hourly_relative_error_percent": measured["relative_error_percent"],
                "forecast_hourly_bias": measured["bias"],
                "forecast_measured_reliability_percent": measured["score"],
                "forecast_measured_reliability_available": measured["available"],
                "forecast_learning_model_version": self._learning_state["model_version"],
                "forecast_hourly_pending_count": len(forecasts),
            })
            if measured["available"]:
                self._attr_extra_state_attributes["forecast_reliability_percent"] = measured["score"]
                self._attr_extra_state_attributes["forecast_reliability_basis"] = measured["basis"]
                self._attr_extra_state_attributes["forecast_reliability_available"] = True
                self._attr_extra_state_attributes["forecast_reliability_is_initial"] = False
            await self._async_refresh_forecast_value()
            self.async_write_ha_state()
        except Exception:  # noqa: BLE001
            _LOGGER.exception("VerbrauchsMonitor: Stündlicher Prognose-Lernzyklus fehlgeschlagen (%s, %s)", self._entry_id, self._direction)

    async def _async_refresh_history(self):
        """Load this meter/direction history daily through Recorder, off the event loop."""
        if not self._source:
            return
        try:
            from datetime import timedelta
            from homeassistant.components.recorder import history
            from homeassistant.util import dt as dt_util
            end = dt_util.utcnow()
            start = end - timedelta(days=366 * 2 + 7)
            samples = []
            # Long-term statistics survive the normal detailed-history purge.
            # They are available for cumulative sensors with a supported
            # state_class (total/total_increasing); unsupported entities fall
            # back to the detailed Recorder history below.
            try:
                from homeassistant.components.recorder import statistics
                from homeassistant.components.recorder import get_instance
                recorder = get_instance(self.hass)
                statistic_rows = await recorder.async_add_executor_job(
                    statistics.statistics_during_period, self.hass, start, end,
                    {self._source}, "hour", None, {"sum", "state"}
                )
                for row in statistic_rows.get(self._source, []):
                    timestamp = row.get("start")
                    value = row.get("sum") if row.get("sum") is not None else row.get("state")
                    if timestamp is not None and value is not None:
                        samples.append((timestamp, value))
            except Exception:  # noqa: BLE001
                # Not every source entity has long-term statistics metadata.
                # Detailed history below remains a safe fallback.
                pass
            if len(samples) < 2:
                from homeassistant.components.recorder import get_instance
                recorder = get_instance(self.hass)
                states = await recorder.async_add_executor_job(
                    history.get_significant_states, self.hass, start, end, [self._source],
                    None, True, False, False, True, False
                )
                for item in states.get(self._source, []):
                    timestamp = getattr(item, "last_updated", None) or getattr(item, "last_changed", None)
                    value = getattr(item, "state", None)
                    if timestamp is not None and value not in (None, "unknown", "unavailable"):
                        samples.append((timestamp, value))
            from .forecast import evaluate_history
            self._history = evaluate_history(samples, today=dt_util.now().date())
            history_months = int(self._history.get("history_months", 0) or 0)
            if history_months >= 24 and int(self._history.get("two_cycle_months", 0) or 0) >= 10 and self._history.get("usable"):
                reliability_method = "seasonal_24m"
            elif history_months >= 12 and self._history.get("usable"):
                reliability_method = "seasonal_12m"
            else:
                reliability_method = "linear_elapsed_period_average"
            current_season = self._configured_season()
            self._attr_extra_state_attributes["forecast_current_season"] = current_season
            self._attr_extra_state_attributes["forecast_season_source"] = "local_astronomical_calculation"
            from .forecast_model import solar_position, daylight_hours
            now_local = dt_util.now()
            solar = solar_position(now_local, self.hass.config.latitude, self.hass.config.longitude)
            self._attr_extra_state_attributes.update({
                "forecast_solar_elevation_deg": round(solar["elevation_deg"], 2),
                "forecast_solar_azimuth_deg": round(solar["azimuth_deg"], 2),
                "forecast_daylight_hours": round(daylight_hours(now_local.date(), self.hass.config.latitude), 2),
                "forecast_solar_phase": "daylight" if solar["daylight"] else "twilight" if solar["twilight"] else "dark",
            })
        except (ImportError, AttributeError, TypeError, ValueError):
            # Recorder disabled/unavailable: the calculation transparently uses linear fallback.
            self._history = {}
        except Exception:  # noqa: BLE001
            _LOGGER.exception("VerbrauchsMonitor: Recorder-Historie für Prognose nicht lesbar")
            self._history = {}
        await self._async_refresh_forecast_value()
        self.async_write_ha_state()

    def _configured_season(self):
        """Resolve the current astronomical season from HA's global location."""
        from homeassistant.util import dt as dt_util
        from .seasons import current_ha_season
        return current_ha_season(self.hass, dt_util.now())

    def _booked_advances(self, period_start, as_of):
        """Sum monthly advances automatically counted from each month's first day."""
        from .ledger import calculate_advance_total
        from decimal import Decimal
        vat = Decimal(str(self._data.get(CONF_VAT_RATE, 19) or 0))
        if self._direction == "consumption":
            monthly_gross = Decimal(str(self._data.get("monthly_advance", 0) or 0)) * (Decimal(1) + vat / Decimal(100))
        else:
            monthly_gross = Decimal(str(self._data.get("feed_in_monthly_advance", 0) or 0)) * (Decimal(1) + vat / Decimal(100))
        overrides = {
            str(item.get("month")): Decimal(str(item.get("amount", 0)))
            for item in self._data.get("monthly_advances", [])
            if item.get("direction") == self._direction and item.get("month") and not item.get("superseded")
        }
        bookings = [
            b for b in self._data.get("bookings", [])
            if b.get("direction") == self._direction and b.get("status", "assigned") == "assigned"
        ]
        return calculate_advance_total(
            monthly_advance_gross=monthly_gross, bookings=bookings,
            period_start=period_start.isoformat(), as_of=as_of,
            period_end=self._data.get("billing_period_end") or self._data.get(CONF_BILLING_END),
            monthly_amounts=overrides,
        )

    @property
    def native_value(self):
        """Return the last asynchronously calculated value without blocking HA."""
        return self._cached_native_value

    async def _async_refresh_forecast_and_write(self):
        """Refresh the cached forecast and publish its new state."""
        await self._async_refresh_forecast_value()
        self.async_write_ha_state()

    def _set_reliability_progress(self, value: int, *, complete: bool = False) -> None:
        """Publish monotonic progress for the current reliability calculation.

        Progress describes completed calculation phases, never the reliability
        score itself. The maximum is retained while a refresh is pending so a
        queued entity update cannot make the visible progress move backwards.
        """
        value = max(0, min(100, int(value)))
        self._reliability_progress_percent = max(
            int(getattr(self, "_reliability_progress_percent", 0)), value
        )
        self._reliability_progress_pending = not complete
        self._attr_extra_state_attributes.update({
            "forecast_reliability_progress_percent": self._reliability_progress_percent,
            "forecast_reliability_pending": not complete,
        })

    async def _async_refresh_forecast_value(self):
        """Recalculate the forecast off the event loop and publish a cached value.

        The synchronous native_value property is called during Home Assistant
        state writes. Recorder-independent forecast projection can be expensive,
        so all pure forecast-model work is delegated to the executor.
        """
        if not self._source:
            self._cached_native_value = None
            self._set_reliability_progress(100, complete=True)
            return
        async with self._forecast_refresh_lock:
            # Progress is monotonic for the lifetime of this sensor. A queued
            # entity update may keep the spinner active, but never resets it.
            self._set_reliability_progress(5)
            state = self.hass.states.get(self._source)
            if state is None or state.state in ("unknown", "unavailable"):
                self._cached_native_value = None
                self._attr_extra_state_attributes["forecast_status"] = "source_unavailable"
                self._set_reliability_progress(100, complete=True)
                return
            start = (self._data.get("billing_period_start") or self._data.get("billing_start")
                     or self._data.get(CONF_CONTRACT_START))
            if not start:
                self._cached_native_value = None
                self._attr_extra_state_attributes["forecast_status"] = "missing_period_start"
                self._set_reliability_progress(100, complete=True)
                return
            self._set_reliability_progress(20)
            try:
                from datetime import date as _date, datetime, timedelta
                from decimal import Decimal as _Decimal
                from homeassistant.util import dt as dt_util
                from .forecast import calculate_forecast
                from .forecast_model import (
                    reliability_from_hourly_evaluations, resolve_forecast_reliability,
                    solar_position, daylight_hours, sunrise_sunset,
                )

                now_local = dt_util.now()
                now_date = now_local.date()
                current_season = self._configured_season()
                self._attr_extra_state_attributes.update({
                    "forecast_current_season": current_season,
                    "forecast_season_source": "home_assistant_location_astronomical",
                })
                period_start_date = _date.fromisoformat(str(start)[:10])
                period_length = max(1, int(self._data.get("billing_period_months", 12) or 12))
                vat = _Decimal(str(self._data.get(CONF_VAT_RATE, 19) or 0))
                vat_factor = _Decimal(1) + vat / _Decimal(100)
                default_gross = (
                    _Decimal(str(self._data.get("monthly_advance", 0) or 0)) * vat_factor
                    if self._direction == "consumption"
                    else _Decimal(str(self._data.get("feed_in_monthly_advance", 0) or 0)) * vat_factor
                )
                overrides = {
                    str(item.get("month")): _Decimal(str(item.get("amount", 0)))
                    for item in self._data.get("monthly_advances", [])
                    if item.get("direction") == self._direction and item.get("month")
                    and not item.get("superseded")
                }
                configured_period_end = (
                    self._data.get("billing_period_end") or self._data.get("billing_end")
                    or self._data.get(CONF_BILLING_END) or self._data.get(CONF_CONTRACT_END)
                )
                end_month_index = period_start_date.year * 12 + period_start_date.month - 1 + period_length
                end_month_start = _date(end_month_index // 12, end_month_index % 12 + 1, 1)
                end_date = (
                    _date.fromisoformat(str(configured_period_end)[:10])
                    if configured_period_end else end_month_start - timedelta(days=1)
                )
                schedule_total = _Decimal("0")
                schedule_month_count = 0
                cursor = _date(period_start_date.year, period_start_date.month, 1)
                # A due date exists only when the first of the month lies
                # inside the billing period, matching calculate_advance_total.
                if cursor < period_start_date:
                    cursor = _date(cursor.year + (cursor.month == 12),
                                   1 if cursor.month == 12 else cursor.month + 1, 1)
                while cursor <= end_date:
                    schedule_total += overrides.get(cursor.strftime("%Y-%m"), default_gross)
                    schedule_month_count += 1
                    cursor = _date(cursor.year + (cursor.month == 12),
                                   1 if cursor.month == 12 else cursor.month + 1, 1)
                average_gross = schedule_total / _Decimal(max(1, schedule_month_count))
                cursor = _date(now_date.year, now_date.month, 1)
                if cursor <= now_date:
                    cursor = _date(cursor.year + (cursor.month == 12),
                                   1 if cursor.month == 12 else cursor.month + 1, 1)
                remaining_schedule = _Decimal("0")
                while cursor <= end_date:
                    remaining_schedule += overrides.get(cursor.strftime("%Y-%m"), default_gross)
                    cursor = _date(cursor.year + (cursor.month == 12),
                                   1 if cursor.month == 12 else cursor.month + 1, 1)

                price = (self._data.get(CONF_PURCHASE_PRICE_NET, 0)
                         if self._direction == "consumption"
                         else self._data.get(CONF_FEED_IN_PRICE_NET, 0))
                accrued_extra_charges = _Decimal("0")
                from .ledger import calculate_booking_adjustments
                period_bookings = [
                    booking for booking in self._data.get("bookings", [])
                    if booking.get("direction") == self._direction
                    and booking.get("status", "assigned") == "assigned"
                    and str(booking.get("date", ""))[:10] >= period_start_date.isoformat()
                    and str(booking.get("date", ""))[:10] <= now_date.isoformat()
                ]
                booking_credits, booking_payments, booking_extra_charges, booking_corrections = calculate_booking_adjustments(
                    bookings=period_bookings, direction=self._direction
                )
                # Only one-off extra charges are added once to the forecast.
                # Credits, extra payments and signed corrections are applied
                # separately using the same account sign convention as balance.
                accrued_extra_charges = booking_extra_charges
                local_timezone = dt_util.get_time_zone(self.hass.config.time_zone) or now_local.tzinfo
                latitude = self.hass.config.latitude
                longitude = self.hass.config.longitude
                forecast_args = {
                    "direction": self._direction,
                    "current_reading": state.state,
                    "baseline_reading": self._data.get(
                        "previous_consumption_reading" if self._direction == "consumption"
                        else "previous_feed_in_reading", 0),
                    "period_start": start, "today": now_date, "price_net": price,
                    "as_of": now_local,
                    "period_end_override": end_date.isoformat(),
                    "vat_rate": vat, "annual_base_price_net": self._data.get(CONF_BASE_PRICE_NET, 0),
                    "monthly_advance_net": average_gross / vat_factor if self._direction == "consumption" else self._data.get(CONF_MONTHLY_ADVANCE, 0),
                    "feed_in_monthly_advance_net": average_gross if self._direction == "feed_in" else self._data.get("feed_in_monthly_advance", 0),
                    "period_months": period_length, "history": self._history,
                    "booked_advances": self._booked_advances(period_start_date, now_date),
                    "future_scheduled_advances": remaining_schedule,
                    "season": current_season,
                    "hemisphere": "south" if float(latitude) < 0 else "north",
                    "latitude": latitude, "longitude": longitude,
                    "local_timezone": local_timezone,
                    "feed_in_directions": _feed_in_orientations(self._data),
                    "accrued_extra_charges": accrued_extra_charges,
                    "additional_payments": booking_payments,
                    "credits": booking_credits,
                    "corrections": booking_corrections,
                }
                from functools import partial
                result = await self.hass.async_add_executor_job(
                    partial(calculate_forecast, **forecast_args)
                )
                self._set_reliability_progress(65)

                hourly_evaluations = list((getattr(self, "_learning_state", {}) or {}).get("evaluations", {}).values())
                from .reliability import derive_impact_weights
                impact_weights = derive_impact_weights(result)
                reliability = resolve_forecast_reliability(
                    initial_score=None,
                    initial_created_at=getattr(self, "_reliability_started_at", None),
                    now=now_local,
                    evaluations=hourly_evaluations,
                    history={
                        **self._history,
                        "context_coverage_percent": 100.0 * sum((
                            bool(self._source),
                            latitude is not None and longitude is not None,
                            bool(period_start_date and end_date),
                            self._data.get(CONF_BASE_PRICE_NET) is not None,
                            self._data.get(CONF_PURCHASE_PRICE_NET) is not None,
                            bool(booking_payments),
                            bool(remaining_schedule),
                            bool(self._history.get("sample_count")),
                        )) / 8.0,
                    },
                    method=result.get("method", "linear_elapsed_period_average"),
                    provisional_hours=0.25,
                    reliability_context={
                        "billing_period_start": period_start_date,
                        "billing_period_end": end_date,
                        # A: measurable source-data freshness. Time of day,
                        # season and solar position influence the forecast
                        # model but are not proof of forecast reliability.
                        "forecast_factors": {
                            "meter_freshness": (
                                max(0.0, min(100.0, 100.0 * (1.0 - max(
                                    0.0, (now_local - state.last_updated).total_seconds()
                                ) / (7.0 * 86400.0))))
                                if state.last_updated and state.state not in ("unknown", "unavailable", "none", "")
                                else None
                            ),
                            **environmental_reliability_factors(
                                self.hass, self._data, dt_util.utcnow()
                            ),
                        },
                        # B: only objectively verifiable financial inputs.
                        # Optional bookings and future plans are not treated
                        # as paid amounts or as an automatic quality bonus.
                        "financial_factors": {
                            "valid_energy_tariff": (
                                100.0 if price is not None and _Decimal(str(price)) >= 0 else None
                            ),
                            "valid_billing_period": (
                                100.0 if period_start_date < end_date else None
                            ),
                            "valid_vat": (
                                100.0 if _Decimal("0") <= vat <= _Decimal("100") else None
                            ),
                        },
                        # Euro-impact weights; a zero-impact module is omitted.
                        # Weights are derived from actual forecast euros, not
                        # from the mere presence of a booking or a fixed split.
                        **impact_weights,
                    },
                )
                self._set_reliability_progress(90)
                reliability.update({
                    "forecast_recommendation_available": bool(
                        result.get("forecast_recommendation_available")
                    ),
                    "forecast_recommendation_unavailable_reason": result.get(
                        "forecast_recommendation_unavailable_reason"
                    ),
                    "forecast_recommendation_is_initial": bool(reliability.get("forecast_reliability_is_initial", False)),
                    "forecast_reliability_start_value": None,
                    "forecast_reliability_last_evaluated": (
                        self._reliability_state.get("last_evaluated") if self._reliability_state else None
                    ),
                })
                if latitude is not None and longitude is not None:
                    solar = solar_position(now_local, latitude, longitude)
                    solar_events = sunrise_sunset(now_date, latitude, longitude, local_timezone)
                    solar_attrs = {
                        "forecast_solar_position_used": True,
                        "forecast_solar_elevation_deg": round(solar["elevation_deg"], 2),
                        "forecast_solar_azimuth_deg": round(solar["azimuth_deg"], 2),
                        "forecast_solar_daylight_hours": round(daylight_hours(now_date, latitude), 2),
                        "forecast_sunrise_local": solar_events["sunrise"].isoformat() if solar_events["sunrise"] else None,
                        "forecast_sunset_local": solar_events["sunset"].isoformat() if solar_events["sunset"] else None,
                        "forecast_solar_polar_day": solar_events["polar_day"],
                        "forecast_solar_directions_used": _feed_in_orientations(self._data) if self._direction == "feed_in" else [],
                        "forecast_feed_in_orientation": _feed_in_orientations(self._data) if self._direction == "feed_in" else None,
                    }
                else:
                    solar_attrs = {"forecast_solar_position_used": False}

                self._attr_extra_state_attributes.update(result)
                self._attr_extra_state_attributes.update(solar_attrs)
                self._attr_extra_state_attributes.update(reliability)
                self._attr_extra_state_attributes.update({
                    "expected_future_advances_eur": float(remaining_schedule.quantize(_Decimal("0.01"), rounding=ROUND_HALF_UP)),
                    "forecast_history_used": bool(self._history.get("usable")),
                    "forecast_history_coverage_percent": self._history.get("coverage_percent", 0),
                    "forecast_history_gap_days_max": self._history.get("gap_days_max", 0),
                    "forecast_history_sample_count": self._history.get("sample_count", 0),
                    "forecast_status": "ok",
                })
                self._cached_native_value = (
                    result["expected_year_end_balance_eur"] if self._metric == "annual_balance"
                    else result["recommended_monthly_advance_eur"]
                )
                self._set_reliability_progress(100, complete=True)
            except (TypeError, ValueError, ArithmeticError) as err:
                self._cached_native_value = None
                self._attr_extra_state_attributes["forecast_status"] = "invalid_basis"
                self._attr_extra_state_attributes["forecast_error"] = str(err)
                self._set_reliability_progress(100, complete=True)
            except Exception as err:  # noqa: BLE001
                self._cached_native_value = None
                _LOGGER.exception(
                    "VerbrauchsMonitor: Prognoseberechnung fehlgeschlagen (%s, %s)",
                    self._entry_id, self._direction,
                )
                self._attr_extra_state_attributes["forecast_status"] = "calculation_error"
                self._attr_extra_state_attributes["forecast_error"] = f"{type(err).__name__}: {err}"
                self._set_reliability_progress(100, complete=True)
