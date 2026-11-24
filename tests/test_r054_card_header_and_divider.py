from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_card_header_uses_meter_name_once_and_keeps_period():
    source = (ROOT / "custom_components/verbrauchsmonitor/frontend/verbrauchsmonitor-card.js").read_text(encoding="utf-8")
    assert '<h1>${esc(meterName)}</h1>' in source
    assert '<h2>${esc(meterName)}</h2>' not in source
    assert 'this.config.title||t("Aktuelle Abrechnung"' not in source
    assert 'class="period-info"' in source

def test_card_editor_has_no_manual_title_field():
    source = (ROOT / "custom_components/verbrauchsmonitor/frontend/verbrauchsmonitor-card.js").read_text(encoding="utf-8")
    assert 't("Kartentitel","Card title")' not in source
    editor = source.split('class VerbrauchsMonitorBillingCardEditor', 1)[1]
    assert 'querySelector("#title")' not in editor

def test_last_meter_detail_row_has_no_thin_separator():
    source = (ROOT / "custom_components/verbrauchsmonitor/frontend/verbrauchsmonitor-card.js").read_text(encoding="utf-8")
    assert '.side > .row:nth-child(5){border-bottom:0}' in source
    assert '.finance-group{margin-top:10px;padding-top:8px;border-top:2px solid var(--divider-color)}' in source
