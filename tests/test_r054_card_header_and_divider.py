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
    assert '.meter-reading-row{border-bottom:1px solid var(--divider-color);padding-bottom:5px;margin-bottom:3px}' in source
    assert '.current-power{display:inline-flex;justify-content:flex-end' in source
    assert '.period-meta-row{display:flex;align-items:center;justify-content:space-between' in source
    assert 'font-size:10px;line-height:12px' in source
    assert '.finance-group{margin-top:10px;padding-top:8px;border-top:2px solid var(--divider-color)}' in source
