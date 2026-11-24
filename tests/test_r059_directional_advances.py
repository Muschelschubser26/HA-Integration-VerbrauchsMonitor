from pathlib import Path

INTEGRATION = Path(__file__).parents[1] / "custom_components" / "verbrauchsmonitor"


def test_sensor_applies_monthly_advance_only_to_consumption():
    source = (INTEGRATION / "sensor.py").read_text(encoding="utf-8")
    assert 'if self._direction == "consumption"' in source
    assert 'else Decimal("0")' in source


def test_dashboard_uses_meter_id_for_independent_meter_groups():
    source = (INTEGRATION / "frontend" / "verbrauchsmonitor-card.js").read_text(encoding="utf-8")
    assert "state.attributes.meter_id || state.attributes.meter_number || state.entity_id" in source


def test_dashboard_calculates_advances_per_source_and_direction():
    source = (INTEGRATION / "frontend" / "verbrauchsmonitor-card.js").read_text(encoding="utf-8")
    assert 'financeFor(counter, "consumption", balance)' in source
    assert 'financeFor(feed, "feed_in", feedBalance)' in source
    assert 'const advancePaid = Number.isFinite(Number(sourceAttributes.recorded_advances_paid))' in source
    assert 'Bisher fällige Abschläge' not in source
    assert 'automaticMonths' in source
