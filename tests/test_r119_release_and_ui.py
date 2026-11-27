import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
INTEGRATION = ROOT / "custom_components/verbrauchsmonitor"


def test_release_metadata_is_centralized_for_prod_001():
    const = (INTEGRATION / "const.py").read_text()
    flow = (INTEGRATION / "config_flow.py").read_text()
    card = (INTEGRATION / "frontend/verbrauchsmonitor-card.js").read_text()
    readme = (ROOT / "README.md").read_text()
    assert 'RELEASE_VERSION: Final = "0.0.1"' in const
    assert 'RELEASE_STAGE: Final = "Prod"' in const
    assert 'RELEASE_REVISION: Final = "R0171"' in const
    assert 'INTEGRATION_VERSION: Final = "0.0.1"' in const
    assert 'description_placeholders={"revision": RELEASE_REVISION, "version": RELEASE_VERSION, "stage": RELEASE_STAGE}' in flow
    assert "v0.0.1 Prod R0171" in card and "**Produktivversion:** `0.0.1`" in readme


def test_database_is_a_direct_navigation_item_not_a_reset_checkbox():
    flow = (INTEGRATION / "config_flow.py").read_text()
    assert 'menu_options=["reset_data", "recorder_entities", "database"]' in flow
    reset_schema = flow.split("def _reset_schema", 1)[1].split("async def async_step_forecast_reset_select", 1)[0]
    assert 'vol.Optional("database"' not in reset_schema
    assert 'selected = [key for key in ("contracts", "meters", "billing", "forecasts", "periods")' in flow


def test_about_translation_uses_release_placeholders_in_both_languages():
    for language in ("de", "en"):
        data = json.loads((INTEGRATION / f"translations/{language}.json").read_text())
        about = data["options"]["step"]["about"]["description"]
        assert "Version {version} – {stage}" in about
        assert "Revision: {revision}" in about


def test_current_power_is_rendered_below_meter_reading_only_when_available():
    card = (INTEGRATION / "frontend/verbrauchsmonitor-card.js").read_text()
    assert 't(isFeed?"Aktuelle Einspeisung":"Aktueller Verbrauch"' in card
    assert '} Watt</strong>' in card
    assert 'if (!valid(power)) return \"\";' in card
    assert 'hasValue(power)' not in card


def test_direction_form_does_not_use_uuid_as_field_name_or_legacy_meter_editor_field():
    flow = (INTEGRATION / "config_flow.py").read_text()
    meter_editor = flow.split("def _meter_edit_schema", 1)[1].split("def _current_season", 1)[0]
    forecast = flow.split("async def async_step_forecast", 1)[1].split("async def async_step_billing", 1)[0]
    assert 'vol.Optional("compass_directions"' not in meter_editor
    assert 'vol.Optional("feed_in_directions", default=selected_directions)' in meter_editor
    assert 'mode=selector.SelectSelectorMode.LIST' in meter_editor
    assert 'multiple=True' in meter_editor
    assert 'else ["south"]' in meter_editor
    assert 'if meter.get("feed_in_entity"):' in forecast
    assert 'meter.get("feed_in_orientation") in' not in forecast



def test_forecast_entities_do_not_register_removed_reliability_callback():
    sensor = (INTEGRATION / "sensor.py").read_text()
    assert "_periodic_reliability_update" not in sensor
    assert "self._periodic_hourly_learning" in sensor
    assert "self._periodic_refresh" in sensor


def test_billing_card_power_entities_are_defined_in_render_scope():
    card = (INTEGRATION / "frontend/verbrauchsmonitor-card.js").read_text()
    billing = card.split("class VerbrauchsMonitorBillingCard", 1)[1]
    render = billing.split("render() {", 1)[1]
    assert 'const consumptionPower = get("consumption_power");' in render
    assert 'const feedPower = get("feed_in_power");' in render
    assert "const power = isFeed ? feedPower : consumptionPower" in render
