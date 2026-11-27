"""R128 tests for optional multi-direction feed-in orientation."""
import ast
from datetime import datetime, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys
import types

ROOT = Path(__file__).parents[1]
INTEGRATION = ROOT / "custom_components" / "verbrauchsmonitor"

_PACKAGE = "vm_r128_package"
_package = types.ModuleType(_PACKAGE)
_package.__path__ = [str(INTEGRATION)]
sys.modules.setdefault(_PACKAGE, _package)


def _load_model():
    name = f"{_PACKAGE}.forecast_model"
    if name in sys.modules:
        return sys.modules[name]
    spec = spec_from_file_location(name, INTEGRATION / "forecast_model.py")
    module = module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _load_orientation_helper():
    source = (INTEGRATION / "sensor.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_feed_in_orientations")
    module = ast.Module(body=[node], type_ignores=[])
    namespace = {}
    exec(compile(module, "sensor.py", "exec"), namespace)
    return namespace["_feed_in_orientations"]


def test_new_feed_in_meter_defaults_to_south_but_allows_empty_or_multiple_choices():
    source = (INTEGRATION / "config_flow.py").read_text(encoding="utf-8")
    block = source.split('if data.get("feed_in_entity"):', 1)[1].split('else:', 1)[0]
    assert 'else ["south"]' in block
    assert 'vol.Optional("feed_in_directions", default=selected_directions)' in block
    assert 'mode=selector.SelectSelectorMode.LIST' in block
    assert 'multiple=True' in block
    assert 'async_step_meter_feed_in_directions' in source
    direction_step = source.split('async def async_step_meter_feed_in_directions', 1)[1].split('def _meter_edit_schema', 1)[0]
    assert 'vol.Optional("feed_in_directions", default=["south"])' in direction_step
    assert 'raw or []' in direction_step
    assert 'async_step_meter_feed_in_orientation' not in source


def test_orientation_values_are_normalized_per_meter_and_empty_is_preserved():
    helper = _load_orientation_helper()
    assert helper({"feed_in_directions": ["east", "south", "east", "invalid"]}) == ["east", "south"]
    assert helper({"feed_in_directions": []}) == []
    assert helper({"feed_in_orientation": "west"}) == ["west"]
    assert helper({}) == []


def test_no_orientation_uses_neutral_four_direction_prior_not_implicit_south():
    model = _load_model()
    when = datetime(2026, 6, 21, 8, tzinfo=timezone.utc)
    no_selection = model.initial_profile_multiplier("feed_in", when, 53.5, 8.1, [])
    all_directions = model.initial_profile_multiplier("feed_in", when, 53.5, 8.1,
                                                       ["north", "east", "south", "west"])
    south_only = model.initial_profile_multiplier("feed_in", when, 53.5, 8.1, ["south"])
    assert no_selection == all_directions
    assert no_selection != south_only


def test_multiple_orientations_are_combined_without_inflating_the_scale():
    model = _load_model()
    when = datetime(2026, 6, 21, 8, tzinfo=timezone.utc)
    east = model.initial_profile_multiplier("feed_in", when, 53.5, 8.1, ["east"])
    east_west = model.initial_profile_multiplier("feed_in", when, 53.5, 8.1, ["east", "west"])
    assert east_west >= 0
    assert east_west < east


def test_feed_in_forecast_does_not_require_an_orientation_to_be_enabled():
    flow = (INTEGRATION / "config_flow.py").read_text(encoding="utf-8")
    sensor = (INTEGRATION / "sensor.py").read_text(encoding="utf-8")
    assert 'if meter.get("feed_in_entity"):' in flow
    assert 'meter.get("feed_in_entity") and f"{mid}|feed_in" in enabled' in flow
    assert 'and entry.data.get("forecast_feed_in_enabled", False)' in sensor
    assert 'entry.data.get("feed_in_orientation") in' not in sensor
