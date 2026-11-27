from pathlib import Path

ROOT = Path(__file__).parents[1]
INTEGRATION = ROOT / "custom_components/verbrauchsmonitor"


def test_static_card_is_served_without_cache_headers():
    source = (INTEGRATION / "frontend/__init__.py").read_text()
    assert "StaticPathConfig(CARD_URL.rsplit(\"/\", 1)[0], _CARD_PATH.parent, False)" in source


def test_card_asset_version_matches_revision():
    source = (INTEGRATION / "const.py").read_text()
    assert 'INTEGRATION_VERSION: Final = "0.0.1"' in source


def test_options_updates_keep_native_entry_reload():
    source = (INTEGRATION / "__init__.py").read_text()
    assert "entry.add_update_listener(async_reload_entry)" in source
    assert "await hass.config_entries.async_reload(entry.entry_id)" in source


def test_reload_document_distinguishes_frontend_and_python_changes():
    doc = (ROOT / "docs/UPDATE_UND_RELOAD.md").read_text()
    assert "Reload the dashboard/browser" in doc
    assert "Restart Home Assistant completely" in doc
