from pathlib import Path


def _source():
    return (Path(__file__).parents[1] / "custom_components/verbrauchsmonitor/frontend/verbrauchsmonitor-card.js").read_text()


def test_billing_card_uses_normal_full_available_card_width():
    source = _source()
    assert ':host{display:block;width:100%;min-width:0;max-width:100%;' in source
    assert '.billing-card{display:block;width:100%;min-width:0;max-width:100%;' in source
    assert 'overflow-x:auto' not in source


def test_editor_explains_separate_cards_for_readings():
    source = _source()
    assert 'Eine Karte zeigt genau einen Zählerstand' in source
    assert 'id="direction"' in source
