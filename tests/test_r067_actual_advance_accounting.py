from datetime import date
from decimal import Decimal
from pathlib import Path
from importlib.util import spec_from_file_location, module_from_spec
import sys

ROOT = Path(__file__).parents[1]
INTEGRATION = ROOT / "custom_components" / "verbrauchsmonitor"


def _ledger():
    path = INTEGRATION / "ledger.py"
    spec = spec_from_file_location("vm_r067_ledger", path)
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_explicit_database_advance_bookings_remain_separately_queryable():
    ledger = _ledger()
    bookings = [{"booking_type": "advance", "date": "2026-09-03", "amount": "175"}]
    due = ledger.calculate_advance_total(
        monthly_advance_gross="200", bookings=bookings,
        period_start="2026-08-01", as_of=date(2026, 11, 1),
    )
    paid = ledger.calculate_recorded_advance_total(
        bookings=bookings, period_start="2026-08-01", as_of=date(2026, 11, 1),
    )
    assert due == Decimal("775.00")
    assert paid == Decimal("175.00")


def test_recorded_advances_are_limited_to_billing_window():
    ledger = _ledger()
    bookings = [
        {"booking_type": "advance", "date": "2026-07-31", "amount": "100"},
        {"booking_type": "advance", "date": "2026-08-01", "amount": "125"},
        {"booking_type": "advance", "date": "2026-11-02", "amount": "200"},
    ]
    paid = ledger.calculate_recorded_advance_total(
        bookings=bookings, period_start="2026-08-01", as_of=date(2026, 11, 1),
        period_end="2026-12-31",
    )
    assert paid == Decimal("125.00")


def test_balance_sensor_counts_first_of_month_advance_as_paid_automatically():
    source = (INTEGRATION / "sensor.py").read_text()
    assert 'advances = money_amount(expected_advances)' in source
    assert '"recorded_advances_paid"] = float(advances)' in source
    assert '"automatic_monthly_advances_paid"] = float(advances)' in source
    assert 'apply_booking_corrections(' in source


def test_feed_in_card_omits_payment_section_and_uses_credit_wording():
    source = (INTEGRATION / "frontend" / "verbrauchsmonitor-card.js").read_text()
    assert 'isFeed?t("Vergütung","Remuneration"):t("Kosten","Costs")' in source
    assert 't("Aktueller Abrechnungszeitraum","Current billing period")' in source
    assert 't("Ø Aktuell im Monat","Average current month")' in source
    assert 'const balanceLabel = balanceValue === null' in source
    assert 't("Offener Betrag","Outstanding amount")' in source
    assert 't("Aktuelles Guthaben","Current credit")' in source
    assert 't("Erhaltene Abschläge","Advances received")' in source
