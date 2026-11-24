from pathlib import Path

ROOT = Path(__file__).parents[1]
INTEGRATION = ROOT / "custom_components/verbrauchsmonitor"

def test_tariff_format_uses_german_comma_and_two_decimals():
    card = (INTEGRATION / "frontend/verbrauchsmonitor-card.js").read_text()
    assert 'minimumFractionDigits:2,maximumFractionDigits:6' in card
    assert 'tariff(price)' in card

def test_annual_base_price_is_informational_and_not_italic():
    card = (INTEGRATION / "frontend/verbrauchsmonitor-card.js").read_text()
    assert 'class="informational"' in card
    assert "money(base)" in card and "monthlyAdvance" in card
    assert "monthlyBase" not in card
    assert '.row .informational' in card and 'font-style:normal' in card

def test_multiple_additional_payments_are_independent_bookings():
    flow = (INTEGRATION / "config_flow.py").read_text()
    ledger = (INTEGRATION / "ledger.py").read_text()
    sensor = (INTEGRATION / "sensor.py").read_text()
    assert '{"value": "payment", "label": self._labels("Sonderzahlung", "Additional payment")}' in flow
    assert 'elif kind == "payment":' in ledger
    assert 'additional_payments += amount' in ledger
    # Each booking is accumulated independently; the sensor passes the complete
    # relevant booking list to the centralized ledger calculation.
    assert 'relevant_bookings.append(booking)' in sensor
    assert 'calculate_booking_adjustments(' in sensor
