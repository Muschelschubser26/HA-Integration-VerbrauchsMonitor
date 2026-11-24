from pathlib import Path

SOURCE = Path(__file__).parents[1] / "custom_components/verbrauchsmonitor/frontend/verbrauchsmonitor-card.js"


def test_billing_card_selects_exactly_one_direction():
    source = SOURCE.read_text()
    assert 'const selectedDirection = this.config.direction === "feed_in" ? "feed_in" : "consumption";' in source
    assert 'if (selectedCounter || selectedBalance) directions.push({kind:selectedDirection' in source


def test_editor_exposes_meter_and_direction_separately():
    source = SOURCE.read_text()
    assert 'id="meter"' in source
    assert 'id="direction"' in source
    assert 'Zählerstand / Abrechnungsbereich' in source
    assert 'Eine Karte zeigt genau einen Zählerstand' in source


def test_card_has_no_multi_column_or_horizontal_scroll_layout():
    source = SOURCE.read_text()
    assert 'billing-scroll' not in source
    assert 'billing-columns' not in source
    assert 'overflow-x:auto' not in source
    assert 'grid-template-columns:repeat(var(--vm-column-count)' not in source


def test_card_uses_native_single_card_width():
    source = SOURCE.read_text()
    assert ':host{display:block;width:100%;min-width:0;max-width:100%;' in source
    assert '.billing-card{display:block;width:100%;min-width:0;max-width:100%;' in source
    assert '.billing-direction{display:block;width:100%;min-width:0}' in source
