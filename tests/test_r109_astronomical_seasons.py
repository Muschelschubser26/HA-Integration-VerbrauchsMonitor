"""Global astronomical seasons and hemisphere-aware forecast regression tests."""
from datetime import datetime, date, timezone
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEASON_PATH = ROOT / "custom_components/verbrauchsmonitor/seasons.py"
_spec = importlib.util.spec_from_file_location("vm_seasons", SEASON_PATH)
_seasons = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_seasons)


def test_2026_equinox_and_solstice_instants_are_astronomically_plausible():
    expected = (
        datetime(2026, 3, 20, 14, 46, tzinfo=timezone.utc),
        datetime(2026, 6, 21, 8, 26, tzinfo=timezone.utc),
        datetime(2026, 9, 23, 0, 6, tzinfo=timezone.utc),
        datetime(2026, 12, 21, 20, 51, tzinfo=timezone.utc),
    )
    for index, target in enumerate(expected):
        actual = _seasons._season_event(2026, index)
        assert abs((actual - target).total_seconds()) < 120


def test_season_changes_at_the_actual_utc_boundary_on_northern_hemisphere():
    boundary = _seasons._season_event(2026, 2)
    before = boundary.replace(microsecond=0)
    before = before.replace(second=max(0, before.second - 1))
    assert _seasons.astronomical_season(before, 52.5) == "summer"
    assert _seasons.astronomical_season(boundary, 52.5) == "autumn"


def test_southern_hemisphere_seasons_are_opposite_north_of_equator():
    points = (
        (datetime(2026, 3, 20, 15, tzinfo=timezone.utc), "spring", "autumn"),
        (datetime(2026, 6, 21, 9, tzinfo=timezone.utc), "summer", "winter"),
        (datetime(2026, 9, 23, 1, tzinfo=timezone.utc), "autumn", "spring"),
        (datetime(2026, 12, 21, 21, tzinfo=timezone.utc), "winter", "summer"),
    )
    for instant, north, south in points:
        assert _seasons.astronomical_season(instant, 40) == north
        assert _seasons.astronomical_season(instant, -33.9) == south


def test_home_assistant_location_is_the_only_location_source():
    class Config:
        latitude = -33.9
        longitude = 151.2

    class Hass:
        config = Config()

    now = datetime(2026, 6, 21, 9, tzinfo=timezone.utc)
    assert _seasons.current_ha_season(Hass(), now) == "winter"


def test_invalid_coordinates_and_naive_datetime_are_rejected():
    try:
        _seasons.astronomical_season(datetime(2026, 1, 1), 52)
        assert False, "naive datetime must be rejected"
    except ValueError:
        pass
    try:
        _seasons.astronomical_season(datetime(2026, 1, 1, tzinfo=timezone.utc), 91)
        assert False, "invalid latitude must be rejected"
    except ValueError:
        pass


def test_manual_and_season_integration_fields_are_removed_from_forecast_flow():
    source = (ROOT / "custom_components/verbrauchsmonitor/config_flow.py").read_text(encoding="utf-8")
    start = source.index("    async def async_step_forecast(")
    end = source.index("    async def async_step_billing(", start)
    flow = source[start:end]
    assert 'vol.Required("season_mode"' not in flow
    assert 'vol.Required("manual_season"' not in flow
    assert "current_ha_season" in source


def test_dashboard_displays_automatically_calculated_season():
    card = (ROOT / "custom_components/verbrauchsmonitor/frontend/verbrauchsmonitor-card.js").read_text(encoding="utf-8")
    assert "forecast_current_season" in card
    assert 't("Jahreszeit:","Season:")' in card


def test_seasonal_history_month_groups_follow_the_local_hemisphere():
    forecast_path = ROOT / "custom_components/verbrauchsmonitor/forecast.py"
    forecast_spec = importlib.util.spec_from_file_location("vm_forecast_r109", forecast_path)
    forecast_module = importlib.util.module_from_spec(forecast_spec)
    forecast_spec.loader.exec_module(forecast_module)
    assert forecast_module.season_for_month(6, "north") == "summer"
    assert forecast_module.season_for_month(6, "south") == "winter"
    assert forecast_module.season_for_month(12, "north") == "winter"
    assert forecast_module.season_for_month(12, "south") == "summer"
