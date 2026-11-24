from pathlib import Path

CARD = Path(__file__).resolve().parents[1] / "custom_components/verbrauchsmonitor/frontend/verbrauchsmonitor-card.js"


def test_redundant_top_summary_is_removed():
    source = CARD.read_text(encoding="utf-8")
    assert "const summary = []" not in source
    assert 'section class="summary"' not in source


def test_meter_detail_section_remains():
    source = CARD.read_text(encoding="utf-8")
    assert 'section class="meter"' in source
    assert 'Verbrauch – Zählerstand' in source
    assert 'Verbrauch – Aktuell' in source
    assert 'Verbrauch – Kontostand' in source
