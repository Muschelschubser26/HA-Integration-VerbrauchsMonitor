from pathlib import Path
import ast

ROOT = Path(__file__).parents[1]
SOURCE = ROOT / "custom_components/verbrauchsmonitor/config_flow.py"

def _load_helper():
    tree = ast.parse(SOURCE.read_text())
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_apply_optional_entities")
    module = ast.Module(body=[node], type_ignores=[])
    namespace = {}
    exec(compile(module, str(SOURCE), "exec"), namespace)
    return namespace["_apply_optional_entities"]

def test_explicitly_cleared_feed_in_entities_and_baseline_are_removed():
    apply = _load_helper()
    old = {"feed_in_entity": "sensor.feed_total", "feed_in_power_entity": "sensor.feed_power", "previous_feed_in_reading": 123.4}
    item = apply(dict(old), old, {"feed_in_entity": None, "feed_in_power_entity": None})
    assert "feed_in_entity" not in item
    assert "feed_in_power_entity" not in item
    assert "previous_feed_in_reading" not in item

def test_individual_optional_sources_can_be_cleared_without_affecting_others():
    apply = _load_helper()
    old = {"consumption_power_entity": "sensor.load_power", "feed_in_entity": "sensor.feed_total", "feed_in_power_entity": "sensor.feed_power", "outdoor_illuminance_entity": "sensor.lux"}
    item = apply(dict(old), old, {"feed_in_power_entity": None, "outdoor_illuminance_entity": None})
    assert item["consumption_power_entity"] == "sensor.load_power"
    assert item["feed_in_entity"] == "sensor.feed_total"
    assert "feed_in_power_entity" not in item
    assert "outdoor_illuminance_entity" not in item

def test_untouched_optional_sources_are_preserved_and_legacy_switches_removed():
    apply = _load_helper()
    old = {"feed_in_entity": "sensor.feed_total", "feed_in_power_entity": "sensor.feed_power", "use_feed_in_counter": True}
    item = apply(dict(old), old, {})
    assert item["feed_in_entity"] == "sensor.feed_total"
    assert item["feed_in_power_entity"] == "sensor.feed_power"
    assert "use_feed_in_counter" not in item

def test_none_string_is_never_saved_as_entity_id():
    apply = _load_helper()
    old = {"feed_in_entity": "sensor.feed_total"}
    item = apply(dict(old), old, {"feed_in_entity": "None"})
    assert "feed_in_entity" not in item
