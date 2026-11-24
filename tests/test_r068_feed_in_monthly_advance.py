from pathlib import Path

ROOT = Path(__file__).parents[1]
INTEGRATION = ROOT / "custom_components" / "verbrauchsmonitor"


def test_feed_in_contract_preserves_monthly_advance_input():
    source = (INTEGRATION / "config_flow.py").read_text(encoding="utf-8")
    assert 'merged["feed_in_monthly_advance"] = str(net_advance.quantize' in source
    assert 'merged.pop("monthly_advance", None)' in source
    assert 'merged["monthly_advance"] = 0.0' not in source


def test_feed_in_card_displays_monthly_advance_without_payment_section():
    source = (INTEGRATION / "frontend" / "verbrauchsmonitor-card.js").read_text(encoding="utf-8")
    assert 't("mtl.","monthly")' in source and 'Einspeisevergütung' in source
    assert 'isFeed && monthlyAdvance>0?field(t("Monatlicher Abschlag","Monthly advance"),money(monthlyAdvance))' not in source
    assert 't("Erhaltene Abschläge","Advances received")' in source
    assert 'money(finance.advancePaid)' in source
