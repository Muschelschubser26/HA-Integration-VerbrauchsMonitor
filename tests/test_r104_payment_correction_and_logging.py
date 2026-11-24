"""Regression coverage for signed corrections, all meter directions and persistence."""
from decimal import Decimal
from pathlib import Path
import importlib.util
import json
import sys
import types

ROOT = Path(__file__).resolve().parents[1]


def _load_ledger():
    path = ROOT / "custom_components/verbrauchsmonitor/ledger.py"
    spec = importlib.util.spec_from_file_location("vm_r104_ledger", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_negative_correction_reduces_customer_credit_identically_for_all_directions():
    ledger = _load_ledger()
    # These account balances already use the customer-centric convention.
    for direction in ("consumption", "feed_in"):
        before = ledger.signed_customer_balance(direction=direction, amount="-200") if direction == "consumption" else ledger.signed_customer_balance(direction=direction, amount="200")
        after = ledger.apply_booking_corrections(account_balance=before, corrections="-66.00")
        assert after == before - Decimal("66.00")


def test_positive_correction_increases_account_and_zero_is_rejected():
    ledger = _load_ledger()
    assert ledger.apply_booking_corrections(account_balance="134.00", corrections="66.00") == Decimal("200.00")
    try:
        ledger.validate_booking_amount(booking_type="correction", amount="0")
    except ValueError:
        pass
    else:
        raise AssertionError("Zero correction must be rejected")


def test_corrections_are_filtered_by_meter_direction_and_not_mutated():
    ledger = _load_ledger()
    bookings = [
        {"id": "c1", "meter_id": "m1", "direction": "consumption", "booking_type": "correction", "amount": "-66.00"},
        {"id": "f1", "meter_id": "m1", "direction": "feed_in", "booking_type": "correction", "amount": "-5.00"},
        {"id": "c2", "meter_id": "m2", "direction": "consumption", "booking_type": "correction", "amount": "-9.00"},
    ]
    original = [dict(item) for item in bookings]
    _, _, _, corrections = ledger.calculate_booking_adjustments(bookings=bookings, direction="consumption")
    assert corrections == Decimal("-75.00")
    assert bookings == original


def test_database_sqlite_writer_preserves_decimal_precision_as_string(tmp_path):
    # Import database.py with a minimal HA type stub; no HA runtime is required.
    homeassistant = types.ModuleType("homeassistant")
    core = types.ModuleType("homeassistant.core")
    core.HomeAssistant = object
    homeassistant.core = core
    sys.modules.setdefault("homeassistant", homeassistant)
    sys.modules.setdefault("homeassistant.core", core)
    path = ROOT / "custom_components/verbrauchsmonitor/database.py"
    spec = importlib.util.spec_from_file_location("vm_r104_database", path)
    database = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = database
    spec.loader.exec_module(database)
    import sqlite3
    target = tmp_path / "verbrauchsmonitor.db"
    payload = {**database._EMPTY, "contracts": [{"id": "contract-1", "amount": Decimal("134.6700")}]}
    database._write(target, payload)
    with sqlite3.connect(target) as connection:
        raw = connection.execute("SELECT payload FROM vm_state WHERE id = 1").fetchone()[0]
    saved = json.loads(raw)
    assert saved["contracts"][0]["amount"] == "134.6700"
    assert Decimal(saved["contracts"][0]["amount"]) == Decimal("134.6700")
    assert (tmp_path / "verbrauchsmonitor-backup.db").is_file()

    class FakeConfig:
        def path(self, *parts):
            return str(tmp_path.joinpath(*parts))

    class FakeHass:
        config = FakeConfig()

    booking = {
        "id": "booking-decimal", "meter_id": "meter-1", "direction": "consumption",
        "booking_type": "correction", "amount": Decimal("-66.2300"),
    }
    stored = database.add_booking(FakeHass(), booking)
    assert stored["amount"] == Decimal("-66.2300")
    reloaded = database.assigned_bookings(FakeHass(), "meter-1", "consumption")
    assert reloaded[0]["amount"] == "-66.2300"
    assert database.assigned_bookings(FakeHass(), "meter-2", "consumption") == []


def test_integration_has_no_info_or_debug_logging_calls():
    integration = ROOT / "custom_components/verbrauchsmonitor"
    for source in integration.rglob("*.py"):
        text = source.read_text(encoding="utf-8")
        assert "_LOGGER.info(" not in text, source
        assert "_LOGGER.debug(" not in text, source


def test_sensor_setup_scopes_booking_ledger_to_each_meter_before_balance_calculation():
    source = (ROOT / "custom_components/verbrauchsmonitor/sensor.py").read_text(encoding="utf-8")
    assert 'b.get("status") == "assigned" and b.get("meter_id") == meter.get("id")' in source
    assert 'b.get("direction") == ("consumption" if self._source == entry.data.get(CONF_CONSUMPTION_ENTITY) else "feed_in")' in source


def test_feed_in_card_displays_the_same_correction_adjusted_payment_total():
    card = (ROOT / "custom_components/verbrauchsmonitor/frontend/verbrauchsmonitor-card.js").read_text(encoding="utf-8")
    assert card.count('money(finance.advancePaid+finance.additionalPayments+finance.corrections)') == 2
    assert 'const totalCosts = Number.isFinite(backendTotalCosts) ? backendTotalCosts :' in card
