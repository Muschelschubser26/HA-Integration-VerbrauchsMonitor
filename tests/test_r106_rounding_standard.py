"""Standard regression checks for ROUND_HALF_UP monetary rounding."""
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]


def _extract_format_amount_de():
    source = (ROOT / "custom_components/verbrauchsmonitor/config_flow.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    node = next(item for item in tree.body if isinstance(item, ast.FunctionDef) and item.name == "format_amount_de")
    module = ast.Module(body=[node], type_ignores=[])
    namespace = {"Decimal": Decimal, "ROUND_HALF_UP": ROUND_HALF_UP}
    exec(compile(module, "config_flow.py::format_amount_de", "exec"), namespace)
    return namespace["format_amount_de"]


def test_display_money_uses_half_up_at_positive_and_negative_half_cent_boundaries():
    formatter = _extract_format_amount_de()
    assert formatter("1.005") == "1,01"
    assert formatter("2.675") == "2,68"
    assert formatter("-1.005") == "-1,01"


def test_all_monetary_quantize_calls_use_explicit_half_up_rounding():
    package = ROOT / "custom_components/verbrauchsmonitor"
    for path in package.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute) or node.func.attr != "quantize":
                continue
            assert any(keyword.arg == "rounding" for keyword in node.keywords), (
                f"{path.relative_to(ROOT)}:{node.lineno}: quantize() ohne explizite Rundungsregel"
            )


def test_sensor_future_advance_rounding_is_explicit_half_up():
    source = (ROOT / "custom_components/verbrauchsmonitor/sensor.py").read_text(encoding="utf-8")
    assert 'remaining_schedule.quantize(_Decimal("0.01"), rounding=ROUND_HALF_UP)' in source
