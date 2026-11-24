import json
from pathlib import Path
ROOT = Path(__file__).parents[1]
INTEGRATION = ROOT / "custom_components/verbrauchsmonitor"

def test_manifest_metadata():
    manifest = json.loads((INTEGRATION / "manifest.json").read_text())
    assert manifest["domain"] == "verbrauchsmonitor"
    assert manifest["version"] == "0.0.2"
    assert manifest["config_flow"] is True

def test_central_translated_management_sections():
    for language in ("de", "en"):
        data = json.loads((INTEGRATION / f"translations/{language}.json").read_text())
        menu = data["options"]["step"]["init"]["menu_options"]
        assert list(menu) == ["contracts", "meters", "forecast", "billing", "data_management", "about"]
        assert menu["billing"] in ("Abrechnungen und Abschläge", "Bills and advances")
        assert "selected" in data["options"]["step"]["meters"]["data"]
        assert "previous_consumption_reading" in data["options"]["step"]["meter_edit"]["data"]
        assert "previous_feed_in_reading" in data["options"]["step"]["meter_edit"]["data"]
        for step in ("contracts", "meters", "billing"):
            assert data["options"]["step"][step]["data"]

def test_central_config_flow_and_legacy_migration():
    source = (INTEGRATION / "config_flow.py").read_text()
    init = (ROOT / "custom_components/verbrauchsmonitor/__init__.py").read_text()
    assert 'async_create_entry(title="VerbrauchsMonitor", data={})' in source
    assert 'menu_options=["contracts", "meters", "forecast", "billing", "data_management", "about"]' in source
    assert "async_migrate_entry" in init and "legacy_meter" in init

def test_card_has_balance_tiles_and_support_link():
    source = (INTEGRATION / "frontend/verbrauchsmonitor-card.js").read_text()
    for term in ("consumption_balance", "feed_in_balance"):
        assert term in source

def test_database_services_are_registered():
    source = (ROOT / "custom_components/verbrauchsmonitor/__init__.py").read_text()
    for service in ("database_status", "database_optimize", "database_export", "database_import"):
        assert f'async_register(DOMAIN, "{service}"' in source

def test_brightness_is_independent_of_feed_in():
    source = (INTEGRATION / "sensor.py").read_text()
    assert "CONF_OUTDOOR_ILLUMINANCE_ENTITY" in source
    assert "if config_key == CONF_OUTDOOR_ILLUMINANCE_ENTITY and not has_feed_in" not in source


def test_card_has_no_about_block_or_database_actions():
    card = (INTEGRATION / "frontend" / "verbrauchsmonitor-card.js").read_text(encoding="utf-8")
    assert "Über VerbrauchsMonitor" not in card
    assert "Muschelschubser26 & ChatGPT" not in card
    assert 'mailto:Support@gehtdoch.eu' not in card
    assert 'data-service="database_' not in card
    assert 'class="database"' not in card


def test_database_and_booking_management_are_in_options_flow():
    flow = (INTEGRATION / "config_flow.py").read_text(encoding="utf-8")
    assert "async_step_database" in flow
    assert "database_optimize" in flow
    assert "async_step_booking_edit" in flow
    assert "_booking_schema" in flow


def test_about_dialog_returns_to_menu_without_saving_options():
    source = (INTEGRATION / "config_flow.py").read_text(encoding="utf-8")
    about = source.split("async def async_step_about", 1)[1]
    assert "if user_input is not None:" in about
    assert 'self.async_show_menu(step_id="init"' in about
    assert "self.async_create_entry(" not in about
