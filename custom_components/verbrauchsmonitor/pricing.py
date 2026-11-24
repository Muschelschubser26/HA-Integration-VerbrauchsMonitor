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
