from datetime import datetime, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

PATH = Path(__file__).parents[1] / "custom_components" / "verbrauchsmonitor" / "forecast.py"
spec = spec_from_file_location("vm_reliability_evidence", PATH)
forecast = module_from_spec(spec)
sys.modules[spec.name] = forecast
spec.loader.exec_module(forecast)


def test_insufficient_history_has_no_reliability_score():
    result = forecast.reliability_score(
        history={"usable": False, "history_months": 0, "sample_count": 0,
                    "coverage_percent": 0, "gap_days_max": 999, "quality": 0},
        method="linear_elapsed_period_average",
    )
    assert result["forecast_reliability_percent"] is None
    assert result["forecast_reliability_available"] is False


def test_usable_low_quality_history_has_no_artificial_floor():
    result = forecast.reliability_score(
        history={"usable": True, "history_months": 12, "sample_count": 2,
                    "coverage_percent": 50, "gap_days_max": 999, "quality": 0},
        method="linear_elapsed_period_average",
    )
    assert result["forecast_reliability_percent"] < 37.6
    assert result["forecast_reliability_percent"] <= 100


def test_high_quality_history_scores_above_floor_deterministically():
    history = {"usable": True, "history_months": 24, "sample_count": 500,
               "coverage_percent": 100, "gap_days_max": 1, "quality": 100}
    values = [forecast.reliability_score(history=history, method="seasonal_24m")["forecast_reliability_percent"] for _ in range(20)]
    assert len(set(values)) == 1
    assert values[0] >= 0


def test_legacy_random_or_stale_score_is_never_reused():
    now = datetime(2026, 11, 25, tzinfo=timezone.utc)
    legacy = {"score": 43.8, "last_evaluated": now.isoformat()}
    state = forecast.update_reliability_state(
        legacy,
        history={"usable": False, "history_months": 0, "sample_count": 0,
                 "coverage_percent": 0, "gap_days_max": 999, "quality": 0},
        method="linear_elapsed_period_average", now=now,
    )
    assert state["score"] is None


def test_legacy_score_does_not_override_current_evidence():
    now = datetime(2026, 11, 25, tzinfo=timezone.utc)
    history = {"usable": True, "history_months": 24, "sample_count": 500,
               "coverage_percent": 100, "gap_days_max": 1, "quality": 100}
    state = forecast.update_reliability_state(
        {"score": 99.9, "last_evaluated": now.isoformat()},
        history=history, method="seasonal_24m", now=now,
    )
    assert state["score"] == forecast.reliability_score(history=history, method="seasonal_24m")["forecast_reliability_percent"]


def test_card_does_not_treat_null_reliability_as_zero_percent():
    source = (PATH.parents[0] / "frontend" / "verbrauchsmonitor-card.js").read_text()
    assert 'reliabilityRaw === null || reliabilityRaw === undefined' in source


def test_forecast_card_hides_unavailable_advance_text_and_uses_colored_value_only():
    card = (PATH.parents[0] / "frontend" / "verbrauchsmonitor-card.js").read_text()
    assert 'const recommendationAvailable = valid(forecastAdvance) && Number.isFinite(Number(forecastAdvance.state)) && recommendationAttributes.forecast_recommendation_available !== false' in card
    assert 'class="forecast-unavailable"' in card
    assert 'forecastReliability.toLocaleString(locale' in card
    assert 'reliabilityIcon' not in card


def test_forecast_card_uses_requested_meter_reading_label_with_colon():
    card = (PATH.parents[0] / "frontend" / "verbrauchsmonitor-card.js").read_text()
    assert 'withColon(t("Zählerstand","Meter reading"))' in card
    assert 'Aktueller Zählerstand' not in card
