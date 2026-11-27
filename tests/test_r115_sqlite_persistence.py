"""Regression tests for the R115 SQLite persistence transition."""
import importlib.util
import json
import sqlite3
import sys
import types
from pathlib import Path

ROOT = Path(__file__).parents[1]


def _load_database_module():
    homeassistant = types.ModuleType("homeassistant")
    core = types.ModuleType("homeassistant.core")
    core.HomeAssistant = object
    homeassistant.core = core
    sys.modules.setdefault("homeassistant", homeassistant)
    sys.modules.setdefault("homeassistant.core", core)
    path = ROOT / "custom_components/verbrauchsmonitor/database.py"
    spec = importlib.util.spec_from_file_location("vm_r115_database", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class _FakeConfig:
    def __init__(self, root):
        self.root = root

    def path(self, *parts):
        return str(self.root.joinpath(*parts))


class _FakeHass:
    def __init__(self, root):
        self.config = _FakeConfig(root)


def test_legacy_json_is_migrated_once_and_kept_as_source(tmp_path):
    database = _load_database_module()
    hass = _FakeHass(tmp_path)
    legacy = Path(hass.config.path(".storage", "verbrauchsmonitor_data.json"))
    legacy.parent.mkdir(parents=True)
    old_data = {**database._EMPTY, "contracts": [{"id": "contract-old"}]}
    legacy.write_text(json.dumps(old_data), encoding="utf-8")

    migrated = database.load_data(hass)

    assert migrated["contracts"] == [{"id": "contract-old"}]
    assert legacy.is_file()
    assert Path(database.database_path(hass)).is_file()
    assert Path(database.backup_path(hass)).is_file()
    assert database.load_data(hass)["contracts"] == [{"id": "contract-old"}]


def test_backup_is_consistent_and_reset_preserves_previous_snapshot(tmp_path):
    database = _load_database_module()
    hass = _FakeHass(tmp_path)
    initial = {**database._EMPTY, "meters": [{"id": "meter-1"}]}
    database.save_data(hass, initial)

    backup = Path(database.backup_path(hass))
    with sqlite3.connect(backup) as connection:
        previous = json.loads(connection.execute("SELECT payload FROM vm_state WHERE id=1").fetchone()[0])
    assert previous["meters"] == [{"id": "meter-1"}]

    database.reset_database(hass)
    assert database.load_data(hass)["meters"] == []
    with sqlite3.connect(backup) as connection:
        preserved = json.loads(connection.execute("SELECT payload FROM vm_state WHERE id=1").fetchone()[0])
    assert preserved["meters"] == [{"id": "meter-1"}]


def test_sqlite_schema_and_integrity_check(tmp_path):
    database = _load_database_module()
    path = tmp_path / "verbrauchsmonitor.db"
    database._write(path, database._EMPTY)
    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == database.SQLITE_SCHEMA_VERSION
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_database_status_counts_contracts_and_meters_from_config_entries(tmp_path):
    database = _load_database_module()
    hass = _FakeHass(tmp_path)
    database.save_data(hass, database._EMPTY)

    class Entry:
        def __init__(self, contracts, meters):
            self.options = {"contracts": contracts, "meters": meters}

    entries = [
        Entry([{"id": "c1"}, {"id": "c2"}], [
            {"id": "m1", "consumption_entity": "sensor.c1", "feed_in_entity": "sensor.f1"}
        ]),
        Entry([{"id": "c3"}], [
            {"id": "m2", "consumption_entity": "sensor.c2"}
        ]),
    ]
    result = database.status(hass, entries)
    assert result["status"] == "ok"
    assert result["contracts"] == 3
    assert result["meters"] == 2
    assert result["meter_readings"] == 3


def test_schema_v1_migrates_to_separated_domain_tables_without_data_loss(tmp_path):
    database = _load_database_module()
    path = tmp_path / "verbrauchsmonitor.db"
    legacy = {
        **database._EMPTY,
        "contracts": [{"id": "contract-1", "name": "Altvertrag"}],
        "meters": [{"id": "meter-1", "contract_id": "contract-1", "name": "Haus"}],
        "bookings": [{"id": "booking-1", "meter_id": "meter-1", "contract_id": "contract-1", "direction": "consumption", "amount": "42.50"}],
        "physical_meter_periods": [{"id": "period-1", "meter_id": "meter-1", "direction": "consumption", "installed_at": "2025-01-01", "start_reading": "100"}],
        "advance_rates": [{"id": "rate-1", "meter_id": "meter-1", "contract_id": "contract-1", "direction": "consumption", "effective_from": "2025-01", "amount": "50.00"}],
        "monthly_advances": [{"id": "advance-1", "meter_id": "meter-1", "direction": "consumption", "month": "2025-01", "amount": "50.00"}],
    }
    payload = json.dumps(legacy)
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE vm_state (id INTEGER PRIMARY KEY CHECK(id=1), payload TEXT NOT NULL, updated_at TEXT NOT NULL)")
        connection.execute("INSERT INTO vm_state VALUES(1, ?, '2026-01-01T00:00:00+00:00')", (payload,))
        connection.execute("PRAGMA user_version = 1")

    migrated = database._read(path)
    assert migrated["contracts"] == legacy["contracts"]
    assert migrated["meters"] == legacy["meters"]
    assert migrated["bookings"] == legacy["bookings"]
    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 2
        assert connection.execute("SELECT record_id FROM vm_contracts").fetchall() == [("contract-1",)]
        assert connection.execute("SELECT record_id, meter_id, direction FROM vm_bookings").fetchall() == [("booking-1", "meter-1", "consumption")]
        assert connection.execute("SELECT record_id, effective_from FROM vm_advance_rates").fetchall() == [("rate-1", "2025-01")]
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_config_entry_projection_is_not_erased_by_ledger_writes(tmp_path):
    database = _load_database_module()
    hass = _FakeHass(tmp_path)
    database.save_data(hass, {**database._EMPTY, "bookings": [{"id": "b1", "meter_id": "m1", "direction": "consumption"}]})

    class Entry:
        entry_id = "entry-1"
        options = {
            "contracts": [{"id": "c1", "name": "Vertrag"}],
            "meters": [{"id": "m1", "contract_id": "c1", "name": "Zähler"}],
        }

    database.sync_config_entries(hass, [Entry()])
    with sqlite3.connect(database.database_path(hass)) as connection:
        assert connection.execute("SELECT meter_id FROM vm_bookings WHERE record_id='b1'").fetchone() == ("m1",)
    database.save_data(hass, {**database._EMPTY, "bookings": [{"id": "b2", "meter_id": "m1", "direction": "feed_in"}]})
    database.save_data(hass, database.load_data(hass))

    with sqlite3.connect(database.database_path(hass)) as connection:
        assert connection.execute("SELECT record_id, entry_id FROM vm_contracts").fetchall() == [("c1", "entry-1")]
        assert connection.execute("SELECT record_id, entry_id, contract_id FROM vm_meters").fetchall() == [("m1", "entry-1", "c1")]
        assert connection.execute("SELECT record_id FROM vm_bookings").fetchall() == [("b2",)]


def test_schema_migration_keeps_immutable_pre_migration_backup(tmp_path):
    database = _load_database_module()
    path = tmp_path / "verbrauchsmonitor.db"
    original_payload = json.dumps({**database._EMPTY, "bookings": [{"id": "legacy-booking"}]})
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE vm_state (id INTEGER PRIMARY KEY CHECK(id=1), payload TEXT NOT NULL, updated_at TEXT NOT NULL)")
        connection.execute("INSERT INTO vm_state VALUES(1, ?, '2026-01-01T00:00:00+00:00')", (original_payload,))
        connection.execute("PRAGMA user_version = 1")

    database._read(path)
    backup = tmp_path / "verbrauchsmonitor-pre-r169-backup.db"
    assert backup.is_file()
    with sqlite3.connect(backup) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 1
        assert json.loads(connection.execute("SELECT payload FROM vm_state WHERE id=1").fetchone()[0])["bookings"][0]["id"] == "legacy-booking"

    database._write(path, {**database._EMPTY, "bookings": [{"id": "new-booking"}]})
    with sqlite3.connect(backup) as connection:
        assert json.loads(connection.execute("SELECT payload FROM vm_state WHERE id=1").fetchone()[0])["bookings"][0]["id"] == "legacy-booking"


def test_r169_payment_label_is_updated_in_both_languages():
    card = (ROOT / "custom_components/verbrauchsmonitor/frontend/verbrauchsmonitor-card.js").read_text(encoding="utf-8")
    assert 't("Bereits bezahlt:","Already paid:")' in card
    assert 't("Bereits gezahlt:","Payments received:")' not in card


def test_r169_normalized_tables_are_read_authority_and_keep_legacy_records(tmp_path):
    database = _load_database_module()
    path = tmp_path / "verbrauchsmonitor.db"
    legacy = {
        **database._EMPTY,
        "bookings": [
            {"id": "duplicate", "meter_id": "m1", "direction": "consumption"},
            {"id": "duplicate", "meter_id": "m2", "direction": "feed_in"},
            {"meter_id": "m3", "direction": "consumption", "legacy_field": "preserve"},
        ],
    }
    database._write(path, legacy, update_backup=False)

    with sqlite3.connect(path) as connection:
        # A stale compatibility snapshot must not override normalized records.
        connection.execute("UPDATE vm_state SET payload=? WHERE id=1", (json.dumps(database._EMPTY),))

    loaded = database._read(path)
    assert len(loaded["bookings"]) == 3
    assert loaded["bookings"][0]["id"] == "duplicate"
    assert loaded["bookings"][1]["id"] == "duplicate"
    assert loaded["bookings"][2]["legacy_field"] == "preserve"


def test_r169_relational_projection_enforces_known_contract_and_meter_references(tmp_path):
    database = _load_database_module()
    path = tmp_path / "verbrauchsmonitor.db"
    data = {
        **database._EMPTY,
        "contracts": [{"id": "c1", "name": "Vertrag"}],
        "meters": [{"id": "m1", "contract_id": "c1", "name": "Zähler"}],
        "bookings": [{"id": "b1", "meter_id": "m1", "contract_id": "c1", "direction": "consumption"}],
        "physical_meter_periods": [{"id": "p1", "meter_id": "m1", "direction": "consumption", "installed_at": "2025-01-01"}],
    }
    database._write(path, data, update_backup=False)
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        foreign_keys = {
            row[2] for table in ("vm_meters", "vm_bookings", "vm_physical_meter_periods", "vm_advance_rates", "vm_monthly_advances")
            for row in connection.execute(f"PRAGMA foreign_key_list({table})")
        }
        assert {"vm_contracts", "vm_meters"}.issubset(foreign_keys)


def test_r169_config_projection_keeps_orphan_contract_reference_in_payload(tmp_path):
    database = _load_database_module()
    hass = _FakeHass(tmp_path)

    class Entry:
        entry_id = "entry-orphan"
        options = {
            "contracts": [],
            "meters": [{"id": "meter-orphan", "contract_id": "missing-contract", "name": "Altzähler"}],
        }

    database.sync_config_entries(hass, [Entry()])
    with sqlite3.connect(database.database_path(hass)) as connection:
        row = connection.execute("SELECT contract_id, payload FROM vm_meters WHERE record_id='meter-orphan'").fetchone()
        assert row[0] is None
        assert json.loads(row[1])["contract_id"] == "missing-contract"
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
