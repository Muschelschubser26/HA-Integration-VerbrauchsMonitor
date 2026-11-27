"""R129 regression coverage for exact tariffs, live horizon and forecast accounting."""
from datetime import date, datetime, timezone
from decimal import Decimal
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from zoneinfo import ZoneInfo
import sys

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "verbrauchsmonitor"


_PACKAGE = "vm_r129_package"
_package = __import__("types").ModuleType(_PACKAGE)
_package.__path__ = [str(INTEGRATION)]
sys.modules.setdefault(_PACKAGE, _package)


def _load(name, path):
    module_name = f"{_PACKAGE}.{name}"
    spec = spec_from_file_location(module_name, path)
    if module_name in sys.modules:
        return sys.modules[module_name]
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_feed_in_amount_uses_exact_stored_gross_tariff_not_two_decimal_label():
    pricing = _load("pricing", INTEGRATION / "pricing.py")
    gross = pricing.gross_decimal_from_net("28.74", "19")
    amount = (Decimal("5382.059") * gross / Decimal("100")).quantize(Decimal("0.01"))
    assert gross == Decimal("34.2006")
    assert amount == Decimal("1840.70")
    card = (INTEGRATION / "frontend" / "verbrauchsmonitor-card.js").read_text(encoding="utf-8")
    assert "minimumFractionDigits:2,maximumFractionDigits:2,useGrouping:false" in card


def test_exact_live_instant_covers_the_entire_billing_period_through_final_day():
    forecast = _load("forecast", INTEGRATION / "forecast.py")
    now = datetime(2026, 11, 25, 12, 0, tzinfo=ZoneInfo("Europe/Berlin"))
    result = forecast.calculate_forecast(
        direction="consumption", current_reading="2000", baseline_reading="1000",
        period_start="2026-08-01", today=now.date(), as_of=now,
        period_end_override="2026-12-31", period_months=5,
        price_net="23.7647058824", vat_rate=19, annual_base_price_net="201.36134454",
    )
    assert result["period_end"] == "2026-12-31"
    assert result["basis_days"] == 116.5
    assert result["remaining_days_fraction"] == 36.5
    assert result["basis_days"] + result["remaining_days_fraction"] == result["period_days"]


def test_seasonal_projection_counts_only_remaining_fraction_of_current_day():
    forecast = _load("forecast", INTEGRATION / "forecast.py")
    now = datetime(2026, 11, 25, 12, 0, tzinfo=ZoneInfo("Europe/Berlin"))
    history = {
        "usable": True,
        "history_months": 12,
        "two_cycle_months": 0,
        "monthly_daily_kwh": {str(month): 10.0 for month in range(1, 13)},
    }
    projected = forecast.seasonal_energy_projection(
        current_reading="110", baseline_reading="10", period_start="2026-11-01",
        today=now.date(), period_months=1, history=history,
        direction="consumption", as_of=now, period_end_override="2026-11-30",
    )
    # 12 hours remain today plus five complete days (26–30 November).
    assert projected == Decimal("155.0")


def test_forecast_balance_includes_payments_credits_and_signed_corrections():
    forecast = _load("forecast", INTEGRATION / "forecast.py")
    common = dict(
        current_reading="1000", baseline_reading="0", period_start="2026-01-01",
        today=date(2026, 6, 30), period_months=12, price_net="10", vat_rate=0,
        booked_advances="40", future_scheduled_advances="20",
    )
    plain = forecast.calculate_forecast(direction="consumption", **common)
    adjusted = forecast.calculate_forecast(
        direction="consumption", additional_payments="5", credits="10",
        corrections="-6", **common,
    )
    assert adjusted["expected_year_end_balance_eur"] == plain["expected_year_end_balance_eur"] + 9.0


def test_feed_in_forecast_uses_same_customer_account_adjustment_signs():
    forecast = _load("forecast", INTEGRATION / "forecast.py")
    result = forecast.calculate_forecast(
        direction="feed_in", current_reading="1000", baseline_reading="0",
        period_start="2026-01-01", today=date(2026, 6, 30), period_months=12,
        price_net="10", vat_rate=0, booked_advances="40",
        future_scheduled_advances="20", additional_payments="5",
        credits="10", corrections="-6",
    )
    expected = result["annual_value_eur"] - 40.0 - 20.0 + 5.0 + 10.0 - 6.0
    assert result["expected_year_end_balance_eur"] == round(expected, 2)


