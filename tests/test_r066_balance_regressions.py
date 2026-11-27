from pathlib import Path

ROOT = Path(__file__).parents[1]
INTEGRATION = ROOT / "custom_components" / "verbrauchsmonitor"


def test_backend_keeps_contractual_advances_for_consumption_only():
    source = (INTEGRATION / "sensor.py").read_text()
    assert 'if self._direction == "consumption"' in source
    assert 'else Decimal("0")' in source
    assert "calculate_advance_total(" in source


def test_dashboard_uses_direction_specific_contractual_advances():
    source = (INTEGRATION / "frontend" / "verbrauchsmonitor-card.js").read_text()
    assert 'const groupedAdvanceTotal = monthlyAdvanceGroups.reduce' in source
    assert 'Bisher fällige Abschläge' not in source
    assert 'monthly_advance_groups' in source
    assert 'build_monthly_advance_groups(' in (ROOT / 'custom_components/verbrauchsmonitor/sensor.py').read_text()


def test_feed_in_has_no_consumption_base_price_and_uses_separate_advance():
    source = (INTEGRATION / "sensor.py").read_text()
    assert 'if self._direction == "consumption"' in source
    assert 'self._data.get("feed_in_monthly_advance", 0)' in source
    assert 'else Decimal("0")' in source


def test_frontend_and_backend_use_the_same_monthly_advance_rule():
    ledger = (INTEGRATION / "ledger.py").read_text()
    card = (INTEGRATION / "frontend" / "verbrauchsmonitor-card.js").read_text()
    assert "automatic_months" in ledger
    assert "monthlyAdvanceGroups" in card and "automaticMonths" not in card
    assert "covered_months" in ledger
    assert "calculate_recorded_advance_total" in ledger
