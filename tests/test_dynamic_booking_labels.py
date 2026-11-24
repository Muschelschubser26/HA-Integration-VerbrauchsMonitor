"""Regression tests for singular/plural labels in the dashboard card."""
from pathlib import Path


CARD = (
    Path(__file__).parents[1]
    / "custom_components"
    / "verbrauchsmonitor"
    / "frontend"
    / "verbrauchsmonitor-card.js"
)


def test_additional_payment_labels_distinguish_singular_and_plural():
    source = CARD.read_text(encoding="utf-8")
    assert 'additionalPaymentCount === 1' in source
    assert 't("Sonderzahlung","Additional payment")' in source
    assert 't("Sonderzahlungen","Additional payments")' in source
    assert 't("Summe der Sonderzahlung","Total additional payment")' in source
    assert 't("Summe der Sonderzahlungen","Total additional payments")' in source


def test_correction_labels_distinguish_singular_and_plural():
    source = CARD.read_text(encoding="utf-8")
    assert 'correctionCount === 1 ? t("Korrektur","Correction")' in source
    assert 't("Korrekturen","Corrections")' in source


def test_zero_amount_booking_rows_remain_hidden():
    source = CARD.read_text(encoding="utf-8")
    assert 'finance.additionalPayments !== 0 ? field(' in source
    assert 'finance.corrections !== 0 ? field(' in source
    assert 'Number(b.amount || 0) !== 0' in source
