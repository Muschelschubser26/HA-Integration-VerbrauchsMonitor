"""Small, deterministic billing calculations used by the integration."""
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

@dataclass(frozen=True)
class Balance:
    """Represent the calculated balance and its supporting payment totals."""
    consumption_cost: Decimal
    feed_in_credit: Decimal
    total: Decimal

def _decimal(value) -> Decimal:
    """Convert a supported numeric input to Decimal with a safe zero fallback."""
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("Ungültiger Zahlenwert") from None
    if not result.is_finite():
        raise ValueError("Nicht endlicher Zahlenwert")
    return result

def calculate_balance(*, consumption_kwh, feed_in_kwh=0, purchase_price_gross_ct_kwh, feed_in_price_gross_ct_kwh=0, base_price_gross=0, base_price_months=0, advances=0, credits=0, extra_charges=0) -> Balance:
    """Calculate a period balance from period energy, prices and booked amounts.

    A positive total means amount still payable; a negative total means credit.
    Energy inputs must be period deltas, never cumulative meter readings.
    """
    consumption = _decimal(consumption_kwh)
    feed_in = _decimal(feed_in_kwh)
    if consumption < 0 or feed_in < 0:
        raise ValueError("Energie-Differenzen dürfen nicht negativ sein")
    cost = (consumption * _decimal(purchase_price_gross_ct_kwh) / Decimal(100))
    credit = (feed_in * _decimal(feed_in_price_gross_ct_kwh) / Decimal(100))
    total = cost + _decimal(base_price_gross) * _decimal(base_price_months) + _decimal(extra_charges) - _decimal(advances) - _decimal(credits) - credit
    # Preserve full Decimal precision; monetary rounding belongs to presentation.
    return Balance(cost, credit, total)




def validate_booking_amount(*, booking_type: str, amount) -> Decimal:
    """Validate the sign convention for a manually entered booking amount."""
    value = _decimal(amount)
    if booking_type == "credit" and value <= 0:
        raise ValueError("Gutschriften müssen positiv sein")
    if booking_type == "correction" and value == 0:
        raise ValueError("Korrekturen dürfen nicht null sein")
    if booking_type not in ("credit", "correction") and value < 0:
        raise ValueError("Betrag darf nicht negativ sein")
    return value

def calculate_booking_adjustments(*, bookings, direction: str) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    """Return credits, additional payments, extra charges and signed corrections.

    ``credit`` amounts are positive and increase the customer's account credit:
    they reduce consumption liabilities and increase feed-in receivables.
    ``correction`` amounts are signed account adjustments. They are returned
    separately so the caller can apply them after converting the balance to
    the customer-account sign convention. This makes a negative correction
    reduce the displayed credit by the same amount for every meter direction.
    """
    if direction not in ("consumption", "feed_in"):
        raise ValueError("Unbekannter Abrechnungsbereich")

    credits = Decimal("0")
    additional_payments = Decimal("0")
    extra_charges = Decimal("0")
    corrections = Decimal("0")
    for booking in bookings or []:
        if booking.get("direction") != direction:
            continue
        amount = _decimal(booking.get("amount", 0) or 0)
        kind = booking.get("booking_type")
        if kind == "credit":
            # New entries are validated as positive; abs() also keeps older
            # manually imported records from inverting the credit's meaning.
            credits += abs(amount)
        elif kind == "payment":
            additional_payments += amount
        elif kind == "extra_charge":
            extra_charges += amount
        elif kind == "correction":
            corrections += amount
    return credits, additional_payments, extra_charges, corrections

