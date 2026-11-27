from datetime import date
from decimal import Decimal
from pathlib import Path

import importlib.util
import sys

LEDGER_PATH = Path(__file__).parents[1] / "custom_components" / "verbrauchsmonitor" / "ledger.py"
_SPEC = importlib.util.spec_from_file_location("verbrauchsmonitor_ledger_r143", LEDGER_PATH)
_LEDGER = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _LEDGER
_SPEC.loader.exec_module(_LEDGER)
apply_booking_corrections = _LEDGER.apply_booking_corrections
build_monthly_advance_groups = _LEDGER.build_monthly_advance_groups
calculate_advance_total = _LEDGER.calculate_advance_total
signed_customer_balance = _LEDGER.signed_customer_balance

ROOT = Path(__file__).parents[1]
INTEGRATION = ROOT / "custom_components" / "verbrauchsmonitor"


def test_monthly_advance_amounts_are_counted_as_paid_in_account_balance():
    advances = calculate_advance_total(
        monthly_advance_gross=Decimal("200.00"),
        bookings=[],
        period_start="2026-08-01",
        as_of=date(2026, 11, 26),
        period_end="2026-12-31",
        monthly_amounts={},
    )
    # Four elapsed months: August through November.
    assert advances == Decimal("800.00")
    balance_before_correction = signed_customer_balance(
        direction="consumption", amount=Decimal("606.38") - advances
    )
    balance = apply_booking_corrections(
        account_balance=balance_before_correction,
        corrections=Decimal("-66.00"),
    )
    assert balance == Decimal("127.62")


def test_payment_groups_keep_single_month_without_multiplier_and_merge_equal_months():
    groups = build_monthly_advance_groups(
        period_start="2026-01-01",
        as_of=date(2026, 9, 26),
        monthly_advance_gross=Decimal("200.00"),
        monthly_amounts={"2026-04": Decimal("250.00")},
    )
    assert [(g["from_month"], g["to_month"], g["count"], g["total"]) for g in groups] == [
        ("2026-01", "2026-03", 3, 600.0),
        ("2026-04", "2026-04", 1, 250.0),
        ("2026-05", "2026-09", 5, 1000.0),
    ]


def test_card_has_no_duplicate_advance_rows_and_totals_are_bold_and_last():
    card = (INTEGRATION / "frontend" / "verbrauchsmonitor-card.js").read_text()
    # The obsolete group renderer before the direction-specific headings is gone.
    assert card.count('finance.monthlyAdvanceGroups.map(group =>') == 2
    assert '<strong>${money(finance.advancePaid+finance.additionalPayments+finance.corrections)}</strong>' in card
    assert card.index('t("Korrektur","Correction")') < card.index('t("Gesamt geleistete Zahlungen"')
    assert card.index('t("Korrektur","Correction")', card.index('t("Bereits bezahlt:"')) < card.index('t("Gesamt geleistete Zahlungen"')
    assert 't("Gesamt erhaltene Zahlungen"' in card


def test_backend_balance_uses_due_monthly_advances_not_only_recorded_bookings():
    source = (INTEGRATION / "sensor.py").read_text()
    assert 'advances = money_amount(expected_advance_amount)' in source
    assert '"recorded_advances_paid"] = float(money_amount(paid_advances))' in source
