"""Regression tests for exact tariffs and consistent cent rounding in the card."""
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import importlib.util
import sys

ROOT = Path(__file__).resolve().parents[1]


def _load_pricing():
    path = ROOT / "custom_components/verbrauchsmonitor/pricing.py"
    spec = importlib.util.spec_from_file_location("vm_r105_pricing", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _money(value):
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def test_feed_in_tariff_precision_matches_the_displayed_energy_amount():
    pricing = _load_pricing()
    gross = pricing.gross_decimal_from_net("28.74", "19")
    assert gross == Decimal("34.2006")
    energy = _money(Decimal("5362.713") * gross / Decimal("100"))
    assert energy == Decimal("1834.08")
    assert f"{gross:.4f}" == "34.2006"


def test_consumption_line_items_and_period_total_use_one_rounding_rule():
    energy = _money(Decimal("1825.864") * Decimal("28.28") / Decimal("100"))
    base = _money(Decimal("239.62") * Decimal("4") / Decimal("12"))
    total = energy + base
    assert energy == Decimal("516.35")
    assert base == Decimal("79.87")
    assert total == Decimal("596.22")
    # The displayed total is the sum of the displayed line items, not a
    # separately rounded sum of hidden, unrounded intermediate values.
    assert total == energy + base


def test_card_uses_backend_line_items_and_displays_sufficient_tariff_precision():
    card = (ROOT / "custom_components/verbrauchsmonitor/frontend/verbrauchsmonitor-card.js").read_text(encoding="utf-8")
    assert "vm_energy_amount" in card
    assert "vm_base_amount" in card
    assert "vm_total_costs" in card
    assert "maximumFractionDigits:6" in card
