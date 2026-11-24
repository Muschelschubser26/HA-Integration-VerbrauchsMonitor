from pathlib import Path

ROOT = Path(__file__).parents[1]
CARD = ROOT / "custom_components/verbrauchsmonitor/frontend/verbrauchsmonitor-card.js"


def test_billing_card_is_registered_and_keeps_live_card():
    source = CARD.read_text()
    assert 'customElements.define("verbrauchsmonitor-card"' in source
    assert 'customElements.define("verbrauchsmonitor-billing-card"' in source
    assert 'VerbrauchsMonitor – Aktuelle Abrechnung' in source


def test_billing_card_contains_required_independent_values():
    source = CARD.read_text()
    for token in ("previous_consumption_reading", "purchase_price_net_ct_kwh", "feed_in_price_net_ct_kwh", "base_price_net", "monthly_advance_net", "consumption_balance", "feed_in_balance"):
        assert token in source


def test_baseline_service_is_registered():
    source = (ROOT / "custom_components/verbrauchsmonitor/__init__.py").read_text()
    assert 'async_register(DOMAIN' in source
