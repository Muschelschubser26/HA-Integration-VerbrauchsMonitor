from pathlib import Path
import ast

ROOT = Path(__file__).parents[1]
SOURCE = ROOT / "custom_components/verbrauchsmonitor/registry_cleanup.py"

def _load_expected_helper():
    tree = ast.parse(SOURCE.read_text())
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "expected_sensor_unique_ids")
    module = ast.Module(body=[node], type_ignores=[])
    namespace = {"ROLE_CONFIG": {
        "consumption_entity": ("consumption_counter", "", ""),
        "consumption_power_entity": ("consumption_power", "", ""),
        "feed_in_entity": ("feed_in_counter", "", ""),
        "feed_in_power_entity": ("feed_in_power", "", ""),
        "outdoor_illuminance_entity": ("outdoor_illuminance", "", ""),
    }, "CONF_OUTDOOR_ILLUMINANCE_ENTITY": "outdoor_illuminance_entity", "slugify_meter_name": lambda value: value.lower().replace(" ", "_")}
    exec(compile(module, str(SOURCE), "exec"), namespace)
    return namespace["expected_sensor_unique_ids"]

def test_expected_ids_follow_configured_meter_and_optional_sources():
    helper = _load_expected_helper()
    options = {"meters": [{"id": "meter-a", "name": "Haus Verbrauch", "consumption_entity": "sensor.energy", "feed_in_entity": "sensor.export"}]}
    expected = helper(options, "hub")
    assert "meter-a_haus_verbrauch_verbrauch_kontostand" in expected
    assert "meter-a_haus_verbrauch_einspeisung_kontostand" in expected
    assert "meter-a_haus_verbrauch_total_kontostand" not in expected
    assert "meter-a_consumption_counter" in expected
    assert "meter-a_feed_in_counter" in expected
    assert "meter-a_outdoor_illuminance" not in expected

def test_removed_feed_in_and_renamed_meter_do_not_keep_old_ids():
    helper = _load_expected_helper()
    options = {"meters": [{"id": "meter-a", "name": "Verbrauch", "consumption_entity": "sensor.energy"}]}
    expected = helper(options, "hub")
    assert "meter-a_1234_einspeisung_kontostand" not in expected
    assert "meter-a_verbrauch_einspeisung_kontostand" not in expected


def test_central_brightness_registry_id_is_expected():
    helper = _load_expected_helper()
    expected = helper({"outdoor_illuminance_entity": "sensor.brightness", "meters": []}, "hub")
    assert "hub_outdoor_illuminance" not in expected


def test_enabled_forecast_entities_are_preserved_by_registry_cleanup():
    helper = _load_expected_helper()
    options = {"meters": [{
        "id": "meter-a", "name": "Haus Verbrauch",
        "consumption_entity": "sensor.energy",
        "feed_in_entity": "sensor.export",
        "forecast_consumption_enabled": True,
        "forecast_feed_in_enabled": True,
    }]}
    expected = helper(options, "hub")
    assert "meter-a_consumption_prognose_annual_balance" in expected
    assert "meter-a_consumption_prognose_monthly_advance" in expected
    assert "meter-a_feed_in_prognose_annual_balance" in expected
    assert "meter-a_feed_in_prognose_monthly_advance" in expected


def test_disabled_or_unconfigured_forecasts_are_not_kept_in_registry():
    helper = _load_expected_helper()
    options = {"meters": [{
        "id": "meter-a", "name": "Haus Verbrauch",
        "consumption_entity": "sensor.energy",
        "feed_in_entity": "sensor.export",
        "forecast_consumption_enabled": False,
        "forecast_feed_in_enabled": False,
    }]}
    expected = helper(options, "hub")
    assert not any("_consumption_prognose_" in item for item in expected)
    assert not any("_feed_in_prognose_" in item for item in expected)


def test_consumption_forecast_defaults_to_enabled_for_legacy_meter_options():
    helper = _load_expected_helper()
    options = {"meters": [{"id": "meter-a", "name": "Haus Verbrauch", "consumption_entity": "sensor.energy"}]}
    expected = helper(options, "hub")
    assert "meter-a_consumption_prognose_annual_balance" in expected
    assert "meter-a_consumption_prognose_monthly_advance" in expected


def test_active_forecast_entity_ids_have_canonical_registry_targets():
    tree = ast.parse(SOURCE.read_text())
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "expected_entity_ids")
    module = ast.Module(body=[node], type_ignores=[])
    namespace = {
        "ROLE_CONFIG": {
            "consumption_entity": ("consumption_counter", "", ""),
            "feed_in_entity": ("feed_in_counter", "", ""),
        },
        "slugify_meter_name": lambda value: value.lower().replace(" ", "_"),
        "meter_entity_object_ids": lambda value: {
            "consumption_counter": "verbrauchsmonitor_haus_verbrauch_verbrauch_zaehlerstand",
            "feed_in_counter": "verbrauchsmonitor_haus_verbrauch_einspeisung_zaehlerstand",
            "consumption_balance": "verbrauchsmonitor_haus_verbrauch_verbrauch_kontostand",
            "feed_in_balance": "verbrauchsmonitor_haus_verbrauch_einspeisung_kontostand",
        },
    }
    exec(compile(module, str(SOURCE), "exec"), namespace)
    result = namespace["expected_entity_ids"]({"meters": [{
        "id": "meter-a", "name": "Haus Verbrauch",
        "consumption_entity": "sensor.energy", "feed_in_entity": "sensor.export",
        "forecast_consumption_enabled": True, "forecast_feed_in_enabled": True,
    }]})
    assert result["meter-a_consumption_prognose_annual_balance"] == "sensor.verbrauchsmonitor_haus_verbrauch_consumption_prognose_annual_balance"
    assert result["meter-a_consumption_prognose_monthly_advance"] == "sensor.verbrauchsmonitor_haus_verbrauch_consumption_prognose_monthly_advance"
    assert result["meter-a_feed_in_prognose_annual_balance"] == "sensor.verbrauchsmonitor_haus_verbrauch_feed_in_prognose_annual_balance"
    assert result["meter-a_feed_in_prognose_monthly_advance"] == "sensor.verbrauchsmonitor_haus_verbrauch_feed_in_prognose_monthly_advance"
