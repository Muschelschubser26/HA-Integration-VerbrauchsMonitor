from datetime import date
from decimal import Decimal
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

ROOT = Path(__file__).parents[1]
INTEGRATION = ROOT / "custom_components" / "verbrauchsmonitor"


def _load_module(name, path):
    spec = spec_from_file_location(name, path)
    module = module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_remaining_payment_months_determine_total_recommended_installment():
    forecast = _load_module("vm_r092_forecast", INTEGRATION / "forecast.py")
    one_month = forecast.calculate_forecast(
        direction="consumption", current_reading="4984.386", baseline_reading="3164.000",
        period_start="2026-08-01", today=date(2026, 11, 23), price_net="23.7647058824",
        vat_rate=19, annual_base_price_net="201.36134454", monthly_advance_net="168.06722689",
        period_months=5, booked_advances=0, future_scheduled_advances=200,
    )
    assert one_month["months_remaining"] == 1
    assert one_month["annual_value_eur"] == round(
        one_month["accrued_energy_cost_eur"]
        + one_month["accrued_base_price_eur"]
        + one_month["remaining_costs_including_base_price_eur"], 2
    )
    assert one_month["expected_year_end_balance_eur"] == -591.18
    assert one_month["recommended_monthly_advance_eur"] == 791.18
    assert one_month["expected_year_end_balance_eur"] == round(-(one_month["annual_value_eur"] - 200), 2)

    two_months = forecast.calculate_forecast(
        direction="consumption", current_reading="4984.386", baseline_reading="3164.000",
        period_start="2026-07-01", today=date(2026, 10, 23), price_net="23.7647058824",
        vat_rate=19, annual_base_price_net="201.36134454", monthly_advance_net="168.06722689",
        period_months=6, booked_advances=0, future_scheduled_advances=400,
    )
    assert two_months["months_remaining"] == 2
    assert two_months["recommended_monthly_advance_eur"] == round(two_months["annual_value_eur"] / 2, 2)


def test_first_of_each_month_is_automatically_counted_as_paid():
    ledger = _load_module("vm_r092_ledger", INTEGRATION / "ledger.py")
    bookings = [
        {"booking_type": "advance", "date": "2026-09-05", "amount": "200.00", "direction": "consumption"},
    ]
    due = ledger.calculate_advance_total(
        monthly_advance_gross="200.00", bookings=bookings,
        period_start="2026-08-01", as_of=date(2026, 11, 23), period_end="2026-12-31",
    )
    received = ledger.calculate_recorded_advance_total(
        bookings=bookings, period_start="2026-08-01", as_of=date(2026, 11, 23),
        period_end="2026-12-31",
    )
    assert due == Decimal("800.00")
    assert received == Decimal("200.00")  # Explicit ledger record remains separately inspectable.

    no_payment_due = ledger.calculate_advance_total(
        monthly_advance_gross="200.00", bookings=[],
        period_start="2026-08-01", as_of=date(2026, 11, 23), period_end="2026-12-31",
    )
    no_payment_received = ledger.calculate_recorded_advance_total(
        bookings=[], period_start="2026-08-01", as_of=date(2026, 11, 23),
        period_end="2026-12-31",
    )
    assert no_payment_due == Decimal("800.00")
    assert no_payment_received == Decimal("0.00")  # No explicit database booking was needed for the automatic total.


def test_billing_card_displays_automatic_monthly_advances_as_paid_without_due_row():
    source = (INTEGRATION / "frontend" / "verbrauchsmonitor-card.js").read_text(encoding="utf-8")
    assert 'Bisher fällige Abschläge' not in source
    assert 't("Erhaltene Abschläge","Advances received")' in source
    assert 'withColon(t("Abschläge","Advances"))' in source
    assert 'const advancePaid = Number.isFinite(Number(sourceAttributes.recorded_advances_paid))' in source
    assert 'money(finance.advancePaid)' in source


def test_actual_bookings_are_filtered_by_meter_and_assignment_before_sensor_creation():
    source = (INTEGRATION / "sensor.py").read_text(encoding="utf-8")
    assert 'b.get("status") == "assigned" and b.get("meter_id") == meter.get("id")' in source
    assert '"bookings": meter_bookings' in source


def test_monthly_average_remains_based_on_billing_start_and_no_unrequested_icon():
    source = (INTEGRATION / "frontend" / "verbrauchsmonitor-card.js").read_text(encoding="utf-8")
    assert "const billingStartTimestamp = periodStart;" in source
    assert 't("Ø Aktuell im Monat","Average current month")' in source
    assert '<ha-icon icon="mdi:chart-box-outline"></ha-icon>' not in source
