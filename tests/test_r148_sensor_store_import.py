"""Regression tests for persistent sensor learning-store initialization."""
import ast
from pathlib import Path

ROOT = Path(__file__).parents[1]
SENSOR = ROOT / "custom_components" / "verbrauchsmonitor" / "sensor.py"


def test_store_is_imported_at_sensor_module_scope():
    tree = ast.parse(SENSOR.read_text(encoding="utf-8"))
    assert any(
        isinstance(node, ast.ImportFrom)
        and node.module == "homeassistant.helpers.storage"
        and any(alias.name == "Store" for alias in node.names)
        for node in tree.body
    ), "Store must be imported before forecast entities initialize their learning store"


def test_learning_store_constructor_is_available_to_sensor_lifecycle():
    source = SENSOR.read_text(encoding="utf-8")
    assert "self._learning_store = Store(" in source
    assert "await self._learning_store.async_load()" in source