def test_reliability_pending_is_limited_to_15_minutes_and_then_numeric():
    model = _load("forecast_model", INTEGRATION / "forecast_model.py")
    created = datetime(2026, 11, 25, 0, 0, tzinfo=timezone.utc)
    before_expiry = model.resolve_forecast_reliability(
        initial_score=38.2, initial_created_at=created,
        now=datetime(2026, 11, 25, 0, 14, tzinfo=timezone.utc),
        evaluations=[], history={}, reliability_context={"forecast_factors": {"meter": 80}, "forecast_impact_weight": 1}, method="linear_elapsed_period_average",
    )
    after_expiry = model.resolve_forecast_reliability(
        initial_score=38.2, initial_created_at=created,
        now=datetime(2026, 11, 25, 0, 15, tzinfo=timezone.utc),
        evaluations=[], history={}, reliability_context={"forecast_factors": {"meter": 80}, "forecast_impact_weight": 1}, method="linear_elapsed_period_average",
    )
    assert before_expiry["forecast_reliability_pending"] is True
    assert before_expiry["forecast_reliability_available"] is False
    assert after_expiry["forecast_reliability_pending"] is False
    assert after_expiry["forecast_reliability_available"] is False
    assert after_expiry["forecast_reliability_percent"] is None


def test_measured_reliability_replaces_fallback_after_24_completed_comparisons():
    model = _load("forecast_model", INTEGRATION / "forecast_model.py")
    created = datetime(2026, 11, 25, 0, 0, tzinfo=timezone.utc)
    evaluations = [
        {"absolute_error": 0.1, "relative_error_percent": 5.0, "error": 0.1}
        for _ in range(24)
    ]
    result = model.resolve_forecast_reliability(
        initial_score=38.2, initial_created_at=created,
        now=datetime(2026, 11, 25, 23, 30, tzinfo=timezone.utc),
        evaluations=[{**item, "relative_error_percent": 0.0, "error": 0.0} for item in evaluations],
        history={}, reliability_context={"forecast_impact_weight": 1, "billing_period_start": "2026-01-01", "billing_period_end": "2026-11-25"}, method="linear_elapsed_period_average",
    )
    assert result["forecast_reliability_percent"] == 95.0
    assert result["forecast_reliability_temporal_ceiling"] == 95.0
    assert result["forecast_reliability_basis"] == "measured_forecast_accuracy_and_billing_period_coverage"
    assert result["forecast_reliability_is_initial"] is False


def test_reliability_fallback_is_deterministic_and_never_random():
    model = _load("forecast_model", INTEGRATION / "forecast_model.py")
    kwargs = dict(
        initial_score=38.2,
        initial_created_at=datetime(2026, 11, 25, 0, 0, tzinfo=timezone.utc),
        now=datetime(2026, 11, 25, 1, 0, tzinfo=timezone.utc),
        evaluations=[],
        history={"history_months": 12, "coverage_percent": 80, "quality": 70, "sample_count": 40},
        reliability_context={"forecast_factors": {"meter": 80}, "forecast_impact_weight": 1},
        method="linear_elapsed_period_average",
    )
    first = model.resolve_forecast_reliability(**kwargs)
    second = model.resolve_forecast_reliability(**kwargs)
    assert first["forecast_reliability_percent"] == second["forecast_reliability_percent"]
    assert first["forecast_reliability_available"] is False
    assert first["forecast_reliability_percent"] is None


def test_empty_feed_in_orientation_means_neutral_mix_not_implicit_south():
    model = _load("forecast_model", INTEGRATION / "forecast_model.py")
    day = date(2026, 6, 21)
    neutral = model.historical_solar_adjustment(
        day, direction="feed_in", latitude=53.5, longitude=8.1,
        timezone_info=ZoneInfo("Europe/Berlin"), orientations=[],
    )
    all_directions = model.historical_solar_adjustment(
        day, direction="feed_in", latitude=53.5, longitude=8.1,
        timezone_info=ZoneInfo("Europe/Berlin"),
        orientations=["north", "east", "south", "west"],
    )
    assert neutral == all_directions


