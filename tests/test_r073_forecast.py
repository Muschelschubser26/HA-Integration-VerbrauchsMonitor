from datetime import date
from decimal import Decimal
import pytest
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "vm_forecast", Path(__file__).parents[1] / "custom_components" / "verbrauchsmonitor" / "forecast.py"
)
_forecast = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_forecast)
calculate_forecast = _forecast.calculate_forecast


def test_consumption_forecast_includes_base_price_and_advance():
    result = calculate_forecast(
        direction="consumption", current_reading="1500", baseline_reading="1000",
        period_start="2026-01-01", today=date(2026, 7, 1), price_net="30",
        vat_rate=19, annual_base_price_net="120", monthly_advance_net="20",
        period_months=12,
    )
    assert result["annual_energy_kwh"] > 990
    assert result["annual_value_eur"] > 470
    assert result["configured_monthly_advance_eur"] == 23.8
    # Consumption liabilities use the customer-account negative sign.
    # Contractual feed-in advances are not treated as paid without a booking.
    assert result["expected_year_end_balance_eur"] < 0


def test_feed_in_forecast_is_separate_and_uses_actual_gross_advance():
    result = calculate_forecast(
        direction="feed_in", current_reading="1800", baseline_reading="1000",
        period_start="2026-01-01", today=date(2026, 7, 1), price_net="8.2",
        vat_rate=0, feed_in_monthly_advance_net="35", period_months=12,
    )
    assert result["annual_value_eur"] > 90
    assert result["configured_monthly_advance_eur"] == 35
    assert result["expected_year_end_balance_eur"] > 0


def test_directions_cannot_be_mixed_and_invalid_inputs_are_rejected():
    with pytest.raises(ValueError):
        calculate_forecast(direction="other", current_reading=1, baseline_reading=0,
                           period_start="2026-01-01", today=date(2026, 2, 1), price_net=1)
    with pytest.raises(ValueError):
        calculate_forecast(direction="consumption", current_reading=1, baseline_reading=2,
                           period_start="2026-01-01", today=date(2026, 2, 1), price_net=1)


def test_future_period_start_is_rejected():
    with pytest.raises(ValueError):
        calculate_forecast(direction="consumption", current_reading=1, baseline_reading=0,
                           period_start="2027-01-01", today=date(2026, 12, 1), price_net=1)


def test_six_month_period_and_zero_vat():
    result = calculate_forecast(
        direction="feed_in", current_reading="600", baseline_reading="300",
        period_start="2026-01-01", today=date(2026, 2, 1), price_net="10",
        vat_rate=0, feed_in_monthly_advance_net="0", period_months=6,
    )
    assert result["annual_energy_kwh"] > 1600
    # The recommendation is distributed over the four remaining payment
    # months, not retrospectively over the complete billing period.
    assert result["recommended_monthly_advance_eur"] == 42.42
    assert result["configured_monthly_advance_eur"] == 0


def test_history_below_twelve_months_uses_linear_fallback():
    history = {"usable": False, "history_months": 11, "monthly_daily_kwh": {"1": 4}, "coverage_percent": 90}
    result = calculate_forecast(
        direction="consumption", current_reading=200, baseline_reading=100,
        period_start="2026-01-01", today=date(2026, 6, 30), price_net=30,
        history=history,
    )
    assert result["method"] == "linear_elapsed_period_average"


def test_actual_booked_advances_reduce_balance_but_not_expected_payments():
    result = calculate_forecast(
        direction="consumption", current_reading=200, baseline_reading=100,
        period_start="2026-01-01", today=date(2026, 6, 30), price_net=30,
        booked_advances=50,
    )
    assert result["booked_advances_eur"] == 50
    assert result["expected_year_end_balance_eur"] < 0


