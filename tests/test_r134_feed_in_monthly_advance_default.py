from decimal import Decimal
import ast
from pathlib import Path

ROOT = Path(__file__).parents[1]
CONFIG_FLOW = ROOT / "custom_components" / "verbrauchsmonitor" / "config_flow.py"


def _load_helper():
    source = CONFIG_FLOW.read_text(encoding="utf-8")
    tree = ast.parse(source)
    node = next(
        item for item in tree.body
        if isinstance(item, ast.FunctionDef) and item.name == "_feed_in_monthly_advance_net"
    )
    namespace = {"Decimal": Decimal, "InvalidOperation": Exception}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(CONFIG_FLOW), "exec"), namespace)
    return namespace["_feed_in_monthly_advance_net"]


def test_feed_in_only_legacy_contract_uses_legacy_monthly_advance():
    helper = _load_helper()
    assert helper({
        "primary_billing_type": "feed_in",
        "monthly_advance": "120.00",
        "vat_rate": 19,
    }) == Decimal("120.00")


def test_canonical_feed_in_advance_takes_precedence():
    helper = _load_helper()
    assert helper({
        "primary_billing_type": "feed_in",
        "monthly_advance": "120.00",
        "feed_in_monthly_advance": "80.00",
    }) == Decimal("80.00")


def test_consumption_advance_is_never_mixed_into_feed_in():
    helper = _load_helper()
    assert helper({
        "primary_billing_type": "consumption",
        "secondary_billing_type": "feed_in",
        "monthly_advance": "200.00",
    }) == Decimal("0")


def test_negative_or_invalid_legacy_amount_is_rejected():
    helper = _load_helper()
    assert helper({
        "primary_billing_type": "feed_in",
        "monthly_advance": "-12.00",
    }) == Decimal("0")
    assert helper({
        "primary_billing_type": "feed_in",
        "monthly_advance": "invalid",
    }) == Decimal("0")


def test_editor_schema_and_migration_use_the_same_contract_default_helper():
    source = CONFIG_FLOW.read_text(encoding="utf-8")
    assert source.count("_feed_in_monthly_advance_net(contract)") >= 2
    assert "_feed_in_monthly_advance_net(contract)" in source
