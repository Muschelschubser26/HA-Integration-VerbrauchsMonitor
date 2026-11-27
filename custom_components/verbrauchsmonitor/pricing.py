"""Pure tariff arithmetic helpers."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def gross_decimal_from_net(net_value: object, vat_percent: object) -> Decimal | None:
    """Return the exact gross tariff as Decimal without binary-float conversion."""
    try:
        net = Decimal(str(net_value))
        vat = Decimal(str(vat_percent))
    except (InvalidOperation, TypeError, ValueError):
        return None
    if not net.is_finite() or not vat.is_finite() or net < 0 or not (0 <= vat <= 100):
        return None
    return net * (Decimal("1") + vat / Decimal("100"))


def gross_from_net(net_value: object, vat_percent: object) -> float | None:
    """Calculate gross value from a net value and VAT percentage.

    Returns None for missing or malformed inputs instead of inventing a value.
    """
    gross = gross_decimal_from_net(net_value, vat_percent)
    # Preserve tariff precision (up to six decimal places per kWh).
    # Monetary totals are rounded separately to cents in the ledger/sensors.
    return float(gross) if gross is not None else None


def accrued_annual_base_price(annual_gross: object, billing_start, now) -> Decimal:
    """Calculate annual base price accrued continuously from start to now.

    The interval is split at calendar-year boundaries so leap years are
    prorated with their actual 365/366-day length. This helper is shared by
    the live balance and forecast, keeping both values on the same time basis.
    """
    from datetime import datetime
    amount = Decimal(str(annual_gross or 0))
    if not amount.is_finite() or amount < 0:
        raise ValueError("annual base price must be a finite nonnegative amount")
    if not isinstance(billing_start, datetime) or not isinstance(now, datetime):
        raise TypeError("billing_start and now must be datetimes")
    if now <= billing_start:
        return Decimal("0.00")
    cursor = billing_start
    accrued = Decimal("0")
    while cursor < now:
        next_year = datetime(cursor.year + 1, 1, 1, tzinfo=cursor.tzinfo)
        segment_end = min(now, next_year)
        year_days = 366 if cursor.year % 4 == 0 and (cursor.year % 100 != 0 or cursor.year % 400 == 0) else 365
        # Billing proration follows local wall-clock elapsed time. The annual
        # denominator remains the actual Gregorian 365/366-day year length.
        seconds = Decimal(str((segment_end - cursor).total_seconds()))
        accrued += amount * seconds / Decimal(year_days * 86400)
        cursor = segment_end
    return min(amount, accrued).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

