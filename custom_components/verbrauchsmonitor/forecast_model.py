"""Local, meter-isolated forecast model and hourly learning primitives.

The module has no Home Assistant dependency. It provides NOAA-style solar
position/daylight calculations, an evidence-based reliability aggregation, immutable hourly forecast records, idempotent evaluation, and a
conservative candidate-model update rule. Consumption and feed-in callers must
use separate model instances and storage keys.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date, datetime, time, timedelta, timezone
from math import acos, atan2, cos, degrees, radians, sin, tan
from functools import lru_cache
import hashlib
import json

DIRECTIONS = ("north", "east", "south", "west")


def _day_of_year(day: date) -> int:
    return day.timetuple().tm_yday


def solar_position(when: datetime, latitude: float, longitude: float) -> dict:
    """Calculate solar elevation and azimuth locally for an aware datetime."""
    if when.tzinfo is None:
        raise ValueError("when must be timezone-aware")
    lat, lon = float(latitude), float(longitude)
    if not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise ValueError("invalid coordinates")
    utc = when.astimezone(timezone.utc)
    n = _day_of_year(utc.date())
    hour = utc.hour + utc.minute / 60 + utc.second / 3600
    gamma = 2 * 3.141592653589793 / 365 * (n - 1 + (hour - 12) / 24)
    eqtime = 229.18 * (0.000075 + 0.001868*cos(gamma) - 0.032077*sin(gamma)
        - 0.014615*cos(2*gamma) - 0.040849*sin(2*gamma))
    decl = (0.006918 - 0.399912*cos(gamma) + 0.070257*sin(gamma)
        - 0.006758*cos(2*gamma) + 0.000907*sin(2*gamma)
        - 0.002697*cos(3*gamma) + 0.00148*sin(3*gamma))
    true_solar_minutes = (hour * 60 + eqtime + 4 * lon) % 1440
    hour_angle = radians(true_solar_minutes / 4 - 180)
    lat_r = radians(lat)
    cos_zenith = max(-1.0, min(1.0, sin(lat_r)*sin(decl) + cos(lat_r)*cos(decl)*cos(hour_angle)))
    zenith = acos(cos_zenith)
    elevation = 90 - degrees(zenith)
    azimuth = (degrees(atan2(sin(hour_angle),
        cos(hour_angle) * sin(lat_r) - tan(decl) * cos(lat_r))) + 180) % 360
    if abs(elevation) >= 89.999:
        azimuth = 180.0
    return {"elevation_deg": elevation, "azimuth_deg": azimuth,
            "daylight": elevation > 0, "twilight": -6 < elevation <= 0,
            "dark": elevation <= -6}


def daylight_hours(day: date, latitude: float) -> float:
    """Return approximate astronomical daylight duration; handles polar day/night."""
    lat = radians(float(latitude))
    n = _day_of_year(day)
    decl = radians(23.44) * sin(2 * 3.141592653589793 * (284 + n) / 365)
    denominator = cos(lat) * cos(decl)
    if abs(denominator) < 1e-12:
        return 24.0 if sin(lat) * sin(decl) > 0 else 0.0
    cos_h = -tan(lat) * tan(decl)
    if cos_h <= -1:
        return 24.0
    if cos_h >= 1:
        return 0.0
    return 24 * degrees(acos(cos_h)) / 180


def sunrise_sunset(day: date, latitude: float, longitude: float, timezone_info) -> dict:
    """Calculate local sunrise and sunset using the NOAA solar equations.

    The standard apparent sunrise zenith (90.833 degrees) includes a small
    refraction/disk-radius correction. Polar day/night are represented with
    ``None`` event times and an explicit ``polar_day`` flag.
    """
    lat, lon = float(latitude), float(longitude)
    if not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise ValueError("invalid coordinates")
    n = _day_of_year(day)
    gamma = 2 * 3.141592653589793 / 365 * (n - 1)
    eqtime = 229.18 * (0.000075 + 0.001868*cos(gamma) - 0.032077*sin(gamma)
        - 0.014615*cos(2*gamma) - 0.040849*sin(2*gamma))
    decl = (0.006918 - 0.399912*cos(gamma) + 0.070257*sin(gamma)
        - 0.006758*cos(2*gamma) + 0.000907*sin(2*gamma)
        - 0.002697*cos(3*gamma) + 0.00148*sin(3*gamma))
    lat_r = radians(lat)
    cos_hour_angle = (
        cos(radians(90.833)) / (cos(lat_r) * cos(decl))
        - tan(lat_r) * tan(decl)
    )
    if cos_hour_angle > 1:
        return {"sunrise": None, "sunset": None, "polar_day": False}
    if cos_hour_angle < -1:
        return {"sunrise": None, "sunset": None, "polar_day": True}
    hour_angle_minutes = 4 * degrees(acos(max(-1.0, min(1.0, cos_hour_angle))) )
    solar_noon_utc_minutes = 720 - 4 * lon - eqtime
    utc_midnight = datetime.combine(day, time.min, tzinfo=timezone.utc)
    sunrise_utc = utc_midnight + timedelta(minutes=solar_noon_utc_minutes - hour_angle_minutes)
    sunset_utc = utc_midnight + timedelta(minutes=solar_noon_utc_minutes + hour_angle_minutes)
    return {
        "sunrise": sunrise_utc.astimezone(timezone_info),
        "sunset": sunset_utc.astimezone(timezone_info),
        "polar_day": False,
    }


def solar_resource_index(day: date, latitude: float) -> float:
    """Return a dimensionless local solar-resource index for a calendar day.

    The index combines astronomical daylight duration and the maximum solar
    elevation. It is a deterministic feature, not a weather or PV-yield claim.
    """
    daylight = daylight_hours(day, latitude)
    lat = radians(float(latitude))
    declination = radians(23.44) * sin(2 * 3.141592653589793 * (284 + _day_of_year(day)) / 365)
    noon_elevation = max(0.0, 90.0 - abs(degrees(lat - declination)))
    return max(0.0, (daylight / 12.0) * sin(radians(noon_elevation)))


def initial_profile_multiplier(direction: str, when: datetime, latitude: float,
                               longitude: float, orientations: list[str] | None = None) -> float:
    """Generic first-install profile using local season and solar geometry.

    Consumption uses daylight duration and solar elevation as a small seasonal
    demand feature (dark/low-sun periods can imply more lighting/heating load).
    Feed-in uses the sun's current azimuth/elevation and every selected panel
    orientation. These are priors only; measured history remains authoritative.
    """
    if direction not in ("consumption", "feed_in"):
        raise ValueError("invalid direction")
    solar = solar_position(when, latitude, longitude)
    hour = when.hour + when.minute / 60
    season_phase = 2 * 3.141592653589793 * (_day_of_year(when.date()) - 80) / 365.2425
    seasonal = 1 + 0.16 * sin(season_phase)
    if direction == "consumption":
        # Household demand prior: morning/evening peaks, lower overnight.
        hourly = 0.62 + 0.22 * (1 + cos((hour - 7.5) * 2*3.141592653589793/24)) / 2
        hourly += 0.30 * (1 + cos((hour - 19.0) * 2*3.141592653589793/24)) / 2
        resource = solar_resource_index(when.date(), latitude)
        # Bounded ±6% astronomical adjustment. It deliberately avoids assuming
        # a universal large heating/lighting response to sunlight.
        daylight_factor = max(0.94, min(1.06, 1.0 + 0.06 * (0.70 - resource)))
        hourly_sun_factor = 0.985 if solar["daylight"] else 1.015
        return max(0.25, hourly * (1.0 + 0.025 * (1-seasonal)) * daylight_factor * hourly_sun_factor)
    selected = [x for x in (orientations or []) if x in DIRECTIONS]
    # An empty selection is valid and means unknown/mixed orientation. Use a
    # neutral four-direction prior rather than silently assuming south.
    if not selected:
        selected = list(DIRECTIONS)
    if not solar["daylight"]:
        return 0.0
    # Directional incidence proxy based on sun azimuth; not a PV yield claim.
    az = solar["azimuth_deg"]
    centers = {"north": 0.0, "east": 90.0, "south": 180.0, "west": 270.0}
    incidence = sum(
        max(0.0, cos(radians((az-centers[d]+180) % 360 - 180)))
        for d in selected
    ) / len(selected)
    elevation_factor = max(0.0, sin(radians(solar["elevation_deg"])))
    return max(0.0, seasonal * incidence * elevation_factor)


@lru_cache(maxsize=4096)
def _cached_daily_profile_factor(day_iso: str, direction: str, latitude: float,
                                longitude: float, timezone_key: str,
                                orientations: tuple[str, ...]) -> float:
    """Cache a daily mean profile feature for a meter/direction/day."""
    day = date.fromisoformat(day_iso)
    # Local standard-time samples are sufficient for a daily shape feature;
    # the actual hourly forecast uses aware HA-local timestamps separately.
    from zoneinfo import ZoneInfo
    try:
        tz = ZoneInfo(timezone_key)
    except Exception:
        tz = timezone.utc
    return sum(
        initial_profile_multiplier(
            direction, datetime.combine(day, time(hour=h), tzinfo=tz),
            latitude, longitude, list(orientations),
        ) for h in range(24)
    ) / 24.0


def historical_solar_adjustment(day: date, *, direction: str, latitude: float,
                                longitude: float, timezone_info,
                                orientations: list[str] | None = None) -> float:
    """Return a conservative solar feature for history-based future rates.

    The historical month profile remains the primary signal. A bounded
    astronomical correction refines rather than replaces observed seasonal
    behavior. Feed-in orientation selection is included.
    """
    if direction not in ("consumption", "feed_in"):
        raise ValueError("invalid direction")
    resource = solar_resource_index(day, latitude)
    if direction == "consumption":
        solar_factor = max(0.90, min(1.10, 1.0 + 0.06 * (0.70 - resource)))
    else:
        selected = tuple(sorted(x for x in (orientations if orientations is not None else ["south"]) if x in DIRECTIONS))
        # An explicitly empty selection means unknown/mixed orientation, not south.
        if not selected:
            selected = DIRECTIONS
        tz_key = getattr(timezone_info, "key", None) or str(timezone_info)
        selected_mean = _cached_daily_profile_factor(day.isoformat(), "feed_in", float(latitude), float(longitude), tz_key, selected)
        south_mean = _cached_daily_profile_factor(day.isoformat(), "feed_in", float(latitude), float(longitude), tz_key, ("south",))
        orientation_ratio = selected_mean / south_mean if south_mean > 1e-9 else 1.0
        orientation_factor = max(0.75, min(1.25, orientation_ratio))
        solar_factor = max(0.65, min(1.25, 0.70 + 0.30 * resource)) * (0.85 + 0.15 * orientation_factor)
    return max(0.90, min(1.10, 1.0 + 0.50 * (solar_factor - 1.0)))


@dataclass(frozen=True)
class HourlyForecast:
    meter_id: str
    direction: str
    target_hour: str
    created_at: str
    predicted_value: float
    model_version: int

    @property
    def key(self) -> str:
        return f"{self.meter_id}|{self.direction}|{self.target_hour}"


def create_hourly_forecast(meter_id: str, direction: str, target: datetime,
                           predicted_value: float, model_version: int = 1,
                           created_at: datetime | None = None) -> dict:
    """Create a serializable immutable hourly forecast record."""
    if direction not in ("consumption", "feed_in") or not meter_id:
        raise ValueError("invalid meter/direction")
    if target.tzinfo is None:
        raise ValueError("target must be timezone-aware")
    created = created_at or datetime.now(timezone.utc)
    if created.tzinfo is None:
        raise ValueError("created_at must be timezone-aware")
    target_hour = target.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
    return asdict(HourlyForecast(str(meter_id), direction, target_hour.isoformat(),
        created.astimezone(timezone.utc).isoformat(), max(0.0, float(predicted_value)), int(model_version)))


def evaluate_hourly_forecast(record: dict, actual_value: float) -> dict:
    """Evaluate a saved prediction against its completed actual hourly value."""
    predicted, actual = float(record["predicted_value"]), float(actual_value)
    if predicted < 0 or actual < 0:
        raise ValueError("hourly energy values must be nonnegative")
    error = actual - predicted
    try:
        created = datetime.fromisoformat(str(record["created_at"]).replace("Z", "+00:00"))
        target = datetime.fromisoformat(str(record["target_hour"]).replace("Z", "+00:00"))
        horizon_hours = max(1.0, (target - created).total_seconds() / 3600.0)
    except (KeyError, TypeError, ValueError):
        horizon_hours = None
    return {"key": f"{record['meter_id']}|{record['direction']}|{record['target_hour']}",
            "meter_id": record["meter_id"], "direction": record["direction"],
            "target_hour": record["target_hour"], "predicted": predicted,
            "actual": actual, "error": error,
            "absolute_error": abs(error),
            "forecast_horizon_hours": horizon_hours,
            "relative_error_percent": abs(error) / max(actual, 0.01) * 100}


def summarize_evaluations(evaluations: list[dict]) -> dict:
    """Summarize one direction's errors without exploding at near-zero readings.

    The former arithmetic mean of per-hour percentage errors gave tiny night-time
    feed-in readings the same influence as substantial daytime energy. The
    weighted absolute percentage error below normalizes by the larger of actual
    and predicted energy (with a small kWh floor), so zero-export hours remain
    visible but cannot dominate the whole evaluation. Consumption and feed-in
    are evaluated from separate learning stores and are never pooled.
    """
    if not evaluations:
        return {"count": 0, "mae": None, "relative_error_percent": None, "bias": None,
                "absolute_error_total": 0.0, "energy_reference_total": 0.0}
    n = len(evaluations)
    absolute_total = sum(max(0.0, float(x.get("absolute_error", 0.0) or 0.0)) for x in evaluations)
    # Near-term predictions are generally more actionable and are evaluated
    # with greater influence than long-horizon predictions. Missing horizon
    # metadata in old persisted rows uses neutral weight 1.0.
    horizon_weights = [1.0 / max(1.0, float(x.get("forecast_horizon_hours") or 1.0)) ** 0.5
                       for x in evaluations]
    has_energy_pairs = any("actual" in x and "predicted" in x for x in evaluations)
    if has_energy_pairs:
        weighted_absolute = sum(max(0.0, float(x.get("absolute_error", 0.0) or 0.0)) * weight
                                for x, weight in zip(evaluations, horizon_weights))
        reference_total = sum(max(float(x.get("actual", 0.0) or 0.0),
                                  float(x.get("predicted", 0.0) or 0.0), 0.05) * weight
                              for x, weight in zip(evaluations, horizon_weights))
        relative_error = 100.0 * weighted_absolute / reference_total if reference_total else None
    else:
        # Backward compatibility for evaluations persisted by earlier releases.
        reference_total = None
        relative_values = [float(x.get("relative_error_percent", 0.0) or 0.0) for x in evaluations]
        relative_error = sum(relative_values) / n
    bias_total = sum(float(x.get("error", 0.0) or 0.0) for x in evaluations)
    return {"count": n,
            "mae": absolute_total / n,
            "relative_error_percent": relative_error,
            "bias": bias_total / n,
            "absolute_error_total": absolute_total,
            "energy_reference_total": reference_total}


def adopt_candidate_model(old_metrics: dict, candidate_metrics: dict,
                          minimum_samples: int = 24) -> bool:
    """Only accept a candidate when it beats the old model on enough samples."""
    if old_metrics.get("count", 0) < minimum_samples or candidate_metrics.get("count", 0) < minimum_samples:
        return False
    old_mae, new_mae = old_metrics.get("mae"), candidate_metrics.get("mae")
    return old_mae is not None and new_mae is not None and new_mae < old_mae



def profile_adjusted_projection(*, observed_energy: float, elapsed_days: float,
                                remaining_days: float, today: date, direction: str,
                                latitude: float, longitude: float, timezone_info,
                                orientations: list[str] | None = None,
                                now: datetime | None = None) -> float:
    """Project the unmeasured interval using a normalized hourly solar profile.

    When ``now`` is supplied, the past interval ends at that exact instant and
    the future interval starts at that instant. This includes the remaining
    hours of today and every hour through the final billing-day boundary.
    """
    observed = max(0.0, float(observed_energy))
    elapsed = max(1.0 / 86400.0, float(elapsed_days))
    remaining = max(0.0, float(remaining_days))
    if remaining <= 0 or observed == 0:
        return observed

    if now is not None and now.tzinfo is not None:
        from datetime import timedelta

        def integrate(start: datetime, end: datetime) -> float:
            total = 0.0
            cursor_utc = start.astimezone(timezone.utc)
            end_utc = end.astimezone(timezone.utc)
            while cursor_utc < end_utc:
                hour_start = cursor_utc.replace(minute=0, second=0, microsecond=0)
                next_hour = hour_start + timedelta(hours=1)
                segment_end_utc = min(next_hour, end_utc)
                midpoint_local = (cursor_utc + (segment_end_utc - cursor_utc) / 2).astimezone(now.tzinfo)
                weight = initial_profile_multiplier(
                    direction, midpoint_local, latitude, longitude, orientations
                )
                total += weight * (segment_end_utc - cursor_utc).total_seconds() / 86400.0
                cursor_utc = segment_end_utc
            return total

        # Reconstruct the local billing interval with wall-clock day fractions;
        # the integrator itself advances in UTC so repeated DST hours remain
        # distinct when evaluating the hourly solar profile.
        start = now - timedelta(days=elapsed)
        end = now + timedelta(days=remaining)
        past_weight = integrate(start, now)
        future_weight = integrate(now, end)
        if past_weight <= 1e-12:
            return observed
        past_average = past_weight / elapsed
        return observed + observed / elapsed * (future_weight / past_average)

    # Compatibility fallback for date-only callers; runtime forecast calls use
    # the exact-instant branch above.
    start_elapsed = today - timedelta(days=max(1, int(elapsed)) - 1)
    def day_weight(day: date) -> float:
        values = []
        for hour in range(24):
            local = datetime.combine(day, time(hour=hour), tzinfo=timezone_info)
            values.append(initial_profile_multiplier(direction, local, latitude, longitude, orientations))
        return sum(values) / 24
    past_weights = [day_weight(start_elapsed + timedelta(days=i)) for i in range(max(1, int(elapsed)))]
    future_weights = [day_weight(today + timedelta(days=i)) for i in range(1, int(remaining) + 1)]
    past_average = sum(past_weights) / max(1, len(past_weights))
    future_average = sum(future_weights) / max(1, len(future_weights)) if future_weights else 0.0
    if past_average <= 1e-9:
        return observed
    return observed + observed / elapsed * future_average * remaining / past_average


def stable_model_key(meter_id: str, direction: str) -> str:
    """Return an opaque stable key that keeps meters/directions isolated."""
    if direction not in ("consumption", "feed_in"):
        raise ValueError("invalid direction")
    return hashlib.sha256(f"{meter_id}|{direction}".encode()).hexdigest()[:24]


def build_hourly_forecasts(*, meter_id: str, direction: str, now: datetime,
                           daily_energy: float, latitude: float, longitude: float,
                           timezone_info, orientations: list[str] | None = None,
                           horizon_hours: int = 24, model_version: int = 1) -> list[dict]:
    """Build immutable next-hour energy predictions from normalized local profiles.

    ``daily_energy`` is a per-day energy baseline derived from this meter and
    direction only. The generic profile shapes the distribution across hours;
    it never changes the measured daily baseline. Forecast timestamps are UTC
    hour boundaries, so repeated DST hours remain distinct instants.
    """
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    if direction not in ("consumption", "feed_in"):
        raise ValueError("invalid direction")
    baseline = max(0.0, float(daily_energy))
    if baseline == 0 or horizon_hours < 1:
        return []
    start = now.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
    targets = [start + timedelta(hours=i) for i in range(1, int(horizon_hours) + 1)]
    weights = []
    for target in targets:
        local = target.astimezone(timezone_info)
        weights.append(initial_profile_multiplier(direction, local, latitude, longitude, orientations))
    # Normalize a complete 24-hour horizon to the meter-specific daily baseline.
    # For shorter horizons, retain the same per-hour scale rather than inflating it.
    # Normalize over the actual rolling horizon. This naturally handles DST
    # transitions and avoids assuming that a local calendar day always has
    # exactly the same UTC-hour composition.
    denominator = sum(weights)
    if denominator <= 1e-12:
        return []
    return [create_hourly_forecast(meter_id, direction, target,
            baseline * weight / denominator, model_version=model_version, created_at=now)
            for target, weight in zip(targets, weights)]


def merge_forecast_records(existing: dict, new_records: list[dict], *, max_records: int = 2400) -> dict:
    """Merge forecasts by their immutable key without replacing original predictions."""
    records = dict(existing or {})
    for record in new_records:
        key = f"{record['meter_id']}|{record['direction']}|{record['target_hour']}"
        records.setdefault(key, record)
    if len(records) > max_records:
        ordered = sorted(records.items(), key=lambda item: item[1].get("target_hour", ""))
        records = dict(ordered[-max_records:])
    return records


def merge_hourly_evaluations(existing: dict, additions: list[dict], *, max_records: int = 2400) -> dict:
    """Idempotently retain completed evaluations, keyed by meter/direction/hour."""
    values = dict(existing or {})
    for item in additions:
        values.setdefault(item["key"], item)
    if len(values) > max_records:
        ordered = sorted(values.items(), key=lambda item: item[1].get("target_hour", ""))
        values = dict(ordered[-max_records:])
    return values


def reliability_from_hourly_evaluations(evaluations: list[dict], *, minimum_samples: int = 24) -> dict:
    """Calculate measured forecast reliability only from completed hourly comparisons."""
    metrics = summarize_evaluations(evaluations)
    if metrics["count"] < minimum_samples:
        return {"available": False, "score": None, "basis": "insufficient_hourly_evaluations", **metrics}
    # A bounded accuracy score based on mean absolute percentage error.
    score = max(0.0, min(100.0, 100.0 - float(metrics["relative_error_percent"])))
    return {"available": True, "score": round(score, 1),
            "basis": "hourly_forecast_vs_actual", **metrics}


def temporal_reliability_factor(*, now: datetime, period_start, period_end) -> dict:
    """Measure how much of the billing period has actually elapsed.

    Billing dates are inclusive. The elapsed fraction scales measured accuracy;
    it is not a bonus and cannot raise a score above the measured accuracy.
    The absolute ceiling is 92% normally, 94% in the final 24 hours and 95%
    only in the final hour.
    """
    current = now if now.tzinfo is not None else now.replace(tzinfo=timezone.utc)
    current = current.astimezone(timezone.utc)
    def as_date(value):
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        return date.fromisoformat(str(value)[:10])
    try:
        first = as_date(period_start)
        last = as_date(period_end)
    except (TypeError, ValueError):
        return {"available": False, "elapsed_fraction": None, "factor": None, "ceiling": None}
    if last < first:
        return {"available": False, "elapsed_fraction": None, "factor": None, "ceiling": None}
    local_tz = now.tzinfo or timezone.utc
    start_dt = datetime.combine(first, time.min, tzinfo=local_tz).astimezone(timezone.utc)
    end_dt = datetime.combine(last + timedelta(days=1), time.min, tzinfo=local_tz).astimezone(timezone.utc)
    total = (end_dt - start_dt).total_seconds()
    if total <= 0:
        return {"available": False, "elapsed_fraction": None, "factor": None, "ceiling": None}
    elapsed = max(0.0, min(1.0, (current - start_dt).total_seconds() / total))
    remaining_seconds = max(0.0, (end_dt - current).total_seconds())
    ceiling = 95.0 if remaining_seconds <= 3600 else 94.0 if remaining_seconds <= 86400 else 92.0
    # A square-root curve is deliberately more conservative than the former
    # fourth-root curve: the passage of time reduces the amount of future
    # uncertainty but must not make an early-period forecast look almost
    # complete. It reaches 1 only when the full billing period has elapsed.
    factor = elapsed ** 0.5
    return {"available": True, "elapsed_fraction": round(elapsed, 6),
            "factor": factor, "ceiling": ceiling,
            "remaining_seconds": remaining_seconds}


def resolve_forecast_reliability(*, initial_score: float | None,
                                  initial_created_at: datetime | None,
                                  now: datetime, evaluations: list[dict],
                                  history: dict, method: str,
                                  provisional_hours: float = 0.25,
                                  reliability_context: dict | None = None) -> dict:
    """Calculate reliability from measured forecast errors and period coverage.

    Live input freshness, valid tariffs and configured entities are diagnostic
    data only. They cannot substitute for forecast-versus-actual evidence.
    """
    current = now if now.tzinfo is not None else now.replace(tzinfo=timezone.utc)
    created = initial_created_at
    if created is not None and created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    age_minutes = ((current - created).total_seconds() / 60) if created else 0.0
    measured = reliability_from_hourly_evaluations(evaluations, minimum_samples=24)
    context = dict(reliability_context or {})
    context["measured_forecast_score"] = measured.get("score") if measured.get("available") else None
    context["measured_forecast_count"] = measured.get("count", 0)
    try:
        from .reliability import evaluate_reliability
    except ImportError:
        import importlib.util
        from pathlib import Path
        module_path = Path(__file__).with_name("reliability.py")
        spec = importlib.util.spec_from_file_location("vm_reliability_engine", module_path)
        module = importlib.util.module_from_spec(spec)
        import sys
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        evaluate_reliability = module.evaluate_reliability
    aggregate = evaluate_reliability(context)
    # Existing Recorder history is a valid initial evidence source even before
    # this integration version has accumulated 24 hours of forecast/actual
    # pairs. It measures history coverage, continuity, plausibility and the
    # forecasting method; it is explicitly NOT labelled as measured forecast
    # accuracy. Once enough immutable forecast comparisons exist, module A
    # takes precedence automatically.
    history_quality = None
    reliability_basis = aggregate.get("basis")
    raw_score = aggregate.get("score")
    if raw_score is None:
        try:
            from .forecast import reliability_score
        except ImportError:
            import importlib.util
            from pathlib import Path
            forecast_path = Path(__file__).with_name("forecast.py")
            forecast_spec = importlib.util.spec_from_file_location("vm_forecast_history_quality", forecast_path)
            forecast_module = importlib.util.module_from_spec(forecast_spec)
            import sys
            sys.modules[forecast_spec.name] = forecast_module
            forecast_spec.loader.exec_module(forecast_module)
            reliability_score = forecast_module.reliability_score
        historical = reliability_score(history=history, method=method)
        if historical.get("forecast_reliability_available"):
            history_quality = historical.get("forecast_reliability_percent")
            raw_score = history_quality
            reliability_basis = "recorder_history_quality_initial_evidence"
    # A real initial assessment is still possible when the Recorder cannot
    # provide a 12-month series: use only currently observed, validated input
    # freshness and configuration evidence. This is explicitly an input-quality
    # assessment, not a claim of measured forecast accuracy. Missing optional
    # entities are omitted rather than scored as failures.
    initial_confidence = None
    if raw_score is not None and history_quality is not None:
        # Recorder history describes the quality of the evidence, not proven
        # forecast accuracy. Apply an explicit confidence multiplier based on
        # independent history depth, coverage and sample volume. This prevents
        # a complete-looking history from immediately producing 90+ percent.
        months = max(0.0, float(history.get("history_months", 0) or 0))
        coverage = max(0.0, min(100.0, float(history.get("coverage_percent", 0) or 0)))
        samples = max(0.0, float(history.get("sample_count", 0) or 0))
        initial_confidence = (
            0.45
            + 0.25 * min(1.0, months / 24.0)
            + 0.20 * (coverage / 100.0)
            + 0.10 * min(1.0, samples / 500.0)
        )
        # Fresh optional measurements can contribute a small amount of
        # evidence only when actually configured and current. Missing optional
        # sensors are omitted, never treated as failures or as implicit zeros.
        factors = context.get("forecast_factors") or {}
        optional = [float(value) for key, value in factors.items()
                    if key != "meter_freshness" and value is not None]
        if optional:
            initial_confidence = min(1.0, initial_confidence + 0.03 * (sum(optional) / len(optional) / 100.0))
        raw_score = float(raw_score) * initial_confidence
        reliability_basis = "recorder_history_quality_initial_evidence"
    if raw_score is None:
        factor_groups = []
        meter_freshness = (context.get("forecast_factors") or {}).get("meter_freshness")
        if meter_freshness is not None:
            factor_groups.append((float(meter_freshness), 0.65))
        history_months = int(history.get("history_months", 0) or 0)
        if history_months > 0:
            history_signal = min(100.0, float(history.get("coverage_percent", 0) or 0) * 0.6
                                + min(100.0, history_months / 24.0 * 100.0) * 0.4)
            factor_groups.append((history_signal, 0.35))
        if factor_groups:
            weight_total = sum(weight for _, weight in factor_groups)
            raw_score = sum(value * weight for value, weight in factor_groups) / weight_total
            # A live-only assessment is explicitly provisional and conservative.
            initial_confidence = 0.70
            raw_score *= initial_confidence
            reliability_basis = "live_input_and_configuration_quality_initial_evidence"
    temporal = temporal_reliability_factor(
        now=current, period_start=context.get("billing_period_start"),
        period_end=context.get("billing_period_end"),
    )
    score = None
    if raw_score is not None and temporal["available"]:
        score = round(min(float(raw_score) * temporal["factor"], temporal["ceiling"], 95.0), 1)
    available = score is not None
    return {
        "forecast_reliability_percent": score,
        "forecast_reliability_level": ("high" if score >= 80 else "medium" if score >= 50 else "low") if available else None,
        "forecast_reliability_basis": (
            "measured_forecast_accuracy_and_billing_period_coverage"
            if available and measured.get("available")
            else "recorder_history_quality_and_billing_period_coverage"
            if available and history_quality is not None
            else "live_input_and_configuration_quality_and_billing_period_coverage"
            if available and reliability_basis == "live_input_and_configuration_quality_initial_evidence"
            else reliability_basis
        ),
        "forecast_reliability_history_quality_percent": history_quality,
        "forecast_reliability_initial_evidence_confidence_percent": (
            round(initial_confidence * 100.0, 1) if initial_confidence is not None else None
        ),
        "forecast_reliability_modules": aggregate.get("modules", {}),
        "forecast_reliability_available": available,
        "forecast_reliability_is_initial": not bool(measured.get("available")),
        "forecast_reliability_pending": bool(not available and age_minutes < 15.0),
        "forecast_reliability_age_minutes": round(max(0.0, age_minutes), 1),
        "forecast_hourly_evaluation_count": int(measured.get("count", 0) or 0),
        "forecast_reliability_temporal_factor": round(temporal["factor"], 4) if temporal["available"] else None,
        "forecast_reliability_temporal_ceiling": temporal["ceiling"],
        "forecast_reliability_period_elapsed_percent": round(temporal["elapsed_fraction"] * 100, 2) if temporal["available"] else None,
        "forecast_reliability_measured_accuracy_percent": measured.get("score") if measured.get("available") else None,
    }

def learn_candidate_scale(evaluations: list[dict], *, minimum_samples: int = 48) -> dict:
    """Learn a conservative global scale only when it improves a holdout set.

    The chronological first half estimates the correction; the second half is
    an untouched validation set. This prevents a parameter update from being
    accepted merely because it fits the observations used to derive it.
    """
    ordered = sorted(evaluations, key=lambda item: item.get("target_hour", ""))
    if len(ordered) < minimum_samples:
        return {"adopted": False, "scale": 1.0, "reason": "insufficient_samples"}
    split = len(ordered) // 2
    train, test = ordered[:split], ordered[split:]
    ratios = [float(x["actual"]) / float(x["predicted"])
              for x in train if float(x["predicted"]) > 0]
    if not ratios:
        return {"adopted": False, "scale": 1.0, "reason": "no_positive_predictions"}
    candidate = max(0.5, min(1.5, sum(ratios) / len(ratios)))
    old_error = sum(abs(float(x["actual"]) - float(x["predicted"])) for x in test) / len(test)
    new_error = sum(abs(float(x["actual"]) - float(x["predicted"]) * candidate) for x in test) / len(test)
    if new_error < old_error:
        return {"adopted": True, "scale": candidate,
                "old_holdout_mae": old_error, "new_holdout_mae": new_error}
    return {"adopted": False, "scale": 1.0,
            "old_holdout_mae": old_error, "new_holdout_mae": new_error,
            "reason": "candidate_not_better"}
