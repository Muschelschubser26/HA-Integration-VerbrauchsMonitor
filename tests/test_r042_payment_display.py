from pathlib import Path

ROOT = Path(__file__).parents[1]
INTEGRATION = ROOT / "custom_components/verbrauchsmonitor"

def test_card_hides_zero_value_payment_rows_and_shows_nonzero_values():
    card = (INTEGRATION / "frontend/verbrauchsmonitor-card.js").read_text()
    assert '"Tatsächlich geleistete Abschläge"' not in card
    assert 't("Abschläge","Advances")' in card
    assert 't("Summe der Sonderzahlungen","Total additional payments")' in card
    assert 't("Summe der Sonderzahlung","Total additional payment")' in card
    assert 'finance.additionalPayments !== 0 ? field' in card
    assert 'finance.corrections !== 0 ? field' in card
    assert '"Gesamt geleistete Zahlungen"' in card
    assert 'money(finance.advancePaid+finance.additionalPayments+finance.corrections)' in card
    assert '"Vereinbarter monatlicher Abschlag"' not in card
    assert '"Geleistete Abschläge"' not in card

def test_payment_type_is_labeled_sonderzahlung_in_german():
    flow = (INTEGRATION / "config_flow.py").read_text()
    assert '"value": "payment", "label": self._labels("Sonderzahlung", "Additional payment")' in flow

def test_finance_separator_has_vertical_spacing():
    card = (INTEGRATION / "frontend/verbrauchsmonitor-card.js").read_text()
    assert '.finance-group{margin-top:10px;padding-top:8px;border-top:2px solid var(--divider-color)}' in card
