from datetime import date
from decimal import Decimal
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

ROOT = Path(__file__).parents[1]
INTEGRATION = ROOT / "custom_components" / "verbrauchsmonitor"


def _load_module(name, filename):
    spec = spec_from_file_location(name, INTEGRATION / filename)
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_feed_in_monthly_advance_is_grossed_and_automatically_paid_each_month_first():
    pricing = _load_module("vm_r100_pricing", "pricing.py")
    ledger = _load_module("vm_r100_ledger", "ledger.py")

    # Contract stores the 136.00 EUR payout advance net of 19% VAT because
    # the contract form's VAT checkbox was enabled for the entered gross value.
    net_advance = Decimal("136") / Decimal("1.19")
    gross_advance = Decimal(str(pricing.gross_from_net(net_advance, 19)))
    paid = ledger.calculate_advance_total(
        monthly_advance_gross=gross_advance,
        bookings=[],
        period_start="2026-01-01",
        as_of=date(2026, 11, 23),
        period_end="2026-12-31",
    )
    assert paid.quantize(Decimal("0.01")) == Decimal("1496.00")


def test_feed_in_balance_uses_its_own_monthly_advance_not_consumption_advance():
    source = (INTEGRATION / "sensor.py").read_text(encoding="utf-8")
    assert 'self._data.get("feed_in_monthly_advance", 0)' in source
    assert 'monthly_advance_gross=monthly_advance_gross' in source
    assert 'advances = money_amount(expected_advances)' in source
    assert '"recorded_advances_paid"] = float(advances)' in source


def test_feed_in_mirror_exposes_direction_specific_gross_monthly_advance():
    source = (INTEGRATION / "sensor.py").read_text(encoding="utf-8")
    assert '"feed_in_monthly_advance"\n                    if self._source == entry.data.get(CONF_FEED_IN_ENTITY)' in source
    assert '"monthly_advance_gross": gross_from_net(' in source


def test_legacy_feed_in_only_contract_advance_is_migrated_without_mixing_directions():
    source = (INTEGRATION / "sensor.py").read_text(encoding="utf-8")
    assert 'merged.get("primary_billing_type") == "feed_in"' in source
    assert 'merged.get("secondary_billing_type") != "consumption"' in source
    assert 'merged["feed_in_monthly_advance"] = merged.get("monthly_advance")' in source


def test_feed_in_only_contract_persists_advance_in_separate_canonical_field():
    source = (INTEGRATION / "config_flow.py").read_text(encoding="utf-8")
    assert 'merged["feed_in_monthly_advance"] = str(net_advance.quantize' in source
    assert 'merged.pop("monthly_advance", None)' in source
    assert '"feed_in_monthly_advance" if "feed_in_monthly_advance" in data else "monthly_advance"' in source


def test_frontend_automatic_monthly_advances_apply_to_both_directions():
    source = (INTEGRATION / "frontend" / "verbrauchsmonitor-card.js").read_text(encoding="utf-8")
    assert 'if (sourcePeriodStart && /^\\d{4}-\\d{2}-\\d{2}$/.test(sourcePeriodStart))' in source
    assert 'const monthlyGross = Number(sourceAttributes.monthly_advance_gross ?? 0);' in source


def test_example_feed_in_credit_after_eleven_monthly_payouts_is_338_08_eur():
    ledger = _load_module("vm_r100_ledger_balance", "ledger.py")
    balance = ledger.signed_customer_balance(
        direction="feed_in",
        amount=Decimal("1834.08") - Decimal("1496.00"),
    )
    assert balance == Decimal("338.08")