def test_runtime_sensor_passes_live_time_and_all_account_adjustments():
    source = (INTEGRATION / "sensor.py").read_text(encoding="utf-8")
    assert '"as_of": now_local' in source
    assert '"period_end_override": end_date.isoformat()' in source
    assert '"additional_payments": booking_payments' in source
    assert '"credits": booking_credits' in source
    assert '"corrections": booking_corrections' in source
    assert 'else _Decimal(str(self._data.get("feed_in_monthly_advance", 0) or 0)) * vat_factor' in source
    assert 'overrides.get(cursor.strftime("%Y-%m"), default_gross)' in source
    assert 'resolve_forecast_reliability(' in source


def test_reliability_card_explains_learning_after_start_value_expires():
    card = (INTEGRATION / "frontend" / "verbrauchsmonitor-card.js").read_text(encoding="utf-8")
    assert "forecast_reliability_pending === true" in card
    assert 't("wird ermittelt", "being determined")' in card
    assert 't("(vorläufiger Startwert)", "(provisional starting value)")' in card


def test_live_and_forecast_base_price_freeze_at_the_same_billing_period_boundary():
    sensor = (INTEGRATION / "sensor.py").read_text(encoding="utf-8")
    assert "base_gross = accrued_annual_base_price(" in sensor
    assert "billing_start_dt, period_end_dt" in sensor
    assert "base_gross_annual * Decimal(max(1, int(configured_duration))) / Decimal(12)" not in sensor


def test_feed_in_monthly_advance_editor_uses_contract_gross_amount():
    source = (INTEGRATION / "config_flow.py").read_text(encoding="utf-8")
    assert '_feed_in_monthly_advance_net(contract)' in source
    assert 'default = gross_from_net(' in source
    assert 'default = meter.get("feed_in_monthly_advance", 0)' not in source


def test_feed_in_orientation_changes_forecasted_energy_and_money_not_only_metadata():
    forecast = _load("forecast", INTEGRATION / "forecast.py")
    now = datetime(2026, 1, 10, 12, 0, tzinfo=ZoneInfo("Europe/Berlin"))
    history = {
        "usable": True,
        "history_months": 12,
        "two_cycle_months": 0,
        "monthly_daily_kwh": {str(month): 20.0 for month in range(1, 13)},
    }
    common = dict(
        direction="feed_in", current_reading="1000", baseline_reading="900",
        period_start="2026-01-01", today=now.date(), as_of=now,
        period_end_override="2026-12-31", period_months=12,
        price_net="34.2006", vat_rate=0, history=history,
        latitude=53.5, longitude=8.1, local_timezone=ZoneInfo("Europe/Berlin"),
    )
    south = forecast.calculate_forecast(**common, feed_in_directions=["south"])
    east = forecast.calculate_forecast(**common, feed_in_directions=["east"])
    assert south["annual_energy_kwh"] != east["annual_energy_kwh"]
    assert south["annual_value_eur"] != east["annual_value_eur"]
    assert south["expected_year_end_balance_eur"] != east["expected_year_end_balance_eur"]


