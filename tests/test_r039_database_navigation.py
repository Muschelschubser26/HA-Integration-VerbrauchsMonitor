from pathlib import Path
import json

ROOT = Path(__file__).parents[1]
INTEGRATION = ROOT / "custom_components/verbrauchsmonitor"

def test_database_is_removed_from_main_menu_and_has_two_actions():
    flow = (INTEGRATION / "config_flow.py").read_text(encoding="utf-8")
    assert 'menu_options=["contracts", "meters", "forecast", "billing", "data_management", "about"]' in flow
    assert 'menu_options=["database_optimize", "database_reset"]' in flow
    assert 'if selected == ["database"]:' in flow
    assert 'return await self.async_step_database()' in flow

def test_database_reset_keeps_confirmation_and_backup():
    flow = (INTEGRATION / "config_flow.py").read_text(encoding="utf-8")
    database = (INTEGRATION / "database.py").read_text(encoding="utf-8")
    assert "async_step_database_reset_confirm" in flow
    assert "reset_database" in flow
    assert "_create_backup(path, backup_path(hass))" in database

def test_translations_have_database_information_and_actions():
    for language in ("de", "en"):
        data = json.loads((INTEGRATION / f"translations/{language}.json").read_text())
        steps = data["options"]["step"]
        assert "database_info" in steps["database"]["description"]
        assert set(steps["database"]["menu_options"]) == {"database_optimize", "database_reset"}
