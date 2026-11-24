"""Deterministic, direction-specific annual and monthly forecasts.

Recorder samples are evaluated independently per meter/direction. Seasonal
weighting is only enabled after the agreed minimum history thresholds; missing
or poor-quality history always falls back to the linear method.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from datetime import timedelta
import secrets

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


def seasonal_energy_projection(*, current_reading, baseline_reading, period_start: str, today: date, period_months: int, history: dict, season: str | None = None, hemisphere: str = "north") -> Decimal | None:
    """Project period energy from historical calendar-month daily rates.

    At 12–23 months, one observed annual cycle is used. From 24 months, at
    least two cycles must exist; month rates are then averaged by calendar
    month. Unobserved months use the current linear rate as fallback.
    """
    months = int(period_months or 12)
    history_months = int(history.get("history_months", 0))
    rates = history.get("monthly_daily_kwh") or {}
    if history_months < 12 or not rates or not history.get("usable", False):
        return None
    if history_months >= 24 and int(history.get("two_cycle_months", 0)) < 10:
        return None
    start = date.fromisoformat(str(period_start)[:10])
    elapsed_days = max(1, (today - start).days + 1)
    observed = max(Decimal("0"), Decimal(str(current_reading)) - Decimal(str(baseline_reading or 0)))
    linear_daily = observed / Decimal(elapsed_days)
    # Use calendar-day weighting over the remaining billing period. The
    # observed portion remains authoritative; history shapes only the future.
    end_month_index = start.year * 12 + start.month - 1 + months
    end_year, end_month0 = divmod(end_month_index, 12)
    end_month = end_month0 + 1
    cursor = date(today.year, today.month, 1)
    projected = observed
    season_order = ("spring", "summer", "autumn", "winter")
    calendar_season_by_month = {
        month: season_for_month(month, hemisphere) for month in range(1, 13)
    }
    current_calendar_season = calendar_season_by_month[today.month]
    selected_season = season if season in season_order else current_calendar_season
    season_shift = (season_order.index(selected_season) - season_order.index(current_calendar_season)) % 4
    seasonal_rates = {}
    for season_name in season_order:
        month_values = [Decimal(str(rates[str(month)])) for month, mapped in calendar_season_by_month.items()
                        if mapped == season_name and str(month) in rates]
        if month_values:
            seasonal_rates[season_name] = sum(month_values, Decimal("0")) / Decimal(len(month_values))
    while (cursor.year, cursor.month) < (end_year, end_month):
        month_start = max(cursor, date(today.year, today.month, today.day))
        month_end = date(cursor.year + (cursor.month == 12), 1 if cursor.month == 12 else cursor.month + 1, 1)
        days = max(0, (month_end - month_start).days)
        calendar_season = calendar_season_by_month[cursor.month]
        shifted_season = season_order[(season_order.index(calendar_season) + season_shift) % 4]
        monthly_rate = Decimal(str(rates.get(str(cursor.month), linear_daily)))
        seasonal_rate = seasonal_rates.get(shifted_season, monthly_rate)
        # Monthly profile remains dominant; the selected/automatic season
        # provides a modest correction based on the observed seasonal group.
        rate = monthly_rate * Decimal("0.75") + seasonal_rate * Decimal("0.25")
        projected += rate * days
        cursor = month_end
    return max(observed, projected)


def reliability_score(*, history: dict, method: str) -> dict:
    """Calculate a transparent 0–100 target score from data and method quality."""
    history_months = int(history.get("history_months", 0))
    length_score = min(100, history_months / 24 * 100)
    coverage_score = min(100, max(0, float(history.get("coverage_percent", 0))))
    interval_score = 100 if float(history.get("gap_days_max", 999)) <= 7 else max(0, 100 - max(0, float(history.get("gap_days_max", 999)) - 7) * 1.5)
    plausibility_score = float(history.get("quality", 0))
    method_score = 95 if method == "seasonal_24m" else 85 if method == "seasonal_12m" else 55 if history_months else 0
    # The measured consumption/cost basis contributes a fixed 40 % foundation.
    # History length, coverage, interval quality, plausibility and method quality
    # contribute the remaining 60 %. This keeps the target at or above 40 % once
    # an evidence-based reassessment has taken place.
    supporting_quality = (
        length_score * .20
        + coverage_score * .25
        + interval_score * .15
        + plausibility_score * .20
        + method_score * .20
    )
    score = int(round(40 + supporting_quality * .60))
    if score >= 80:
        level = "high"
    elif score >= 50:
        level = "medium"
    else:
        level = "low"
    return {"forecast_reliability_percent": score, "forecast_reliability_level": level, "forecast_reliability_basis": "history_length_coverage_intervals_plausibility_method", "forecast_history_months": history_months}



def initial_reliability_state(*, now: datetime | None = None) -> dict:
    """Create a stable, randomized starting value for one forecast cycle.

    The value is stored by the sensor and is never randomized on refresh.
    Integer tenths avoid floating-point boundary errors (37.6–44.3 %).
    """
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return {
        "score": (376 + secrets.randbelow(68)) / 10,
        "last_evaluated": current.astimezone(timezone.utc).isoformat(),
    }


def update_reliability_state(state: dict | None, *, history: dict, method: str,
                             now: datetime | None = None, interval_hours: int = 1,
                             max_change_per_day: float = 1.0) -> dict:
    """Move reliability gradually toward the evidence-based target.

    The target is recalculated from cached history. Updates may run hourly,
    but the score can move by at most ``max_change_per_day`` percentage points
    per elapsed day. Only the current state is persisted; no time series is
    written to the database.
    """
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    current = current.astimezone(timezone.utc)
    if not state or "score" not in state or "last_evaluated" not in state:
        return initial_reliability_state(now=current)
    try:
        last = datetime.fromisoformat(str(state["last_evaluated"]).replace("Z", "+00:00"))
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        last = last.astimezone(timezone.utc)
        score = float(state["score"])
        if not 0 <= score <= 100:
            raise ValueError("Reliability score out of range")
    except (TypeError, ValueError):
        return initial_reliability_state(now=current)
    elapsed_seconds = max(0.0, (current - last).total_seconds())
    if elapsed_seconds < interval_hours * 3600:
        return {"score": round(score, 4), "last_evaluated": last.isoformat()}
    target = float(reliability_score(history=history, method=method)["forecast_reliability_percent"])
    allowed_change = max(0.0, float(max_change_per_day)) * elapsed_seconds / 86400.0
    difference = target - score
    change = max(-allowed_change, min(allowed_change, difference))
    # Keep sub-tenth precision internally so hourly 1/24-point increments
    # accumulate instead of being rounded away on every update.
    reassessed = round(score + change, 4)
    return {"score": max(0.0, min(100.0, reassessed)), "last_evaluated": current.isoformat()}


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
                       accrued_extra_charges=0) -> dict:
    """Return annual energy, value, expected balance and remaining monthly target."""
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
    # Derive the exact period end from the configured start date and month
    # duration. Calendar months are not all 30.44 days long.
    from datetime import timedelta
    end_month_index = start.year * 12 + start.month - 1 + billing_months
    period_end = date(end_month_index // 12, end_month_index % 12 + 1, 1) - timedelta(days=1)
    period_days = max(1, (period_end - start).days + 1)
    elapsed_days = min(period_days, max(1, (today - start).days + 1))
    elapsed_for_linear = elapsed_days
    delta = current - baseline
    history = history or {}
    seasonal_energy = seasonal_energy_projection(current_reading=current, baseline_reading=baseline, period_start=period_start, today=today, period_months=billing_months, history=history, season=season, hemisphere=hemisphere)
    if seasonal_energy is not None:
        annual_energy = seasonal_energy
        method = "seasonal_24m" if int(history.get("history_months", 0)) >= 24 else "seasonal_12m"
    else:
        annual_energy = delta * Decimal(period_days) / Decimal(elapsed_for_linear)
        method = "linear_elapsed_period_average"
    gross_factor = Decimal(1) + vat / Decimal(100)
    energy_value = annual_energy * price / Decimal(100) * gross_factor
    # The contract base price is annual; only the configured billing-period
    # share belongs in this forecast (e.g. 5/12 for a five-month period).
    base = (
        Decimal(str(annual_base_price_net or 0)) * gross_factor
        * Decimal(billing_months) / Decimal(12)
        if direction == "consumption" else Decimal(0)
    )
    annual_value = energy_value + base

    # Expose the forecast remainder as a verifiable cost breakdown. The
    # accrued base-price portion follows the same calendar-month rule as the
    # account-balance sensor (start month through current month, inclusive).
    # This makes the remaining amount explicitly include both future energy
    # costs and the still-accruing prorated base price.
    accrued_energy_value = (
        delta * price / Decimal(100) * gross_factor
    ).quantize(CENT, rounding=ROUND_HALF_UP)
    elapsed_base_months = min(
        billing_months,
        max(0, (today.year - start.year) * 12 + today.month - start.month + 1),
    )
    accrued_base = (
        Decimal(str(annual_base_price_net or 0)) * gross_factor
        * Decimal(elapsed_base_months) / Decimal(12)
        if direction == "consumption" else Decimal(0)
    ).quantize(CENT, rounding=ROUND_HALF_UP)
    projected_energy_value = energy_value.quantize(CENT, rounding=ROUND_HALF_UP)
    projected_base_value = base.quantize(CENT, rounding=ROUND_HALF_UP)
    # The agreed linear remainder projection uses the same accrued monthly
    # average as the card. That average already contains the prorated base
    # price, so the base price must not be added a second time. Partial months
    # are weighted by their actual remaining calendar days.
    remaining_days = max(0, (period_end - today).days)
    average_month_days = Decimal("30.436875")
    extra_charges_value = Decimal(str(accrued_extra_charges or 0)).quantize(CENT, rounding=ROUND_HALF_UP)
    if not extra_charges_value.is_finite() or extra_charges_value < 0:
        raise ValueError("Ungültige bereits angefallene Zusatzkosten")
    accrued_total_cost = accrued_energy_value + accrued_base + extra_charges_value
    monthly_average_cost = (
        accrued_total_cost / Decimal(elapsed_days) * average_month_days
        if elapsed_days > 0 else Decimal(0)
    )
    remaining_cost_value = (
        monthly_average_cost * Decimal(remaining_days) / average_month_days
    ).quantize(CENT, rounding=ROUND_HALF_UP)
    # Keep the breakdown useful: the remaining base-price share is already
    # included in the monthly-average projection and is never added twice.
    remaining_base_value = max(Decimal(0), projected_base_value - accrued_base)
    remaining_energy_value = max(Decimal(0), remaining_cost_value - remaining_base_value)
    # Use the same remainder projection for the total forecast, expected
    # account balance and monthly advance recommendation.
    annual_value = accrued_total_cost + remaining_cost_value
    annual_value = annual_value.quantize(CENT, rounding=ROUND_HALF_UP)
    # Reconcile the displayed total energy-cost projection with the linear
    # remaining-cost model (the extra-charge component is already accrued).
    projected_energy_value = max(Decimal(0), annual_value - projected_base_value).quantize(CENT, rounding=ROUND_HALF_UP)

    # Only actual, explicitly booked advances reduce the already-paid amount.
    booked = Decimal(str(booked_advances or 0))
    future_scheduled = Decimal(str(future_scheduled_advances or 0))
    if not booked.is_finite() or booked < 0 or not future_scheduled.is_finite() or future_scheduled < 0:
        raise ValueError("Ungültige gebuchte oder erwartete Abschläge")
    # Count only future contractual monthly due dates inside this period.
    first_due = date(start.year, start.month, 1)
    if first_due < start:
        first_due = date(first_due.year + (first_due.month == 12), 1 if first_due.month == 12 else first_due.month + 1, 1)
    cursor = date(today.year, today.month, 1)
    if cursor <= today:
        cursor = date(cursor.year + (cursor.month == 12), 1 if cursor.month == 12 else cursor.month + 1, 1)
    if cursor < first_due:
        cursor = first_due
    months_remaining = 0
    while cursor <= period_end:
        months_remaining += 1
        cursor = date(cursor.year + (cursor.month == 12), 1 if cursor.month == 12 else cursor.month + 1, 1)
    remaining_amount = max(Decimal(0), annual_value - booked)
    # The recommended amount is the total monthly payment needed over the
    # remaining payment dates, not a small adjustment to the existing amount.
    monthly_target = (remaining_amount / Decimal(months_remaining)).quantize(CENT, rounding=ROUND_HALF_UP) if months_remaining else Decimal("0.00")
    configured = Decimal(str(monthly_advance_net or 0)) * gross_factor if direction == "consumption" else Decimal(str(feed_in_monthly_advance_net or 0))
    # Approved lower bound: at least 70 % of average monthly total costs
    # (consumption, including the prorated base price). In the final three
    # remaining payment dates, additionally protect at least 70 % of the
    # currently configured monthly advance against an excessive reduction.
    average_cost_floor = (monthly_average_cost * Decimal("0.70")).quantize(CENT, rounding=ROUND_HALF_UP)
    configured_floor = (configured * Decimal("0.70")).quantize(CENT, rounding=ROUND_HALF_UP) if 0 < months_remaining <= 3 else Decimal("0.00")
    recommendation_floor = max(average_cost_floor if direction == "consumption" else Decimal("0.00"), configured_floor)
    monthly_target = max(monthly_target, recommendation_floor)
    expected_end_amount = annual_value - booked - future_scheduled
    signed_balance = expected_end_amount * (Decimal(-1) if direction == "consumption" else Decimal(1))
    return {
        "annual_energy_kwh": float(annual_energy.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)),
        "annual_value_eur": float(annual_value.quantize(CENT, rounding=ROUND_HALF_UP)),
        "forecast_energy_cost_total_eur": float(projected_energy_value),
        "forecast_base_price_total_eur": float(projected_base_value),
        "accrued_energy_cost_eur": float(accrued_energy_value),
        "accrued_base_price_eur": float(accrued_base),
        "accrued_extra_charges_eur": float(extra_charges_value),
        "remaining_energy_cost_eur": float(remaining_energy_value),
        "remaining_base_price_eur": float(remaining_base_value),
        "remaining_costs_including_base_price_eur": float(remaining_cost_value),
        "expected_year_end_balance_eur": float(signed_balance.quantize(CENT, rounding=ROUND_HALF_UP)),
        "recommended_monthly_advance_eur": float(monthly_target),
        "configured_monthly_advance_eur": float(configured.quantize(CENT, rounding=ROUND_HALF_UP)),
        "advance_recommendation_minimum_eur": float(recommendation_floor),
        "advance_recommendation_final_period_protection": bool(0 < months_remaining <= 3 and configured > 0),
        "booked_advances_eur": float(booked.quantize(CENT, rounding=ROUND_HALF_UP)),
        "future_scheduled_advances_eur": float(future_scheduled.quantize(CENT, rounding=ROUND_HALF_UP)),
        "months_remaining": months_remaining,
        "method": method,
        "basis_days": elapsed_days,
        "period_days": period_days,
        "period_end": period_end.isoformat(),
    }
