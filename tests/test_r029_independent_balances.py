from pathlib import Path

ROOT = Path(__file__).parents[1] / "custom_components" / "verbrauchsmonitor"


def test_total_balance_is_not_created_or_displayed():
    sensor = (ROOT / "sensor.py").read_text(encoding="utf-8")
    card = (ROOT / "frontend" / "verbrauchsmonitor-card.js").read_text(encoding="utf-8")
    assert 'BalanceSensor(entry, "total"' not in sensor
    assert '"total_balance"' not in card
    assert "Offener Betrag" in card and "Aktuelles Guthaben" in card


def test_both_balance_sensors_use_configured_name_in_required_order():
    sensor = (ROOT / "sensor.py").read_text(encoding="utf-8")
    assert 'f"Kontostand {suffix}"' in sensor
    assert 'meter_entity_object_ids(name)[f"{direction}_balance"]' in sensor


def test_balance_formula_is_independent_and_prorates_annual_base_price():
    sensor = (ROOT / "sensor.py").read_text(encoding="utf-8")
    assert 'if self._direction == "consumption":' in sensor
    assert 'price = gross_decimal_from_net(self._data.get(CONF_PURCHASE_PRICE_NET, 0), vat)' in sensor
    assert 'price = gross_decimal_from_net(self._data.get(CONF_FEED_IN_PRICE_NET, 0), vat)' in sensor
    assert 'base_gross_annual = base_net * (Decimal(1) + vat / Decimal(100))' in sensor
    assert 'accrued_annual_base_price(base_gross_annual, billing_start_dt, now_local)' in sensor
    assert 'credit_effect = credits if self._direction == "feed_in" else -credits' in sensor
    assert 'energy_amount + base_gross + extra_charges' in sensor
    ledger = (ROOT / "ledger.py").read_text(encoding="utf-8")
    assert 'def calculate_booking_adjustments(' in ledger
    assert 'base_price_months' not in sensor


def test_billing_period_fields_are_available_in_contract_configuration():
    flow = (ROOT / "config_flow.py").read_text(encoding="utf-8")
    assert '"billing_period_start"' in flow
    assert 'vol.Required("billing_period_months"' in flow
