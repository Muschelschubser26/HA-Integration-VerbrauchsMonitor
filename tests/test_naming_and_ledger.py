from importlib.util import spec_from_file_location, module_from_spec
from pathlib import Path
from decimal import Decimal
import sys

ROOT = Path(__file__).parents[1]

def load_module(name):
    path = ROOT / "custom_components/verbrauchsmonitor" / f"{name}.py"
    spec = spec_from_file_location(f"vm_{name}", path)
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module

def test_name_normalization_and_entity_ids():
    naming = load_module("naming")
    assert naming.slugify_meter_name("HWR Stromzähler äöü ß") == "hwr_stromzahler_aou_ss"
    assert naming.balance_entity_ids("HWR Stromzähler", feed_in=True) == {
        "consumption": "sensor.verbrauchsmonitor_hwr_stromzahler_verbrauch_kontostand",
        "feed_in": "sensor.verbrauchsmonitor_hwr_stromzahler_einspeisung_kontostand",
    }
    assert "feed_in" not in naming.balance_entity_ids("Haus", feed_in=False)

def test_period_balance_uses_energy_deltas_and_bookings():
    ledger = load_module("ledger")
    result = ledger.calculate_balance(
        consumption_kwh=100, feed_in_kwh=20,
        purchase_price_gross_ct_kwh=35, feed_in_price_gross_ct_kwh=8,
        base_price_gross=12, base_price_months=1, advances=30,
    )
    assert result.consumption_cost == 35
    assert result.feed_in_credit == Decimal("1.6")
    assert result.total == Decimal("15.4")

def test_period_balance_rejects_negative_energy():
    ledger = load_module("ledger")
    try:
        ledger.calculate_balance(consumption_kwh=-1, purchase_price_gross_ct_kwh=30)
    except ValueError:
        pass
    else:
        raise AssertionError("negative energy delta must be rejected")

def test_period_balance_rejects_cumulative_negative_or_invalid_values():
    ledger = load_module("ledger")
    for value in ("NaN", "Infinity", "invalid"):
        try:
            ledger.calculate_balance(consumption_kwh=value, purchase_price_gross_ct_kwh=30)
        except ValueError:
            continue
        raise AssertionError(f"invalid value accepted: {value}")

def test_only_recorded_advances_are_counted_as_paid():
    from datetime import date
    ledger = load_module("ledger")
    total = ledger.calculate_advance_total(
        monthly_advance_gross="200.00",
        elapsed_months=4,
        bookings=[
            {"booking_type": "advance", "amount": "200", "date": "2026-01-05"},
            {"booking_type": "credit", "amount": "50", "date": "2026-02-01"},
        ],
        period_start="2026-01-01",
        as_of=date(2026, 4, 30),
    )
    assert total == 800  # contractual due amount, not the amount paid
    paid = ledger.calculate_recorded_advance_total(
        bookings=[
            {"booking_type": "advance", "amount": "200", "date": "2026-01-05"},
            {"booking_type": "credit", "amount": "50", "date": "2026-02-01"},
        ], period_start="2026-01-01", as_of=date(2026, 4, 30),
    )
    assert paid == 200


def test_multiple_booked_advances_in_same_month_are_all_counted():
    from datetime import date
    ledger = load_module("ledger")
    total = ledger.calculate_advance_total(
        monthly_advance_gross="100",
        elapsed_months=2,
        bookings=[
            {"booking_type": "advance", "amount": "60", "date": "2026-01-05"},
            {"booking_type": "advance", "amount": "40", "date": "2026-01-20"},
        ],
        period_start="2026-01-01",
        as_of=date(2026, 2, 28),
    )
    assert total == 200


def test_measurement_entity_ids_follow_meter_and_direction_convention():
    naming = load_module("naming")
    assert naming.meter_entity_object_ids("Einspeisung neu") == {
        "consumption_counter": "verbrauchsmonitor_einspeisung_neu_verbrauch_zaehlerstand",
        "consumption_power": "verbrauchsmonitor_einspeisung_neu_verbrauch_leistung",
        "feed_in_counter": "verbrauchsmonitor_einspeisung_neu_einspeisung_zaehlerstand",
        "feed_in_power": "verbrauchsmonitor_einspeisung_neu_einspeisung_leistung",
        "consumption_balance": "verbrauchsmonitor_einspeisung_neu_verbrauch_kontostand",
        "feed_in_balance": "verbrauchsmonitor_einspeisung_neu_einspeisung_kontostand",
    }
