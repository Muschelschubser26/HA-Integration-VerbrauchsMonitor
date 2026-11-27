from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_billing_card_calculates_financials_from_each_direction_source():
    source = (ROOT / "custom_components/verbrauchsmonitor/frontend/verbrauchsmonitor-card.js").read_text(encoding="utf-8")
    assert 'const financeC=financeFor(counter, "consumption", balance), financeF=financeFor(feed, "feed_in", feedBalance);' in source
    assert 'const financeC=financeFor(counter, "consumption", balance), financeF=financeFor(feed, "feed_in", feedBalance);' in source
    assert "const sourceState=isFeed?feed:counter, finance=isFeed?financeF:financeC;" in source
    assert 'const recordedAdvances = validBookings.filter(b => b.booking_type === "advance")' in source
    assert 'const groupedAdvanceTotal = monthlyAdvanceGroups.reduce' in source
    assert ': recordedAdvanceTotal;' in source
    assert 'monthlyAdvanceGroups' in source
    assert 'each elapsed month is counted as a paid monthly advance' in source
    assert 'Bisher fällige Abschläge' not in source


def test_billing_card_does_not_duplicate_lower_consumption_heading_and_values_do_not_wrap():
    source = (ROOT / "custom_components/verbrauchsmonitor/frontend/verbrauchsmonitor-card.js").read_text(encoding="utf-8")
    assert '<h3>${esc(directionTitle)}</h3>' in source
    assert 'Einspeisung im Abrechnungszeitraum' in source
    assert "white-space:nowrap" in source
    assert ".billing-direction{display:block;width:100%;min-width:0}" in source
    assert "overflow-x:auto" not in source


def test_contract_wizard_uses_one_visible_primary_direction():
    source = (ROOT / "custom_components/verbrauchsmonitor/config_flow.py").read_text(encoding="utf-8")
    assert 'vol.Required("primary_billing_type"' in source
    assert 'vol.Optional("secondary_billing_type"' not in source
    assert 'if "secondary_billing_type" in merged and merged["secondary_billing_type"] == primary:' in source
    assert 'if not secondary:' in source
