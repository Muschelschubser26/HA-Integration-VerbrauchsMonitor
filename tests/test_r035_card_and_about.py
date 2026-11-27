from pathlib import Path
import json

ROOT = Path(__file__).parents[1]
INTEGRATION = ROOT / "custom_components/verbrauchsmonitor"

def test_card_edit_is_single_column_and_contains_baseline_fields():
    source = (INTEGRATION / "frontend/verbrauchsmonitor-card.js").read_text()
    assert ".contract-edit{display:grid;grid-template-columns:minmax(0,1fr)" in source
    assert 'meter_changes' in source
    assert 'Zählerwechsel hinzufügen' in source
    assert 'Endzählerstand korrigieren (kWh)' not in source
    assert "meter_id:form.dataset.meter" in source

def test_about_dialog_includes_revision_placeholder():
    for name in ("strings.json", "translations/de.json", "translations/en.json"):
        data = json.loads((INTEGRATION / name).read_text())
        description = data["options"]["step"]["about"]["description"]
        assert "Revision: {revision}" in description
    flow = (INTEGRATION / "config_flow.py").read_text()
    assert 'description_placeholders={"revision": RELEASE_REVISION, "version": RELEASE_VERSION, "stage": RELEASE_STAGE}' in flow

def test_revision_metadata_is_consistent():
    const = (INTEGRATION / "const.py").read_text()
    assert 'INTEGRATION_VERSION: Final = "0.0.1"' in const
    readme = (ROOT / "README.md").read_text()
    assert "forecast" in readme.lower()
