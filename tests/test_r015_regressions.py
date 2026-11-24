import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "verbrauchsmonitor"

def test_sensor_imports_consumption_entity_constant():
    source = (INTEGRATION / "sensor.py").read_text(encoding="utf-8")
    assert "CONF_CONSUMPTION_ENTITY," in source

def test_balance_sensors_use_suggested_object_id():
    source = (INTEGRATION / "sensor.py").read_text(encoding="utf-8")
    assert "self._attr_suggested_object_id = object_id" in source

def test_options_flow_commits_payload_without_midflow_update():
    source = (INTEGRATION / "config_flow.py").read_text(encoding="utf-8")
    save = source.split("async def _save", 1)[1].split("async def async_step_contracts", 1)[0]
    assert 'return self.async_create_entry(title="", data=options)' in save
    assert "self.hass.config_entries.async_update_entry(" not in save

def test_contract_dates_can_be_cleared_or_updated():
    source = (INTEGRATION / "config_flow.py").read_text(encoding="utf-8")
    assert 'identity[date_key] = user_input.get(date_key) or None' in source
    assert 'identity[date_key] = user_input.get(date_key) or None' in source

def test_optional_meter_entities_can_be_cleared():
    source = (INTEGRATION / "config_flow.py").read_text(encoding="utf-8")
    assert 'item = _apply_optional_entities(item, old, user_input)' in source
    assert 'def _apply_optional_entities(item, old, user_input):' in source

def test_dashboard_card_and_balance_roles_are_present():
    card = (INTEGRATION / "frontend" / "verbrauchsmonitor-card.js").read_text(encoding="utf-8")
    assert 'customElements.define("verbrauchsmonitor-card"' in card
    for role in ("consumption_balance", "feed_in_balance"):
        assert role in card
