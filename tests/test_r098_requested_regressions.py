"""Regression coverage for R098 user-requested tariff and forecast UI fixes."""
import ast
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).parents[1]
FLOW = ROOT / "custom_components/verbrauchsmonitor/config_flow.py"
CARD = ROOT / "custom_components/verbrauchsmonitor/frontend/verbrauchsmonitor-card.js"
SENSOR = ROOT / "custom_components/verbrauchsmonitor/sensor.py"


def _function(name):
    tree = ast.parse(FLOW.read_text())
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    ns = {"Decimal": Decimal, "InvalidOperation": InvalidOperation, "ROUND_HALF_UP": ROUND_HALF_UP}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(FLOW), "exec"), ns)
    return ns[name]


def test_feed_in_tariff_default_preserves_six_decimal_places():
    formatter = _function("format_feed_in_tariff_de")
    assert formatter("0.287400") == "0,287400"
    assert formatter("0.287401") == "0,287401"


def test_feed_in_tariff_uses_precision_formatter_on_edit_form():
    source = FLOW.read_text()
    assert 'default=format_feed_in_tariff_de(input_value("feed_in_price_input", "feed_in_price_net", "feed_in_price_includes_vat", True))' in source


def test_forecast_visibility_is_per_meter_and_direction():
    card = CARD.read_text()
    sensor = SENSOR.read_text()
    assert 'isFeed ? a.forecast_feed_in_enabled === true : a.forecast_consumption_enabled !== false' in card
    assert 'forecastEnabled ? forecastBox : ""' in card
    assert '"forecast_feed_in_enabled": entry.data.get("forecast_feed_in_enabled", False)' in sensor


def test_neutral_monthly_advance_label_is_used():
    assert 't("Voraussichtlicher monatlicher Abschlag:", "Likely monthly advance:")' in CARD.read_text()


def test_elapsed_period_label_is_rendered_for_both_directions():
    card = CARD.read_text()
    assert 't("Monate","months")' in card
    assert 't("Tage","days")' in card
    assert 'elapsedMs / totalMs * 100' in card
    assert 'minimumFractionDigits:2, maximumFractionDigits:2' in card
