from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
def test_edit_form_uses_repeated_dated_meter_change_rows():
    source = (ROOT / "custom_components/verbrauchsmonitor/frontend/verbrauchsmonitor-card.js").read_text(encoding="utf-8")
    assert 'class="meter-change-row"' in source
    assert 'class="change-date"' in source
    assert 'class="change-consumption"' in source
    assert 'class="change-feed-in"' in source
    assert 'Zählerwechsel hinzufügen' in source
def test_submit_sends_meter_change_records():
    source = (ROOT / "custom_components/verbrauchsmonitor/frontend/verbrauchsmonitor-card.js").read_text(encoding="utf-8")
    assert 'payload.meter_changes=[...outsidePeriod,...meterChanges]' in source
    assert 'if(!Number.isFinite(value)||value<0)' in source
def test_revision_metadata_is_consistent():
    const = (ROOT / "custom_components/verbrauchsmonitor/const.py").read_text()
    assert 'INTEGRATION_VERSION: Final = "0.0.2-dev-r111"' in const
    assert "Prognose" in (ROOT / "README.md").read_text()
