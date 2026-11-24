"""Regression tests for R099 gross feed-in display and deferred rounding."""
from decimal import Decimal
from pathlib import Path
import importlib.util
import sys

ROOT = Path(__file__).parents[1]
LEDGER = ROOT / "custom_components/verbrauchsmonitor/ledger.py"
SENSOR = ROOT / "custom_components/verbrauchsmonitor/sensor.py"
CARD = ROOT / "custom_components/verbrauchsmonitor/frontend/verbrauchsmonitor-card.js"


def _load_ledger():
    spec = importlib.util.spec_from_file_location("vm_r099_ledger", LEDGER)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_ledger_keeps_unrounded_energy_and_balance_values():
    ledger = _load_ledger()
    result = ledger.calculate_balance(
        consumption_kwh="1821.981", feed_in_kwh="5362.713",
        purchase_price_gross_ct_kwh="33.6532",
        feed_in_price_gross_ct_kwh="0.342006",
        advances="0",
    )
    assert result.feed_in_credit == Decimal("5362.713") * Decimal("0.342006") / 100
    assert result.total == result.consumption_cost - result.feed_in_credit
    assert ledger.signed_customer_balance(direction="feed_in", amount="18.341234") == Decimal("18.341234")


def test_feed_in_balance_sensor_does_not_round_intermediate_amounts():
    source = SENSOR.read_text(encoding="utf-8")
    assert 'energy_amount = money_amount(energy_delta * price / Decimal(100))' in source
    assert 'base_gross = money_amount(base_gross_annual * Decimal(months) / Decimal(12))' in source
    ledger = (ROOT / "custom_components/verbrauchsmonitor/ledger.py").read_text(encoding="utf-8")
    assert 'additional_payments += amount' in ledger
    assert 'credits += abs(amount)' in ledger
    assert 'extra_charges += amount' in ledger
    assert 'return float(final_balance)' in source
    assert 'ROUND_HALF_UP' in source


def test_card_shows_gross_feed_in_tariff_with_two_decimals_and_rounds_only_for_display():
    card = CARD.read_text(encoding="utf-8")
    assert 'const priceF = gross(a.feed_in_price_net_ct_kwh);' in card
    assert 'minimumFractionDigits:2,maximumFractionDigits:2,useGrouping:false' in card
    assert 'const money = v => `${num(v,2)} €`;' in card
    assert 'const costF = deltaF !== null && deltaF >= 0 ? deltaF*priceF/100 : null;' in card
    assert 'const totalCosts = Number.isFinite(backendTotalCosts) ? backendTotalCosts :' in card


def test_screenshot_feed_in_example_is_gross_and_cent_display_is_consistent():
    net_rate = Decimal("0.287400")
    gross_rate = net_rate * Decimal("1.19")
    feed_in = Decimal("5362.713")
    gross_remuneration = feed_in * gross_rate / Decimal(100)
    assert gross_rate == Decimal("0.342006000")
    assert gross_remuneration.quantize(Decimal("0.01"), rounding="ROUND_HALF_UP") == Decimal("18.34")


def test_period_progress_occupies_the_baseline_metadata_spacing_without_extra_gap():
    card = CARD.read_text(encoding="utf-8")
    value = '<div class="row period-row"><span class="period-label">'
    progress = '<span class="baseline-meta period-progress">'
    assert value in card and progress in card
    assert card.index(value) < card.index(progress)
    assert '<div class="period-divider"></div>' not in card
    assert '.period-row{align-items:center;padding:4px 0;border-bottom:1px solid var(--divider-color)}' in card
    assert '.period-label{display:inline-flex;flex-direction:column;align-items:flex-start;gap:0;line-height:18px}' in card
    assert '.period-progress{display:block;margin:0;font-size:9px;line-height:10px}' in card


def test_pricing_backend_converts_net_feed_in_tariff_to_exact_gross_value():
    spec = importlib.util.spec_from_file_location(
        "vm_r099_pricing", ROOT / "custom_components/verbrauchsmonitor/pricing.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    assert module.gross_from_net("0.287400", "19") == 0.342006