def test_history_quality_and_seasonal_thresholds():
    from datetime import datetime, timedelta
    samples = []
    start = datetime(2024, 1, 1)
    value = 1000
    for day in range(0, 736, 7):
        samples.append((start + timedelta(days=day), value))
        value += 7
    quality = _forecast.evaluate_history(samples, today=date(2026, 1, 1))
    assert quality["history_months"] >= 24
    assert quality["usable"] is True
    result = calculate_forecast(
        direction="consumption", current_reading=value, baseline_reading=1000,
        period_start="2025-01-01", today=date(2026, 1, 1), price_net=30,
        history=quality,
    )
    assert result["method"] == "seasonal_24m"


def test_twelve_month_history_enables_first_seasonal_method():
    from datetime import datetime, timedelta
    samples = []
    start = datetime(2025, 1, 1)
    value = 1000
    for day in range(0, 367, 3):
        samples.append((start + timedelta(days=day), value))
        value += 3
    history = _forecast.evaluate_history(samples, today=date(2026, 1, 1))
    assert history["history_months"] >= 12
    assert history["usable"]
    result = calculate_forecast(
        direction="consumption", current_reading=value, baseline_reading=1000,
        period_start="2025-01-01", today=date(2026, 1, 1), price_net=30,
        history=history,
    )
    assert result["method"] == "seasonal_12m"


def test_insufficient_history_coverage_forces_linear_fallback():
    history = {
        "usable": False, "history_months": 24, "coverage_percent": 20,
        "monthly_daily_kwh": {str(month): 1 for month in range(1, 13)},
        "two_cycle_months": 12,
    }
    result = calculate_forecast(
        direction="feed_in", current_reading=500, baseline_reading=100,
        period_start="2025-01-01", today=date(2026, 1, 1), price_net=10,
        history=history,
    )
    assert result["method"] == "linear_elapsed_period_average"


def test_selected_season_adjusts_seasonal_projection_from_observed_profile():
    history = {
        "usable": True, "history_months": 12, "coverage_percent": 95,
        "monthly_daily_kwh": {str(month): (1 if month in (12, 1, 2) else 10) for month in range(1, 13)},
        "two_cycle_months": 0,
    }
    common = dict(
        direction="consumption", current_reading=1000, baseline_reading=900,
        period_start="2026-01-01", today=date(2026, 6, 1), price_net=30,
        history=history,
    )
    summer = calculate_forecast(**common, season="summer")
    winter = calculate_forecast(**common, season="winter")
    assert summer["method"] == winter["method"] == "seasonal_12m"
    assert summer["annual_energy_kwh"] != winter["annual_energy_kwh"]


def test_two_year_method_requires_two_calendar_cycles():
    history = {
        "usable": True, "history_months": 24, "coverage_percent": 95,
        "monthly_daily_kwh": {str(month): 2 for month in range(1, 13)},
        "two_cycle_months": 8,
    }
    result = calculate_forecast(
        direction="consumption", current_reading=1000, baseline_reading=900,
        period_start="2025-01-01", today=date(2026, 1, 1), price_net=30,
        history=history,
    )
    assert result["method"] == "linear_elapsed_period_average"


def test_reliability_index_has_low_medium_and_high_bands():
    high = _forecast.reliability_score(
        history={"history_months": 24, "coverage_percent": 100, "gap_days_max": 1, "quality": 100},
        method="seasonal_24m",
    )
    medium = _forecast.reliability_score(
        history={"history_months": 12, "coverage_percent": 50, "gap_days_max": 14, "quality": 50},
        method="linear_elapsed_period_average",
    )
    low = _forecast.reliability_score(history={}, method="linear_elapsed_period_average")
    assert high["forecast_reliability_percent"] >= 80
    assert medium["forecast_reliability_percent"] >= 50
    assert medium["forecast_reliability_percent"] < 80
    assert low["forecast_reliability_percent"] < 50


