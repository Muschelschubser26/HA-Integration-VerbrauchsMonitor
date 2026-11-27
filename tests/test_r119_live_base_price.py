from datetime import datetime, timezone
from decimal import Decimal
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

ROOT = Path(__file__).parents[1]
PRICING = ROOT / "custom_components/verbrauchsmonitor/pricing.py"


def _load_pricing():
    spec = spec_from_file_location("vm_r119_pricing", PRICING)
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_base_price_accrues_to_exact_current_timestamp():
    pricing = _load_pricing()
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    halfway = datetime(2026, 7, 2, 12, 0, tzinfo=timezone.utc)
    result = pricing.accrued_annual_base_price("120.00", start, halfway)
    assert result == Decimal("60.00")


def test_base_price_zero_and_future_start_are_zero():
    pricing = _load_pricing()
    now = datetime(2026, 5, 1, tzinfo=timezone.utc)
    future = datetime(2026, 5, 2, tzinfo=timezone.utc)
    assert pricing.accrued_annual_base_price("0", now, now) == Decimal("0.00")
    assert pricing.accrued_annual_base_price("120", future, now) == Decimal("0.00")


def test_base_price_never_exceeds_one_annual_amount():
    pricing = _load_pricing()
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    now = datetime(2027, 1, 1, tzinfo=timezone.utc)
    assert pricing.accrued_annual_base_price("120", start, now) == Decimal("120.00")
