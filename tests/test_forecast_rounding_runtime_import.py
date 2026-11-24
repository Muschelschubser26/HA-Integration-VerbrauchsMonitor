"""Regression coverage for forecast runtime rounding dependencies."""
import ast
from pathlib import Path

ROOT = Path(__file__).parents[1]
SENSOR_PATH = ROOT / "custom_components" / "verbrauchsmonitor" / "sensor.py"


def test_forecast_native_value_rounding_constant_is_imported_at_module_scope():
    """Forecast native_value must not fail with NameError during HA updates."""
    tree = ast.parse(SENSOR_PATH.read_text(encoding="utf-8"))
    module_imports_rounding = False
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == "decimal":
            module_imports_rounding |= any(alias.name == "ROUND_HALF_UP" for alias in node.names)
    assert module_imports_rounding, "ROUND_HALF_UP must be available in sensor module scope"


def test_forecast_sensor_uses_the_module_scope_rounding_constant():
    """The future-advance attribute calculation references the shared import."""
    source = SENSOR_PATH.read_text(encoding="utf-8")
    assert 'remaining_schedule.quantize(_Decimal("0.01"), rounding=ROUND_HALF_UP)' in source
