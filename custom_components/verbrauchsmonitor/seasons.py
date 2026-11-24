"""Global astronomical season calculation based on the HA location.

Season boundaries are the UTC instants of the March/June/September/December
solar events. The Meeus/USNO polynomial approximation is valid for years
1000–3000 and includes the periodic correction terms.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import math

# JDE0 polynomial coefficients for March equinox, June solstice,
# September equinox and December solstice (Meeus, years 1000–3000).
_EVENT_COEFFICIENTS = (
    (2451623.80984, 365242.37404, 0.05169, -0.00411, -0.00057),
    (2451716.56767, 365241.62603, 0.00325, 0.00888, -0.00030),
    (2451810.21715, 365242.01767, -0.11575, 0.00337, 0.00078),
    (2451900.05952, 365242.74049, -0.06223, -0.00823, 0.00032),
)
_PERIODIC_TERMS = (
    (485, 324.96, 1934.136), (203, 337.23, 32964.467),
    (199, 342.08, 20.186), (182, 27.85, 445267.112),
    (156, 73.14, 45036.886), (136, 171.52, 22518.443),
    (77, 222.54, 65928.934), (74, 296.72, 3034.906),
    (70, 243.58, 9037.513), (58, 119.81, 33718.147),
    (52, 297.17, 150.678), (50, 21.02, 2281.226),
    (45, 247.54, 29929.562), (44, 325.15, 31555.956),
    (29, 60.93, 4443.417), (18, 155.12, 67555.328),
    (17, 288.79, 4562.452), (16, 198.04, 62894.029),
    (14, 199.76, 31436.921), (12, 95.39, 14577.848),
    (12, 287.11, 31931.756), (12, 320.81, 34777.259),
    (9, 227.73, 1222.114), (8, 15.45, 16859.074),
)


def _julian_day_to_utc(julian_day: float) -> datetime:
    """Convert a Julian day number to an aware UTC datetime."""
    unix_days = julian_day - 2440587.5
    return datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(days=unix_days)


def _season_event(year: int, event_index: int) -> datetime:
    """Return one astronomical season boundary as a UTC datetime."""
    if not 1000 <= year <= 3000:
        raise ValueError("Astronomical season calculation supports years 1000–3000")
    y = (year - 2000) / 1000
    c = _EVENT_COEFFICIENTS[event_index]
    jde0 = c[0] + c[1] * y + c[2] * y**2 + c[3] * y**3 + c[4] * y**4
    t = (jde0 - 2451545.0) / 36525
    w = math.radians(35999.373 * t - 2.47)
    delta_lambda = 1 + 0.0334 * math.cos(w) + 0.0007 * math.cos(2 * w)
    s = sum(a * math.cos(math.radians(b + c_ * t)) for a, b, c_ in _PERIODIC_TERMS)
    return _julian_day_to_utc(jde0 + (0.00001 * s) / delta_lambda)


def astronomical_season(now: datetime, latitude: float) -> str:
    """Return spring/summer/autumn/winter for either hemisphere.

    The latitude sign selects the hemisphere. At the equator, the northern
    astronomical convention is used deterministically.
    """
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    if not math.isfinite(float(latitude)) or not -90 <= float(latitude) <= 90:
        raise ValueError("latitude must be between -90 and 90 degrees")
    instant = now.astimezone(timezone.utc)
    if not 1000 <= instant.year <= 3000:
        raise ValueError("Astronomical season calculation supports years 1000–3000")
    events = []
    for year in (instant.year - 1, instant.year, instant.year + 1):
        if 1000 <= year <= 3000:
            for index, season in enumerate(("spring", "summer", "autumn", "winter")):
                events.append((_season_event(year, index), season))
    north_season = max((item for item in events if item[0] <= instant), key=lambda item: item[0])[1]
    if float(latitude) >= 0:
        return north_season
    return {"spring": "autumn", "summer": "winter", "autumn": "spring", "winter": "summer"}[north_season]


def current_ha_season(hass, now: datetime) -> str:
    """Resolve the current global astronomical season from HA core location."""
    latitude = getattr(hass.config, "latitude", None)
    longitude = getattr(hass.config, "longitude", None)
    if latitude is None or longitude is None:
        raise ValueError("Home Assistant location coordinates are not configured")
    # Longitude is validated as part of the location configuration even
    # though the global astronomical event is an absolute UTC instant.
    if not -180 <= float(longitude) <= 180:
        raise ValueError("Home Assistant longitude is invalid")
    return astronomical_season(now, float(latitude))
