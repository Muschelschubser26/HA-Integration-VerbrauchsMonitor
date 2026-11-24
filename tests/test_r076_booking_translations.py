import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "verbrauchsmonitor"


def test_booking_management_field_labels_are_translated():
    expected = {
        "de": {"action": "Aktion", "selected": "Buchung auswählen"},
        "en": {"action": "Action", "selected": "Select booking"},
    }
    for language, labels in expected.items():
        data = json.loads((ROOT / "translations" / f"{language}.json").read_text())
        actual = data["options"]["step"]["billing_bookings"]["data"]
        assert actual == labels


def test_german_source_strings_match_german_translation_for_booking_fields():
    source = json.loads((ROOT / "strings.json").read_text())
    german = json.loads((ROOT / "translations" / "de.json").read_text())
    assert source["options"]["step"]["billing_bookings"]["data"] == german["options"]["step"]["billing_bookings"]["data"]
