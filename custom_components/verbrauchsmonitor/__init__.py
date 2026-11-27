"""VerbrauchsMonitor integration."""
from __future__ import annotations
import json
from calendar import monthrange
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall

from .const import DOMAIN, PLATFORMS
from .frontend import async_register_card
from .database import status as db_status, optimize as db_optimize, export_database, import_database
from .registry_cleanup import expected_sensor_unique_ids, expected_entity_ids


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up integration-wide resources."""
    await async_register_card(hass)
    async def handle_status(call):
        """Return the current local database status through the registered integration service."""
        entries = [entry for entry in hass.config_entries.async_entries(DOMAIN)]
        result=await hass.async_add_executor_job(db_status, hass, entries); hass.states.async_set("sensor.verbrauchsmonitor_datenbankstatus", result.get("status", "error"), result)
    async def handle_optimize(call):
        """Run the local database optimization operation in the executor."""
        result=await hass.async_add_executor_job(db_optimize, hass); hass.states.async_set("sensor.verbrauchsmonitor_datenbankstatus", result.get("status", "error"), result)
    async def handle_export(call):
        """Export the integration database to the requested service response."""
        url=await hass.async_add_executor_job(export_database, hass); hass.states.async_set("sensor.verbrauchsmonitor_datenbank_export", url)
    async def handle_import(call: ServiceCall):
        """Validate and import a supplied database payload."""
        try:
            result=await hass.async_add_executor_job(import_database, hass, call.data["filename"])
        except (OSError, ValueError, json.JSONDecodeError) as err:
            hass.states.async_set("sensor.verbrauchsmonitor_datenbankstatus", "error", {"message": str(err)})
            raise
        hass.states.async_set("sensor.verbrauchsmonitor_datenbankstatus", result.get("status", "error"), result)
    hass.services.async_register(DOMAIN, "database_status", handle_status)
    hass.services.async_register(DOMAIN, "database_optimize", handle_optimize)
    hass.services.async_register(DOMAIN, "database_export", handle_export)
    hass.services.async_register(DOMAIN, "database_import", handle_import)

    async def handle_set_baseline(call: ServiceCall):
        """Update a meter's previous-period closing reading and reload entities."""
        entry_id = call.data["entry_id"]
        meter_id = call.data["meter_id"]
        direction = call.data["direction"]
        if direction not in ("consumption", "feed_in"):
            raise ValueError("Ungültige Abrechnungsrichtung")
        from decimal import Decimal
        value = Decimal(str(call.data["value"]))
        if not value.is_finite() or value < 0 or max(0, -value.as_tuple().exponent) > 6:
            raise ValueError("Zählerstände müssen gültig sein und dürfen höchstens sechs Nachkommastellen haben")
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is None or entry.domain != DOMAIN:
            raise ValueError("VerbrauchsMonitor-Konfiguration nicht gefunden")
        key = "previous_consumption_reading" if direction == "consumption" else "previous_feed_in_reading"
        meters = [dict(m) for m in entry.options.get("meters", [])]
        target = next((m for m in meters if m.get("id") == meter_id), None)
        if target is None:
            raise ValueError("Zähler nicht gefunden")
        if direction == "feed_in" and not target.get("feed_in_entity"):
            raise ValueError("Für diesen Zähler ist keine Einspeisung konfiguriert")
        from homeassistant.util import dt as dt_util
        old_value = target.get(key, "0")
        source_key = "feed_in_baseline_source" if direction == "feed_in" else "consumption_baseline_source"
        date_key = "feed_in_baseline_updated_at" if direction == "feed_in" else "consumption_baseline_updated_at"
        history_key = "feed_in_baseline_history" if direction == "feed_in" else "consumption_baseline_history"
        previous_source = target.get(source_key, "manual")
        history = list(target.get(history_key, []))
        if str(old_value) != str(value):
            history.append({"value": str(old_value), "source": previous_source, "date": target.get(date_key)})
        target[key] = str(value)
        target[source_key] = "corrected" if previous_source == "routine" else "manual"
        target[date_key] = dt_util.now().date().isoformat()
        target[history_key] = history
        hass.config_entries.async_update_entry(entry, options={**dict(entry.options), "meters": meters})

    hass.services.async_register(DOMAIN, "set_billing_baseline", handle_set_baseline)

    async def handle_update_contract(call: ServiceCall):
        """Update supported tariff fields from the billing card, values are gross."""
        from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
        entry = hass.config_entries.async_get_entry(call.data["entry_id"])
        if entry is None or entry.domain != DOMAIN:
            raise ValueError("VerbrauchsMonitor-Konfiguration nicht gefunden")
        contract_id = str(call.data["contract_id"])
        contracts = [dict(item) for item in entry.options.get("contracts", [])]
        contract = next((item for item in contracts if item.get("id") == contract_id), None)
        if contract is None:
            raise ValueError("Vertrag nicht gefunden")
        try:
            vat = Decimal(str(call.data.get("vat_rate_percent", contract.get("vat_rate", 19))))
            if not vat.is_finite() or vat < 0 or vat > 100:
                raise ValueError
            factor = Decimal(1) + vat / Decimal(100)
            mapping = {
                "purchase_price_gross_ct_kwh": "purchase_price_net",
                "feed_in_price_gross_ct_kwh": "feed_in_price_net",
                "base_price_gross": "base_price_net",
                "monthly_advance_gross": "monthly_advance",
            }
            for incoming, stored in mapping.items():
                if incoming not in call.data:
                    continue
                value = Decimal(str(call.data[incoming]))
                if not value.is_finite() or value < 0 or max(0, -value.as_tuple().exponent) > 6:
                    raise ValueError
                # Keep exact decimal text in options; Decimal(str(...)) is used by calculations.
                net_value = value / factor if factor else value
                contract[stored] = str(net_value.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))
            contract["vat_rate"] = float(vat)
        except (InvalidOperation, ValueError, TypeError, ArithmeticError):
            raise ValueError("Ungültige Vertrags- oder Tarifwerte") from None
        options = {**dict(entry.options), "contracts": contracts}
        # The billing card edits the previous-period closing readings in the
        # same save operation as contract tariffs. Keep meter baselines central.
        if "previous_consumption_reading" in call.data or "previous_feed_in_reading" in call.data:
            meters = [dict(item) for item in options.get("meters", [])]
            meter = next((item for item in meters if item.get("id") == call.data.get("meter_id")), None)
            if meter is None:
                raise ValueError("Zähler nicht gefunden")
            for incoming, stored in (("previous_consumption_reading", "previous_consumption_reading"), ("previous_feed_in_reading", "previous_feed_in_reading")):
                if incoming in call.data:
                    raw = str(call.data[incoming]).strip().replace(" ", "")
                    raw = raw.replace(".", "").replace(",", ".") if "," in raw else raw
                    value = Decimal(raw)
                    if not value.is_finite() or value < 0:
                        raise ValueError("Ungültiger Endzählerstand")
                    if max(0, -value.as_tuple().exponent) > 6:
                        raise ValueError("Zählerstände dürfen höchstens sechs Nachkommastellen haben")
                    source_key = "feed_in_baseline_source" if stored == "previous_feed_in_reading" else "consumption_baseline_source"
                    date_key = "feed_in_baseline_updated_at" if stored == "previous_feed_in_reading" else "consumption_baseline_updated_at"
                    history_key = "feed_in_baseline_history" if stored == "previous_feed_in_reading" else "consumption_baseline_history"
                    old_value = meter.get(stored, "0")
                    previous_source = meter.get(source_key, "manual")
                    history = list(meter.get(history_key, []))
                    if str(old_value) != str(value):
                        history.append({"value": str(old_value), "source": previous_source, "date": meter.get(date_key)})
                    meter[stored] = str(value)
                    meter[source_key] = "corrected" if previous_source == "routine" else "manual"
                    from homeassistant.util import dt as dt_util
                    meter[date_key] = dt_util.now().date().isoformat()
                    meter[history_key] = history
            options["meters"] = meters
        # Meter-change records are stored per logical meter. Each record is
        # dated and carries independent end readings; this supports multiple
        # replacements in one billing period without overwriting earlier ones.
        if "meter_changes" in call.data:
            import uuid
            raw_changes = call.data["meter_changes"]
            if not isinstance(raw_changes, list):
                raise ValueError("Ungültige Zählerwechsel-Liste")
            meters = [dict(item) for item in options.get("meters", [])]
            meter = next((item for item in meters if item.get("id") == call.data.get("meter_id")), None)
            if meter is None:
                raise ValueError("Zähler nicht gefunden")
            changes = []
            for record in raw_changes:
                if not isinstance(record, dict):
                    raise ValueError("Ungültiger Zählerwechsel")
                date = str(record.get("date", ""))[:10]
                if len(date) != 10:
                    raise ValueError("Für jeden Zählerwechsel ist ein Datum erforderlich")
                from datetime import date as date_type
                date_type.fromisoformat(date)
                item = {"id": str(record.get("id") or uuid.uuid4()), "date": date}
                for key in ("consumption_reading", "feed_in_reading"):
                    value = record.get(key)
                    if value not in (None, ""):
                        number = Decimal(str(value))
                        if not number.is_finite() or number < 0:
                            raise ValueError("Zählerwechselwerte müssen gültige nichtnegative Zahlen sein")
                        item[key] = float(number)
                if "consumption_reading" not in item:
                    raise ValueError("Verbrauchs-Endstand fehlt")
                if meter.get("feed_in_entity") and "feed_in_reading" not in item:
                    raise ValueError("Einspeisungs-Endstand fehlt")
                changes.append(item)
            changes.sort(key=lambda item: item["date"])
            meter["meter_changes"] = changes
            options["meters"] = meters
        hass.config_entries.async_update_entry(entry, options=options)

    hass.services.async_register(DOMAIN, "update_contract", handle_update_contract)
    return True