def calculate_advance_total(*, monthly_advance_gross, elapsed_months=None, bookings, period_start=None, as_of=None, period_end=None, monthly_amounts=None) -> Decimal:
    """Return expected regular advances plus recorded advances.

    The contractual advance is counted once on the first day of each calendar
    month in the billing window. A recorded advance suppresses the automatic
    amount for that month, preventing double counting. Special payments are
    intentionally handled separately by the caller.
    """
    from datetime import date

    monthly = _decimal(monthly_advance_gross)
    today = as_of or date.today()
    if isinstance(today, str):
        today = date.fromisoformat(today[:10])

    if period_start:
        start = date.fromisoformat(str(period_start)[:10])
    else:
        # Backward-compatible fallback for callers that only provide a count.
        months = max(0, int(elapsed_months or 0))
        start = date(today.year, today.month, 1)
        for _ in range(max(0, months - 1)):
            start = date(start.year - (start.month == 1), 12 if start.month == 1 else start.month - 1, 1)

    end = today
    if period_end:
        configured_end = date.fromisoformat(str(period_end)[:10])
        end = min(end, configured_end)
    if start > end:
        return Decimal("0.00")

    # Advance due dates are the first of each month, including the start month
    # only when that month's first day lies within the billing period.
    due_months: list[str] = []
    year, month = start.year, start.month
    while date(year, month, 1) < start:
        if month == 12:
            year, month = year + 1, 1
        else:
            month += 1
    while date(year, month, 1) <= end:
        due_months.append(f"{year:04d}-{month:02d}")
        if month == 12:
            year, month = year + 1, 1
        else:
            month += 1

    covered_months: set[str] = set()
    recorded = Decimal("0")
    for booking in bookings or []:
        if booking.get("booking_type") != "advance":
            continue
        raw_date = str(booking.get("date", ""))[:10]
        if len(raw_date) < 10:
            continue
        try:
            booked_on = date.fromisoformat(raw_date)
        except ValueError:
            continue
        if booked_on < start or booked_on > end:
            continue
        recorded += _decimal(booking.get("amount", 0) or 0)
        covered_months.add(raw_date[:7])

    automatic_months = sum(1 for month_key in due_months if month_key not in covered_months)
    overrides = monthly_amounts or {}
    automatic_total = sum(
        (_decimal(overrides.get(month_key, monthly)) for month_key in due_months if month_key not in covered_months),
        Decimal("0"),
    )
    total = recorded + automatic_total
    return total


def calculate_recorded_advance_total(*, bookings, period_start=None, as_of=None, period_end=None) -> Decimal:
    """Sum only proven advance bookings inside the active billing window.

    Contractual monthly amounts are expected/due values, not payment evidence.
    Only explicit ``advance`` bookings are deducted from an account balance.
    """
    from datetime import date

    today = as_of or date.today()
    if isinstance(today, str):
        today = date.fromisoformat(today[:10])
    start = date.fromisoformat(str(period_start)[:10]) if period_start else date.min
    end = today
    if period_end:
        end = min(end, date.fromisoformat(str(period_end)[:10]))
    total = Decimal("0")
    for booking in bookings or []:
        if booking.get("booking_type") != "advance":
            continue
        raw_date = str(booking.get("date", ""))[:10]
        try:
            booked_on = date.fromisoformat(raw_date)
        except ValueError:
            continue
        if start <= booked_on <= end:
            total += _decimal(booking.get("amount", 0) or 0)
    return total


def apply_booking_corrections(*, account_balance, corrections) -> Decimal:
    """Apply signed corrections to the customer account after sign conversion.

    The same rule applies to every meter and billing direction: positive
    corrections increase the customer account balance; negative corrections
    reduce it. The original booking records remain unchanged in the ledger.
    """
    return _decimal(account_balance) + _decimal(corrections)


def signed_customer_balance(*, direction: str, amount) -> Decimal:
    """Convert an independently calculated balance to customer-account signs.

    Consumption liabilities are negative; feed-in remuneration credits are
    positive. The function preserves the distinction between the two billing
    directions and rounds only the final account amount to cents.
    """
    value = _decimal(amount)
    if direction == "consumption":
        value = -value
    elif direction != "feed_in":
        raise ValueError("Unbekannter Abrechnungsbereich")
    return value


def build_monthly_advance_groups(*, period_start, as_of=None, period_end=None, monthly_advance_gross=0, monthly_amounts=None, bookings=None):
    """Group each elapsed monthly advance by effective amount within a billing period.

    Project rule: each elapsed month in the active billing period counts as a
    paid monthly advance. Explicit advance bookings do not create a second
    amount for the same month. The effective monthly amount is taken from the
    month-specific history, falling back to the configured default.
    """
    from datetime import date

    today = as_of or date.today()
    if isinstance(today, str):
        today = date.fromisoformat(today[:10])
    if not period_start:
        return []
    start = date.fromisoformat(str(period_start)[:10])
    end = today
    if period_end:
        end = min(end, date.fromisoformat(str(period_end)[:10]))
    if start > end:
        return []

    overrides = monthly_amounts or {}
    groups = []
    year, month = start.year, start.month
    while date(year, month, 1) <= end:
        key = f"{year:04d}-{month:02d}"
        amount = _decimal(overrides.get(key, monthly_advance_gross)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if groups and groups[-1]["to_month"] == previous_key and groups[-1]["monthly_amount"] == amount:
            groups[-1]["count"] += 1
            groups[-1]["total"] = (groups[-1]["total"] + amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            groups[-1]["to_month"] = key
        else:
            groups.append({"from_month": key, "to_month": key, "count": 1,
                           "monthly_amount": amount, "total": amount})
        previous_key = key
        if month == 12:
            year, month = year + 1, 1
        else:
            month += 1
    return [{key: (float(value) if isinstance(value, Decimal) else value) for key, value in group.items()} for group in groups]
