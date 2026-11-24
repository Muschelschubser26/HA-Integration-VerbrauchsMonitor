from pathlib import Path

ROOT = Path(__file__).parents[1]
INTEGRATION = ROOT / "custom_components/verbrauchsmonitor"


def test_recommendation_no_longer_uses_reliability_caps_in_sensor():
    source = (INTEGRATION / "sensor.py").read_text()
    assert "apply_advance_recommendation_limit" not in source
    assert "future_scheduled_advances=remaining_schedule" in source


def test_expected_future_payments_are_separate_from_actual_bookings():
    forecast = (INTEGRATION / "forecast.py").read_text()
    assert "expected_end_amount = annual_value - booked - future_scheduled" in forecast
    assert "remaining_amount = max(Decimal(0), annual_value - booked)" in forecast


def test_forecast_base_price_is_prorated_to_billing_period_length():
    forecast = (INTEGRATION / "forecast.py").read_text()
    assert "Decimal(billing_months) / Decimal(12)" in forecast


def test_monthly_first_day_schedule_is_included_in_paid_advances():
    sensor = (INTEGRATION / "sensor.py").read_text()
    assert 'meter_bookings = [b for b in ledger.get("bookings", []) if b.get("status") == "assigned" and b.get("meter_id") == meter.get("id")]' in sensor
    assert 'advances = money_amount(expected_advances)' in sensor
    assert 'def _booked_advances(self, period_start, as_of):' in sensor
    assert 'return calculate_advance_total(' in sensor


def test_monthly_average_and_cost_total_keep_precision_until_display():
    card = (INTEGRATION / "frontend/verbrauchsmonitor-card.js").read_text()
    assert "const totalCosts = Number.isFinite(backendTotalCosts) ? backendTotalCosts :" in card
    assert "const money = v => `${num(v,2)} €`;" in card
    assert "const billingStartTimestamp = periodStart;" in card
    assert '<ha-icon icon="mdi:chart-box-outline"></ha-icon>' not in card