def _period_start_for_date(anchor: date, period_months: int, today: date) -> date | None:
    """Return the latest recurring billing-period start at or before today."""
    if period_months < 1 or anchor > today:
        return None
    month_delta = (today.year - anchor.year) * 12 + today.month - anchor.month
    period_index = month_delta // period_months
    target_month_index = anchor.year * 12 + anchor.month - 1 + period_index * period_months
    year, month_zero = divmod(target_month_index, 12)
    month = month_zero + 1
    day = min(anchor.day, monthrange(year, month)[1])
    return date(year, month, day)


async def _async_apply_routine_baselines(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Capture current readings exactly on a new billing-period start date.

    This is deliberately not a meter replacement. It updates the logical
    billing baseline independently for consumption and feed-in and preserves
    the previous value and its provenance in the meter options.
    """
    from homeassistant.util import dt as dt_util
    today = dt_util.now().date()
    options = dict(entry.options)
    contracts = {str(item.get("id")): item for item in options.get("contracts", [])}
    meters = [dict(item) for item in options.get("meters", [])]
    changed = False
    for meter in meters:
        contract = contracts.get(str(meter.get("contract_id")), {})
        anchor_text = contract.get("billing_period_start") or contract.get("billing_start") or contract.get("contract_start")
        if not anchor_text:
            continue
        try:
            anchor = date.fromisoformat(str(anchor_text)[:10])
            months = max(1, int(contract.get("billing_period_months", 12)))
        except (ValueError, TypeError):
            continue
        current_period_start = _period_start_for_date(anchor, months, today)
        # Only capture on the actual boundary. If Home Assistant was offline
        # that day, do not pretend a later reading was the boundary reading.
        if current_period_start != today:
            continue
        period_marker = today.isoformat()
        for direction, entity_key, reading_key in (
            ("consumption", "consumption_entity", "previous_consumption_reading"),
            ("feed_in", "feed_in_entity", "previous_feed_in_reading"),
        ):
            period_key = f"{direction}_baseline_period_start"
            if meter.get(period_key) == period_marker:
                continue
            entity_id = meter.get(entity_key)
            if not entity_id:
                continue
            state = hass.states.get(entity_id)
            if state is None or state.state in ("unknown", "unavailable"):
                continue
            try:
                reading = Decimal(str(state.state))
                if not reading.is_finite() or reading < 0:
                    continue
            except (InvalidOperation, ValueError):
                continue
            source_key = f"{direction}_baseline_source"
            date_key = f"{direction}_baseline_updated_at"
            history_key = f"{direction}_baseline_history"
            history = list(meter.get(history_key, []))
            old_value = meter.get(reading_key, "0")
            # A new billing period is a distinct historical event even when
            # the numerical reading happens to be unchanged.
            history.append({"value": str(old_value), "source": meter.get(source_key, "manual"), "date": meter.get(date_key)})
            meter[reading_key] = str(reading)
            meter[source_key] = "routine"
            meter[date_key] = period_marker
            meter[history_key] = history
            meter[period_key] = period_marker
            meter["billing_period_start"] = period_marker
            changed = True
    if changed:
        hass.config_entries.async_update_entry(entry, options={**options, "meters": meters})
    return changed


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a configured VerbrauchsMonitor entry."""
    # Register the Lovelace resource from the config-entry path as well.
    # Registration is idempotent, so this also repairs a missing resource after upgrades.
    await async_register_card(hass)
    # Remove orphaned sensor registry entries left behind by renamed meters or
    # disabled optional sources. Only this integration's sensor entities for
    # this config entry are considered; unrelated entities are never touched.
    from homeassistant.helpers import entity_registry as er

    registry = er.async_get(hass)
    expected_ids = expected_sensor_unique_ids(entry.options, entry.entry_id)
    canonical_entity_ids = expected_entity_ids(entry.options)
    for registry_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
        if registry_entry.platform != DOMAIN or registry_entry.domain != "sensor":
            continue
        if registry_entry.unique_id not in expected_ids:
            registry.async_remove(registry_entry.entity_id)
            continue
        target_entity_id = canonical_entity_ids.get(registry_entry.unique_id)
        if target_entity_id and registry_entry.entity_id != target_entity_id and registry.async_get(target_entity_id) is None:
            registry.async_update_entity(registry_entry.entity_id, new_entity_id=target_entity_id)

    # Remove stale device-registry records owned by this integration entry.
    # Active logical meter IDs are retained; obsolete legacy devices (including
    # the long-retired "Weitere Werte" device) are removed together with their
    # stale entity-registry entries above.
    from homeassistant.helpers import device_registry as dr
    device_registry = dr.async_get(hass)
    active_meter_ids = {str(m.get("id")) for m in entry.options.get("meters", []) if m.get("id")}
    for device in dr.async_entries_for_config_entry(device_registry, entry.entry_id):
        integration_identifiers = {identifier for identifier in device.identifiers if identifier[0] == DOMAIN}
        if not integration_identifiers:
            continue
        keep = any(identifier[1] in active_meter_ids for identifier in integration_identifiers)
        if device.name == "Weitere Werte" or not keep:
            device_registry.async_remove_device(device.id)

    # R039 global bookings are imported once into the durable ledger and remain
    # unresolved until the user assigns meter + direction. Never auto-allocate.
    from .database import migrate_legacy_bookings, load_data
    await hass.async_add_executor_job(
        migrate_legacy_bookings,
        hass,
        entry.entry_id,
        list(entry.options.get("bookings", [])),
        list(entry.options.get("meters", [])),
    )
    await hass.async_add_executor_job(load_data, hass)
    # R169: keep contracts and logical meters in dedicated SQLite domain
    # tables as well as in their existing config-entry authority. Pass the
    # complete current entry set so stale projections can be reconciled safely.
    from .database import sync_config_entries
    await hass.async_add_executor_job(
        sync_config_entries,
        hass,
        hass.config_entries.async_entries(DOMAIN),
    )
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {"entry": entry}
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # Apply a billing-start baseline once when HA starts on the boundary date,
    # then retry every five minutes on that date if a source sensor was not yet
    # available. A missed boundary date is intentionally not backfilled.
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    from homeassistant.helpers.event import async_track_time_change
    await _async_apply_routine_baselines(hass, entry)
    async def _daily_baseline_check(now):
        """Retry billing-baseline capture while the current date is a billing-period boundary."""
        await _async_apply_routine_baselines(hass, entry)
    entry.async_on_unload(async_track_time_change(hass, _daily_baseline_check, minute=range(0, 60, 5), second=0))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload an integration entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unloaded


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate legacy per-meter entries to the central hub data model."""
    if entry.version < 2:
        data = dict(entry.data)
        options = dict(entry.options)
        if data.get("meter_name"):
            contract_id = "legacy_contract"
            meter_id = "legacy_meter"
            contract = {"id": contract_id, "name": data.get("contract_name") or "Altvertrag",
                "contract_number": data.get("contract_number", ""),
                "purchase_price_net": data.get("purchase_price_net", 0),
                "feed_in_price_net": data.get("feed_in_price_net", 0),
                "vat_rate": data.get("vat_rate", 19), "base_price_net": data.get("base_price_net", 0),
                "base_price_period": data.get("base_price_period", "monthly"),
                "monthly_advance": data.get("monthly_advance", 0)}
            meter = {"id": meter_id, "name": data.get("meter_name"), "meter_number": data.get("meter_number", ""),
                "contract_id": contract_id}
            for key in ("consumption_entity", "consumption_power_entity", "feed_in_entity",
                        "feed_in_power_entity", "previous_consumption_reading", "previous_feed_in_reading"):
                if key in data: meter[key] = data[key]
            if data.get("outdoor_illuminance_entity"):
                options.setdefault("outdoor_illuminance_entity", data["outdoor_illuminance_entity"])
            options.setdefault("contracts", [contract])
            options.setdefault("meters", [meter])
        hass.config_entries.async_update_entry(entry, data={}, options=options, version=2, title="VerbrauchsMonitor")
    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Reload entities after central options have changed."""
    await hass.config_entries.async_reload(entry.entry_id)
    return True
