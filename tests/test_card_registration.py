from pathlib import Path

ROOT = Path(__file__).parents[1]
INTEGRATION = ROOT / "custom_components/verbrauchsmonitor"

def test_card_asset_is_packaged():
    card = INTEGRATION / "frontend/verbrauchsmonitor-card.js"
    assert card.is_file() and card.stat().st_size > 1000
    source = card.read_text()
    assert 'customElements.define("verbrauchsmonitor-card"' in source
    assert 'window.customCards.push' in source

def test_card_registration_on_both_setup_paths():
    init = (INTEGRATION / "__init__.py").read_text()
    assert "await async_register_card(hass)" in init
    assert init.count("await async_register_card(hass)") >= 2

def test_card_resource_path_and_balance_values():
    const = (INTEGRATION / "const.py").read_text()
    card = (INTEGRATION / "frontend/verbrauchsmonitor-card.js").read_text()
    assert '"/verbrauchsmonitor/verbrauchsmonitor-card.js"' in const
    for role in ("consumption_balance", "feed_in_balance"):
        assert role in card
