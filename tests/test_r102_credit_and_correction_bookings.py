from decimal import Decimal
from pathlib import Path
import importlib.util
import sys

ROOT = Path(__file__).resolve().parents[1]
LEDGER_PATH = ROOT / "custom_components" / "verbrauchsmonitor" / "ledger.py"
SPEC = importlib.util.spec_from_file_location("vm_r102_ledger", LEDGER_PATH)
LEDGER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = LEDGER
SPEC.loader.exec_module(LEDGER)


def test_credit_amount_must_be_positive_and_correction_may_be_signed():
    assert LEDGER.validate_booking_amount(booking_type="credit", amount="12.50") == Decimal("12.50")
    assert LEDGER.validate_booking_amount(booking_type="correction", amount="-3.25") == Decimal("-3.25")
    assert LEDGER.validate_booking_amount(booking_type="correction", amount="3.25") == Decimal("3.25")


def test_credit_rejects_zero_and_negative_amounts_and_correction_rejects_zero():
    for amount in ("0", "-1"):
        try:
            LEDGER.validate_booking_amount(booking_type="credit", amount=amount)
        except ValueError:
            pass
        else:
            raise AssertionError("Gutschrift muss einen positiven Betrag haben")
    try:
        LEDGER.validate_booking_amount(booking_type="correction", amount="0")
    except ValueError:
        pass
    else:
        raise AssertionError("Korrektur darf nicht null sein")


def test_booking_adjustments_apply_credit_by_billing_direction_and_signed_corrections():
    bookings = [
        {"booking_type": "credit", "amount": "10.00", "direction": "consumption"},
        {"booking_type": "correction", "amount": "-2.00", "direction": "consumption"},
        {"booking_type": "correction", "amount": "3.00", "direction": "consumption"},
        {"booking_type": "credit", "amount": "10.00", "direction": "feed_in"},
    ]
    consumption = LEDGER.calculate_booking_adjustments(bookings=bookings, direction="consumption")
    feed_in = LEDGER.calculate_booking_adjustments(bookings=bookings, direction="feed_in")
    assert consumption == (Decimal("10.00"), Decimal("0"), Decimal("0"), Decimal("1.00"))
    assert feed_in == (Decimal("10.00"), Decimal("0"), Decimal("0"), Decimal("0"))
    legacy_negative_credit = LEDGER.calculate_booking_adjustments(
        bookings=[{"booking_type": "credit", "amount": "-4.00", "direction": "feed_in"}],
        direction="feed_in",
    )
    assert legacy_negative_credit[0] == Decimal("4.00")


def test_balance_sensor_applies_signed_corrections_after_customer_sign_conversion():
    source = (ROOT / "custom_components" / "verbrauchsmonitor" / "sensor.py").read_text()
    assert 'credit_effect = credits if self._direction == "feed_in" else -credits' in source
    assert "apply_booking_corrections(" in source
    assert "energy_amount + base_gross + extra_charges" in source


def test_card_keeps_corrections_separate_from_credits_and_extra_charges():
    card = (ROOT / "custom_components" / "verbrauchsmonitor" / "frontend" / "verbrauchsmonitor-card.js").read_text()
    assert '.filter(b => b.booking_type === "extra_charge")' in card
    assert '.filter(b => b.booking_type === "credit")' in card
    assert '.filter(b => b.booking_type === "correction")' in card
    assert 'finance.correctionCount === 1 ? t("Korrektur","Correction") : t("Korrekturen","Corrections")' in card
    assert 'finance.extraCharges+finance.corrections' not in card
    assert "finance.advancePaid+finance.additionalPayments+finance.corrections" in card


def test_successful_manual_booking_is_not_logged_at_info_level_and_save_errors_are_reported():
    source = (ROOT / "custom_components" / "verbrauchsmonitor" / "config_flow.py").read_text()
    assert "await self.hass.async_add_executor_job(add_booking, self.hass, item)" in source
    assert 'errors={"base": "save_failed"}' in source
    assert "_LOGGER.exception(" in source
    frontend = (ROOT / "custom_components" / "verbrauchsmonitor" / "frontend" / "__init__.py").read_text()
    assert "_LOGGER.info(" not in frontend
    assert "_LOGGER.debug(" not in frontend
