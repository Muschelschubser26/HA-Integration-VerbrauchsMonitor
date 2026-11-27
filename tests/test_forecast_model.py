from datetime import datetime, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

PATH = Path(__file__).parents[1] / "custom_components" / "verbrauchsmonitor" / "forecast_model.py"
spec = spec_from_file_location("vm_forecast_model", PATH)
model = module_from_spec(spec)
sys.modules[spec.name] = model
spec.loader.exec_module(model)


def test_solar_position_is_local_and_returns_daylight_state():
    result = model.solar_position(datetime(2026, 6, 21, 12, tzinfo=timezone.utc), 53.5, 8.1)
    assert result["elevation_deg"] > 0
    assert result["daylight"] is True
    assert 0 <= result["azimuth_deg"] <= 360


def test_daylight_handles_polar_day_and_night():
    assert model.daylight_hours(datetime(2026, 6, 21).date(), 89) > 23
    assert model.daylight_hours(datetime(2026, 12, 21).date(), 89) < 1


def test_consumption_and_feed_in_priors_are_separate():
    when = datetime(2026, 6, 21, 12, tzinfo=timezone.utc)
    consumption = model.initial_profile_multiplier("consumption", when, 53.5, 8.1)
    feed_in = model.initial_profile_multiplier("feed_in", when, 53.5, 8.1, ["south"])
    assert consumption > 0
    assert feed_in > 0
    assert consumption != feed_in


def test_feed_in_direction_selection_changes_profile():
    when = datetime(2026, 6, 21, 9, tzinfo=timezone.utc)
    east = model.initial_profile_multiplier("feed_in", when, 53.5, 8.1, ["east"])
    west = model.initial_profile_multiplier("feed_in", when, 53.5, 8.1, ["west"])
    assert east != west


def test_hourly_forecast_is_immutable_and_evaluation_is_idempotently_keyed():
    target = datetime(2026, 11, 25, 18, 30, tzinfo=timezone.utc)
    record = model.create_hourly_forecast("meter-a", "consumption", target, 1.25)
    result = model.evaluate_hourly_forecast(record, 1.5)
    assert record["target_hour"] == "2026-11-25T18:00:00+00:00"
    assert result["key"] == "meter-a|consumption|2026-11-25T18:00:00+00:00"
    assert result["absolute_error"] == 0.25


def test_learning_adopts_only_a_better_candidate_with_enough_samples():
    assert not model.adopt_candidate_model({"count": 23, "mae": 1}, {"count": 30, "mae": .5})
    assert model.adopt_candidate_model({"count": 30, "mae": 1}, {"count": 30, "mae": .9})
    assert not model.adopt_candidate_model({"count": 30, "mae": 1}, {"count": 30, "mae": 1.1})


def test_hourly_forecasts_are_meter_and_direction_specific_and_normalized():
    from zoneinfo import ZoneInfo
    now = datetime(2026, 6, 21, 12, 15, tzinfo=ZoneInfo("Europe/Berlin"))
    records = model.build_hourly_forecasts(
        meter_id="meter-a", direction="consumption", now=now,
        daily_energy=12.0, latitude=53.5, longitude=8.1,
        timezone_info=now.tzinfo, horizon_hours=24,
    )
    assert len(records) == 24
    assert all(item["meter_id"] == "meter-a" for item in records)
    assert all(item["direction"] == "consumption" for item in records)
    assert abs(sum(item["predicted_value"] for item in records) - 12.0) < 1e-9


def test_forecast_merge_never_replaces_original_prediction():
    target = datetime(2026, 11, 25, 18, tzinfo=timezone.utc)
    first = model.create_hourly_forecast("meter-a", "feed_in", target, 1.0)
    revised = model.create_hourly_forecast("meter-a", "feed_in", target, 9.0)
    merged = model.merge_forecast_records({}, [first])
    merged = model.merge_forecast_records(merged, [revised])
    assert len(merged) == 1
    assert next(iter(merged.values()))["predicted_value"] == 1.0


def test_hourly_reliability_requires_actual_comparisons():
    empty = model.reliability_from_hourly_evaluations([])
    assert empty["available"] is False
    evaluations = []
    for index in range(24):
        evaluations.append({"absolute_error": 0.1, "relative_error_percent": 5.0, "error": 0.1})
    measured = model.reliability_from_hourly_evaluations(evaluations)
    assert measured["available"] is True
    assert measured["score"] == 95.0


def test_candidate_learning_uses_holdout_and_only_adopts_improvement():
    training = []
    for index in range(48):
        training.append({
            "target_hour": f"2026-01-{1 + index // 24:02d}T{index % 24:02d}:00:00+00:00",
            "predicted": 1.0, "actual": 1.2,
        })
    result = model.learn_candidate_scale(training)
    assert result["adopted"] is True
    assert abs(result["scale"] - 1.2) < 1e-9


def test_candidate_learning_rejects_non_improving_candidate():
    evaluations = []
    for index in range(48):
        actual = 1.2 if index < 24 else 0.5
        evaluations.append({
            "target_hour": f"2026-01-{1 + index // 24:02d}T{index % 24:02d}:00:00+00:00",
            "predicted": 1.0, "actual": actual,
        })
    result = model.learn_candidate_scale(evaluations)
    assert result["adopted"] is False