def test_fixed_screenshot_reference_case_accounts_for_correction_and_gross_feed_in_advance():
    forecast = _load("forecast", INTEGRATION / "forecast.py")
    now = datetime(2026, 11, 25, 23, 56, tzinfo=ZoneInfo("Europe/Berlin"))
    consumption = forecast.calculate_forecast(
        direction="consumption", current_reading="5024.851", baseline_reading="3164.000",
        period_start="2026-08-01", today=now.date(), as_of=now,
        period_end_override="2026-12-31", period_months=5,
        price_net="23.7647058824", vat_rate=19,
        annual_base_price_net="201.36134454", booked_advances="800",
        future_scheduled_advances="200", corrections="-66",
    )
    feed_in = forecast.calculate_forecast(
        direction="feed_in", current_reading="5440.059", baseline_reading="58.000",
        period_start="2026-01-01", today=now.date(), as_of=now,
        period_end_override="2026-12-31", period_months=12,
        price_net="28.74", vat_rate=19, booked_advances="1496",
        future_scheduled_advances="136",
    )
    # Fixed linear reference only (no Recorder history or location prior):
    # the live installation may differ when its seasonal/solar evidence is used.
    assert consumption["expected_year_end_balance_eur"] == 145.37
    assert consumption["corrections_eur"] == -66.0
    assert consumption["accrued_base_price_eur"] == 76.81
    assert feed_in["expected_year_end_balance_eur"] == 410.13
    assert feed_in["accrued_energy_cost_eur"] == 1840.70
    assert feed_in["future_scheduled_advances_eur"] == 136.0


def test_feed_in_monthly_advance_editor_defaults_to_contract_gross_like_consumption():
    """A feed-in contract entered as 136 EUR gross must show 136 EUR in each
    month without an explicit override, rather than the old meter-level zero.
    Explicit per-month overrides remain authoritative, including zero.
    """
    pricing = _load("pricing", INTEGRATION / "pricing.py")
    net_advance = Decimal("136.00") / Decimal("1.19")
    gross_advance = Decimal(str(pricing.gross_from_net(net_advance, 19)))
    assert gross_advance.quantize(Decimal("0.01")) == Decimal("136.00")

    # The database helper falls back to the contract default when a month has
    # not been individually edited; an explicit override (including zero)
    # remains authoritative.
    import types
    if "homeassistant.core" not in sys.modules:
        ha = types.ModuleType("homeassistant")
        core = types.ModuleType("homeassistant.core")
        core.HomeAssistant = object
        ha.core = core
        sys.modules.setdefault("homeassistant", ha)
        sys.modules.setdefault("homeassistant.core", core)
    db = _load("database", INTEGRATION / "database.py")
    meter_id = "feed-meter-1"
    empty_ledger = {"monthly_advances": []}
    assert db.get_monthly_advance(
        empty_ledger, meter_id=meter_id, direction="feed_in",
        month="2026-01", default=float(gross_advance),
    ) == 136.0
    explicit_zero = {"monthly_advances": [{
        "meter_id": meter_id, "direction": "feed_in",
        "month": "2026-01", "amount": 0.0, "source": "manual",
    }]}
    assert db.get_monthly_advance(
        explicit_zero, meter_id=meter_id, direction="feed_in",
        month="2026-01", default=float(gross_advance),
    ) == 0.0

    # R128 could save its erroneous zero defaults. Those legacy records have
    # no source marker and now fall back to the configured contract advance;
    # a new, explicitly manual zero remains zero.
    legacy_zero = {"monthly_advances": [{
        "meter_id": meter_id, "direction": "feed_in",
        "month": "2026-02", "amount": 0.0,
    }]}
    assert db.get_monthly_advance(
        legacy_zero, meter_id=meter_id, direction="feed_in",
        month="2026-02", default=float(gross_advance),
    ) == 136.0
    manual_zero = {"monthly_advances": [{
        "meter_id": meter_id, "direction": "feed_in",
        "month": "2026-03", "amount": 0.0, "source": "manual",
    }]}
    assert db.get_monthly_advance(
        manual_zero, meter_id=meter_id, direction="feed_in",
        month="2026-03", default=float(gross_advance),
    ) == 0.0

    assert '_feed_in_monthly_advance_net(contract)' in (
        INTEGRATION / "config_flow.py"
    ).read_text(encoding="utf-8")

    config = (INTEGRATION / "config_flow.py").read_text(encoding="utf-8")
    marker = config.index("# Feed-in monthly advances")
    branch_start = config.rfind("        else:", 0, marker)
    feed_branch = config[branch_start:config.index("        fields = {}", marker)]
    assert 'gross_from_net(' in feed_branch
    assert '_feed_in_monthly_advance_net(contract)' in feed_branch
    assert 'contract.get("vat_rate", 19)' in feed_branch
