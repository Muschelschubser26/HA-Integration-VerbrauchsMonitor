from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

PATH = Path(__file__).parents[1] / "custom_components" / "verbrauchsmonitor" / "ledger.py"
spec = spec_from_file_location("vm_r142_ledger", PATH)
ledger = module_from_spec(spec)
sys.modules[spec.name] = ledger
spec.loader.exec_module(ledger)


def test_monthly_advance_groups_split_at_effective_change_and_year_boundary():
    groups = ledger.build_monthly_advance_groups(
        period_start="2026-12-01",
        as_of="2027-04-15",
        monthly_advance_gross=200,
        monthly_amounts={"2027-02": 250, "2027-03": 250, "2027-04": 250},
    )
    assert groups == [
        {"from_month": "2026-12", "to_month": "2027-01", "count": 2,
         "monthly_amount": 200.0, "total": 400.0},
        {"from_month": "2027-02", "to_month": "2027-04", "count": 3,
         "monthly_amount": 250.0, "total": 750.0},
    ]


def test_monthly_advance_groups_count_elapsed_months_even_without_booking_records():
    groups = ledger.build_monthly_advance_groups(
        period_start="2027-01-01",
        as_of="2027-08-01",
        period_end="2027-12-31",
        monthly_advance_gross=200,
        monthly_amounts={"2027-03": 250},
        bookings=[{"booking_type": "advance", "date": "2027-02-03", "amount": 200}],
    )
    assert [(g["from_month"], g["to_month"], g["count"], g["total"]) for g in groups] == [
        ("2027-01", "2027-02", 2, 400.0),
        ("2027-03", "2027-03", 1, 250.0),
        ("2027-04", "2027-08", 5, 1000.0),
    ]


def test_zero_monthly_advance_is_preserved_as_a_valid_amount():
    groups = ledger.build_monthly_advance_groups(
        period_start="2027-01-01",
        as_of="2027-02-01",
        monthly_advance_gross=200,
        monthly_amounts={"2027-02": 0},
    )
    assert [g["monthly_amount"] for g in groups] == [200.0, 0.0]


def test_recorded_month_does_not_split_group_when_effective_rate_is_unchanged():
    groups = ledger.build_monthly_advance_groups(
        period_start="2027-01-01",
        as_of="2027-03-01",
        monthly_advance_gross=200,
        bookings=[{"booking_type": "advance", "date": "2027-02-01", "amount": 200}],
    )
    assert [(g["from_month"], g["to_month"], g["count"]) for g in groups] == [
        ("2027-01", "2027-03", 3),
    ]


def test_single_month_group_is_one_month_and_uses_its_month_amount():
    groups = ledger.build_monthly_advance_groups(
        period_start="2027-01-01", as_of="2027-04-15", monthly_advance_gross=200,
        monthly_amounts={"2027-04": 250},
    )
    assert groups[-1] == {"from_month": "2027-04", "to_month": "2027-04", "count": 1,
                          "monthly_amount": 250.0, "total": 250.0}
