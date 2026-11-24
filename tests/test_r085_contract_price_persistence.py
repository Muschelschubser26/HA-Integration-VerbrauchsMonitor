"""Regression checks for contract tariff persistence and localized entry."""
import ast
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).parents[1]
FLOW = ROOT / "custom_components/verbrauchsmonitor/config_flow.py"


def _extract_function(name):
    tree = ast.parse(FLOW.read_text())
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    namespace = {"Decimal": Decimal, "InvalidOperation": InvalidOperation, "ROUND_HALF_UP": ROUND_HALF_UP}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(FLOW), "exec"), namespace)
    return namespace[name]


def test_german_brutto_price_is_parsed_exactly():
    parse = _extract_function("_parse_tariff_input")
    assert Decimal(str(parse("239,62"))) == Decimal("239.62")
    assert Decimal(str(parse("28,28"))) == Decimal("28.28")


def test_all_consumption_tariff_values_are_persisted_inside_loop():
    source = FLOW.read_text()
    loop = source.split('for source, target, includes in (("base_price_input"', 1)[1].split('\n                else:', 1)[0]
    assert 'merged[target] = str(net_value.quantize' in loop
    assert '"base_price_net"' in source and '"purchase_price_net"' in source


def test_feed_in_fields_are_conditional_and_not_part_of_consumption_contract():
    source = FLOW.read_text()
    schema = source.split("def _contract_prices_schema", 1)[1].split("async def async_step_meters", 1)[0]
    assert 'if has_feed_in:' in schema
    assert 'if has_consumption:' in schema
    assert 'vol.Required("feed_in_price_input"' in schema
    assert 'fields[vol.Optional("feed_in_monthly_advance"' not in source


def test_forecast_reset_includes_configured_readings_even_when_disabled():
    source = FLOW.read_text()
    reset = source.split("async def async_step_forecast_reset_select", 1)[1].split("def _forecast_reset_schema", 1)[0]
    assert 'if meter.get("consumption_entity") or "previous_consumption_reading" in meter:' in reset
    assert 'if meter.get("feed_in_entity") or "previous_feed_in_reading" in meter:' in reset
    assert 'forecast_consumption_enabled' not in reset


def test_billing_period_duration_is_immediately_after_billing_period_start():
    source = FLOW.read_text()
    schema = source.split("def _contract_identity_schema", 1)[1].split("async def async_step_contract_wizard_prices", 1)[0]
    assert schema.index('"billing_period_start"') < schema.index('"billing_period_months"') < schema.index('"contract_end"')


def test_tariff_default_is_displayed_as_exact_cents():
    formatter = _extract_function("format_tariff_de")
    assert formatter(239.620001) == "239,62"
    assert formatter("28.28") == "28,28"


def test_contract_net_conversion_keeps_precision_for_gross_round_trip():
    gross = Decimal("239.62")
    net = (gross / Decimal("1.19")).quantize(Decimal("0.000000000001"))
    restored = (net * Decimal("1.19")).quantize(Decimal("0.01"))
    assert restored == gross
    source = FLOW.read_text()
    assert 'net_value.quantize(Decimal("0.000000000001")' in source
