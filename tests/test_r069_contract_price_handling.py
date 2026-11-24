import ast
import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
INTEGRATION = ROOT / "custom_components/verbrauchsmonitor"

def _price_parser():
    source = (INTEGRATION / "config_flow.py").read_text()
    tree = ast.parse(source)
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_parse_tariff_input")
    module = ast.Module(body=[node], type_ignores=[])
    namespace = {"InvalidOperation": __import__("decimal").InvalidOperation, "Decimal": __import__("decimal").Decimal}
    exec(compile(module, "config_flow.py", "exec"), namespace)
    return namespace["_parse_tariff_input"]

def test_integer_prices_and_decimal_comma_are_valid_and_precision_is_limited():
    parse = _price_parser()
    assert parse("31") == 31.0
    assert parse("110") == 110.0
    assert parse("31,123456") == 31.123456
    import pytest
    with pytest.raises(Exception):
        parse("31,1234567")

def test_step_two_has_no_visible_secondary_billing_selector():
    source = (INTEGRATION / "config_flow.py").read_text()
    schema = source.split("def _contract_prices_schema", 1)[1].split("async def async_step_meters", 1)[0]
    assert 'vol.Optional("secondary_billing_type"' not in schema
    assert 'vol.Required("primary_billing_type"' in schema

def test_gross_checked_defaults_represent_gross_values_from_stored_net():
    source = (INTEGRATION / "config_flow.py").read_text()
    assert 'data.get("base_price_includes_vat", False)' in source
    assert 'data.get("purchase_price_includes_vat", False)' in source
    assert 'data.get("monthly_advance_includes_vat", True)' in source
    assert 'data.get("feed_in_price_includes_vat", True)' in source

def test_balance_labels_have_colons_and_translations_remain_valid():
    card = (INTEGRATION / "frontend/verbrauchsmonitor-card.js").read_text()
    assert 't("Aktuelles Guthaben","Current credit")' in card
    assert 't("Offener Betrag","Outstanding amount")' in card
    assert 'withColon(label)' in card
    de = json.loads((INTEGRATION / "translations/de.json").read_text())
    en = json.loads((INTEGRATION / "translations/en.json").read_text())
    de_keys = de["options"]["step"]["contract_wizard_prices"]["data"].keys()
    en_keys = en["options"]["step"]["contract_wizard_prices"]["data"].keys()
    assert set(de_keys) == set(en_keys)
