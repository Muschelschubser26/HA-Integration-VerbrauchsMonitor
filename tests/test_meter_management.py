import json
from pathlib import Path
ROOT = Path(__file__).parents[1]
INTEGRATION = ROOT / "custom_components/verbrauchsmonitor"

def test_meter_management_uses_two_step_edit_flow():
    source = (INTEGRATION / "config_flow.py").read_text()
    assert "async_step_meter_edit" in source
    assert "_meter_select_schema" in source
    assert "previous_consumption_reading" in source
    assert "previous_feed_in_reading" in source
    assert "if contracts and not contract_id" in source
    assert 'errors["consumption_entity"] = "required"' in source

def test_meter_fields_are_translated_in_both_languages():
    required = {"name", "meter_number", "contract_id", "consumption_entity", "previous_consumption_reading", "feed_in_entity", "previous_feed_in_reading"}
    for language in ("de", "en"):
        data = json.loads((INTEGRATION / f"translations/{language}.json").read_text())
        fields = data["options"]["step"]["meter_edit"]["data"]
        assert required <= set(fields)
        assert all(fields[key] for key in required)

def test_manifest_revision():
    data = json.loads((INTEGRATION / "manifest.json").read_text())
    assert data["version"] == "0.0.1"

def test_meter_contract_is_required_and_selected_from_saved_contracts():
    source = (INTEGRATION / "config_flow.py").read_text()
    assert 'contract_options = [{"value": c["id"], "label": c.get("name", "Vertrag")} for c in contracts]' in source
    assert 'vol.Required("contract_id", default=data.get("contract_id"))' in source
    assert 'not any(c.get("id") == contract_id for c in contracts)' in source
