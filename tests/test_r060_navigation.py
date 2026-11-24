from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
FLOW = ROOT / "custom_components/verbrauchsmonitor/config_flow.py"
STRINGS = ROOT / "custom_components/verbrauchsmonitor/strings.json"

def test_main_menu_keeps_existing_grouped_navigation():
    source = FLOW.read_text()
    expected = 'menu_options=["contracts", "meters", "forecast", "billing", "data_management", "about"]'
    assert expected in source

def test_database_is_reached_through_data_management():
    source = FLOW.read_text()
    assert 'if selected == ["database"]:' in source
    assert 'return await self.async_step_database()' in source

def test_database_menu_has_explicit_actions():
    import json
    data = json.loads(STRINGS.read_text())
    options = data["options"]["step"]["database"]["menu_options"]
    assert "database_optimize" in options
    assert "database_reset" in options

def test_navigation_uses_native_home_assistant_flow():
    source = FLOW.read_text()
    assert "class VerbrauchsMonitorOptionsFlow(config_entries.OptionsFlow)" in source
    assert "async_show_menu" in source
    assert 'description_placeholders={"revision": "R111"}' in source
