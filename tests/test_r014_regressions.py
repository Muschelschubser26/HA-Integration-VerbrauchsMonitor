import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "verbrauchsmonitor"

def test_options_flow_returns_full_options_and_explicitly_persists():
    source = (INTEGRATION / "config_flow.py").read_text(encoding="utf-8")
    assert "async_update_entry(" not in source
    assert "return self.async_create_entry(title=\"\", data=options)" in source

def test_options_changes_reload_integration():
    source = (INTEGRATION / "__init__.py").read_text(encoding="utf-8")
    assert "add_update_listener(async_reload_entry)" in source
    assert "async_reload(entry.entry_id)" in source

def test_card_is_present_and_renders_all_balances():
    card = (INTEGRATION / "frontend" / "verbrauchsmonitor-card.js").read_text(encoding="utf-8")
    assert "verbrauchsmonitor-card" in card
    assert "consumption_balance" in card
    assert "feed_in_balance" in card
    assert "total_balance" not in card
    assert "Offener Betrag" in card and "Aktuelles Guthaben" in card

def test_balance_sensors_have_meter_grouping_metadata():
    source = (INTEGRATION / "sensor.py").read_text(encoding="utf-8")
    assert '"meter_number": entry.data.get(CONF_METER_NUMBER)' in source
    assert '"contract_name": entry.data.get(CONF_CONTRACT_NAME)' in source

def test_manifest_version_matches_release():
    manifest = json.loads((INTEGRATION / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["version"] == "0.0.2"
