from datetime import date
from decimal import Decimal
from importlib.util import spec_from_file_location, module_from_spec
from pathlib import Path
import sys

ROOT = Path(__file__).parents[1]


def load_ledger():
    path = ROOT / "custom_components/verbrauchsmonitor/ledger.py"
    spec = spec_from_file_location("vm_r057_ledger", path)
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_contractual_monthly_advances_are_counted_for_elapsed_months():
    ledger = load_ledger()
    assert ledger.calculate_advance_total(
        monthly_advance_gross="200", bookings=[], period_start="2026-08-01",
        as_of=date(2026, 11, 1), period_end="2027-07-31",
    ) == Decimal("800.00")


def test_only_recorded_advances_are_counted_as_paid():
    ledger = load_ledger()
    bookings = [
        {"booking_type": "advance", "date": "2026-09-03", "amount": "180"},
        {"booking_type": "payment", "date": "2026-09-04", "amount": "25"},
    ]
    assert ledger.calculate_advance_total(
        monthly_advance_gross="200", bookings=bookings,
        period_start="2026-08-01", as_of=date(2026, 11, 1),
    ) == Decimal("780.00")
    assert ledger.calculate_recorded_advance_total(
        bookings=bookings, period_start="2026-08-01", as_of=date(2026, 11, 1),
    ) == Decimal("180.00")


def test_advance_outside_billing_period_is_ignored():
    ledger = load_ledger()
    bookings = [
        {"booking_type": "advance", "date": "2026-07-03", "amount": "180"},
        {"booking_type": "advance", "date": "2026-12-03", "amount": "180"},
    ]
    assert ledger.calculate_advance_total(
        monthly_advance_gross="200", bookings=bookings,
        period_start="2026-08-01", as_of=date(2026, 11, 1),
    ) == Decimal("800.00")


def test_billing_end_caps_recorded_advances():
    ledger = load_ledger()
    bookings = [
        {"booking_type": "advance", "date": "2026-09-03", "amount": "180"},
        {"booking_type": "advance", "date": "2026-11-03", "amount": "200"},
    ]
    assert ledger.calculate_advance_total(
        monthly_advance_gross="200", bookings=bookings,
        period_start="2026-08-01", as_of=date(2027, 2, 1),
        period_end="2026-10-31",
    ) == Decimal("580.00")


def test_month_specific_advance_amounts_are_used_without_changing_other_months():
    ledger = load_ledger()
    assert ledger.calculate_advance_total(
        monthly_advance_gross="100", bookings=[], period_start="2026-01-01",
        as_of=date(2026, 3, 31), monthly_amounts={"2026-02": Decimal("175")},
    ) == Decimal("375.00")
