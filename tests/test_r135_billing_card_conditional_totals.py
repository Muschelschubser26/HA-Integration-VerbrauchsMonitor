from pathlib import Path

CARD = Path(__file__).parents[1] / "custom_components" / "verbrauchsmonitor" / "frontend" / "verbrauchsmonitor-card.js"

def test_total_payment_rows_are_always_rendered_for_monthly_advance_breakdown():
    source = CARD.read_text()
    assert 't("Gesamt erhaltene Zahlungen"' in source
    assert 't("Gesamt erhaltene Zahlungen"' in source
    assert 't("Gesamt geleistete Zahlungen"' in source

def test_payment_breakdown_precedes_balance():
    source = CARD.read_text()
    assert source.index('t("Gesamt geleistete Zahlungen"') < source.index('<div class="grand-balance ${balanceClass}">')


def test_recommendation_calculation_message_matches_approved_wording():
    source = CARD.read_text()
    assert 'Ein voraussichtlicher monatlicher Abschlag wird gerade berechnet.' in source
