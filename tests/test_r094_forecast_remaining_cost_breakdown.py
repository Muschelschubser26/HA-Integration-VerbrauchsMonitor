from datetime import date
from decimal import Decimal
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

ROOT = Path(__file__).parents[1]
FORECAST_PATH = ROOT / "custom_components" / "verbrauchsmonitor" / "forecast.py"


def _load_forecast():
    spec = spec_from_file_location("vm_r094_forecast", FORECAST_PATH)
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_remaining_forecast_costs_separate_energy_and_prorated_base_price():
    forecast = _load_forecast()
    result = forecast.calculate_forecast(
        direction="consumption",
        current_reading="4984.229",
        baseline_reading="3164.000",
        period_start="2026-08-01",
        today=date(2026, 11, 23),
        price_net="23.7647058824",
        vat_rate=19,
        annual_base_price_net="201.36134454",
        period_months=5,
        history={},
        booked_advances="800.00",
        future_scheduled_advances="200.00",
    )

    # Current accrued base charge is four calendar months; the full forecast
    # period covers five. The remaining base charge is therefore exactly one
    # prorated month and is kept separate from remaining energy costs.
    assert result["accrued_base_price_eur"] == 79.87
    assert result["forecast_base_price_total_eur"] == 99.84
    assert result["remaining_base_price_eur"] == 19.97
    assert result["remaining_energy_cost_eur"] > 0
    assert result["remaining_costs_including_base_price_eur"] == round(
        result["remaining_energy_cost_eur"] + result["remaining_base_price_eur"], 2
    )

    # Expected balance includes the December payment once, while the future
    # cost breakdown includes energy and base price once each.
    expected = Decimal("800.00") + Decimal("200.00") - Decimal(str(result["annual_value_eur"]))
    assert Decimal(str(result["expected_year_end_balance_eur"])) == expected.quantize(Decimal("0.01"))

    current_balance = Decimal("800.00") - Decimal(str(result["accrued_energy_cost_eur"])) - Decimal(str(result["accrued_base_price_eur"]))
    remaining_costs = Decimal(str(result["remaining_costs_including_base_price_eur"]))
    assert (current_balance + Decimal("200.00") - remaining_costs).quantize(Decimal("0.01")) == expected.quantize(Decimal("0.01"))


def test_feed_in_forecast_never_inherits_consumption_base_price():
    forecast = _load_forecast()
    result = forecast.calculate_forecast(
        direction="feed_in",
        current_reading="1200", baseline_reading="1000",
        period_start="2026-08-01", today=date(2026, 11, 23),
        price_net="8", vat_rate=0, annual_base_price_net="201.36",
        period_months=5, booked_advances=0, future_scheduled_advances=0,
    )
    assert result["forecast_base_price_total_eur"] == 0
    assert result["accrued_base_price_eur"] == 0
    assert result["remaining_base_price_eur"] == 0
