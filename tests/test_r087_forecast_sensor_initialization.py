"""Regression tests for forecast entity initialization and reliability storage."""
import ast
from pathlib import Path

ROOT = Path(__file__).parents[1]
SENSOR = ROOT / "custom_components/verbrauchsmonitor/sensor.py"
FORECAST = ROOT / "custom_components/verbrauchsmonitor/forecast.py"


def _forecast_constructor():
    tree = ast.parse(SENSOR.read_text())
    cls = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "VerbrauchsMonitorForecastSensor"
    )
    return next(
        node for node in cls.body
        if isinstance(node, ast.FunctionDef) and node.name == "__init__"
    )


def test_forecast_sensor_initializes_meter_id_before_storage_lifecycle():
    constructor = _forecast_constructor()
    assignments = [
        node for node in constructor.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Attribute) and target.attr == "_entry_id" for target in node.targets)
    ]
    assert assignments, "_entry_id must be initialized in the forecast sensor constructor"
    assert isinstance(assignments[0].value, ast.Attribute)
    assert assignments[0].value.attr == "entry_id"


def test_reliability_store_key_uses_initialized_meter_id():
    source = SENSOR.read_text()
    assert 'Legacy synthetic reliability storage is intentionally no longer read.' in source
    assert 'f"{DOMAIN}_{self._entry_id}_{self._direction}_forecast_reliability"' not in source
    constructor = _forecast_constructor()
    entry_id_line = next(i for i, node in enumerate(constructor.body)
                         if isinstance(node, ast.Assign)
                         and any(isinstance(t, ast.Attribute) and t.attr == "_entry_id" for t in node.targets))
    data_line = next(i for i, node in enumerate(constructor.body)
                     if isinstance(node, ast.Assign)
                     and any(isinstance(t, ast.Attribute) and t.attr == "_data" for t in node.targets))
    assert entry_id_line < data_line


def test_reliability_has_no_randomized_start_value():
    source = FORECAST.read_text()
    assert "secrets.randbelow" not in source
    assert '"score": None' in source


def test_forecast_box_remains_visible_when_forecast_entities_are_missing():
    card = (ROOT / "custom_components/verbrauchsmonitor/frontend/verbrauchsmonitor-card.js").read_text()
    assert 'const forecastBox = `<section class="forecast-box"' in card
    assert 'forecast sensors are missing or unavailable' not in card.lower()
    assert 'Abschlagsprognose derzeit nicht verfügbar' not in card


def test_cost_summary_shows_monthly_average_and_current_billing_period():
    card = (ROOT / "custom_components/verbrauchsmonitor/frontend/verbrauchsmonitor-card.js").read_text()
    assert 't("Ø im Monat","Average per month")' in card
    assert 't("Aktueller Abrechnungszeitraum","Current billing period")' in card
    assert 'totalCosts / elapsedDays * 30.436875' in card
    assert 'noch nicht berechenbar' in card


def test_monthly_advances_reduce_account_balance_automatically_on_day_one():
    source = SENSOR.read_text()
    assert 'advances = money_amount(expected_advance_amount)' in source
    assert 'expected_advances_total' in source
    assert 'No confirmation or manual booking is required' in source


def test_balance_sensor_imports_every_advance_calculation_it_calls():
    tree = ast.parse(SENSOR.read_text())
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == ".ledger"
        for alias in node.names
    }
    # The balance sensor uses a local relative import; AST stores the module
    # without its leading dot for ImportFrom nodes with level=1.
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == "ledger" and node.level == 1
        for alias in node.names
    }
    assert "calculate_advance_total" in imports


def test_forecast_sensor_defines_weekly_refresh_callback():
    tree = ast.parse(SENSOR.read_text())
    cls = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "VerbrauchsMonitorForecastSensor"
    )
    methods = {node.name for node in cls.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    assert "_periodic_refresh" in methods
    assert "_async_refresh_history" in methods


def test_daily_history_refresh_is_registered_only_after_forecast_sensor_initialization():
    source = SENSOR.read_text()
    assert "self._periodic_refresh, timedelta(days=1)" in source
    assert "def _periodic_refresh(self, now):" in source
