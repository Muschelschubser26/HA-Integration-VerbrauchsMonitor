"""Regression tests for the R149 forecast sensor runtime failure."""
import ast
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).parents[1]
SENSOR = ROOT / "custom_components" / "verbrauchsmonitor" / "sensor.py"


def _function(tree, name):
    return next(node for node in ast.walk(tree)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == name)


def test_forecast_refresh_uses_defined_billing_period_end_variable():
    tree = ast.parse(SENSOR.read_text(encoding="utf-8"))
    function = _function(tree, "_async_refresh_forecast_value")
    names = {node.id for node in ast.walk(function) if isinstance(node, ast.Name)}
    assigned = {
        target.id
        for node in ast.walk(function)
        for target in (node.targets if isinstance(node, ast.Assign) else
                       [node.target] if isinstance(node, ast.AnnAssign) else [])
        if isinstance(target, ast.Name)
    }
    assert "end_date" in names
    assert "end_date" in assigned
    assert "period_end_date" not in names, (
        "The old undefined variable caused every forecast refresh to fail."
    )


def test_real_forecast_and_reliability_pipeline_returns_numeric_value_without_history():
    # This exercises the real forecast calculation and the same weight/aggregation
    # functions used by the sensor after the billing-period variables are resolved.
    import importlib.util
    import sys

    package = ROOT / "custom_components" / "verbrauchsmonitor"

    def load(name, filename):
        spec = importlib.util.spec_from_file_location(name, package / filename)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module

    forecast = load("vm_r149_forecast", "forecast.py")
    reliability = load("vm_r149_reliability", "reliability.py")
    model = load("vm_r149_forecast_model", "forecast_model.py")
    now = datetime(2026, 11, 26, 16, 0, tzinfo=ZoneInfo("Europe/Berlin"))
    calculated = forecast.calculate_forecast(
        direction="consumption", current_reading="5035.278",
        baseline_reading="3164.000", period_start="2026-08-01",
        today=date(2026, 11, 26), price_net="28.28", vat_rate="19",
        annual_base_price_net="239.62", booked_advances="734.00",
        future_scheduled_advances="200.00", as_of=now,
        period_end_override="2026-12-31",
    )
    weights = reliability.derive_impact_weights(calculated)
    resolved = model.resolve_forecast_reliability(
        initial_score=None, initial_created_at=now, now=now,
        evaluations=[], history={}, method=calculated["method"],
        reliability_context={
            "forecast_factors": {"meter_freshness": 99.0},
            "financial_factors": {
                "valid_energy_tariff": 100.0,
                "valid_billing_period": 100.0,
                "valid_vat": 100.0,
            },
            **weights,
        },
    )
    assert calculated["forecast_energy_cost_total_eur"] > 0
    assert weights["forecast_impact_weight"] > 0
    assert weights["financial_impact_weight"] > 0
    assert resolved["forecast_reliability_available"] is False
    assert resolved["forecast_reliability_percent"] is None
    assert resolved["forecast_reliability_pending"] is True
