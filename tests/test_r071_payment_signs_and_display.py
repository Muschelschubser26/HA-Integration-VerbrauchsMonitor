from pathlib import Path

ROOT = Path(__file__).parents[1]
INTEGRATION = ROOT / "custom_components" / "verbrauchsmonitor"


def test_annual_base_price_is_shown_in_grey_parentheses_without_monthly_label():
    card = (INTEGRATION / "frontend" / "verbrauchsmonitor-card.js").read_text()
    expected = 'withColon(t("Anteiliger Grundpreis","Prorated base price")))} <span class="informational">(${money(base)})'
    assert expected in card
    assert '(${t("mtl.","monthly")} ${money(monthlyBase)})' not in card


def test_due_advances_and_special_payments_make_total_payments():
    card = (INTEGRATION / "frontend" / "verbrauchsmonitor-card.js").read_text()
    assert 'money(finance.advancePaid+finance.additionalPayments+finance.corrections)' in card
    assert 'Tatsächlich geleistete Abschläge' not in card


def test_signed_customer_balance_is_used_for_amount_credit_and_neutral_states():
    card = (INTEGRATION / "frontend" / "verbrauchsmonitor-card.js").read_text()
    sensor = (INTEGRATION / "sensor.py").read_text()
    assert 'apply_booking_corrections(' in sensor
    ledger = (INTEGRATION / "ledger.py").read_text()
    assert 'def signed_customer_balance(' in ledger
    assert 'balanceValue < 0 ? t("Offener Betrag","Outstanding amount")' in card
    assert 'balanceValue > 0 ? t("Aktuelles Guthaben","Current credit")' in card
    assert 'class="grand-balance ${balanceClass}"' in card
    assert '.grand-balance.liability' in card
    assert '.grand-balance.credit' in card
    assert '.grand-balance.settled' in card


def test_fällige_advances_are_subtracted_from_consumption_balance():
    sensor = (INTEGRATION / "sensor.py").read_text()
    assert 'advances = money_amount(expected_advance_amount)' in sensor
    assert 'expected_advances_total' in sensor
    assert 'credit_effect = credits if self._direction == "feed_in" else -credits' in sensor
    assert 'energy_amount + base_gross + extra_charges' in sensor


def test_signed_balance_helper_preserves_precision_and_customer_perspective():
    import importlib.util
    from decimal import Decimal
    path = INTEGRATION / "ledger.py"
    spec = importlib.util.spec_from_file_location("vm_r071_ledger", path)
    module = importlib.util.module_from_spec(spec)
    import sys
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    assert module.signed_customer_balance(direction="consumption", amount="683.191") == Decimal("-683.191")
    assert module.signed_customer_balance(direction="feed_in", amount="1365.925") == Decimal("1365.925")
