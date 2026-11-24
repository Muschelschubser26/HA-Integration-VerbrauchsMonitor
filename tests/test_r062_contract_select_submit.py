import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRANSLATIONS = ROOT / "custom_components" / "verbrauchsmonitor" / "translations"


def test_contract_select_has_explicit_continue_label_in_all_languages():
    expected = {"de.json": "Weiter", "en.json": "Next"}
    for filename, label in expected.items():
        data = json.loads((TRANSLATIONS / filename).read_text())
        assert data["options"]["step"]["contract_select"]["submit"] == label


def test_contract_select_submit_label_is_consistent_with_strings_json():
    strings = json.loads((ROOT / "custom_components" / "verbrauchsmonitor" / "strings.json").read_text())
    translations = json.loads((TRANSLATIONS / "de.json").read_text())
    assert strings["options"]["step"]["contract_select"]["submit"] == "Weiter"
    assert translations["options"]["step"]["contract_select"]["submit"] == "Weiter"
