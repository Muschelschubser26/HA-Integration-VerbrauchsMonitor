"""R125 regressions for non-blocking forecast entity state updates."""
import ast
from pathlib import Path

ROOT = Path(__file__).parents[1]
SENSOR = ROOT / "custom_components" / "verbrauchsmonitor" / "sensor.py"

def _forecast_class():
    tree = ast.parse(SENSOR.read_text(encoding="utf-8"))
    return next(node for node in tree.body if isinstance(node, ast.ClassDef)
                and node.name == "VerbrauchsMonitorForecastSensor")

def test_native_value_is_a_constant_time_cached_property():
    cls = _forecast_class()
    prop = next(node for node in cls.body if isinstance(node, ast.FunctionDef)
                and node.name == "native_value")
    assert len(prop.body) == 2  # docstring + cached attribute return
    assert isinstance(prop.body[-1], ast.Return)
    assert isinstance(prop.body[-1].value, ast.Attribute)
    assert prop.body[-1].value.attr == "_cached_native_value"

def test_expensive_forecast_calculation_runs_in_executor():
    cls = _forecast_class()
    method = next(node for node in cls.body if isinstance(node, ast.AsyncFunctionDef)
                  and node.name == "_async_refresh_forecast_value")
    source = ast.get_source_segment(SENSOR.read_text(encoding="utf-8"), method)
    assert "async_add_executor_job" in source
    assert "partial(calculate_forecast, **forecast_args)" in source
    assert "calculate_forecast(" not in source

def test_source_and_season_callbacks_schedule_cached_forecast_refresh():
    cls = _forecast_class()
    methods = {node.name: node for node in cls.body
               if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    for name in ("_changed", "_periodic_season_refresh"):
        source = ast.get_source_segment(SENSOR.read_text(encoding="utf-8"), methods[name])
        assert "_async_refresh_forecast_and_write" in source

def test_forecast_refresh_is_serialized_and_cache_is_initialized():
    source = SENSOR.read_text(encoding="utf-8")
    assert "self._cached_native_value = None" in source
    assert "self._forecast_refresh_lock = asyncio.Lock()" in source
    method = next(node for node in _forecast_class().body
                  if isinstance(node, ast.AsyncFunctionDef)
                  and node.name == "_async_refresh_forecast_value")
    assert any(isinstance(node, ast.AsyncWith) for node in ast.walk(method))
