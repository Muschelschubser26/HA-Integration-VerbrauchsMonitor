"""R124 fixed-reference tests for solar-aware forecasts and safe advances."""
from datetime import date, datetime, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from zoneinfo import ZoneInfo
import sys
import types

ROOT = Path(__file__).parents[1]
INTEGRATION = ROOT / "custom_components" / "verbrauchsmonitor"

_PACKAGE = "vm_r125_package"
_package = types.ModuleType(_PACKAGE)
_package.__path__ = [str(INTEGRATION)]
sys.modules.setdefault(_PACKAGE, _package)

def _load(name, path):
    module_name = f"{_PACKAGE}.{name}"
    spec = spec_from_file_location(module_name, path)
    if module_name in sys.modules:
        return sys.modules[module_name]
    module = module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

def test_solar_position_and_daylight_change_consumption_prior_by_season():
    model = _load("forecast_model", INTEGRATION / "forecast_model.py")
    winter = datetime(2026, 1, 15, 12, tzinfo=timezone.utc)
    summer = datetime(2026, 7, 15, 12, tzinfo=timezone.utc)
    winter_weight = model.initial_profile_multiplier("consumption", winter, 53.5, 8.1)
    summer_weight = model.initial_profile_multiplier("consumption", summer, 53.5, 8.1)
    assert model.solar_resource_index(winter.date(), 53.5) < model.solar_resource_index(summer.date(), 53.5)
    assert winter_weight > summer_weight

def test_local_sunrise_and_sunset_are_calculated_for_the_configured_timezone():
    model = _load("forecast_model", INTEGRATION / "forecast_model.py")
    events = model.sunrise_sunset(date(2026, 6, 21), 53.5, 8.1, ZoneInfo("Europe/Berlin"))
    assert events["sunrise"] is not None
    assert events["sunset"] is not None
    assert events["sunrise"].tzinfo is not None
    assert events["sunrise"] < events["sunset"]
    assert 16.0 <= (events["sunset"] - events["sunrise"]).total_seconds() / 3600 <= 18.0


def test_selected_compass_directions_change_feed_in_solar_profile():
    model = _load("forecast_model", INTEGRATION / "forecast_model.py")
    when = datetime(2026, 6, 21, 8, tzinfo=timezone.utc)
    east = model.initial_profile_multiplier("feed_in", when, 53.5, 8.1, ["east"])
    south = model.initial_profile_multiplier("feed_in", when, 53.5, 8.1, ["south"])
    combined = model.initial_profile_multiplier("feed_in", when, 53.5, 8.1, ["east", "south", "west"])
    assert east > south
    assert combined >= south

def test_history_projection_uses_solar_geometry_for_both_directions():
    forecast = _load("forecast", INTEGRATION / "forecast.py")
    history = {"usable": True, "history_months": 12, "two_cycle_months": 0,
               "monthly_daily_kwh": {str(month): 10.0 for month in range(1, 13)}}
    common = dict(current_reading="100", baseline_reading="90", period_start="2026-01-01",
                  today=date(2026, 1, 1), period_months=12, history=history,
                  latitude=53.5, longitude=8.1, timezone_info=ZoneInfo("Europe/Berlin"))
    consumption = forecast.seasonal_energy_projection(**common, direction="consumption")
    feed_south = forecast.seasonal_energy_projection(**common, direction="feed_in", orientations=["south"])
    feed_east = forecast.seasonal_energy_projection(**common, direction="feed_in", orientations=["east"])
    assert consumption is not None and feed_south is not None and feed_east is not None
    assert consumption > 10
    assert feed_south != feed_east

def test_single_remaining_payment_date_never_produces_advance_recommendation_even_with_credit():
    forecast = _load("forecast", INTEGRATION / "forecast.py")
    result = forecast.calculate_forecast(
        direction="feed_in", current_reading="5440.059", baseline_reading="5382.059",
        period_start="2026-08-01", today=date(2026, 11, 25), price_net="34.20",
        vat_rate=0, period_months=5, booked_advances="0",
        future_scheduled_advances="0", feed_in_monthly_advance_net="200",
    )
    assert result["months_remaining"] == 1
    assert result["expected_year_end_balance_eur"] > 0
    assert result["recommended_monthly_advance_eur"] == 0.0
    assert result["forecast_recommendation_available"] is False
    assert result["forecast_recommendation_unavailable_reason"] == "final_payment_period"

def test_future_scheduled_advances_are_subtracted_before_monthly_recommendation():
    forecast = _load("forecast", INTEGRATION / "forecast.py")
    result = forecast.calculate_forecast(
        direction="consumption", current_reading="2000", baseline_reading="1000",
        period_start="2026-07-01", today=date(2026, 10, 23), price_net="30",
        vat_rate=0, annual_base_price_net="120", monthly_advance_net="200",
        period_months=6, booked_advances="0", future_scheduled_advances="400",
    )
    assert result["months_remaining"] == 2
    assert result["recommended_monthly_advance_eur"] == 70.25
    assert result["forecast_recommendation_available"] is True

def test_card_uses_compact_power_next_to_progress_and_season_above_forecast_heading():
    card = (INTEGRATION / "frontend" / "verbrauchsmonitor-card.js").read_text(encoding="utf-8")
    block = card.split('const forecastBox = `', 1)[1].split('</section>`;', 1)[0]
    assert block.index('class="forecast-season"') < block.index('class="forecast-reliability"')
    assert block.index('class="forecast-heading"') < block.index('class="forecast-reliability"')
    assert block.index('class="forecast-reliability"') < block.index('class="forecast-balance"')
    assert 'class="period-meta-row"' in card
    assert 'class="current-power"' in card
    assert '.forecast-balance{display:flex;justify-content:space-between;gap:12px;padding:5px 0 2px;border-bottom:0' in card
