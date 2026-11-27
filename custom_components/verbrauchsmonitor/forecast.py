"""Deterministic, direction-specific annual and monthly forecasts.

Recorder samples are evaluated independently per meter/direction. Seasonal
weighting is only enabled after the agreed minimum history thresholds; missing
or poor-quality history always falls back to the linear method.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import date, datetime, time, timezone, timedelta
from decimal import Decimal, ROUND_HALF_UP

CENT = Decimal("0.01")


def season_for_month(month: int, hemisphere: str = "north") -> str:
    """Return the meteorological month group for the selected hemisphere."""
    north = {
        1: "winter", 2: "winter", 3: "spring", 4: "spring", 5: "spring",
        6: "summer", 7: "summer", 8: "summer", 9: "autumn", 10: "autumn",
        11: "autumn", 12: "winter",
    }
    if hemisphere not in ("north", "south"):
        raise ValueError("hemisphere must be 'north' or 'south'")
    if month not in range(1, 13):
        raise ValueError("month must be between 1 and 12")
    return north[month if hemisphere == "north" else ((month + 5) % 12) + 1]


def evaluate_history(samples, *, today: date, minimum_months: int = 12) -> dict:
    """Evaluate cumulative counter samples without inventing missing values.

    Samples are ``(timestamp, value)`` pairs. Duplicate timestamps are
    collapsed, decreases are treated as meter resets/invalid intervals, and
    intervals longer than 14 days reduce coverage and plausibility.
    """
    parsed = {}
    for timestamp, raw_value in samples or []:
        try:
            if isinstance(timestamp, datetime):
                when = timestamp
            elif isinstance(timestamp, (int, float)):
                when = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            else:
                when = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
            if when.tzinfo is None:
                when = when.replace(tzinfo=timezone.utc)
            when = when.astimezone(timezone.utc)
            value = Decimal(str(raw_value))
            if value.is_finite() and value >= 0:
                parsed[when] = value
        except (TypeError, ValueError, ArithmeticError):
            continue
    points = sorted(parsed.items())
    if len(points) < 2:
        return {"usable": False, "history_months": 0, "coverage_percent": 0, "gap_days_max": 0, "monthly_daily_kwh": {}, "sample_count": len(points), "quality": 0}
    first, last = points[0][0], points[-1][0]
    span_days = max(0.0, (last - first).total_seconds() / 86400)
    history_months = max(0, (last.year - first.year) * 12 + last.month - first.month - (last.day < first.day))
    valid_days = 0.0
    gap_days_max = 0.0
    monthly_energy = defaultdict(Decimal)
    monthly_days = defaultdict(float)
    years_by_month = defaultdict(set)
    invalid = 0
    for (t1, v1), (t2, v2) in zip(points, points[1:]):
        days = (t2 - t1).total_seconds() / 86400
        if days <= 0:
            continue
        gap_days_max = max(gap_days_max, days)
        delta = v2 - v1
        if delta < 0:
            invalid += 1
            continue
        # A cumulative interval is attributed to its midpoint month. This is
        # intentionally conservative; intervals crossing a month boundary
        # are not artificially split without intermediate readings.
        midpoint = t1 + (t2 - t1) / 2
        key = midpoint.month
        monthly_energy[key] += delta
        monthly_days[key] += days
        years_by_month[key].add(midpoint.year)
        if days <= 14:
            valid_days += days
    coverage = min(100.0, valid_days / max(span_days, 1.0) * 100)
    distinct_months = len(monthly_energy)
    plausible_ratio = max(0.0, 1 - invalid / max(len(points) - 1, 1))
    gap_factor = 1.0 if gap_days_max <= 14 else max(0.0, 1 - (gap_days_max - 14) / 90)
    quality = int(round(coverage * 0.45 + plausible_ratio * 100 * 0.35 + gap_factor * 100 * 0.20))
    daily = {str(month): float(monthly_energy[month] / Decimal(str(max(monthly_days[month], 1)))) for month in monthly_energy if monthly_days[month] > 0}
    two_cycle_months = sum(1 for years in years_by_month.values() if len(years) >= 2)
    enough = history_months >= minimum_months and coverage >= 50 and distinct_months >= 6 and invalid == 0
    return {"usable": enough, "history_months": history_months, "coverage_percent": round(coverage, 1), "gap_days_max": round(gap_days_max, 1), "monthly_daily_kwh": daily, "sample_count": len(points), "quality": quality, "distinct_months": distinct_months, "two_cycle_months": two_cycle_months}


def seasonal_energy_projection(*, current_reading, baseline_reading, period_start: str,
                                today: date, period_months: int, history: dict,
                                season: str | None = None, hemisphere: str = "north",
                                direction: str = "consumption", latitude: float | None = None,
                                longitude: float | None = None, timezone_info=None,
                                orientations: list[str] | None = None,
                                as_of: datetime | None = None,
                                period_end_override: str | None = None) -> Decimal | None:
    """Project energy through the final billing day using only future time.

    The measured counter delta is authoritative through ``as_of``. For the
    remainder, historical calendar-month rates are shaped by season and local
    solar geometry. When an aware ``as_of`` is supplied, only the remaining
    fraction of the current day is projected; the current day is never counted
    twice and the complete final billing day is included.
    """
    months = int(period_months or 12)
    history_months = int(history.get("history_months", 0))
    rates = history.get("monthly_daily_kwh") or {}
    if history_months < 12 or not rates or not history.get("usable", False):
        return None
    if history_months >= 24 and int(history.get("two_cycle_months", 0)) < 10:
        return None
    start = date.fromisoformat(str(period_start)[:10])
    observed = max(Decimal("0"), Decimal(str(current_reading)) - Decimal(str(baseline_reading or 0)))
    end_month_index = start.year * 12 + start.month - 1 + months
    period_end = (date.fromisoformat(str(period_end_override)[:10])
                  if period_end_override else
                  date(end_month_index // 12, end_month_index % 12 + 1, 1) - timedelta(days=1))
    end_month = period_end + timedelta(days=1)
    if as_of is not None and as_of.tzinfo is not None:
        projection_today = as_of.date()
        current_midnight = datetime.combine(projection_today, time.min, tzinfo=as_of.tzinfo)
        next_midnight = datetime.combine(projection_today + timedelta(days=1), time.min, tzinfo=as_of.tzinfo)
        day_seconds = (next_midnight.astimezone(timezone.utc) - current_midnight.astimezone(timezone.utc)).total_seconds()
        remaining_seconds = (next_midnight.astimezone(timezone.utc) - as_of.astimezone(timezone.utc)).total_seconds()
        current_day_fraction = max(0.0, min(1.0, remaining_seconds / day_seconds)) if day_seconds > 0 else 0.0
    else:
        projection_today = today
        current_day_fraction = 1.0
    if projection_today > period_end:
        return observed

    season_order = ("spring", "summer", "autumn", "winter")
    calendar_season_by_month = {month: season_for_month(month, hemisphere) for month in range(1, 13)}
    current_calendar_season = calendar_season_by_month[projection_today.month]
    selected_season = season if season in season_order else current_calendar_season
    season_shift = (season_order.index(selected_season) - season_order.index(current_calendar_season)) % 4
    seasonal_rates = {}
    for season_name in season_order:
        month_values = [Decimal(str(rates[str(month)])) for month, mapped in calendar_season_by_month.items()
                        if mapped == season_name and str(month) in rates]
        if month_values:
            seasonal_rates[season_name] = sum(month_values, Decimal("0")) / Decimal(len(month_values))

    projected = observed
    cursor = date(projection_today.year, projection_today.month, 1)
    while cursor < end_month:
        month_start = max(cursor, projection_today)
        month_end = min(
            date(cursor.year + (cursor.month == 12), 1 if cursor.month == 12 else cursor.month + 1, 1),
            end_month,
        )
        calendar_season = calendar_season_by_month[cursor.month]
        shifted_season = season_order[(season_order.index(calendar_season) + season_shift) % 4]
        monthly_rate = Decimal(str(rates.get(str(cursor.month), 0)))
        seasonal_rate = seasonal_rates.get(shifted_season, monthly_rate)
        base_rate = monthly_rate * Decimal("0.75") + seasonal_rate * Decimal("0.25")
        for offset in range(max(0, (month_end - month_start).days)):
            day = month_start + timedelta(days=offset)
            fraction = current_day_fraction if day == projection_today else 1.0
            if fraction <= 0:
                continue
            solar_factor = 1.0
            if latitude is not None and longitude is not None and timezone_info is not None:
                from .forecast_model import historical_solar_adjustment
                solar_factor = historical_solar_adjustment(
                    day, direction=direction, latitude=float(latitude),
                    longitude=float(longitude), timezone_info=timezone_info,
                    orientations=orientations,
                )
            projected += base_rate * Decimal(str(solar_factor)) * Decimal(str(fraction))
        cursor = month_end
    return max(observed, projected)



def calendar_season_projection(*, observed_energy, today: date, period_end: date,
                               history: dict, hemisphere: str = "north",
                               as_of: datetime | None = None) -> Decimal | None:
    """Independent model 3: project from meteorological-season daily averages.

    Unlike the monthly/solar model, this model uses only the historical average
    daily energy of the matching calendar season. It requires at least 12 months
    of usable history and never substitutes missing seasonal evidence with zero.
    """
    if not history.get("usable") or int(history.get("history_months", 0)) < 12:
        return None
    rates = history.get("monthly_daily_kwh") or {}
    if not rates or period_end < today:
        return None
    season_rates: dict[str, list[Decimal]] = defaultdict(list)
    for month_text, raw_rate in rates.items():
        try:
            month = int(month_text)
            rate = Decimal(str(raw_rate))
        except (TypeError, ValueError, ArithmeticError):
            continue
        if month not in range(1, 13) or not rate.is_finite() or rate < 0:
            continue
        season_rates[season_for_month(month, hemisphere)].append(rate)
    if not season_rates:
        return None
    # Require evidence for every season that will be projected.
    remaining_fraction = Decimal("1")
    if as_of is not None and as_of.tzinfo is not None:
        local_now = as_of
        midnight = datetime.combine(local_now.date(), time.min, tzinfo=local_now.tzinfo)
        next_midnight = datetime.combine(local_now.date() + timedelta(days=1), time.min, tzinfo=local_now.tzinfo)
        total = (next_midnight.astimezone(timezone.utc) - midnight.astimezone(timezone.utc)).total_seconds()
        left = (next_midnight.astimezone(timezone.utc) - local_now.astimezone(timezone.utc)).total_seconds()
        remaining_fraction = Decimal(str(max(0.0, min(1.0, left / total)))) if total else Decimal("0")
    projected = Decimal(str(max(0.0, float(observed_energy))))
    cursor = today
    while cursor <= period_end:
        season_name = season_for_month(cursor.month, hemisphere)
        values = season_rates.get(season_name)
        if not values:
            return None
        daily_rate = sum(values, Decimal("0")) / Decimal(len(values))
        fraction = remaining_fraction if cursor == today else Decimal("1")
        projected += daily_rate * fraction
        cursor += timedelta(days=1)
    return projected



def reliability_score(*, history: dict, method: str) -> dict:
    """Return a deterministic, evidence-based reliability score.

    Missing or insufficient history is omitted. The active A/B aggregate is
    provided by forecast_model and does not penalize its absence.
    """
    history_months = int(history.get("history_months", 0) or 0)
    sample_count = int(history.get("sample_count", 0) or 0)
    usable = bool(history.get("usable"))
    coverage = float(history.get("coverage_percent", 0) or 0)
    if not usable or history_months < 12 or sample_count < 2 or coverage < 50:
        return {
            "forecast_reliability_percent": None,
            "forecast_reliability_level": None,
            "forecast_reliability_basis": "insufficient_history",
            "forecast_history_months": history_months,
            "forecast_reliability_available": False,
        }

    length_score = min(100.0, history_months / 24 * 100)
    interval_days = float(history.get("gap_days_max", 999) or 999)
    interval_score = 100.0 if interval_days <= 7 else max(0.0, 100.0 - (interval_days - 7) * 1.5)
    plausibility_score = max(0.0, min(100.0, float(history.get("quality", 0) or 0)))
    method_score = 100.0 if method == "seasonal_24m" else 90.0 if method == "seasonal_12m" else 65.0
    evidence = (
        length_score * 0.20
        + coverage * 0.25
        + interval_score * 0.15
        + plausibility_score * 0.20
        + method_score * 0.20
    )
    # Reflect the evidence directly; there is no artificial score floor.
    score = round(max(0.0, min(100.0, evidence)), 1)
    level = "high" if score >= 80 else "medium" if score >= 50 else "low"
    return {
        "forecast_reliability_percent": score,
        "forecast_reliability_level": level,
        "forecast_reliability_basis": "history_length_coverage_intervals_plausibility_method",
        "forecast_history_months": history_months,
        "forecast_reliability_available": True,
    }



def initial_reliability_state(*, now: datetime | None = None) -> dict:
    """Return an empty legacy-compatible state; no score is initialized."""
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return {"score": None, "last_evaluated": current.astimezone(timezone.utc).isoformat()}


def update_reliability_state(state: dict | None, *, history: dict, method: str,
                             now: datetime | None = None, interval_hours: int = 1,
                             max_change_per_day: float = 1.0) -> dict:
    """Recompute reliability directly from evidence; ignore legacy stored scores."""
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    current = current.astimezone(timezone.utc)
    result = reliability_score(history=history, method=method)
    updated = {"score": result["forecast_reliability_percent"], "last_evaluated": current.isoformat()}
    # The one-time installation seed is independent from measured reliability
    # and must survive every hourly/daily evidence refresh.
    if state and state.get("initial_score") is not None:
        updated["initial_score"] = state["initial_score"]
        if state.get("initial_score_created_at"):
            updated["initial_score_created_at"] = state["initial_score_created_at"]
    return updated


def apply_advance_recommendation_limit(*, result: dict, reliability: dict, history: dict) -> dict:
    """Limit the recommended advance relative to the established contract value.

    The unbounded calculated requirement remains available for transparency.
    Limits are applied independently for each meter and direction.
    """
    from copy import deepcopy

    updated = deepcopy(result)
    required = Decimal(str(result.get("recommended_monthly_advance_eur", 0) or 0))
    configured = Decimal(str(result.get("configured_monthly_advance_eur", 0) or 0))
    months = int(history.get("history_months", 0) or 0)
    score = int(reliability.get("forecast_reliability_percent", 0) or 0)

    if months >= 24 and score >= 90:
        limit = Decimal("75.00")
    elif months >= 12 and score >= 80:
        limit = Decimal("50.00")
    else:
        limit = Decimal("30.00")

    # Without a configured advance there is no meaningful baseline to limit
    # against. Keep the calculated value and expose that no limit was applied.
    if configured <= 0:
        recommended = required
        applied = False
        effective_limit = Decimal("0.00")
    else:
        difference = required - configured
        bounded_difference = max(-limit, min(limit, difference))
        recommended = max(Decimal("0.00"), configured + bounded_difference)
        applied = recommended != required
        effective_limit = limit

    updated["recommended_monthly_advance_eur"] = float(recommended.quantize(CENT, rounding=ROUND_HALF_UP))
    updated["uncapped_monthly_advance_eur"] = float(required.quantize(CENT, rounding=ROUND_HALF_UP))
    updated["advance_recommendation_limit_eur"] = float(effective_limit)
    updated["advance_recommendation_limit_applied"] = applied
    updated["advance_recommendation_history_months"] = months
    updated["advance_recommendation_reliability_percent"] = score
    return updated

def calculate_forecast(*, direction: str, current_reading, baseline_reading,
                       period_start: str, today: date, price_net,
                       vat_rate=19, annual_base_price_net=0,
                       monthly_advance_net=0, feed_in_monthly_advance_net=0,
                       period_months=12, history=None, booked_advances=0,
                       future_scheduled_advances=0, season=None, hemisphere="north",
                       accrued_extra_charges=0, latitude=None, longitude=None,
                       local_timezone=None, feed_in_directions=None,
                       as_of: datetime | None = None, period_end_override: str | None = None,
                       additional_payments=0, credits=0, corrections=0) -> dict:
    """Return a full-period forecast, including all time and account adjustments.

    ``as_of`` is the exact local instant represented by the current meter
    reading. The forecast covers the remaining part of that day through the
    final billing day, without dropping or double-counting a calendar day.
    """
    if direction not in ("consumption", "feed_in"):
        raise ValueError("Ungültiger Abrechnungsbereich")
    current, baseline = Decimal(str(current_reading)), Decimal(str(baseline_reading or 0))
    price, vat = Decimal(str(price_net or 0)), Decimal(str(vat_rate or 0))
    if not all(v.is_finite() for v in (current, baseline, price, vat)):
        raise ValueError("Nicht numerische Prognosegrundlage")
    if current < baseline or price < 0 or vat < 0 or vat > 100:
        raise ValueError("Ungültige Prognosegrundlage")
    start = date.fromisoformat(str(period_start)[:10])
    if start > today:
        raise ValueError("Abrechnungszeitraum beginnt in der Zukunft")
    billing_months = max(1, int(period_months or 12))
    end_month_index = start.year * 12 + start.month - 1 + billing_months
    period_end = (date.fromisoformat(str(period_end_override)[:10])
                  if period_end_override else
                  date(end_month_index // 12, end_month_index % 12 + 1, 1) - timedelta(days=1))
    if period_end < start:
        raise ValueError("Abrechnungsende liegt vor dem Abrechnungsbeginn")
    period_days = max(1, (period_end - start).days + 1)

    if as_of is None:
        # Compatibility for pure date-based callers: treat today as beginning
        # of day. Runtime callers always supply the actual aware local instant.
        as_of = datetime.combine(today + timedelta(days=1), time.min)
    if as_of.tzinfo is not None:
        start_dt = datetime.combine(start, time.min, tzinfo=as_of.tzinfo)
        end_exclusive = datetime.combine(period_end + timedelta(days=1), time.min, tzinfo=as_of.tzinfo)
    else:
        start_dt = datetime.combine(start, time.min)
        end_exclusive = datetime.combine(period_end + timedelta(days=1), time.min)
    if as_of.tzinfo is not None:
        # Home Assistant billing periods and daily profiles use local wall time.
        # Subtract aware datetimes with the same configured timezone so a DST
        # clock change does not create or remove a fraction of a billing day.
        elapsed_seconds = (as_of - start_dt).total_seconds()
        remaining_seconds = (end_exclusive - as_of).total_seconds()
        elapsed_days = min(float(period_days), max(1.0 / 86400.0, elapsed_seconds / 86400.0))
        remaining_days = max(0.0, remaining_seconds / 86400.0)
    else:
        # Date-only compatibility: the current day is considered fully elapsed.
        elapsed_days = min(float(period_days), max(1.0, (today - start).days + 1.0))
        remaining_days = max(0.0, float(period_days) - elapsed_days)
    delta = current - baseline
    history = history or {}
    seasonal_energy = seasonal_energy_projection(
        current_reading=current, baseline_reading=baseline,
        period_start=period_start, today=today, period_months=billing_months,
        history=history, season=season, hemisphere=hemisphere,
        direction=direction, latitude=latitude, longitude=longitude,
        timezone_info=local_timezone, orientations=feed_in_directions,
        as_of=as_of if as_of.tzinfo is not None else None,
        period_end_override=period_end.isoformat(),
    )
    model_results = {}
    if seasonal_energy is not None:
        model_results["historical_monthly_seasonal"] = seasonal_energy

    # Existing model 2: normalized solar/hourly profile. It remains independent
    # and is evaluated even when model 1 has sufficient history.
    if latitude is not None and longitude is not None and local_timezone is not None:
        from .forecast_model import profile_adjusted_projection
        adjusted = profile_adjusted_projection(
            observed_energy=float(delta), elapsed_days=elapsed_days,
            remaining_days=remaining_days, today=today, direction=direction,
            latitude=float(latitude), longitude=float(longitude),
            timezone_info=local_timezone, orientations=feed_in_directions,
            now=as_of if as_of.tzinfo is not None else None,
        )
        model_results["solar_profile"] = Decimal(str(adjusted))

    # Independent model 3: calendar season averages, without solar correction.
    model3 = calendar_season_projection(
        observed_energy=delta, today=(as_of.date() if as_of and as_of.tzinfo else today),
        period_end=period_end, history=history, hemisphere=hemisphere,
        as_of=as_of,
    )
    if model3 is not None:
        model_results["calendar_season"] = model3

    if model_results:
        # Evidence-weighted ensemble. Model 3 is deliberately conservative and
        # receives a lower weight; unavailable models do not enter the average.
        history_quality = max(0.10, min(1.0, float(history.get("quality", 0) or 0) / 100.0))
        weights = {
            "historical_monthly_seasonal": Decimal("0.40") * Decimal(str(history_quality)),
            "solar_profile": Decimal("0.40"),
            "calendar_season": Decimal("0.20") * Decimal(str(history_quality)),
        }
        active_weights = {key: weights[key] for key in model_results}
        active_weight = sum(active_weights.values(), Decimal("0"))
        normalized_weights = {key: weight / active_weight for key, weight in active_weights.items()}
        annual_energy = sum((value * normalized_weights[key] for key, value in model_results.items()), Decimal("0"))
        annual_energy = max(delta, annual_energy)
        method = (
            "seasonal_24m" if seasonal_energy is not None and int(history.get("history_months", 0)) >= 24
            else "seasonal_12m" if seasonal_energy is not None
            else "initial_profile_prior"
        )
    else:
        annual_energy = delta * Decimal(str(elapsed_days + remaining_days)) / Decimal(str(elapsed_days))
        method = "linear_elapsed_period_average"

    gross_factor = Decimal(1) + vat / Decimal(100)
    accrued_energy_value = (delta * price / Decimal(100) * gross_factor).quantize(CENT, rounding=ROUND_HALF_UP)
    annual_base_gross = Decimal(str(annual_base_price_net or 0)) * gross_factor if direction == "consumption" else Decimal("0")
    try:
        from .pricing import accrued_annual_base_price
    except ImportError:  # standalone pure-module tests
        from importlib.util import module_from_spec, spec_from_file_location
        from pathlib import Path
        pricing_path = Path(__file__).with_name("pricing.py")
        pricing_spec = spec_from_file_location("vm_forecast_pricing", pricing_path)
        pricing_module = module_from_spec(pricing_spec)
        pricing_spec.loader.exec_module(pricing_module)
        accrued_annual_base_price = pricing_module.accrued_annual_base_price
    projected_base_value = accrued_annual_base_price(annual_base_gross, start_dt, end_exclusive)
    accrued_base = accrued_annual_base_price(annual_base_gross, start_dt, min(as_of, end_exclusive))
    extra_charges_value = Decimal(str(accrued_extra_charges or 0)).quantize(CENT, rounding=ROUND_HALF_UP)
    if not extra_charges_value.is_finite() or extra_charges_value < 0:
        raise ValueError("Ungültige bereits angefallene Zusatzkosten")

    # One-off extra charges are included once. They must not be extrapolated as
    # if they were recurring daily energy/base-price costs.
    # The monetary projection must use the same forecasted energy quantity
    # that was shaped by Recorder history, astronomical season, solar position,
    # sunrise/sunset and (for feed-in) the configured panel orientations.
    # A separate straight-line cost extrapolation here would silently discard
    # those model inputs even though annual_energy_kwh had used them.
    remaining_energy_kwh = max(Decimal("0"), annual_energy - delta)
    remaining_energy_value = (
        remaining_energy_kwh * price / Decimal(100) * gross_factor
    ).quantize(CENT, rounding=ROUND_HALF_UP)
    remaining_base_value = max(Decimal("0"), projected_base_value - accrued_base).quantize(CENT, rounding=ROUND_HALF_UP)
    remaining_cost_value = remaining_energy_value + remaining_base_value
    annual_value = (
        accrued_energy_value + accrued_base + extra_charges_value
        + remaining_energy_value + remaining_base_value
    ).quantize(CENT, rounding=ROUND_HALF_UP)
    projected_energy_value = (accrued_energy_value + remaining_energy_value).quantize(CENT, rounding=ROUND_HALF_UP)

    booked = Decimal(str(booked_advances or 0))
    future_scheduled = Decimal(str(future_scheduled_advances or 0))
    additional = Decimal(str(additional_payments or 0))
    credit_amount = Decimal(str(credits or 0))
    correction_amount = Decimal(str(corrections or 0))
    if any(not value.is_finite() for value in (booked, future_scheduled, additional, credit_amount, correction_amount)):
        raise ValueError("Ungültige gebuchte oder erwartete Zahlungen")
    if any(value < 0 for value in (booked, future_scheduled, additional, credit_amount)):
        raise ValueError("Gebuchte Zahlungen und Gutschriften dürfen nicht negativ sein")

    # Apply the same customer-account sign convention as the live balance
    # sensor. Payments, credits and signed corrections are not discarded.
    direction_sign = Decimal(-1) if direction == "consumption" else Decimal(1)
    signed_balance = (
        direction_sign * (annual_value - booked - future_scheduled)
        + additional + credit_amount + correction_amount
    ).quantize(CENT, rounding=ROUND_HALF_UP)
    remaining_amount = max(
        Decimal("0"), -signed_balance if direction == "consumption" else signed_balance
    )
    months_remaining = 0
    cursor = date(today.year, today.month, 1)
    if cursor <= today:
        cursor = date(cursor.year + (cursor.month == 12), 1 if cursor.month == 12 else cursor.month + 1, 1)
    first_due = date(start.year, start.month, 1)
    if first_due < start:
        first_due = date(first_due.year + (first_due.month == 12), 1 if first_due.month == 12 else first_due.month + 1, 1)
    if cursor < first_due:
        cursor = first_due
    while cursor <= period_end:
        months_remaining += 1
        cursor = date(cursor.year + (cursor.month == 12), 1 if cursor.month == 12 else cursor.month + 1, 1)
    recommendation_available = months_remaining >= 2 and remaining_amount > CENT
    monthly_target = (
        (remaining_amount / Decimal(months_remaining)).quantize(CENT, rounding=ROUND_HALF_UP)
        if recommendation_available else Decimal("0.00")
    )
    configured = Decimal(str(monthly_advance_net or 0)) * gross_factor if direction == "consumption" else Decimal(str(feed_in_monthly_advance_net or 0))
    return {
        "annual_energy_kwh": float(annual_energy.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)),
        "forecast_models_used": sorted(model_results),
        "forecast_model_outputs_kwh": {key: float(value) for key, value in model_results.items()},
        "forecast_model_weights": {key: float(value) for key, value in normalized_weights.items()} if model_results else {},
        "annual_value_eur": float(annual_value),
        "forecast_energy_cost_total_eur": float(projected_energy_value),
        "forecast_base_price_total_eur": float(projected_base_value),
        "accrued_energy_cost_eur": float(accrued_energy_value),
        "accrued_base_price_eur": float(accrued_base),
        "accrued_extra_charges_eur": float(extra_charges_value),
        "remaining_energy_kwh": float(remaining_energy_kwh.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)),
        "remaining_energy_cost_eur": float(remaining_energy_value),
        "remaining_base_price_eur": float(remaining_base_value),
        "remaining_costs_including_base_price_eur": float(remaining_cost_value),
        "expected_year_end_balance_eur": float(signed_balance),
        "recommended_monthly_advance_eur": float(monthly_target),
        "configured_monthly_advance_eur": float(configured.quantize(CENT, rounding=ROUND_HALF_UP)),
        "advance_recommendation_minimum_eur": 0.0,
        "advance_recommendation_final_period_protection": months_remaining < 2,
        "forecast_recommendation_available": recommendation_available,
        "forecast_recommendation_unavailable_reason": (
            "final_payment_period" if months_remaining < 2 else
            "no_remaining_payment_gap" if remaining_amount <= CENT else None
        ),
        "booked_advances_eur": float(booked.quantize(CENT, rounding=ROUND_HALF_UP)),
        "future_scheduled_advances_eur": float(future_scheduled.quantize(CENT, rounding=ROUND_HALF_UP)),
        "additional_payments_eur": float(additional.quantize(CENT, rounding=ROUND_HALF_UP)),
        "credits_eur": float(credit_amount.quantize(CENT, rounding=ROUND_HALF_UP)),
        "corrections_eur": float(correction_amount.quantize(CENT, rounding=ROUND_HALF_UP)),
        "months_remaining": months_remaining,
        "method": method,
        "basis_days": round(elapsed_days, 6),
        "remaining_days_fraction": round(remaining_days, 6),
        "period_days": period_days,
        "period_end": period_end.isoformat(),
    }

