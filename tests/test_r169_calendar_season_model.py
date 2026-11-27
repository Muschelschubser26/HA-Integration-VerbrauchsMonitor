from datetime import date, datetime, timezone
from decimal import Decimal

import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "custom_components/verbrauchsmonitor/forecast.py"
SPEC = importlib.util.spec_from_file_location("vm_forecast_r169", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
calendar_season_projection = MODULE.calendar_season_projection


def test_calendar_season_model_uses_season_average_independently():
    history = {
        "usable": True,
        "history_months": 24,
        "monthly_daily_kwh": {str(month): 10 for month in range(1, 13)},
    }
    result = calendar_season_projection(
        observed_energy=Decimal("5"), today=date(2026, 1, 1),
        period_end=date(2026, 1, 3), history=history,
    )
    assert result == Decimal("35")


def test_calendar_season_model_does_not_invent_missing_season_data():
    history = {"usable": True, "history_months": 12, "monthly_daily_kwh": {"1": 10}}
    result = calendar_season_projection(
        observed_energy=Decimal("5"), today=date(2026, 3, 1),
        period_end=date(2026, 3, 3), history=history,
    )
    assert result is None


def test_calendar_season_model_respects_remaining_fraction_of_current_day():
    history = {"usable": True, "history_months": 12, "monthly_daily_kwh": {str(month): 10 for month in range(1, 13)}}
    as_of = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
    result = calendar_season_projection(
        observed_energy=Decimal("5"), today=date(2026, 1, 1),
        period_end=date(2026, 1, 2), history=history, as_of=as_of,
    )
    assert result == Decimal("20.0")


def test_full_forecast_reports_independent_third_model_when_history_is_usable():
    result = MODULE.calculate_forecast(
        direction="consumption", current_reading="100", baseline_reading="0",
        period_start="2026-01-01", today=date(2026, 1, 1), price_net="30",
        period_months=12,
        history={
            "usable": True,
            "history_months": 24,
            "two_cycle_months": 12,
            "monthly_daily_kwh": {str(month): float(5 + month) for month in range(1, 13)},
        },
    )
    assert "calendar_season" in result["forecast_models_used"]
    assert "historical_monthly_seasonal" in result["forecast_models_used"]
    assert result["annual_energy_kwh"] >= 100
    assert abs(sum(result["forecast_model_weights"].values()) - 1.0) < 1e-9
    assert set(result["forecast_model_outputs_kwh"]) == set(result["forecast_models_used"])
