from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
def test_meter_change_values_are_only_rendered_for_changes_in_billing_period():
    source = (ROOT / "custom_components/verbrauchsmonitor/frontend/verbrauchsmonitor-card.js").read_text(encoding="utf-8")
    assert "const meterChanges = allMeterChanges.filter" in source
    assert 'date >= periodStart' in source
    assert 'meterChanges.filter(change => isFeed' in source
    assert 'num(baseline,3)' in source
def test_multiple_changes_can_be_added_and_removed():
    source = (ROOT / "custom_components/verbrauchsmonitor/frontend/verbrauchsmonitor-card.js").read_text(encoding="utf-8")
    assert 'Zählerwechsel hinzufügen' in source and 'meter-change-row' in source
