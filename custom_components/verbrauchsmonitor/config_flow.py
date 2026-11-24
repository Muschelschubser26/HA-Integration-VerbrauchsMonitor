"""Central configuration flow for VerbrauchsMonitor."""
from __future__ import annotations
import uuid
import logging
from functools import partial
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


def format_amount_de(value):
    """Format a monetary value with German decimal and thousands separators."""
    try:
        amount = Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except Exception:
        amount = Decimal("0.00")
    return f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def format_tariff_de(value):
    """Format monetary tariff inputs to cents with a German decimal comma."""
    try:
        amount = Decimal(str(value if value not in (None, "") else 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        text = format(amount, ".2f")
        return text.replace(".", ",")
    except (InvalidOperation, ValueError, TypeError):
        return "0,0"


def format_feed_in_tariff_de(value):
    """Format feed-in tariff inputs without losing six-decimal precision."""
    try:
        amount = Decimal(str(value if value not in (None, "") else 0)).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
        return format(amount, ".6f").replace(".", ",")
    except (InvalidOperation, ValueError, TypeError):
        return "0"

def _date_default(value):
    """Normalize legacy German dates and ISO dates for HA DateSelector defaults."""
    if not value:
        return None
    text = str(value).strip()
    if len(text) == 10 and text[2] == ".":
        day, month, year = text.split(".")
        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    return text[:10]

def _entity():
    """Create the Home Assistant sensor entity selector used by configuration forms."""
    return selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor"))

def _num(minimum=0, maximum=1000000, step=0.01):
    """Create a bounded numeric selector for configuration forms."""
    return selector.NumberSelector(selector.NumberSelectorConfig(min=minimum, max=maximum, step=step, mode=selector.NumberSelectorMode.BOX))


def _parse_localized_meter_reading(value):
    """Parse meter readings with German decimal comma (and accept decimal dot).

    If both separators occur, dots are treated as German thousands separators
    and the comma as decimal separator. A lone dot remains a decimal separator
    for compatibility with values already entered using the previous UI.
    """
    if isinstance(value, (int, float, Decimal)):
        parsed = Decimal(str(value))
    else:
        text = str(value or "").strip().replace("\u00a0", "").replace(" ", "")
        if not text:
            raise InvalidOperation
        if "," in text:
            text = text.replace(".", "").replace(",", ".")
        parsed = Decimal(text)
    if not parsed.is_finite() or parsed < 0 or parsed > Decimal("1000000"):
        raise InvalidOperation
    return float(parsed)

def _parse_tariff_input(value):
    """Parse a tariff with comma/dot decimal notation and max. 6 decimals."""
    text = str(value if value is not None else "0").strip().replace("\u00a0", "").replace(" ", "")
    if not text:
        raise InvalidOperation
    if "," in text:
        if "." in text:
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", ".")
    parsed = Decimal(text)
    if not parsed.is_finite() or parsed < 0 or parsed > Decimal("1000000"):
        raise InvalidOperation
    if max(0, -parsed.as_tuple().exponent) > 6:
        raise InvalidOperation
    return float(parsed)


def _parse_localized_amount(value):
    """Parse monetary values using German comma or decimal-point notation."""
    text = str(value or "0").strip().replace("\u00a0", "").replace(" ", "")
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    number = Decimal(text)
    if not number.is_finite():
        raise InvalidOperation
    return float(number)

def _select(options):
    """Create a dropdown selector for the supplied option list."""
    return selector.SelectSelector(selector.SelectSelectorConfig(options=options, mode=selector.SelectSelectorMode.DROPDOWN, custom_value=False))


def _apply_optional_entities(item, old, user_input):
    """Persist optional entity selectors without redundant enable switches.

    A missing selector value preserves the previous value (HA may omit an
    untouched optional field); an explicit None/empty value removes it.
    """
    optional_sources = (
        "consumption_power_entity",
        "feed_in_entity",
        "feed_in_power_entity",
        "outdoor_illuminance_entity",
    )
    for entity_key in optional_sources:
        if entity_key in user_input:
            value = user_input.get(entity_key)
            if value is None or str(value).strip().lower() in ("", "none"):
                item.pop(entity_key, None)
            else:
                item[entity_key] = value
        elif old.get(entity_key):
            item[entity_key] = old[entity_key]
        else:
            item.pop(entity_key, None)

    # Remove legacy switch keys from existing entries as well.
    for legacy_key in ("use_consumption_power", "use_feed_in_counter", "use_feed_in_power", "use_outdoor_illuminance"):
        item.pop(legacy_key, None)

    if not item.get("feed_in_entity"):
        item.pop("feed_in_entity", None)
        item.pop("feed_in_power_entity", None)
        item.pop("previous_feed_in_reading", None)
    return item

def _month_field_label(month: str, hass) -> str:
    """Return a localized human-readable month label for dynamic form fields."""
    from datetime import date
    parsed = date.fromisoformat(f"{month}-01")
    language = str(getattr(getattr(hass, "config", None), "language", "de") or "de").lower()
    # Keep field IDs readable; Home Assistant's form labels are the schema keys.
    names_de = ("Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember")
    names_en = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December")
    names = names_en if language.startswith("en") else names_de
    return f"{names[parsed.month - 1]} {parsed.year}"


class VerbrauchsMonitorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """One integration-wide hub entry, not one entry per meter."""
    VERSION = 2

    async def async_step_user(self, user_input=None):
        """Create the single integration-wide hub entry.

        Do not assign a domain-wide flow unique_id here. Home Assistant keeps
        flows with the same unique_id mutually exclusive; an abandoned flow
        could therefore block a fresh installation with "already in progress".
        A persisted entry is checked explicitly instead.
        """
        if self.hass.config_entries.async_entries(DOMAIN):
            return self.async_abort(reason="already_configured")
        if user_input is not None:
            # Recheck immediately before creation to avoid duplicate hub entries.
            if self.hass.config_entries.async_entries(DOMAIN):
                return self.async_abort(reason="already_configured")
            return self.async_create_entry(title="VerbrauchsMonitor", data={})
        return self.async_show_form(step_id="user", data_schema=vol.Schema({}))

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Return the options-flow handler for an existing integration entry."""
        return VerbrauchsMonitorOptionsFlow()

class VerbrauchsMonitorOptionsFlow(config_entries.OptionsFlow):
    """Grouped central administration for contracts, meters, billing and database."""
    async def async_step_init(self, user_input=None):
        """Show and process the initial contract and meter management menu."""
        return self.async_show_menu(step_id="init", menu_options=["contracts", "meters", "forecast", "billing", "data_management", "about"])

    async def _save(self, **changes):
        """Persist the complete options payload through the OptionsFlow result.

        Returning an empty options-flow payload after updating the entry directly
        caused Home Assistant to replace the stored options with an empty dict.
        The options-flow result is the authoritative persistence mechanism.
        """
        options = {**dict(self.config_entry.options), **changes}
        # Outdoor illuminance is a hub-wide additional value, never meter-specific.
        if "meters" in options:
            options["meters"] = [
                {key: value for key, value in meter.items() if key != "outdoor_illuminance_entity"}
                for meter in options["meters"]
            ]
        # Home Assistant commits this complete payload when the OptionsFlow
        # finishes. Do not call async_update_entry here: that can trigger the
        # reload listener while the flow is still completing.
        return self.async_create_entry(title="", data=options)

    async def async_step_contracts(self, user_input=None):
        """Choose an action once, then continue without asking for it again."""
        contracts = list(self.config_entry.options.get("contracts", []))
        if not contracts and user_input is None:
            self._contract_action = "new"
            self._contract_edit_id = str(uuid.uuid4())
            self._contract_edit_data = {}
            self._contract_prices_direction_selected = False
            return await self.async_step_contract_wizard_identity()
        if user_input is not None:
            action = user_input.get("action", "new")
            self._contract_action = action
            if action == "new":
                self._contract_edit_id = str(uuid.uuid4())
                self._contract_edit_data = {}
                self._contract_prices_direction_selected = False
                return await self.async_step_contract_wizard_identity()
            return await self.async_step_contract_select()
        return self.async_show_form(step_id="contracts", data_schema=self._contract_action_schema())

    def _contract_action_schema(self):
        """Build the schema for contract creation, editing or removal actions."""
        actions = [
            {"value": "new", "label": self._labels("Neuen Vertrag anlegen", "Create contract")},
            {"value": "edit", "label": self._labels("Vertrag bearbeiten", "Edit contract")},
            {"value": "delete", "label": self._labels("Vertrag löschen", "Delete contract")},
        ]
        return vol.Schema({vol.Required("action", default="new"): selector.SelectSelector(
            selector.SelectSelectorConfig(options=actions, mode=selector.SelectSelectorMode.DROPDOWN)
        )})

    async def async_step_contract_select(self, user_input=None):
        """Select the contract for the previously chosen edit/delete action."""
        contracts = list(self.config_entry.options.get("contracts", []))
        action = getattr(self, "_contract_action", None)
        if action not in ("edit", "delete"):
            return await self.async_step_contracts()
        if not contracts:
            return self.async_abort(reason="no_contracts")
        if user_input is not None:
            selected = user_input.get("selected")
            if not selected or not any(c.get("id") == selected for c in contracts):
                return self.async_show_form(step_id="contract_select", data_schema=self._contract_selection_schema(contracts), errors={"base": "select_contract"})
            if action == "delete":
                self._contract_delete_id = selected
                return await self.async_step_contract_delete_confirm()
            self._contract_edit_id = selected
            self._contract_edit_data = dict(next(c for c in contracts if c.get("id") == selected))
            self._contract_prices_direction_selected = False
            return await self.async_step_contract_wizard_identity()
        return self.async_show_form(step_id="contract_select", data_schema=self._contract_selection_schema(contracts))

    def _contract_selection_schema(self, contracts):
        """Build the selector schema for choosing an existing contract."""
        opts = [{"value": c["id"], "label": f'{c.get("name", self._labels("Vertrag", "Contract"))} ({c.get("contract_number", "")})'} for c in contracts]
        return vol.Schema({vol.Required("selected", default=opts[0]["value"]): _select(opts)})

    async def async_step_contract_delete_confirm(self, user_input=None):
        """Require a separate confirmation before deleting a contract."""
        if user_input is not None:
            if not user_input.get("confirm"):
                return await self.async_step_contracts()
            selected = getattr(self, "_contract_delete_id", None)
            if any(m.get("contract_id") == selected for m in self.config_entry.options.get("meters", [])):
                return self.async_abort(reason="contract_in_use")
            contracts = [c for c in self.config_entry.options.get("contracts", []) if c.get("id") != selected]
            return await self._save(contracts=contracts)
        return self.async_show_form(step_id="contract_delete_confirm", data_schema=vol.Schema({vol.Required("confirm", default=False): bool}))

    def _labels(self, german, english):
        """Return UI labels in the Home Assistant configured language."""
        return german if str(self.hass.config.language).lower().startswith("de") else english

    def _contract_schema(self, contracts, show_selector=True):
        """Build the input schema for creating or editing contract data."""
        opts = [
            {
                "value": c["id"],
                "label": f'{c.get("name", self._labels("Vertrag", "Contract"))} ({c.get("contract_number", "")})'.strip(),
            }
            for c in contracts
        ]
        actions = [
            {"value": "new", "label": self._labels("Neuen Vertrag anlegen", "Create contract")},
            {"value": "edit", "label": self._labels("Vertrag bearbeiten", "Edit contract")},
            {"value": "delete", "label": self._labels("Vertrag löschen", "Delete contract")},
        ]
        fields = {
            vol.Required("action", default="new"): selector.SelectSelector(selector.SelectSelectorConfig(options=actions, mode=selector.SelectSelectorMode.DROPDOWN)),
        }
        if show_selector and opts:
            # Preselect the first existing contract for edit/delete. The user
            # can still choose another one explicitly in the dropdown.
            fields[vol.Optional("selected", default=opts[0]["value"])] = _select(opts)
        return vol.Schema(fields)

    async def async_step_contract_wizard_identity(self, user_input=None):
        """Wizard step 1: contract identity and billing-period dates/duration."""
        data = dict(getattr(self, "_contract_edit_data", {}))
        if user_input is not None:
            if not str(user_input.get("provider", "")).strip() or not str(user_input.get("name", "")).strip() or not str(user_input.get("contract_number", "")).strip():
                return self.async_show_form(step_id="contract_wizard_identity", data_schema=self._contract_identity_schema(user_input), errors={"base": "required_identity"})
            identity = {**data, **user_input}
            for date_key in ("contract_start", "contract_change_date", "billing_period_start", "contract_end"):
                identity[date_key] = user_input.get(date_key) or None
            try:
                months = max(1, int(identity.get("billing_period_months", 12) or 12))
                identity["billing_period_months"] = months
                start_text = identity.get("billing_period_start") or identity.get("billing_start") or identity.get("contract_start")
                if start_text:
                    from datetime import date
                    start_date = date.fromisoformat(str(start_text)[:10])
                    from calendar import monthrange
                    # Preserve the day where possible; otherwise use the month's last day.
                    end_month_index = start_date.month - 1 + months
                    end_year = start_date.year + end_month_index // 12
                    end_month = end_month_index % 12 + 1
                    from datetime import timedelta
                    end_date = date(end_year, end_month, min(start_date.day, monthrange(end_year, end_month)[1])) - timedelta(days=1)
                    identity["billing_period_end"] = end_date.isoformat()
                    identity["billing_end"] = end_date.isoformat()
                identity["billing_start"] = identity.get("billing_period_start")
            except (ValueError, TypeError, OverflowError):
                return self.async_show_form(step_id="contract_wizard_identity", data_schema=self._contract_identity_schema(identity), errors={"base": "invalid_billing_period"})
            self._contract_edit_data = identity
            try:
                return await self.async_step_contract_wizard_prices()
            except Exception:  # noqa: BLE001 - retain diagnostic traceback in HA logs
                _LOGGER.exception("VerbrauchsMonitor: Fehler beim Übergang Vertragsassistent Schritt 1 -> 2 (contract_id=%s)", getattr(self, "_contract_edit_id", "unknown"))
                return self.async_show_form(step_id="contract_wizard_identity", data_schema=self._contract_identity_schema(identity), errors={"base": "contract_flow_internal_error"})
        return self.async_show_form(step_id="contract_wizard_identity", data_schema=self._contract_identity_schema(data))

    def _contract_identity_schema(self, data=None):
        """Build step-one fields and preserve values while editing a contract."""
        data = data or {}
        fields = {
            vol.Required("provider", default=str(data.get("provider", ""))): str,
            vol.Required("name", default=str(data.get("name", ""))): str,
            vol.Required("contract_number", default=data.get("contract_number", "")): str,
        }
        for key in ("contract_start", "contract_change_date", "billing_period_start"):
            stored = data.get(key) or (data.get("billing_start") if key == "billing_period_start" else None)
            default = _date_default(stored)
            marker = vol.Optional(key, default=default) if default else vol.Optional(key)
            fields[marker] = selector.DateSelector(selector.DateSelectorConfig())
        # The billing-period duration belongs immediately below its start date.
        fields[vol.Required("billing_period_months", default=data.get("billing_period_months", 12))] = _num(1, 1200, 1)
        stored_end = data.get("contract_end")
        end_default = _date_default(stored_end)
        end_marker = vol.Optional("contract_end", default=end_default) if end_default else vol.Optional("contract_end")
        fields[end_marker] = selector.DateSelector(selector.DateSelectorConfig())
        return vol.Schema(fields)

    async def async_step_contract_wizard_prices(self, user_input=None):
        """Wizard step 2: billing areas and all prices; saving finishes the wizard."""
        data = getattr(self, "_contract_edit_data", {})
        if user_input is not None:
            merged = {**data, **user_input}
            try:
                primary = merged.get("primary_billing_type", "consumption")
                vat = Decimal(str(merged.get("vat_rate", 19) or 0))
                factor = Decimal(1) + vat / Decimal(100)
                secondary = merged.get("secondary_billing_type", "")
                has_consumption = primary == "consumption" or secondary == "consumption"
                has_feed_in = primary == "feed_in" or secondary == "feed_in"
                # Form values are always interpreted in the unit indicated by
                # their VAT checkbox. Persisted values remain net; defaults are
                # converted back to the selected input representation below.
                if has_consumption:
                    for source, target, includes in (("base_price_input", "base_price_net", "base_price_includes_vat"), ("purchase_price_input", "purchase_price_net", "purchase_price_includes_vat"), ("monthly_advance_input", "monthly_advance", "monthly_advance_includes_vat")):
                        raw = Decimal(str(_parse_tariff_input(merged.get(source, 0))))
                        net_value = raw / factor if merged.get(includes) else raw
                        merged[target] = str(net_value.quantize(Decimal("0.000000000001"), rounding=ROUND_HALF_UP))
                else:
                    # A feed-in-only contract has its own monthly payout advance.
                    # Persist it separately from the consumption advance so a
                    # shared meter can never mix the two billing directions.
                    raw_advance = Decimal(str(_parse_tariff_input(merged.get("monthly_advance_input", merged.get("feed_in_monthly_advance", merged.get("monthly_advance", 0))))))
                    net_advance = raw_advance / factor if merged.get("monthly_advance_includes_vat") else raw_advance
                    merged["feed_in_monthly_advance"] = str(net_advance.quantize(Decimal("0.000000000001"), rounding=ROUND_HALF_UP))
                    merged.pop("monthly_advance", None)
                    merged["base_price_net"] = 0.0
                    merged.pop("purchase_price_net", None)
                if has_feed_in:
                    raw = Decimal(str(_parse_tariff_input(merged.get("feed_in_price_input", merged.get("feed_in_price_net", 0)))))
                    includes = merged.get("feed_in_price_includes_vat", True)
                    net_feed_in = raw / factor if includes else raw
                    merged["feed_in_price_net"] = str(net_feed_in.quantize(Decimal("0.000000000001"), rounding=ROUND_HALF_UP))
                else:
                    merged.pop("feed_in_price_net", None)
                if "secondary_billing_type" in merged and merged["secondary_billing_type"] == primary:
                    raise ValueError("duplicate_billing_type")
            except (InvalidOperation, ValueError, TypeError, ArithmeticError):
                _LOGGER.warning("VerbrauchsMonitor: Ungültiger Preis im Vertragsassistenten (contract_id=%s)", getattr(self, "_contract_edit_id", "new"))
                return self.async_show_form(step_id="contract_wizard_prices", data_schema=self._contract_prices_schema(merged, preserve_inputs=True), errors={"base": "invalid_tariff"})
            secondary = merged.get("secondary_billing_type", "")
            if not secondary:
                merged.pop("secondary_billing_type", None)
            # Input fields are transient UI values. Persist only canonical net
            # amounts so reopening the form always derives the display value
            # from the authoritative stored amount and VAT flag.
            for transient in ("base_price_input", "purchase_price_input", "monthly_advance_input", "feed_in_price_input"):
                merged.pop(transient, None)
            contract_id = getattr(self, "_contract_edit_id", str(uuid.uuid4()))
            merged["id"] = contract_id
            contracts = list(self.config_entry.options.get("contracts", []))
            contracts = [item for item in contracts if item.get("id") != contract_id] + [merged]
            try:
                return await self._save(contracts=contracts)
            except Exception:  # noqa: BLE001 - do not discard entered values on a save failure
                _LOGGER.exception("VerbrauchsMonitor: Fehler beim Speichern des Vertrags (contract_id=%s)", contract_id)
                return self.async_show_form(step_id="contract_wizard_prices", data_schema=self._contract_prices_schema(merged), errors={"base": "contract_flow_internal_error"})
        return self.async_show_form(step_id="contract_wizard_prices", data_schema=self._contract_prices_schema(data))

    def _contract_prices_schema(self, data=None, preserve_inputs=False):
        """Build step two; persisted net values are re-presented in the selected unit."""
        data = data or {}
        def input_value(key, net_key, includes_key, default_includes):
            """Normalize the submitted value for the matching configuration field."""
            if preserve_inputs and key in data:
                return data[key]
            net = Decimal(str(data.get(net_key, 0) or 0))
            includes = data.get(includes_key, default_includes)
            gross_or_net = net * (factor if includes else Decimal(1))
            return gross_or_net.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
        primary = data.get("primary_billing_type", "consumption")
        schema_vat = Decimal(str(data.get("vat_rate", 19) or 0))
        factor = Decimal(1) + schema_vat / Decimal(100)
        fields = {
            vol.Required("primary_billing_type", default=primary): selector.SelectSelector(selector.SelectSelectorConfig(options=[{"value":"consumption","label":self._labels("Verbrauch","Consumption")},{"value":"feed_in","label":self._labels("Einspeisung","Feed-in")}], mode=selector.SelectSelectorMode.DROPDOWN, custom_value=False)),
            vol.Required("vat_rate", default=data.get("vat_rate", 19)): _num(0, 100, 0.1),
        }
        has_consumption = primary == "consumption" or data.get("secondary_billing_type") == "consumption"
        has_feed_in = primary == "feed_in" or data.get("secondary_billing_type") == "feed_in"
        if has_consumption:
            fields.update({
                vol.Required("base_price_input", default=format_tariff_de(input_value("base_price_input", "base_price_net", "base_price_includes_vat", False))): str,
                vol.Required("base_price_includes_vat", default=data.get("base_price_includes_vat", False)): bool,
                vol.Required("purchase_price_input", default=format_tariff_de(input_value("purchase_price_input", "purchase_price_net", "purchase_price_includes_vat", False))): str,
                vol.Required("purchase_price_includes_vat", default=data.get("purchase_price_includes_vat", False)): bool,
                vol.Required("monthly_advance_input", default=format_tariff_de(input_value("monthly_advance_input", "monthly_advance", "monthly_advance_includes_vat", True))): str,
                vol.Required("monthly_advance_includes_vat", default=data.get("monthly_advance_includes_vat", True)): bool,
            })
        if has_feed_in:
            fields.update({
                vol.Required("feed_in_price_input", default=format_feed_in_tariff_de(input_value("feed_in_price_input", "feed_in_price_net", "feed_in_price_includes_vat", True))): str,
                vol.Required("feed_in_price_includes_vat", default=data.get("feed_in_price_includes_vat", True)): bool,
                vol.Required("monthly_advance_input", default=format_tariff_de(
                    input_value(
                        "monthly_advance_input",
                        "monthly_advance" if has_consumption else "feed_in_monthly_advance",
                        "monthly_advance_includes_vat",
                        True,
                    ) if has_consumption else input_value(
                        "monthly_advance_input",
                        "feed_in_monthly_advance" if "feed_in_monthly_advance" in data else "monthly_advance",
                        "monthly_advance_includes_vat",
                        True,
                    )
                )): str,
                vol.Required("monthly_advance_includes_vat", default=data.get("monthly_advance_includes_vat", True)): bool,
            })
        return vol.Schema(fields)

    async def async_step_meters(self, user_input=None):
        """Create, edit or delete a meter from one action screen.

        The meter selector is only added to this same form for edit/delete.
        New meter creation never shows a selector and goes directly to the
        meter editor. The former separate meter_select step is no longer used.
        """
        meters = list(self.config_entry.options.get("meters", []))
        contracts = list(self.config_entry.options.get("contracts", []))

        if not contracts and not meters and user_input is None:
            return await self.async_step_contracts()

        if user_input is None:
            return self.async_show_form(
                step_id="meters",
                data_schema=self._meter_select_schema(meters, action="new"),
            )

        action = user_input.get("action", "new")

        if action == "new":
            self._meter_edit_id = str(uuid.uuid4())
            self._meter_edit_data = {}
            return await self.async_step_meter_edit()

        if not meters:
            return self.async_show_form(
                step_id="meters",
                data_schema=self._meter_select_schema(meters, action=action),
                errors={"base": "no_meters"},
            )

        selected = user_input.get("selected")
        if not selected:
            # Re-render the SAME step with the meter dropdown directly below
            # the action selector. This is not a second selection dialog.
            return self.async_show_form(
                step_id="meters",
                data_schema=self._meter_select_schema(meters, action=action),
            )

        old = next((meter for meter in meters if meter.get("id") == selected), None)
        if old is None:
            return self.async_show_form(
                step_id="meters",
                data_schema=self._meter_select_schema(meters, action=action),
                errors={"base": "select_meter"},
            )

        if action == "delete":
            updated = [meter for meter in meters if meter.get("id") != selected]
            return await self._save(meters=updated)

        self._meter_edit_id = selected
        self._meter_edit_data = dict(old)
        return await self.async_step_meter_edit()

    def _meter_select_schema(self, meters, action="new"):
        """Build the selector schema for choosing an existing logical meter."""
        actions = [
            {"value": "new", "label": self._labels("Neuen Zähler anlegen", "Create meter")},
            {"value": "edit", "label": self._labels("Zähler bearbeiten", "Edit meter")},
            {"value": "delete", "label": self._labels("Zähler löschen", "Delete meter")},
        ]
        fields = {
            vol.Required("action", default=action): selector.SelectSelector(
                selector.SelectSelectorConfig(options=actions, mode=selector.SelectSelectorMode.DROPDOWN)
            ),
        }
        if action in ("edit", "delete") and meters:
            options = [
                {"value": meter["id"], "label": meter.get("name", self._labels("Zähler", "Meter"))}
                for meter in meters
            ]
            fields[vol.Required("selected", default=options[0]["value"])] = _select(options)
        return vol.Schema(fields)

    async def async_step_meter_edit(self, user_input=None):
        """Create or edit one meter with translated, entity-based selectors."""
        meters = list(self.config_entry.options.get("meters", []))
        contracts = list(self.config_entry.options.get("contracts", []))
        old = getattr(self, "_meter_edit_data", {})
        meter_id = getattr(self, "_meter_edit_id", str(uuid.uuid4()))
        if user_input is not None:
            name = str(user_input.get("name", "")).strip()
            number = str(user_input.get("meter_number", "")).strip()
            consumption_entity = user_input.get("consumption_entity")
            contract_id = user_input.get("contract_id")
            errors = {}
            if not name:
                errors["name"] = "required"
            if not number:
                errors["meter_number"] = "required"
            if not consumption_entity:
                errors["consumption_entity"] = "required"
            if contracts and not contract_id:
                errors["contract_id"] = "required"
            if contract_id and not any(c.get("id") == contract_id for c in contracts):
                errors["contract_id"] = "invalid_contract"
            normalized_readings = {}
            for field in ("previous_consumption_reading", "previous_feed_in_reading"):
                # Feed-in baseline is only relevant when a feed-in counter exists.
                if field == "previous_feed_in_reading" and not (user_input.get("feed_in_entity", old.get("feed_in_entity"))):
                    continue
                try:
                    normalized_readings[field] = _parse_localized_meter_reading(user_input.get(field, old.get(field, 0)))
                except (InvalidOperation, ValueError, TypeError):
                    errors[field] = "invalid_reading"
            if errors:
                return self.async_show_form(step_id="meter_edit", data_schema=self._meter_edit_schema(contracts, user_input), errors=errors)
            item = {**old, **user_input, **normalized_readings, "id": meter_id, "name": name, "meter_number": number}
            # Manual baseline input is marked separately; routine-origin values become corrections.
            from homeassistant.util import dt as dt_util
            for direction, reading_key in (("consumption", "previous_consumption_reading"), ("feed_in", "previous_feed_in_reading")):
                if reading_key not in normalized_readings:
                    continue
                source_key = f"{direction}_baseline_source"
                date_key = f"{direction}_baseline_updated_at"
                history_key = f"{direction}_baseline_history"
                old_source = old.get(source_key, "manual")
                history = list(old.get(history_key, []))
                changed = str(old.get(reading_key, "0")) != str(normalized_readings[reading_key])
                if changed:
                    history.append({"value": str(old.get(reading_key, "0")), "source": old_source, "date": old.get(date_key)})
                    item[source_key] = "corrected" if old_source == "routine" else "manual"
                    item[date_key] = dt_util.now().date().isoformat()
                elif source_key not in old:
                    item[source_key] = "manual"
                item[history_key] = history
            # Optional selectors are authoritative when explicitly cleared;
            # no separate "use ..." switches are needed.
            item = _apply_optional_entities(item, old, user_input)
            item = {
                key: value
                for key, value in item.items()
                if value not in (None, "")
                or key in ("previous_consumption_reading", "previous_feed_in_reading")
            }
            meters = [meter for meter in meters if meter.get("id") != meter_id] + [item]
            return await self._save(meters=meters)
        return self.async_show_form(step_id="meter_edit", data_schema=self._meter_edit_schema(contracts, old))

    def _meter_edit_schema(self, contracts, data=None):
        """Build the input schema for creating or editing a logical meter."""
        data = data or {}
        contract_options = [{"value": c["id"], "label": c.get("name", "Vertrag")} for c in contracts]
        fields = {
            vol.Required("name", default=data.get("name", "")): str,
            vol.Required("meter_number", default=data.get("meter_number", "")): str,
            vol.Required("contract_id", default=data.get("contract_id")): _select(contract_options),
            vol.Required("consumption_entity", default=data.get("consumption_entity")): _entity(),
            vol.Required("previous_consumption_reading", default=str(data.get("previous_consumption_reading", 0)).replace(".", ",")): selector.TextSelector(selector.TextSelectorConfig()),
        }
        # Do not pass None as an EntitySelector default. Optional selectors are
        # only included with a default when a real entity is currently stored.
        for key in ("consumption_power_entity", "feed_in_entity", "feed_in_power_entity"):
            if data.get(key):
                fields[vol.Optional(key, default=data[key])] = _entity()
            else:
                fields[vol.Optional(key)] = _entity()
        if data.get("feed_in_entity"):
            fields[vol.Optional("previous_feed_in_reading", default=str(data.get("previous_feed_in_reading", 0)).replace(".", ","))] = selector.TextSelector(selector.TextSelectorConfig())
        else:
            fields[vol.Optional("previous_feed_in_reading", default="0")] = selector.TextSelector(selector.TextSelectorConfig())
        return vol.Schema(fields)

    def _current_season(self):
        """Return the global astronomical season at the configured HA location."""
        from homeassistant.util import dt as dt_util
        from .seasons import current_ha_season
        return current_ha_season(self.hass, dt_util.now())

    async def async_step_forecast(self, user_input=None):
        """Configure enabled forecasts; season selection is fully automatic."""
        meters = [dict(m) for m in self.config_entry.options.get("meters", [])]
        if not meters:
            return self.async_abort(reason="no_meters")
        options = []
        defaults = []
        for meter in meters:
            mid = str(meter.get("id"))
            consumption = f"{mid}|consumption"
            options.append({"value": consumption, "label": f"{meter.get('name', 'Stromzähler')} {self._labels('– Verbrauch', '– Consumption')}"})
            if meter.get("forecast_consumption_enabled", True):
                defaults.append(consumption)
            if meter.get("feed_in_entity"):
                feed_in = f"{mid}|feed_in"
                options.append({"value": feed_in, "label": f"{meter.get('name', 'Stromzähler')} {self._labels('– Einspeisung', '– Feed-in')}"})
                if meter.get("forecast_feed_in_enabled", False):
                    defaults.append(feed_in)
        if user_input is not None:
            enabled = set(user_input.get("enabled_forecasts", []))
            for meter in meters:
                mid = str(meter.get("id"))
                meter["forecast_consumption_enabled"] = f"{mid}|consumption" in enabled
                meter["forecast_feed_in_enabled"] = bool(meter.get("feed_in_entity") and f"{mid}|feed_in" in enabled)
            options_update = dict(self.config_entry.options)
            options_update["meters"] = meters
            return self.async_create_entry(title="", data=options_update)
        fields = {
            vol.Optional("enabled_forecasts", default=defaults): selector.SelectSelector(
                selector.SelectSelectorConfig(options=options, mode=selector.SelectSelectorMode.LIST, multiple=True)
            )
        }
        season = self._current_season()
        season_labels = {"spring": ("Frühling", "Spring"), "summer": ("Sommer", "Summer"),
                         "autumn": ("Herbst", "Autumn"), "winter": ("Winter", "Winter")}
        de, en = season_labels[season]
        return self.async_show_form(step_id="forecast", data_schema=vol.Schema(fields), description_placeholders={
            "current_season": self._labels(de, en)
        })

    async def async_step_billing(self, user_input=None):
        """Offer billing records and per-meter monthly advance management."""
        return self.async_show_menu(step_id="billing", menu_options=["billing_bookings", "advance_meter"])

    async def async_step_advance_meter(self, user_input=None):
        """Select the logical meter whose monthly advances are to be edited."""
        meters = list(self.config_entry.options.get("meters", []))
        if not meters:
            return self.async_abort(reason="no_meters")
        if user_input is not None:
            self._advance_meter_id = user_input["meter_id"]
            meter = next(m for m in meters if str(m.get("id")) == self._advance_meter_id)
            directions = [{"value": "consumption", "label": self._labels("Verbrauch", "Consumption")}]
            if meter.get("feed_in_entity"):
                directions.append({"value": "feed_in", "label": self._labels("Einspeisung", "Feed-in")})
            if len(directions) == 1:
                self._advance_direction = directions[0]["value"]
                return await self.async_step_advance_months()
            return self.async_show_form(step_id="advance_direction", data_schema=vol.Schema({vol.Required("direction"): _select(directions)}))
        return self.async_show_form(step_id="advance_meter", data_schema=vol.Schema({
            vol.Required("meter_id"): _select([{"value": str(m.get("id")), "label": m.get("name", self._labels("Stromzähler", "Electricity meter"))} for m in meters])
        }))

    async def async_step_advance_direction(self, user_input=None):
        """Select consumption or feed-in for monthly advance editing."""
        if user_input is not None:
            self._advance_direction = user_input["direction"]
            return await self.async_step_advance_months()
        meter = next(m for m in self.config_entry.options.get("meters", []) if str(m.get("id")) == self._advance_meter_id)
        options = [{"value": "consumption", "label": self._labels("Verbrauch", "Consumption")}]
        if meter.get("feed_in_entity"):
            options.append({"value": "feed_in", "label": self._labels("Einspeisung", "Feed-in")})
        return self.async_show_form(step_id="advance_direction", data_schema=vol.Schema({vol.Required("direction"): _select(options)}))

    async def async_step_advance_months(self, user_input=None):
        """Show and save monthly advance values for the selected meter and direction."""
        from datetime import date
        from .database import load_data, get_monthly_advance, record_monthly_advance
        meter = next(m for m in self.config_entry.options.get("meters", []) if str(m.get("id")) == self._advance_meter_id)
        contract = next(c for c in self.config_entry.options.get("contracts", []) if c.get("id") == meter.get("contract_id"))
        start_text = contract.get("billing_period_start") or contract.get("billing_start") or contract.get("contract_start")
        if not start_text:
            return self.async_abort(reason="missing_billing_start")
        start = date.fromisoformat(str(start_text)[:10])
        from homeassistant.util import dt as dt_util
        today = dt_util.now().date()
        duration = max(1, int(contract.get("billing_period_months", 12) or 12))
        months = []
        cursor = date(start.year, start.month, 1)
        for _ in range(duration):
            if cursor > date(today.year, today.month, 1):
                break
            months.append(cursor.strftime("%Y-%m"))
            cursor = date(cursor.year + (cursor.month == 12), 1 if cursor.month == 12 else cursor.month + 1, 1)
        if not months:
            return self.async_abort(reason="no_current_billing_month")
        ledger = await self.hass.async_add_executor_job(load_data, self.hass)
        if user_input is not None:
            try:
                for month in months:
                    field_label = _month_field_label(month, self.hass)
                    amount = _parse_localized_amount(user_input[field_label])
                    if amount < 0:
                        raise InvalidOperation
                    await self.hass.async_add_executor_job(partial(record_monthly_advance, self.hass,
                        meter_id=self._advance_meter_id, direction=self._advance_direction,
                        contract_id=str(meter.get("contract_id")), month=month, amount=amount))
            except (InvalidOperation, ValueError, TypeError, KeyError):
                return self.async_show_form(step_id="advance_months", data_schema=self._advance_month_schema(months, ledger), errors={"base": "invalid_advance_amount"})
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return await self.async_step_billing()
        return self.async_show_form(step_id="advance_months", data_schema=self._advance_month_schema(months, ledger))

    def _advance_month_schema(self, months, ledger):
        """Build the localized form schema for monthly advance values."""
        from .database import get_monthly_advance
        meter = next(m for m in self.config_entry.options.get("meters", []) if str(m.get("id")) == self._advance_meter_id)
        contract = next(c for c in self.config_entry.options.get("contracts", []) if c.get("id") == meter.get("contract_id"))
        if self._advance_direction == "consumption":
            from .pricing import gross_from_net
            default = gross_from_net(contract.get("monthly_advance", 0), contract.get("vat_rate", 19))
        else:
            default = meter.get("feed_in_monthly_advance", 0)
        fields = {}
        for month in months:
            value = get_monthly_advance(ledger, meter_id=self._advance_meter_id, direction=self._advance_direction, month=month, default=default)
            fields[vol.Required(_month_field_label(month, self.hass), default=format_amount_de(value))] = selector.TextSelector(selector.TextSelectorConfig())
        return vol.Schema(fields)

    async def async_step_billing_bookings(self, user_input=None):
        """Show booking management for the selected billing scope."""
        from .database import load_data
        ledger = await self.hass.async_add_executor_job(load_data, self.hass)
        bookings = list(ledger.get("bookings", []))
        if user_input is not None:
            action = user_input.get("action", "new")
            selected = user_input.get("selected") or ""
            if action == "delete":
                if not selected:
                    return self.async_show_form(step_id="billing_bookings", data_schema=self._booking_schema(bookings), errors={"base": "select_booking"})
                ledger["bookings"] = [b for b in bookings if b.get("id") != selected]
                from .database import save_data
                await self.hass.async_add_executor_job(save_data, self.hass, ledger)
                await self.hass.config_entries.async_reload(self.config_entry.entry_id)
                return await self.async_step_billing_bookings()
            if action == "edit" and not selected:
                return self.async_show_form(step_id="billing_bookings", data_schema=self._booking_schema(bookings), errors={"base": "select_booking"})
            if action in ("edit", "new"):
                old = next((item for item in bookings if item.get("id") == selected), {}) if action == "edit" else {}
                self._booking_edit_id = old.get("id", str(uuid.uuid4()))
                self._booking_edit_data = dict(old)
                return await self.async_step_booking_edit()
        return self.async_show_form(step_id="billing_bookings", data_schema=self._booking_schema(bookings))

    def _booking_schema(self, bookings):
        """Build the form schema for adding a new payment or adjustment booking."""
        actions = [
            {"value": "new", "label": self._labels("Neue Buchung anlegen", "Create booking")},
            {"value": "edit", "label": self._labels("Buchung bearbeiten", "Edit booking")},
            {"value": "delete", "label": self._labels("Buchung löschen", "Delete booking")},
        ]
        fields = {vol.Required("action", default="new"): selector.SelectSelector(selector.SelectSelectorConfig(options=actions, mode=selector.SelectSelectorMode.DROPDOWN))}
        if bookings:
            fields[vol.Optional("selected")] = _select([{"value": b["id"], "label": f"{(str(b.get('date',''))[8:10] + '.' + str(b.get('date',''))[5:7] + '.' + str(b.get('date',''))[:4]) if len(str(b.get('date',''))) >= 10 else b.get('date','')} – {format_amount_de(b.get('amount', 0))} € – {self._labels('Zugeordnet' if b.get('status') == 'assigned' else 'Ungeklärt', 'Assigned' if b.get('status') == 'assigned' else 'Unresolved')} – {b.get('comment') or b.get('description','')}"} for b in bookings])
        return vol.Schema(fields)

    async def async_step_booking_edit(self, user_input=None):
        """Select and process an existing booking for editing or deletion."""
        data = getattr(self, "_booking_edit_data", {})
        if user_input is not None:
            try:
                amount = _parse_localized_amount(user_input.get("amount", "0"))
                booking_type = user_input.get("booking_type", "payment")
                from .ledger import validate_booking_amount
                amount = validate_booking_amount(booking_type=booking_type, amount=amount)
            except (InvalidOperation, ValueError, TypeError):
                return self.async_show_form(step_id="booking_edit", data_schema=self._booking_edit_schema(data), errors={"base": "invalid_amount"})
            meter = next((m for m in self.config_entry.options.get("meters", []) if m.get("id") == user_input.get("meter_id")), None)
            contract = next((c for c in self.config_entry.options.get("contracts", []) if c.get("id") == user_input.get("contract_id")), None)
            if meter is None or contract is None or meter.get("contract_id") != contract.get("id"):
                return self.async_show_form(step_id="booking_edit", data_schema=self._booking_edit_schema(data), errors={"base": "invalid_assignment"})
            if user_input.get("direction") == "feed_in" and not meter.get("feed_in_entity"):
                return self.async_show_form(step_id="booking_edit", data_schema=self._booking_edit_schema(data), errors={"base": "invalid_assignment"})
            item = {**data, **user_input, "amount": amount, "id": self._booking_edit_id,
                    "description": user_input.get("comment", ""), "status": "assigned", "source": "manual"}
            from .database import add_booking
            try:
                await self.hass.async_add_executor_job(add_booking, self.hass, item)
            except Exception:
                _LOGGER.exception(
                    "VerbrauchsMonitor: Manuelle Buchung konnte nicht dauerhaft gespeichert werden "
                    "(booking_id=%s, meter_id=%s, direction=%s)",
                    self._booking_edit_id,
                    item.get("meter_id"),
                    item.get("direction"),
                )
                return self.async_show_form(
                    step_id="booking_edit",
                    data_schema=self._booking_edit_schema(data),
                    errors={"base": "save_failed"},
                )
            # Sensor attributes are loaded from the durable ledger at setup.
            # Reload immediately so the dashboard reflects the saved booking.
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return await self.async_step_billing_bookings()
        return self.async_show_form(step_id="booking_edit", data_schema=self._booking_edit_schema(data))

    def _booking_edit_schema(self, data=None):
        """Build the form schema for editing an existing booking."""
        data = data or {}
        meters = list(self.config_entry.options.get("meters", []))
        meter_options = [{"value": m.get("id"), "label": f"{m.get('name','Zähler')} ({m.get('meter_number','')})"} for m in meters]
        contracts = list(self.config_entry.options.get("contracts", []))
        contract_options = [{"value": c.get("id"), "label": f"{c.get('name','Vertrag')} ({c.get('contract_number','')})"} for c in contracts]
        return vol.Schema({
            vol.Required("meter_id", default=data.get("meter_id") or (meter_options[0]["value"] if meter_options else "")): _select(meter_options),
            vol.Required("direction", default=data.get("direction", "consumption")): selector.SelectSelector(selector.SelectSelectorConfig(options=[{"value":"consumption","label":self._labels("Verbrauch","Consumption")},{"value":"feed_in","label":self._labels("Einspeisung","Feed-in")}], mode=selector.SelectSelectorMode.DROPDOWN)),
            vol.Required("contract_id", default=data.get("contract_id") or (contract_options[0]["value"] if contract_options else "")): _select(contract_options),
            vol.Required("date", default=data.get("date") or ""): selector.DateSelector(),
            vol.Required("amount", default=str(data.get("amount", 0)).replace(".", ",")): selector.TextSelector(selector.TextSelectorConfig()),
            vol.Optional("comment", default=data.get("comment", data.get("description", ""))): str,
            vol.Required("booking_type", default=data.get("booking_type", "payment")): selector.SelectSelector(selector.SelectSelectorConfig(options=[
                                {"value": "advance", "label": self._labels("Abschlagszahlung", "Regular advance payment")},
                                {"value": "payment", "label": self._labels("Sonderzahlung", "Additional payment")},
                {"value": "credit", "label": self._labels("Gutschrift", "Credit")},
                {"value": "extra_charge", "label": self._labels("Zusatzkosten", "Extra charge")},
                {"value": "correction", "label": self._labels("Korrektur", "Correction")},
                            ], mode=selector.SelectSelectorMode.DROPDOWN)),
        })

    async def async_step_database(self, user_input=None):
        """Show database information and offer explicit database actions."""
        from .database import status
        details = await self.hass.async_add_executor_job(status, self.hass)
        if details.get("status") == "ok":
            modified = details.get("last_modified")
            if modified:
                from homeassistant.util import dt as dt_util
                parsed_modified = dt_util.parse_datetime(str(modified))
                local_modified = dt_util.as_local(parsed_modified) if parsed_modified else None
                modified = local_modified.strftime("%d.%m.%Y, %H:%M:%S Uhr") if local_modified else str(modified)
            else:
                modified = "Noch keine Datenbankdatei vorhanden"
            info = (
                f"Status: OK\nDateigröße: {details.get('size_bytes', 0)} Byte\n"
                f"Schema-Version: {details.get('schema_version')}\n"
                f"Verträge: {details.get('contracts', 0)}\n"
                f"Zähler: {details.get('meters', 0)}\n"
                f"Buchungen: {details.get('bookings', 0)}\n"
                f"Letzte Änderung: {modified}"
            )
        else:
            info = f"Datenbankfehler: {details.get('message', 'Unbekannter Fehler')}"
        return self.async_show_menu(
            step_id="database",
            menu_options=["database_optimize", "database_reset"],
            description_placeholders={"database_info": info, "feedback": getattr(self, "_database_feedback", "")},
        )

    async def async_step_database_optimize(self, user_input=None):
        """Run the requested local database optimization action."""
        if user_input is not None:
            try:
                await self.hass.services.async_call(DOMAIN, "database_optimize", {}, blocking=True)
                self._database_feedback = "Datenbank erfolgreich optimiert."
            except Exception:  # noqa: BLE001
                _LOGGER.exception("VerbrauchsMonitor: Datenbankoptimierung fehlgeschlagen")
                self._database_feedback = "Datenbankoptimierung fehlgeschlagen. Details stehen im Home-Assistant-Protokoll."
            return await self.async_step_database()
        return self.async_show_form(step_id="database_optimize", data_schema=vol.Schema({}))

    async def async_step_database_reset(self, user_input=None):
        """Present the available database reset scopes and their consequences."""
        self._reset_scopes = ["database"]
        return await self.async_step_database_reset_confirm()

    async def async_step_database_reset_confirm(self, user_input=None):
        """Require explicit confirmation before executing a destructive reset."""
        if user_input is not None:
            if not user_input.get("confirm"):
                return self.async_show_form(step_id="database_reset_confirm", data_schema=self._reset_confirm_schema(), errors={"base": "reset_confirmation_required"})
            from .database import reset_database
            try:
                await self.hass.async_add_executor_job(reset_database, self.hass)
                self._database_feedback = "Datenbank wurde zurückgesetzt. Eine Sicherung wurde erstellt."
            except Exception:  # noqa: BLE001
                _LOGGER.exception("VerbrauchsMonitor: Datenbankreset fehlgeschlagen")
                self._database_feedback = "Datenbankreset fehlgeschlagen. Details stehen im Home-Assistant-Protokoll."
            return await self.async_step_database()
        return self.async_show_form(step_id="database_reset_confirm", data_schema=self._reset_confirm_schema())

    async def async_step_data_management(self, user_input=None):
        """Select reset scopes. The destructive operation is always confirmed separately."""
        if user_input is not None:
            selected = [key for key in ("contracts", "meters", "billing", "forecasts", "database") if user_input.get(key)]
            if not selected:
                return self.async_show_form(step_id="data_management", data_schema=self._reset_schema(), errors={"base": "reset_select_at_least_one"})
            if "contracts" in selected and "meters" not in selected:
                return self.async_show_form(step_id="data_management", data_schema=self._reset_schema(), errors={"base": "reset_contracts_require_meters"})
            if selected == ["database"]:
                return await self.async_step_database()
            self._reset_scopes = selected
            if "forecasts" in selected:
                return await self.async_step_forecast_reset_select()
            return await self.async_step_data_management_confirm()
        return self.async_show_form(step_id="data_management", data_schema=self._reset_schema())

    def _reset_schema(self):
        """Build the reset-scope selection schema."""
        return vol.Schema({
            vol.Optional("contracts", default=False): bool,
            vol.Optional("meters", default=False): bool,
            vol.Optional("billing", default=False): bool,
            vol.Optional("forecasts", default=False): bool,
            vol.Optional("database", default=False): bool,
        })

    async def async_step_forecast_reset_select(self, user_input=None):
        """Select exact meter/direction forecasts before the destructive confirmation."""
        meters = list(self.config_entry.options.get("meters", []))
        choices = []
        for meter in meters:
            mid = str(meter.get("id"))
            # Reset selection covers every configured reading, regardless of
            # whether its forecast is currently enabled.
            if meter.get("consumption_entity") or "previous_consumption_reading" in meter:
                choices.append({"value": f"{mid}|consumption", "label": f"{meter.get('name', 'Stromzähler')} – {self._labels('Verbrauch', 'Consumption')}"})
            if meter.get("feed_in_entity") or "previous_feed_in_reading" in meter:
                choices.append({"value": f"{mid}|feed_in", "label": f"{meter.get('name', 'Stromzähler')} – {self._labels('Einspeisung', 'Feed-in')}"})
        if user_input is not None:
            selected_forecasts = list(user_input.get("selected_forecasts", []))
            if not selected_forecasts:
                return self.async_show_form(step_id="forecast_reset_select", data_schema=self._forecast_reset_schema(choices), errors={"base": "reset_select_at_least_one"})
            self._selected_forecasts_for_reset = selected_forecasts
            return await self.async_step_data_management_confirm()
        if not choices:
            self._selected_forecasts_for_reset = []
            return await self.async_step_data_management_confirm()
        return self.async_show_form(step_id="forecast_reset_select", data_schema=self._forecast_reset_schema(choices))

    def _forecast_reset_schema(self, choices):
        """Build the selection schema for resetting forecast state."""
        return vol.Schema({vol.Required("selected_forecasts"): selector.SelectSelector(
            selector.SelectSelectorConfig(options=choices, mode=selector.SelectSelectorMode.LIST, multiple=True)
        )})

    async def async_step_data_management_confirm(self, user_input=None):
        """Confirm and execute the selected data-management operation."""
        scopes = list(getattr(self, "_reset_scopes", []))
        if user_input is not None:
            if not user_input.get("confirm"):
                return self.async_show_form(step_id="data_management_confirm", data_schema=self._reset_confirm_schema(), errors={"base": "reset_confirmation_required"})
            options = dict(self.config_entry.options)
            if "contracts" in scopes: options["contracts"] = []
            if "meters" in scopes: options["meters"] = []
            if "billing" in scopes: options["bookings"] = []
            if "forecasts" in scopes:
                # Reset only the selected meter/direction forecasts. Global
                # seasonal preferences are removed only when every active
                # forecast was selected; billing and payment data stay intact.
                selected_forecasts = set(getattr(self, "_selected_forecasts_for_reset", []))
                active_forecasts = set()
                for meter in options.get("meters", []):
                    mid = str(meter.get("id"))
                    if meter.get("forecast_consumption_enabled", True):
                        active_forecasts.add(f"{mid}|consumption")
                    if meter.get("feed_in_entity") and meter.get("forecast_feed_in_enabled", False):
                        active_forecasts.add(f"{mid}|feed_in")
                    if f"{mid}|consumption" in selected_forecasts:
                        meter["forecast_consumption_enabled"] = False
                    if f"{mid}|feed_in" in selected_forecasts:
                        meter["forecast_feed_in_enabled"] = False
                if active_forecasts and active_forecasts.issubset(selected_forecasts):
                    options.pop("forecast_season_mode", None)
                    options.pop("forecast_manual_season", None)
            if "database" in scopes:
                from .database import reset_database
                await self.hass.async_add_executor_job(reset_database, self.hass)
            # Persist the complete options payload after the selected scopes have been cleared.
            return self.async_create_entry(title="", data=options)
        return self.async_show_form(
            step_id="data_management_confirm", data_schema=self._reset_confirm_schema(),
            description_placeholders={"scopes": ", ".join(self._labels({"contracts":"Vertrag","meters":"Zähler","billing":"Abrechnungen","forecasts":"Prognosen","database":"Datenbank"}.get(x,x), {"contracts":"Contracts","meters":"Meters","billing":"Billing","forecasts":"Forecasts","database":"Database"}.get(x,x)) for x in scopes)},
        )

    def _reset_confirm_schema(self):
        """Build the explicit confirmation form for a reset operation."""
        return vol.Schema({vol.Required("confirm", default=False): bool})

    async def async_step_about(self, user_input=None):
        """Display informational metadata without changing stored options."""
        if user_input is not None:
            return self.async_show_menu(step_id="init", menu_options=["contracts", "meters", "forecast", "billing", "data_management", "about"])
        return self.async_show_form(
            step_id="about",
            data_schema=vol.Schema({}),
            description_placeholders={"revision": "R111"},
        )
