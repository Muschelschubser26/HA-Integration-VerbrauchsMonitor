from datetime import date
from decimal import Decimal
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

ROOT = Path(__file__).parents[1]
INTEGRATION = ROOT / "custom_components" / "verbrauchsmonitor"


def _ledger():
    path = INTEGRATION / "ledger.py"
    spec = spec_from_file_location("vm_r093_ledger", path)
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_four_first_of_month_dates_count_as_four_paid_advances_without_bookings():
    ledger = _ledger()
    total = ledger.calculate_advance_total(
        monthly_advance_gross="200.00", bookings=[],
        period_start="2026-08-01", as_of=date(2026, 11, 23),
        period_end="2026-12-31",
    )
    assert total == Decimal("800.00")


def test_month_start_after_billing_start_is_first_eligible_advance_date():
    ledger = _ledger()
    total = ledger.calculate_advance_total(
        monthly_advance_gross="200.00", bookings=[],
        period_start="2026-08-15", as_of=date(2026, 11, 23),
        period_end="2026-12-31",
    )
    assert total == Decimal("600.00")


def test_explicit_advance_booking_replaces_automatic_month_not_duplicates_it():
    ledger = _ledger()
    bookings = [{"booking_type": "advance", "date": "2026-09-05", "amount": "180.00"}]
    total = ledger.calculate_advance_total(
        monthly_advance_gross="200.00", bookings=bookings,
        period_start="2026-08-01", as_of=date(2026, 11, 23),
        period_end="2026-12-31",
    )
    assert total == Decimal("780.00")


def test_card_has_no_separate_due_advances_row_and_shows_monthly_amount_as_paid():
    source = (INTEGRATION / "frontend" / "verbrauchsmonitor-card.js").read_text(encoding="utf-8")
    assert 'Bisher fällige Abschläge' not in source
    assert 'monthlyAdvanceGroups.map(group =>' in source
    assert 'money(finance.advancePaid+finance.additionalPayments+finance.corrections)' in source
    assert 'const groupedAdvanceTotal = monthlyAdvanceGroups.reduce' in source


def test_balance_and_forecast_use_the_same_automatic_monthly_payment_calculation():
    source = (INTEGRATION / "sensor.py").read_text(encoding="utf-8")
    assert 'advances = money_amount(expected_advance_amount)' in source
    assert 'expected_advances_total' in source
    assert 'return calculate_advance_total(' in source
    assert 'No confirmation or manual booking is required' in source
