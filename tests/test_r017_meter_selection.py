from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components/verbrauchsmonitor"


def test_meter_action_schema_only_adds_selector_for_edit_delete():
    source = (INTEGRATION / "config_flow.py").read_text(encoding="utf-8")
    schema = source.split("def _meter_select_schema", 1)[1].split("async def async_step_meter_edit", 1)[0]
    assert 'vol.Required("action"' in schema
    assert 'if action in ("edit", "delete") and meters:' in schema
    assert 'vol.Required("selected", default=options[0]["value"])' in schema


def test_new_meter_goes_directly_to_meter_wizard():
    source = (INTEGRATION / "config_flow.py").read_text(encoding="utf-8")
    block = source.split("async def async_step_meters", 1)[1].split("def _meter_select_schema", 1)[0]
    assert 'if action == "new":' in block
    assert "return await self.async_step_meter_edit()" in block


def test_old_separate_meter_selection_step_is_removed():
    source = (INTEGRATION / "config_flow.py").read_text(encoding="utf-8")
    assert "async def async_step_meter_select" not in source
    assert 'step_id="meter_select"' not in source
    assert 'selected = user_input.get("selected")' in source


def test_meter_step_translations_keep_next_and_finish_labels():
    for lang, next_label, finish_label in (("de", "Weiter", "Fertigstellen"), ("en", "Next", "Finish")):
        data = json.loads((INTEGRATION / "translations" / f"{lang}.json").read_text(encoding="utf-8"))
        steps = data["options"]["step"]
        assert steps["meters"]["submit"] == next_label
        assert steps["meter_edit"]["submit"] == finish_label
