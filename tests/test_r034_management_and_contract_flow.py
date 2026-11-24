import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
INTEGRATION = ROOT / "custom_components/verbrauchsmonitor"

def test_management_menu_order_and_labels():
    source = (INTEGRATION / "config_flow.py").read_text()
    assert 'menu_options=["contracts", "meters", "forecast", "billing", "data_management", "about"]' in source
    for lang in ("de", "en"):
        data = json.loads((INTEGRATION / f"translations/{lang}.json").read_text())
        menu = data["options"]["step"]["init"]["menu_options"]
        assert list(menu) == ["contracts", "meters", "forecast", "billing", "data_management", "about"]
    assert json.loads((INTEGRATION / "translations/de.json").read_text())["options"]["step"]["init"]["menu_options"]["billing"] == "Abrechnungen und Abschläge"

def test_contract_selection_is_hidden_until_edit_or_delete():
    source = (INTEGRATION / "config_flow.py").read_text()
    assert "self._contract_action = action" in source
    assert "async_step_contract_select" in source
    assert "async_step_contract_delete_confirm" in source

def test_contract_flow_has_traceback_logging_and_non_destructive_error_display():
    source = (INTEGRATION / "config_flow.py").read_text()
    assert "async_step_contract_wizard_identity" in source and "async_step_contract_wizard_prices" in source
    assert 'errors={"base": "contract_flow_internal_error"}' in source

def test_database_menu_and_reset_scopes_are_separate():
    source = (INTEGRATION / "config_flow.py").read_text()
    assert 'menu_options=["database_optimize", "database_reset"]' in source
    assert "database_info" in source
    assert 'async_step_data_management_confirm' in source
    assert '"contracts", "meters", "billing", "forecasts", "database"' in source
    assert "reset_database" in source

def test_reset_database_creates_backup_before_removing_data():
    source = (INTEGRATION / "database.py").read_text()
    block = source.split("def reset_database", 1)[1]
    assert "shutil.copy2(path, backup)" in block
    assert "path.unlink()" in block

def test_billing_card_has_inline_contract_edit_controls_and_service():
    card = (INTEGRATION / "frontend/verbrauchsmonitor-card.js").read_text()
    integration = (INTEGRATION / "__init__.py").read_text()
    assert 'class="toggle-edit"' in card
    assert 'form.contract-edit' in card
    assert 'callService("verbrauchsmonitor","update_contract"' in card
    assert 'async_register(DOMAIN, "update_contract"' in integration
    assert 'previous_feed_in_reading' in card
    assert 'previous_consumption_reading' in card
    assert 'data-meter="${esc(selectedId)}"' in card
