from decimal import Decimal

import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "custom_components/verbrauchsmonitor/measurement_validation.py"
SPEC = importlib.util.spec_from_file_location("vm_measurement_validation", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
parse_reading = MODULE.parse_reading
validate_reading = MODULE.validate_reading


def test_parse_accepts_finite_nonnegative_numeric_values():
    assert parse_reading("123.45") == Decimal("123.45")
    assert parse_reading(0) == Decimal("0")
    assert parse_reading("0") == Decimal("0")


def test_parse_rejects_unknown_empty_non_numeric_and_non_finite_values():
    for value in (None, "", "  ", "unknown", "unavailable", "none", "null", "text", "NaN", "Infinity", "-Infinity", "1e10000", float("nan"), float("inf"), -1, "-0.01", True):
        assert parse_reading(value) is None, value


def test_monotonic_validation_accepts_equal_and_increasing_but_rejects_decrease():
    assert validate_reading("10", "10") == (Decimal("10"), "accepted")
    assert validate_reading("10.1", "10") == (Decimal("10.1"), "accepted")
    assert validate_reading("9.99", "10") == (None, "decreased")


def test_invalid_value_never_becomes_new_reference():
    last = Decimal("100.0")
    for invalid in ("unavailable", "NaN", "-1", "not-a-number"):
        accepted, status = validate_reading(invalid, last)
        assert accepted is None
        assert status == "invalid"
        assert last == Decimal("100.0")


def test_sensor_runtime_requires_dated_meter_change_before_accepting_counter_decrease():
    source = (MODULE_PATH.parent / "sensor.py").read_text(encoding="utf-8")
    assert "def _confirmed_meter_change(self, previous_reading):" in source
    assert "confirmed_meter_change(" in source
    helper = MODULE_PATH.read_text(encoding="utf-8")
    assert "start_date <= change_date <= today_date" in helper
    assert "end_reading >= baseline_value" in helper
    assert "rückläufiger Messwert ignoriert" in source


def test_meter_change_confirmation_requires_matching_direction_date_and_valid_end_reading():
    confirm = MODULE.confirmed_meter_change
    changes = [{"date": "2026-11-26", "consumption_reading": "1200", "feed_in_reading": "400"}]
    assert confirm(changes, direction="consumption", period_start="2026-11-01", today="2026-11-27", baseline="1000", previous_reading="1200")
    assert confirm(changes, direction="feed_in", period_start="2026-11-01", today="2026-11-27", baseline="300", previous_reading="400")
    assert not confirm(changes, direction="consumption", period_start="2026-11-27", today="2026-11-27", baseline="1000", previous_reading="1200")
    assert not confirm(changes, direction="consumption", period_start="2026-11-01", today="2026-11-25", baseline="1000", previous_reading="1200")
    assert not confirm(changes, direction="consumption", period_start="2026-11-01", today="2026-11-27", baseline="1300", previous_reading="1400")
