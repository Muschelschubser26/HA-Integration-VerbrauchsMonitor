from pathlib import Path
import json


ROOT = Path(__file__).parents[1] / "custom_components" / "verbrauchsmonitor"


def test_brightness_is_not_a_meter_role():
    const = (ROOT / "const.py").read_text()
    assert 'CONF_OUTDOOR_ILLUMINANCE_ENTITY: ("outdoor_illuminance"' not in const


def test_additional_values_menu_is_temporarily_removed_without_deleting_legacy_data():
    flow = (ROOT / "config_flow.py").read_text()
    assert '"additional_values"' not in flow
    assert "outdoor_illuminance_entity" in flow


def test_dashboard_has_no_about_block():
    card = (ROOT / "frontend" / "verbrauchsmonitor-card.js").read_text()
    assert "Über VerbrauchsMonitor" not in card
    assert "mailto:Support@gehtdoch.eu" not in card


def test_brightness_is_rendered_as_global_value():
    card = (ROOT / "frontend" / "verbrauchsmonitor-card.js").read_text()
    assert 'state.attributes.vm_role === "outdoor_illuminance"' in card
    assert 'meterIndex === 0 && brightness' in card


def test_german_and_english_have_additional_values_translation():
    for filename in ("de.json", "en.json"):
        data = json.loads((ROOT / "translations" / filename).read_text())
        assert "additional_values" not in data["options"]["step"]["init"]["menu_options"]
