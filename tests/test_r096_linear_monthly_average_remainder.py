from datetime import date
from decimal import Decimal
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

ROOT = Path(__file__).parents[1]
FORECAST_PATH = ROOT / "custom_components" / "verbrauchsmonitor" / "forecast.py"


def _load_forecast():
    spec = spec_from_file_location("vm_r096_forecast", FORECAST_PATH)
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_remaining_costs_use_accrued_monthly_average_including_base_price():
    forecast = _load_forecast()
    result = forecast.calculate_forecast(
        direction="consumption", current_reading="4984.229", baseline_reading="3164.000",
        period_start="2026-08-01", today=date(2026, 11, 23),
        price_net="23.7647058824", vat_rate=19,
        annual_base_price_net="201.36134454", period_months=5,
        booked_advances="800.00", future_scheduled_advances="200.00",
    )
    accrued = Decimal(str(result["accrued_energy_cost_eur"])) + Decimal(str(result["accrued_base_price_eur"]))
    elapsed_days = Decimal(str(result["basis_days"]))
    remaining_days = Decimal(str((date(2026, 12, 31) - date(2026, 11, 23)).days))
    expected = (accrued / elapsed_days * remaining_days).quantize(Decimal("0.01"))
    assert Decimal(str(result["remaining_costs_including_base_price_eur"])) == expected
    assert result["remaining_base_price_eur"] > 0
    assert result["expected_year_end_balance_eur"] == round(
        800.00 + 200.00 - result["annual_value_eur"], 2
    )


def test_remaining_costs_include_accrued_extra_charges_once():
    forecast = _load_forecast()
    plain = forecast.calculate_forecast(
        direction="consumption", current_reading="1200", baseline_reading="1000",
        period_start="2026-08-01", today=date(2026, 11, 23),
        price_net="20", vat_rate=0, annual_base_price_net="120",
        period_months=5, booked_advances=0, future_scheduled_advances=200,
    )
    with_extra = forecast.calculate_forecast(
        direction="consumption", current_reading="1200", baseline_reading="1000",
        period_start="2026-08-01", today=date(2026, 11, 23),
        price_net="20", vat_rate=0, annual_base_price_net="120",
        period_months=5, booked_advances=0, future_scheduled_advances=200,
        accrued_extra_charges="15.00",
    )
    assert with_extra["accrued_extra_charges_eur"] == 15.0
    assert with_extra["remaining_costs_including_base_price_eur"] > plain["remaining_costs_including_base_price_eur"]
    assert with_extra["annual_value_eur"] > plain["annual_value_eur"]


def test_feed_in_never_adds_base_price_to_monthly_average_remainder():
    forecast = _load_forecast()
    result = forecast.calculate_forecast(
        direction="feed_in", current_reading="1200", baseline_reading="1000",
        period_start="2026-08-01", today=date(2026, 11, 23),
        price_net="8", vat_rate=0, annual_base_price_net="201.36",
        period_months=5, booked_advances=0, future_scheduled_advances=0,
    )
    assert result["forecast_base_price_total_eur"] == 0
    assert result["accrued_base_price_eur"] == 0
    assert result["remaining_base_price_eur"] == 0
