import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "verbrauchsmonitor"


def test_recorder_entity_export_navigation_and_registry_source():
    source = (INTEGRATION / "config_flow.py").read_text(encoding="utf-8")
    assert 'menu_options=["reset_data", "recorder_entities", "database"]' in source
    assert 'menu_options=["recorder_entities_plain", "recorder_entities_include"]' in source
    assert "consumption_month" in source
    assert "feed_in_month" in source
    assert "verbrauch_jahresbilanz_prognose" in source
    assert "einspeisung_jahresbilanz_prognose" in source
    assert "External source entities" in source
    assert 'selector.TextSelectorConfig(multiline=True)' in source
    assert '      # note: {topic}' in source
    assert '      - {entity_id}' in source
    assert 'content = "\\n".join(lines)' in source
    assert '########################' in source


def test_recorder_entity_export_translations_are_complete():
    de = json.loads((INTEGRATION / "translations" / "de.json").read_text(encoding="utf-8"))
    en = json.loads((INTEGRATION / "translations" / "en.json").read_text(encoding="utf-8"))
    keys = ("data_management", "recorder_entities", "recorder_entities_plain", "recorder_entities_include")
    for key in keys:
        assert key in de["options"]["step"]
        assert key in en["options"]["step"]
    assert de["options"]["step"]["data_management"]["menu_options"]["recorder_entities"] == "Verwendet Recorder – Entitäten"