def test_advance_recommendation_is_capped_at_30_without_history():
    result = {"recommended_monthly_advance_eur": 486.16, "configured_monthly_advance_eur": 150.00}
    adjusted = _forecast.apply_advance_recommendation_limit(
        result=result,
        reliability={"forecast_reliability_percent": 22},
        history={"history_months": 0},
    )
    assert adjusted["recommended_monthly_advance_eur"] == 180.00
    assert adjusted["uncapped_monthly_advance_eur"] == 486.16
    assert adjusted["advance_recommendation_limit_applied"] is True


def test_advance_recommendation_limit_increases_with_reliable_history():
    result = {"recommended_monthly_advance_eur": 300.00, "configured_monthly_advance_eur": 150.00}
    twelve_months = _forecast.apply_advance_recommendation_limit(
        result=result, reliability={"forecast_reliability_percent": 80},
        history={"history_months": 12},
    )
    twenty_four_months = _forecast.apply_advance_recommendation_limit(
        result=result, reliability={"forecast_reliability_percent": 90},
        history={"history_months": 24},
    )
    assert twelve_months["recommended_monthly_advance_eur"] == 200.00
    assert twenty_four_months["recommended_monthly_advance_eur"] == 225.00


def test_advance_recommendation_is_not_limited_without_configured_baseline():
    result = {"recommended_monthly_advance_eur": 486.16, "configured_monthly_advance_eur": 0}
    adjusted = _forecast.apply_advance_recommendation_limit(
        result=result, reliability={"forecast_reliability_percent": 22},
        history={"history_months": 0},
    )
    assert adjusted["recommended_monthly_advance_eur"] == 486.16
    assert adjusted["advance_recommendation_limit_applied"] is False


def test_five_month_billing_period_prorates_annual_base_price():
    result = calculate_forecast(
        direction="consumption", current_reading="4984.229", baseline_reading="3164",
        period_start="2026-08-01", today=date(2026, 11, 23), price_net="23.7647058824",
        vat_rate=19, annual_base_price_net="239.62", monthly_advance_net="168.06722689",
        period_months=5, booked_advances=0, future_scheduled_advances=200,
    )
    expected_base = Decimal("239.62") * Decimal("1.19") * Decimal(5) / Decimal(12)
    # R096: total projected cost is accrued energy/base cost plus the
    # remaining-cost estimate derived from the current monthly average.
    assert Decimal(str(result["forecast_base_price_total_eur"])) == expected_base.quantize(Decimal("0.01"))
    assert Decimal(str(result["annual_value_eur"])) == (
        Decimal(str(result["accrued_energy_cost_eur"]))
        + Decimal(str(result["accrued_base_price_eur"]))
        + Decimal(str(result["remaining_costs_including_base_price_eur"]))
    ).quantize(Decimal("0.01"))
    assert result["months_remaining"] == 1
    assert result["future_scheduled_advances_eur"] == 200.0
    assert result["expected_year_end_balance_eur"] < 0


def test_recommendation_uses_all_remaining_months_without_artificial_cap():
    one_month = calculate_forecast(
        direction="consumption", current_reading=2000, baseline_reading=1000,
        period_start="2026-08-01", today=date(2026, 11, 23), price_net=30,
        vat_rate=0, annual_base_price_net=120, monthly_advance_net=200,
        period_months=5, booked_advances=0, future_scheduled_advances=200,
    )
    two_months = calculate_forecast(
        direction="consumption", current_reading=2000, baseline_reading=1000,
        period_start="2026-07-01", today=date(2026, 10, 23), price_net=30,
        vat_rate=0, annual_base_price_net=120, monthly_advance_net=200,
        period_months=6, booked_advances=0, future_scheduled_advances=400,
    )
    assert one_month["months_remaining"] == 1
    assert two_months["months_remaining"] == 2
    assert one_month["recommended_monthly_advance_eur"] > 200
    assert two_months["recommended_monthly_advance_eur"] == round(two_months["annual_value_eur"] / 2, 2)
    assert one_month["recommended_monthly_advance_eur"] == one_month["annual_value_eur"]
    assert one_month["expected_year_end_balance_eur"] == round(
        -(one_month["annual_value_eur"] - 200), 2
    )
