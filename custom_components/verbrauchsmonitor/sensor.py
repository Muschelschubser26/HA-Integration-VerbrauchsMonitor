"""Sensor mirrors for configured VerbrauchsMonitor source entities."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from types import SimpleNamespace
import logging
from decimal import ROUND_HALF_UP

_LOGGER = logging.getLogger(__name__)

from .const import (
    DOMAIN,
    CONF_CONSUMPTION_ENTITY,
    CONF_METER_NAME,
    CONF_METER_NUMBER,
    CONF_FEED_IN_ENTITY,
    CONF_FEED_IN_POWER_ENTITY,
    CONF_OUTDOOR_ILLUMINANCE_ENTITY,
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
from .naming import slugify_meter_name, meter_entity_object_ids


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
        merged = {**contract, **meter, CONF_METER_NAME: meter.get("name", "Stromzähler"), "bookings": meter_bookings, "monthly_advances": monthly_records}
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
        merged["hub_entry_id"] = entry.entry_id
        meter_entry = SimpleNamespace(entry_id=meter.get("id", entry.entry_id), data=merged)
        has_feed_in = bool(merged.get(CONF_FEED_IN_ENTITY))
        entities.extend(_build_meter_entities(meter_entry, has_feed_in))
    if entities:
        async_add_entities(entities)


def _build_meter_entities(entry, has_feed_in):
    """Build the native sensor entity descriptions for all configured meters and directions."""
    entities = []
    for config_key, (role, label, icon) in ROLE_CONFIG.items():
        source = entry.data.get(config_key)
        if source:
            entities.append(VerbrauchsMonitorMirrorSensor(entry, source, role, label, icon))
    entities.append(VerbrauchsMonitorBalanceSensor(entry, "consumption"))
    if has_feed_in:
        entities.append(VerbrauchsMonitorBalanceSensor(entry, "feed_in"))
    if entry.data.get("forecast_consumption_enabled", True):
        entities.extend(_build_forecast_entities(entry, "consumption"))
    if has_feed_in and entry.data.get("forecast_feed_in_enabled", False):
        entities.extend(_build_forecast_entities(entry, "feed_in"))
    return entities


def _build_forecast_entities(entry, direction):
    """Create annual-balance and monthly-advance forecast sensors per direction."""
    return [
        VerbrauchsMonitorForecastSensor(entry, direction, "annual_balance"),
        VerbrauchsMonitorForecastSensor(entry, direction, "monthly_advance"),
    ]


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


class VerbrauchsMonitorBalanceSensor(SensorEntity):
    """Calculated per-meter period balance based on the previous billing reading."""
    _attr_has_entity_name = False
    _attr_native_unit_of_measurement = "€"
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
        sources = [self._source] if self._source else []
        if sources:
            self.async_on_remove(async_track_state_change_event(self.hass, sources, self._changed))
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
        from .ledger import calculate_advance_total, apply_booking_corrections, signed_customer_balance
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
            today = date.today()
            months = 0
            if start_text:
                start = date.fromisoformat(str(start_text)[:10])
                if start > today:
                    return None
                months = (today.year - start.year) * 12 + today.month - start.month + 1
            configured_duration = self._data.get("billing_period_months")
            if configured_duration not in (None, ""):
                months = min(months, max(0, int(configured_duration)))
            base_gross = money_amount(base_gross_annual * Decimal(months) / Decimal(12))
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
            advances = money_amount(expected_advances)
            self._attr_extra_state_attributes["recorded_advances_paid"] = float(advances)
            self._attr_extra_state_attributes["automatic_monthly_advances_paid"] = float(advances)

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
        name = self._data.get(CONF_METER_NAME, "Stromzähler")
        label = "Jahresprognose" if metric == "annual_balance" else "Monatlicher Abschlag empfohlen"
        suffix = "Verbrauch" if direction == "consumption" else "Einspeisung"
        self._attr_unique_id = f"{entry.entry_id}_{direction}_prognose_{metric}"
        self._attr_name = f"{label} {suffix}"
        self._attr_extra_state_attributes = {"meter_name": name, "card_meter_id": entry.entry_id, "card_meter_name": name, "meter_id": entry.entry_id, "direction": direction, "vm_role": f"{direction}_forecast_{metric}", "forecast_method": "linear_elapsed_period_average"}
        self._attr_suggested_object_id = f"verbrauchsmonitor_{slugify_meter_name(name)}_{direction}_prognose_{metric}"
        self._attr_device_info = {"identifiers": {(DOMAIN, entry.entry_id)}, "name": name, "manufacturer": "Muschelschubser26 & ChatGPT", "model": "VerbrauchsMonitor"}

    async def async_added_to_hass(self):
        """Subscribe to the source entity updates after this sensor is added to Home Assistant."""
        await super().async_added_to_hass()
        self._history = {}
        from homeassistant.helpers.storage import Store
        self._reliability_store = Store(
            self.hass, 1,
            f"{DOMAIN}_{self._entry_id}_{self._direction}_forecast_reliability",
        )
        self._reliability_state = await self._reliability_store.async_load()
        if self._source:
            from datetime import timedelta
            self.async_on_remove(async_track_state_change_event(self.hass, [self._source], self._changed))
            # Refresh the expensive Recorder history daily. The reliability
            # value itself is smoothed hourly from this cached evidence.
            self.async_on_remove(async_track_time_interval(
                self.hass, self._periodic_refresh, timedelta(days=1)
            ))
            self.async_on_remove(async_track_time_interval(
                self.hass, self._periodic_reliability_update, timedelta(hours=1)
            ))
            # Season boundaries can occur at any local time; refresh hourly.
            self.async_on_remove(async_track_time_interval(
                self.hass, self._periodic_season_refresh, timedelta(hours=1)
            ))
            await self._async_refresh_history()
        self.async_write_ha_state()

    @callback
    def _periodic_refresh(self, now):
        """Refresh the two-year Recorder evidence once per day."""
        self.hass.async_create_task(self._async_refresh_history())

    @callback
    def _periodic_reliability_update(self, now):
        """Smooth the persisted reliability score hourly using cached history."""
        self.hass.async_create_task(self._async_update_reliability())

    @callback
    def _periodic_season_refresh(self, now):
        """Refresh season-dependent forecast values at least once per hour."""
        self.async_write_ha_state()

    async def _async_update_reliability(self):
        """Advance the current score by at most one point per elapsed day."""
        if not getattr(self, "_reliability_state", None):
            return
        from homeassistant.util import dt as dt_util
        from .forecast import update_reliability_state
        history_months = int(self._history.get("history_months", 0) or 0)
        if history_months >= 24 and int(self._history.get("two_cycle_months", 0) or 0) >= 10 and self._history.get("usable"):
            method = "seasonal_24m"
        elif history_months >= 12 and self._history.get("usable"):
            method = "seasonal_12m"
        else:
            method = "linear_elapsed_period_average"
        previous = dict(self._reliability_state)
        updated = update_reliability_state(
            previous, history=self._history, method=method, now=dt_util.utcnow()
        )
        if updated != previous:
            self._reliability_state = updated
            await self._reliability_store.async_save(updated)
            self.async_write_ha_state()

    @callback
    def _changed(self, event):
        """Refresh the live forecast when the source meter changes.

        Recorder history is deliberately not reloaded for every source update;
        its bounded daily refresh avoids repeated two-year history queries.
        """
        self.async_write_ha_state()

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
                statistic_rows = await self.hass.async_add_executor_job(
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
                states = await self.hass.async_add_executor_job(
                    history.get_significant_states, self.hass, start, end, [self._source],
                    None, True, False, False, True, False
                )
                for item in states.get(self._source, []):
                    timestamp = getattr(item, "last_updated", None) or getattr(item, "last_changed", None)
                    value = getattr(item, "state", None)
                    if timestamp is not None and value not in (None, "unknown", "unavailable"):
                        samples.append((timestamp, value))
            from .forecast import evaluate_history, update_reliability_state
            self._history = evaluate_history(samples, today=dt_util.now().date())
            history_months = int(self._history.get("history_months", 0) or 0)
            if history_months >= 24 and int(self._history.get("two_cycle_months", 0) or 0) >= 10 and self._history.get("usable"):
                reliability_method = "seasonal_24m"
            elif history_months >= 12 and self._history.get("usable"):
                reliability_method = "seasonal_12m"
            else:
                reliability_method = "linear_elapsed_period_average"
            self._reliability_state = update_reliability_state(
                self._reliability_state,
                history=self._history,
                method=reliability_method,
                now=dt_util.utcnow(),
            )
            await self._reliability_store.async_save(self._reliability_state)
            current_season = self._configured_season()
            self._attr_extra_state_attributes["forecast_current_season"] = current_season
            self._attr_extra_state_attributes["forecast_season_source"] = "home_assistant_location_astronomical"
        except (ImportError, AttributeError, TypeError, ValueError):
            # Recorder disabled/unavailable: the calculation transparently uses linear fallback.
            self._history = {}
        except Exception:  # noqa: BLE001
            _LOGGER.exception("VerbrauchsMonitor: Recorder-Historie für Prognose nicht lesbar")
            self._history = {}
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
        """Calculate from the current counter, tariff and direction-specific advance."""
        from datetime import date
        from homeassistant.util import dt as dt_util
        from .forecast import calculate_forecast
        state = self.hass.states.get(self._source) if self._source else None
        if state is None or state.state in ("unknown", "unavailable"):
            return None
        start = self._data.get("billing_period_start") or self._data.get("billing_start") or self._data.get(CONF_CONTRACT_START)
        if not start:
            self._attr_extra_state_attributes["forecast_status"] = "missing_period_start"
            return None
        try:
            current_season = self._configured_season()
            self._attr_extra_state_attributes["forecast_current_season"] = current_season
            self._attr_extra_state_attributes["forecast_season_source"] = "home_assistant_location_astronomical"
            price = self._data.get(CONF_PURCHASE_PRICE_NET, 0) if self._direction == "consumption" else self._data.get(CONF_FEED_IN_PRICE_NET, 0)
            from datetime import date as _date
            from decimal import Decimal as _Decimal
            period_start_date = _date.fromisoformat(str(start)[:10])
            period_length = max(1, int(self._data.get("billing_period_months", 12) or 12))
            default_gross = (
                _Decimal(str(self._data.get("monthly_advance", 0) or 0)) * (_Decimal(1) + _Decimal(str(self._data.get(CONF_VAT_RATE, 19) or 0)) / _Decimal(100))
                if self._direction == "consumption"
                else _Decimal(str(self._data.get("feed_in_monthly_advance", 0) or 0))
            )
            overrides = {str(item.get("month")): _Decimal(str(item.get("amount", 0))) for item in self._data.get("monthly_advances", []) if item.get("direction") == self._direction and item.get("month") and not item.get("superseded")}
            schedule_total = _Decimal("0")
            cursor = _date(period_start_date.year, period_start_date.month, 1)
            for _ in range(period_length):
                key = cursor.strftime("%Y-%m")
                schedule_total += overrides.get(key, default_gross)
                cursor = _date(cursor.year + (cursor.month == 12), 1 if cursor.month == 12 else cursor.month + 1, 1)
            average_gross = schedule_total / _Decimal(period_length)
            vat_factor = _Decimal(1) + _Decimal(str(self._data.get(CONF_VAT_RATE, 19) or 0)) / _Decimal(100)

            # Determine future contractual payment dates only. Amounts due in
            # the past are not payment evidence and are not added here.
            from datetime import timedelta
            month_index = period_start_date.year * 12 + period_start_date.month - 1 + period_length
            end_month_start = _date(month_index // 12, month_index % 12 + 1, 1)
            end_date = end_month_start - timedelta(days=1)
            now_date = dt_util.now().date()
            cursor = _date(now_date.year, now_date.month, 1)
            if cursor <= now_date:
                cursor = _date(cursor.year + (cursor.month == 12), 1 if cursor.month == 12 else cursor.month + 1, 1)
            remaining_schedule = _Decimal("0")
            while cursor <= end_date:
                month_key = cursor.strftime("%Y-%m")
                remaining_schedule += overrides.get(month_key, average_gross)
                cursor = _date(cursor.year + (cursor.month == 12), 1 if cursor.month == 12 else cursor.month + 1, 1)

            result = calculate_forecast(
                direction=self._direction,
                current_reading=state.state,
                baseline_reading=self._data.get("previous_consumption_reading" if self._direction == "consumption" else "previous_feed_in_reading", 0),
                period_start=start,
                today=now_date,
                price_net=price,
                vat_rate=self._data.get(CONF_VAT_RATE, 19),
                annual_base_price_net=self._data.get(CONF_BASE_PRICE_NET, 0),
                monthly_advance_net=(average_gross / vat_factor if self._direction == "consumption" else self._data.get(CONF_MONTHLY_ADVANCE, 0)),
                feed_in_monthly_advance_net=(
                    average_gross if self._direction == "feed_in" else
                    self._data.get("feed_in_monthly_advance", 0)
                ),
                period_months=period_length,
                history=self._history,
                booked_advances=self._booked_advances(period_start_date, now_date),
                future_scheduled_advances=remaining_schedule,
                season=self._configured_season(),
                hemisphere="south" if float(self.hass.config.latitude) < 0 else "north",
                accrued_extra_charges=sum(
                    (_Decimal(str(b.get("amount", 0) or 0))
                     for b in self._data.get("bookings", [])
                     if b.get("direction") == self._direction
                     and b.get("status", "assigned") == "assigned"
                     and b.get("booking_type") in ("extra_charge", "correction")
                     and str(b.get("date", ""))[:10] >= period_start_date.isoformat()
                     and str(b.get("date", ""))[:10] <= now_date.isoformat()
                     and _Decimal(str(b.get("amount", 0) or 0)) >= 0),
                    _Decimal("0"),
                ),
            )
            from .forecast import reliability_score
            reliability = reliability_score(history=self._history, method=result["method"])
            if getattr(self, "_reliability_state", None):
                reliability["forecast_reliability_percent"] = float(self._reliability_state["score"])
                reliability["forecast_reliability_level"] = (
                    "high" if reliability["forecast_reliability_percent"] >= 80
                    else "medium" if reliability["forecast_reliability_percent"] >= 50
                    else "low"
                )
            reliability["forecast_reliability_start_value"] = (
                self._reliability_state.get("score") if self._reliability_state else None
            )
            reliability["forecast_reliability_last_evaluated"] = (
                self._reliability_state.get("last_evaluated") if self._reliability_state else None
            )
            self._attr_extra_state_attributes.update(result)
            # Keep the future payment separate from costs still to accrue.
            # These attributes make it possible to verify that the expected
            # year-end balance includes the remaining energy and base price
            # exactly once, without adding new dashboard rows.
            self._attr_extra_state_attributes["expected_future_advances_eur"] = float(remaining_schedule.quantize(_Decimal("0.01"), rounding=ROUND_HALF_UP))
            self._attr_extra_state_attributes.update(reliability)
            self._attr_extra_state_attributes.update({
                "forecast_history_used": bool(self._history.get("usable")),
                "forecast_history_coverage_percent": self._history.get("coverage_percent", 0),
                "forecast_history_gap_days_max": self._history.get("gap_days_max", 0),
                "forecast_history_sample_count": self._history.get("sample_count", 0),
            })
            self._attr_extra_state_attributes["forecast_status"] = "ok"
            return result["expected_year_end_balance_eur"] if self._metric == "annual_balance" else result["recommended_monthly_advance_eur"]
        except (TypeError, ValueError, ArithmeticError) as err:
            self._attr_extra_state_attributes["forecast_status"] = "invalid_basis"
            self._attr_extra_state_attributes["forecast_error"] = str(err)
            return None
        except Exception as err:  # noqa: BLE001
            # Keep runtime failures visible as diagnosed sensor attributes.
            _LOGGER.exception("VerbrauchsMonitor: Prognoseberechnung fehlgeschlagen (%s, %s)", self._entry_id, self._direction)
            self._attr_extra_state_attributes["forecast_status"] = "calculation_error"
            self._attr_extra_state_attributes["forecast_error"] = f"{type(err).__name__}: {err}"
            return None
