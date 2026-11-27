"""Central validation for cumulative electricity meter readings.

Only finite, non-negative numeric values are accepted. A decrease is never
interpreted as a reset by itself; callers must separately confirm a configured
meter replacement before changing the meter segment.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
import math


def parse_reading(value) -> Decimal | None:
    """Parse a Home Assistant state or stored value as a finite non-negative number."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, str) and value.strip().lower() in {
        "", "unknown", "unavailable", "none", "null", "nan", "inf", "+inf", "-inf",
        "infinity", "+infinity", "-infinity",
    }:
        return None
    try:
        reading = Decimal(str(value).strip())
    except (InvalidOperation, TypeError, ValueError, AttributeError):
        return None
    if not reading.is_finite() or reading < 0:
        return None
    try:
        if not math.isfinite(float(reading)):
            return None
    except (OverflowError, ValueError):
        return None
    return reading


def validate_reading(value, last_accepted=None) -> tuple[Decimal | None, str]:
    """Validate syntax/range and monotonicity against the last accepted value."""
    reading = parse_reading(value)
    if reading is None:
        return None, "invalid"
    previous = parse_reading(last_accepted) if last_accepted is not None else None
    if previous is not None and reading < previous:
        return None, "decreased"
    return reading, "accepted"


def confirmed_meter_change(changes, *, direction: str, period_start, today,
                           baseline, previous_reading) -> bool:
    """Confirm a decrease only from a dated, direction-specific meter change.

    The change must belong to the active calendar period and contain a valid
    old-meter end reading not below the active period baseline. The original
    change record remains untouched for auditability.
    """
    from datetime import date

    if direction not in ("consumption", "feed_in"):
        return False
    try:
        start_date = date.fromisoformat(str(period_start)[:10])
        today_date = date.fromisoformat(str(today)[:10])
    except (TypeError, ValueError):
        return False
    baseline_value = parse_reading(baseline)
    previous_value = parse_reading(previous_reading)
    if baseline_value is None or previous_value is None:
        return False
    end_key = "consumption_reading" if direction == "consumption" else "feed_in_reading"
    for change in changes or []:
        if not isinstance(change, dict):
            continue
        try:
            change_date = date.fromisoformat(str(change.get("date", ""))[:10])
        except (TypeError, ValueError):
            continue
        end_reading = parse_reading(change.get(end_key))
        if start_date <= change_date <= today_date and end_reading is not None and end_reading >= baseline_value:
            return True
    return False
