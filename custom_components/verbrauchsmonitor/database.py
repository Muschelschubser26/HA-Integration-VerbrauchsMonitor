"""Local SQLite persistence for historical billing data.

Live Home Assistant sensor states are deliberately never written here. The
integration stores its validated domain payload in a transactional SQLite
snapshot. JSON remains the portable import/export format.
"""
from __future__ import annotations

import copy
from contextlib import closing
import json
import sqlite3
import uuid
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timezone
from pathlib import Path
from homeassistant.core import HomeAssistant

SCHEMA_VERSION = 3
SQLITE_SCHEMA_VERSION = 2
_EMPTY = {
    "schema_version": SCHEMA_VERSION,
    "contracts": [],
    "meters": [],
    "bookings": [],
    "physical_meter_periods": [],
    "advance_rates": [],
    "monthly_advances": [],
    "migration": {"legacy_bookings_imported": False},
}


def database_path(hass: HomeAssistant) -> Path:
    """Return the primary SQLite database path in the HA configuration root."""
    return Path(hass.config.path("verbrauchsmonitor.db"))


def backup_path(hass: HomeAssistant) -> Path:
    """Return the single rolling SQLite backup path."""
    return Path(hass.config.path("verbrauchsmonitor-backup.db"))


def _legacy_json_path(hass: HomeAssistant) -> Path:
    """Return the former JSON store path used by releases before SQLite."""
    return Path(hass.config.path(".storage", "verbrauchsmonitor_data.json"))


def _normalize(data: dict) -> dict:
    """Upgrade and validate the domain payload independently of SQLite schema."""
    if not isinstance(data, dict):
        raise ValueError("Ungültige Datenbank")
    version = data.get("schema_version", 1)
    if version == 1:
        data = {**_EMPTY, **data, "schema_version": SCHEMA_VERSION}
        data.setdefault("physical_meter_periods", [])
        data.setdefault("advance_rates", [])
        data.setdefault("monthly_advances", [])
        data.setdefault("migration", {"legacy_bookings_imported": False})
    elif version == 2:
        data = {**_EMPTY, **data, "schema_version": SCHEMA_VERSION}
        data.setdefault("monthly_advances", [])
    elif version != SCHEMA_VERSION:
        raise ValueError("Unbekannte oder ungültige Datenbankversion")
    for key in ("contracts", "meters", "bookings", "physical_meter_periods", "advance_rates", "monthly_advances"):
        if not isinstance(data.get(key), list):
            raise ValueError(f"Ungültiger Datenbankbereich: {key}")
    data.setdefault("migration", {"legacy_bookings_imported": False})
    return data


def _json_default(value):
    """Serialize exact monetary Decimals as strings, never binary floats."""
    if isinstance(value, Decimal):
        return format(value, "f")
    raise TypeError(f"Nicht JSON-serialisierbarer Datentyp: {type(value).__name__}")


def _connect(path: Path) -> sqlite3.Connection:
    """Open a configured SQLite connection and ensure the minimal schema exists."""
    path.parent.mkdir(parents=True, exist_ok=True)
    database_existed = path.is_file()
    connection = sqlite3.connect(path, timeout=30)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA synchronous = FULL")
    connection.execute(
        "CREATE TABLE IF NOT EXISTS vm_state ("
        "id INTEGER PRIMARY KEY CHECK (id = 1), "
        "payload TEXT NOT NULL, updated_at TEXT NOT NULL)"
    )
    current_version = connection.execute("PRAGMA user_version").fetchone()[0]
    if current_version > SQLITE_SCHEMA_VERSION:
        connection.close()
        raise ValueError("SQLite-Datenbank wurde mit einer neueren Integration-Version erstellt")
    if current_version < 2 and database_existed:
        # Preserve the exact pre-migration database before changing even its
        # schema-version marker. This backup is never replaced automatically.
        migration_backup = path.with_name("verbrauchsmonitor-pre-r169-backup.db")
        if not migration_backup.exists():
            _create_backup(path, migration_backup)
    if current_version < 1:
        # R115: the original transactional snapshot is the compatibility
        # source. It is intentionally retained during the staged migration.
        connection.execute("PRAGMA user_version = 1")
        current_version = 1
    if current_version < 2:
        # R169: introduce separated domain tables. Every table keeps the
        # complete original record as JSON while exposing stable relationship
        # columns for integrity checks and future indexed queries. The legacy
        # snapshot remains available for rollback and portable export.
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS vm_contracts (
                record_id TEXT PRIMARY KEY, entry_id TEXT NOT NULL DEFAULT '',
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS vm_meters (
                record_id TEXT PRIMARY KEY, entry_id TEXT NOT NULL DEFAULT '',
                contract_id TEXT REFERENCES vm_contracts(record_id) ON DELETE SET NULL,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS vm_bookings (
                record_id TEXT PRIMARY KEY,
                meter_id TEXT REFERENCES vm_meters(record_id) ON DELETE SET NULL,
                contract_id TEXT REFERENCES vm_contracts(record_id) ON DELETE SET NULL,
                direction TEXT, payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS vm_physical_meter_periods (
                record_id TEXT PRIMARY KEY,
                meter_id TEXT REFERENCES vm_meters(record_id) ON DELETE SET NULL,
                direction TEXT NOT NULL, installed_at TEXT, payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS vm_advance_rates (
                record_id TEXT PRIMARY KEY,
                meter_id TEXT REFERENCES vm_meters(record_id) ON DELETE SET NULL,
                contract_id TEXT REFERENCES vm_contracts(record_id) ON DELETE SET NULL,
                direction TEXT NOT NULL,
                effective_from TEXT NOT NULL, payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS vm_monthly_advances (
                record_id TEXT PRIMARY KEY,
                meter_id TEXT REFERENCES vm_meters(record_id) ON DELETE SET NULL,
                direction TEXT NOT NULL, month TEXT NOT NULL,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS vm_migration_state (
                state_key TEXT PRIMARY KEY, payload TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_vm_meters_contract ON vm_meters(contract_id);
            CREATE INDEX IF NOT EXISTS idx_vm_bookings_meter_direction ON vm_bookings(meter_id, direction);
            CREATE INDEX IF NOT EXISTS idx_vm_periods_meter_direction ON vm_physical_meter_periods(meter_id, direction);
            CREATE INDEX IF NOT EXISTS idx_vm_rates_lookup ON vm_advance_rates(meter_id, direction, effective_from);
            CREATE INDEX IF NOT EXISTS idx_vm_monthly_lookup ON vm_monthly_advances(meter_id, direction, month);
        """)
        # Backfill atomically from the pre-existing snapshot. Re-running this
        # migration is safe because the tables are rebuilt from that snapshot.
        row = connection.execute("SELECT payload FROM vm_state WHERE id = 1").fetchone()
        if row:
            try:
                legacy_payload = json.loads(row[0])
            except (TypeError, json.JSONDecodeError) as err:
                connection.close()
                raise ValueError("SQLite-Migration abgebrochen: bestehender Datenbestand ist ungültig") from err
            _sync_domain_tables(connection, legacy_payload)
        connection.execute("PRAGMA user_version = 2")
    return connection


def _sync_domain_tables(connection: sqlite3.Connection, data: dict) -> None:
    """Synchronize separated domain tables from one validated snapshot.

    All replacement statements run in the caller's SQLite transaction. The
    separated tables are the read authority for these record collections;
    vm_state remains a compatibility snapshot for rollback and JSON export.
    """
    tables = (
        "vm_bookings", "vm_physical_meter_periods", "vm_advance_rates",
        "vm_monthly_advances", "vm_migration_state",
    )
    for table in tables:
        connection.execute(f"DELETE FROM {table}")

    def payload(record: dict) -> str:
        return json.dumps(record, ensure_ascii=False, sort_keys=True, default=_json_default)

    seen_ids: dict[str, set[str]] = {}

    def storage_id(record: dict, prefix: str, index: int) -> str:
        # Legacy records without IDs and duplicate legacy IDs remain lossless.
        # Synthetic storage keys are deterministic and never alter payloads.
        base = str(record.get("id") or f"legacy-{prefix}-{index}")
        used = seen_ids.setdefault(prefix, set())
        candidate = base
        suffix = 2
        while candidate in used:
            candidate = f"{base}#{suffix}"
            suffix += 1
        used.add(candidate)
        return candidate

    # Config-entry options are the live authority for these two domains.
    # Empty lists in an ordinary ledger write must not erase their projection.
    contract_entries = {row[0]: row[1] for row in connection.execute("SELECT record_id, entry_id FROM vm_contracts")}
    meter_entries = {row[0]: row[1] for row in connection.execute("SELECT record_id, entry_id FROM vm_meters")}
    if data.get("contracts") or data.get("meters"):
        connection.execute("DELETE FROM vm_meters")
    if data.get("contracts"):
        connection.execute("DELETE FROM vm_contracts")
    for index, record in enumerate(data.get("contracts", [])):
        record_id = storage_id(record, "contract", index)
        connection.execute("INSERT INTO vm_contracts(record_id,entry_id,payload) VALUES(?,?,?)", (record_id, contract_entries.get(record_id, ""), payload(record)))
    known_contracts = {row[0] for row in connection.execute("SELECT record_id FROM vm_contracts")}
    for index, record in enumerate(data.get("meters", [])):
        contract_id = str(record.get("contract_id")) if record.get("contract_id") is not None else None
        if contract_id not in known_contracts:
            contract_id = None
        record_id = storage_id(record, "meter", index)
        connection.execute("INSERT INTO vm_meters(record_id,entry_id,contract_id,payload) VALUES(?,?,?,?)", (record_id, meter_entries.get(record_id, ""), contract_id, payload(record)))
    known_meters = {row[0] for row in connection.execute("SELECT record_id FROM vm_meters")}
    for index, record in enumerate(data.get("bookings", [])):
        meter_id = str(record.get("meter_id")) if record.get("meter_id") is not None else None
        contract_id = str(record.get("contract_id")) if record.get("contract_id") is not None else None
        connection.execute("INSERT INTO vm_bookings(record_id,meter_id,contract_id,direction,payload) VALUES(?,?,?,?,?)", (storage_id(record, "booking", index), meter_id if meter_id in known_meters else None, contract_id if contract_id in known_contracts else None, record.get("direction"), payload(record)))
    for index, record in enumerate(data.get("physical_meter_periods", [])):
        meter_id = str(record.get("meter_id")) if record.get("meter_id") is not None else None
        connection.execute("INSERT INTO vm_physical_meter_periods(record_id,meter_id,direction,installed_at,payload) VALUES(?,?,?,?,?)", (storage_id(record, "period", index), meter_id if meter_id in known_meters else None, str(record.get("direction", "")), record.get("installed_at"), payload(record)))
    for index, record in enumerate(data.get("advance_rates", [])):
        meter_id = str(record.get("meter_id")) if record.get("meter_id") is not None else None
        contract_id = str(record.get("contract_id")) if record.get("contract_id") is not None else None
        connection.execute("INSERT INTO vm_advance_rates(record_id,meter_id,contract_id,direction,effective_from,payload) VALUES(?,?,?,?,?,?)", (storage_id(record, "rate", index), meter_id if meter_id in known_meters else None, contract_id if contract_id in known_contracts else None, str(record.get("direction", "")), str(record.get("effective_from", "")), payload(record)))
    for index, record in enumerate(data.get("monthly_advances", [])):
        meter_id = str(record.get("meter_id")) if record.get("meter_id") is not None else None
        connection.execute("INSERT INTO vm_monthly_advances(record_id,meter_id,direction,month,payload) VALUES(?,?,?,?,?)", (storage_id(record, "monthly-advance", index), meter_id if meter_id in known_meters else None, str(record.get("direction", "")), str(record.get("month", "")), payload(record)))
    migration = data.get("migration", {})
    connection.execute("INSERT INTO vm_migration_state(state_key,payload) VALUES('integration',?)", (payload(migration),))


def sync_config_entries(hass: HomeAssistant, entries) -> None:
    """Project all configured contracts and meters into relational tables.

    Config-entry options remain authoritative. The projection uses nullable
    foreign keys for unresolved legacy links while preserving the full option
    payload unchanged.
    """
    path = database_path(hass)
    entries = list(entries)
    with closing(_connect(path)) as connection:
        with connection:
            connection.execute("DELETE FROM vm_meters")
            connection.execute("DELETE FROM vm_contracts")
            for entry in entries:
                entry_id = str(entry.entry_id)
                for contract in entry.options.get("contracts", []):
                    if contract.get("id") is None:
                        continue
                    connection.execute(
                        "INSERT INTO vm_contracts(record_id,entry_id,payload) VALUES(?,?,?)",
                        (str(contract["id"]), entry_id, json.dumps(contract, ensure_ascii=False, sort_keys=True, default=_json_default)),
                    )
            known_contracts = {row[0] for row in connection.execute("SELECT record_id FROM vm_contracts")}
            for entry in entries:
                entry_id = str(entry.entry_id)
                for meter in entry.options.get("meters", []):
                    if meter.get("id") is None:
                        continue
                    contract_id = str(meter.get("contract_id")) if meter.get("contract_id") is not None else None
                    if contract_id not in known_contracts:
                        contract_id = None
                    connection.execute(
                        "INSERT INTO vm_meters(record_id,entry_id,contract_id,payload) VALUES(?,?,?,?)",
                        (str(meter["id"]), entry_id, contract_id, json.dumps(meter, ensure_ascii=False, sort_keys=True, default=_json_default)),
                    )
            # Rebuild ledger relationship columns against the freshly projected
            # config-entry IDs. Keep the option-backed parent tables untouched.
            snapshot_row = connection.execute("SELECT payload FROM vm_state WHERE id = 1").fetchone()
            if snapshot_row:
                snapshot = json.loads(snapshot_row[0])
                snapshot["contracts"] = []
                snapshot["meters"] = []
                _sync_domain_tables(connection, snapshot)


def _read(path: Path) -> dict:
    """Read the current snapshot, or return an empty validated structure."""
    if not path.exists():
        return copy.deepcopy(_EMPTY)
    with closing(_connect(path)) as connection:
        with connection:
            row = connection.execute("SELECT payload FROM vm_state WHERE id = 1").fetchone()
            if row is None:
                data = copy.deepcopy(_EMPTY)
            else:
                try:
                    data = json.loads(row[0])
                except (TypeError, json.JSONDecodeError) as err:
                    raise ValueError("SQLite-Datenbank enthält einen ungültigen Datenbestand") from err
            # R169 read-path cutover for persisted domain records. The snapshot
            # is retained as rollback/export metadata, while normalized tables
            # are authoritative for the separated record collections.
            for key, table in (
                ("contracts", "vm_contracts"),
                ("meters", "vm_meters"),
                ("bookings", "vm_bookings"),
                ("physical_meter_periods", "vm_physical_meter_periods"),
                ("advance_rates", "vm_advance_rates"),
                ("monthly_advances", "vm_monthly_advances"),
            ):
                rows = connection.execute(f"SELECT payload FROM {table} ORDER BY rowid").fetchall()
                data[key] = [json.loads(item[0]) for item in rows]
            migration_rows = connection.execute("SELECT payload FROM vm_migration_state WHERE state_key='integration'").fetchone()
            if migration_rows:
                data["migration"] = json.loads(migration_rows[0])
    return _normalize(data)


def _create_backup(source: Path, target: Path) -> None:
    """Create a transactionally consistent replacement of the backup database."""
    if not source.exists():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".tmp")
    temporary.unlink(missing_ok=True)
    with closing(sqlite3.connect(source, timeout=30)) as source_connection:
        with closing(sqlite3.connect(temporary, timeout=30)) as target_connection:
            source_connection.backup(target_connection)
    temporary.replace(target)


def _write(path: Path, data: dict, *, update_backup: bool = True) -> None:
    """Persist one complete validated snapshot in a SQLite transaction."""
    normalized = _normalize(dict(data))
    payload = json.dumps(normalized, ensure_ascii=False, sort_keys=True, default=_json_default)
    with closing(_connect(path)) as connection:
        with connection:
            connection.execute(
                "INSERT INTO vm_state (id, payload, updated_at) VALUES (1, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET payload=excluded.payload, updated_at=excluded.updated_at",
                (payload, datetime.now(timezone.utc).isoformat()),
            )
            _sync_domain_tables(connection, normalized)
    if update_backup:
        _create_backup(path, path.with_name("verbrauchsmonitor-backup.db"))


def load_data(hass: HomeAssistant) -> dict:
    """Load data and migrate the former JSON store once without deleting it."""
    path = database_path(hass)
    if not path.exists():
        legacy = _legacy_json_path(hass)
        if legacy.is_file():
            try:
                legacy_data = _normalize(json.loads(legacy.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError, ValueError) as err:
                raise ValueError(f"Alte JSON-Datenbank konnte nicht übernommen werden: {err}") from err
            _write(path, legacy_data)
            return legacy_data
        _write(path, copy.deepcopy(_EMPTY))
    return _read(path)

def migrate_legacy_bookings(
    hass: HomeAssistant,
    entry_id: str,
    bookings: list[dict],
    meters: list[dict] | None = None,
) -> dict:
    """Import and safely reconcile legacy bookings without guessing assignments.

    A legacy booking is assigned only when it already identifies a valid
    direction and exactly one configured logical meter supports that
    direction. Ambiguous or incomplete records remain unresolved.
    """
    p = database_path(hass)
    data = load_data(hass)
    migration = data.setdefault("migration", {})
    imported_entries = migration.setdefault("legacy_entries", [])
    known = {str(item.get("id")): item for item in data["bookings"]}
    configured_meters = list(meters or [])

    for old in bookings or []:
        original_id = str(old.get("id") or uuid.uuid4())
        legacy_id = f"legacy-{entry_id}-{original_id}"
        existing = known.get(legacy_id)
        # Re-read the original config-entry payload on every setup. This
        # restores direction metadata that older migration code may have
        # cleared, while preserving any user edits already made in the ledger.
        item = dict(old) if existing is None else {**dict(old), **existing}
        direction = (
            old.get("direction")
            if old.get("direction") in ("consumption", "feed_in")
            else (existing or {}).get("direction")
        )
        meter_id = old.get("meter_id") or (existing or {}).get("meter_id")
        meter = next((m for m in configured_meters if meter_id and str(m.get("id")) == str(meter_id)), None)
        if meter is None and direction:
            candidates = [
                m for m in configured_meters
                if (m.get("consumption_entity") if direction == "consumption" else m.get("feed_in_entity"))
            ]
            if len(candidates) == 1:
                meter = candidates[0]
                meter_id = meter.get("id")
        if meter and direction:
            contract_id = meter.get("contract_id")
            status = "assigned"
        else:
            meter_id = None
            contract_id = None
            status = "unresolved"

        item.update({
            "id": legacy_id,
            "legacy_id": original_id,
            "source": "r039",
            "status": status,
            "meter_id": meter_id,
            "direction": direction if status == "assigned" else None,
            "contract_id": contract_id if status == "assigned" else None,
            "comment": old.get("comment", old.get("description", "")),
        })
        data["bookings"] = [record for record in data["bookings"] if record.get("id") != legacy_id]
        data["bookings"].append(item)
        known[legacy_id] = item

    if entry_id not in imported_entries:
        imported_entries.append(entry_id)
    migration["legacy_bookings_imported"] = True
    _write(p, data)
    return data

def save_data(hass: HomeAssistant, data: dict) -> dict:
    """Persist a validated database payload atomically."""
    normalized=_validate_import(dict(data)); _write(database_path(hass), normalized); return normalized

def add_booking(hass: HomeAssistant, booking: dict) -> dict:
    """Persist a validated booking in the local database."""
    p=database_path(hass); data=_read(p); item=dict(booking)
    item.setdefault("id", str(uuid.uuid4())); item["status"]="assigned"
    if not item.get("meter_id") or item.get("direction") not in ("consumption", "feed_in"):
        raise ValueError("Zähler und Abrechnungsbereich müssen zugeordnet sein")
    data["bookings"]=[b for b in data["bookings"] if b.get("id") != item["id"]]+[item]
    _write(p,data); return item

def assigned_bookings(hass: HomeAssistant, meter_id: str, direction: str) -> list[dict]:
    """Return bookings assigned to the requested meter and billing direction."""
    data=load_data(hass)
    return [dict(b) for b in data["bookings"] if b.get("status") == "assigned" and b.get("meter_id") == meter_id and b.get("direction") == direction]

def status(hass: HomeAssistant, config_entries=None) -> dict:
    """Return database metadata and counts from their authoritative stores.

    Contracts and logical meters live in ConfigEntry options, not in SQLite.
    Historical records and bookings remain counted from the local ledger.
    """
    p=database_path(hass)
    try:
        data=load_data(hass)
        with closing(_connect(p)) as connection:
            integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise sqlite3.DatabaseError(f"SQLite-Integritätsprüfung fehlgeschlagen: {integrity}")
        entries = list(config_entries or [])
        configured_contracts = sum(len(entry.options.get("contracts", [])) for entry in entries)
        configured_meters = sum(len(entry.options.get("meters", [])) for entry in entries)
        # Count actual configured meter-reading source entities, not helper
        # records or SQLite rows. A logical meter may have consumption,
        # feed-in, or both directions configured.
        configured_readings = sum(
            1
            for entry in entries
            for meter in entry.options.get("meters", [])
            for key in ("consumption_entity", "feed_in_entity")
            if meter.get(key)
        )
        return {"status":"ok", "integrity_check":integrity, "exists":p.exists(), "size_bytes":p.stat().st_size if p.exists() else 0,
          "schema_version":SCHEMA_VERSION,
          "contracts":configured_contracts if config_entries is not None else len(data['contracts']),
          "meters":configured_meters if config_entries is not None else len(data['meters']),
          "meter_readings":configured_readings if config_entries is not None else 0,
          "bookings":len(data['bookings']), "unresolved_bookings":sum(1 for b in data['bookings'] if b.get('status')=='unresolved'),
          "physical_meter_periods":len(data['physical_meter_periods']), "advance_rates":len(data['advance_rates']), "monthly_advances":len(data['monthly_advances']),
          "last_modified":datetime.fromtimestamp(p.stat().st_mtime, timezone.utc).isoformat() if p.exists() else None}
    except (OSError, ValueError, sqlite3.Error, json.JSONDecodeError) as err: return {"status":"error", "message":str(err)}

def optimize(hass: HomeAssistant) -> dict:
    """Rewrite the local data file in its normalized compact representation."""
    p=database_path(hass); data=load_data(hass); _write(p,data); return status(hass)
def export_database(hass: HomeAssistant) -> str:
    """Create a validated export payload for the local database."""
    p=database_path(hass); data=load_data(hass)
    export_dir=Path(hass.config.path("www", "verbrauchsmonitor")); export_dir.mkdir(parents=True, exist_ok=True)
    target=export_dir/"verbrauchsmonitor-datenbank.json"
    payload = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True, default=_json_default) + "\n"
    temporary = target.with_suffix(".tmp")
    temporary.write_text(payload, encoding="utf-8")
    temporary.replace(target)
    return "/local/verbrauchsmonitor/verbrauchsmonitor-datenbank.json"
def import_database(hass: HomeAssistant, source: str) -> dict:
    """Validate and persist an imported database payload."""
    base=Path(hass.config.path("www", "verbrauchsmonitor")).resolve(); candidate=(base/source).resolve()
    if candidate.parent != base or not candidate.is_file(): raise ValueError("Importdatei nicht gefunden oder nicht zulässig")
    data=json.loads(candidate.read_text(encoding="utf-8")); data=_validate_import(data)
    p=database_path(hass); p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists():
        _create_backup(p, backup_path(hass))
    _write(p,data,update_backup=False)
    return status(hass)
def _validate_import(data):
    """Validate and normalize a portable JSON import payload."""
    return _normalize(data)

def reset_database(hass: HomeAssistant) -> dict:
    """Reset the integration database using the requested reset scope."""
    path=database_path(hass)
    if path.exists():
        _create_backup(path, backup_path(hass))
    _write(path, copy.deepcopy(_EMPTY), update_backup=False)
    # Reset only the persisted database projection. Config-entry options are
    # untouched and will repopulate these two tables on the next setup.
    with closing(_connect(path)) as connection:
        with connection:
            connection.execute("DELETE FROM vm_meters")
            connection.execute("DELETE FROM vm_contracts")
    return status(hass)


def record_physical_meter_period(hass: HomeAssistant, record: dict) -> dict:
    """Store a historical physical meter segment, never a live reading."""
    required=("meter_id", "direction", "physical_meter_number", "installed_at", "start_reading")
    if any(record.get(key) in (None, "") for key in required): raise ValueError("Unvollständiger Zählerabschnitt")
    if record.get("direction") not in ("consumption", "feed_in"): raise ValueError("Ungültiger Messbereich")
    item=dict(record); item.setdefault("id", str(uuid.uuid4()))
    p=database_path(hass); data=_read(p)
    data["physical_meter_periods"]=[x for x in data["physical_meter_periods"] if x.get("id") != item["id"]]+[item]
    _write(p,data); return item

def record_advance_rate(hass: HomeAssistant, *, meter_id: str, direction: str, effective_from: str, amount: float, contract_id: str) -> dict:
    """Store a monthly amount effective from a calendar month (ISO YYYY-MM)."""
    if direction not in ("consumption", "feed_in"): raise ValueError("Ungültiger Abrechnungsbereich")
    month=str(effective_from)[:7]
    if len(month)!=7 or month[4]!="-": raise ValueError("Gültigkeitsbeginn muss YYYY-MM sein")
    value=float(amount)
    if value < 0: raise ValueError("Abschlag darf nicht negativ sein")
    item={"id":str(uuid.uuid4()),"meter_id":meter_id,"direction":direction,"contract_id":contract_id,"effective_from":month,"amount":round(value,2)}
    p=database_path(hass); data=_read(p)
    data["advance_rates"]=[x for x in data["advance_rates"] if not (x.get("meter_id")==meter_id and x.get("direction")==direction and x.get("effective_from")==month)]+[item]
    _write(p,data); return item

def calculate_scheduled_advances(data: dict, *, meter_id: str, direction: str, start_month: str, end_month: str) -> float:
    """Calculate scheduled monthly amounts using the rate valid in each month."""
    from datetime import date
    start=date.fromisoformat(str(start_month)[:7]+"-01"); end=date.fromisoformat(str(end_month)[:7]+"-01")
    if end < start: return 0.0
    rates=sorted((r for r in data.get("advance_rates",[]) if r.get("meter_id")==meter_id and r.get("direction")==direction),key=lambda r:r.get("effective_from",""))
    total=0.0; cursor=start
    while cursor<=end:
        key=cursor.strftime("%Y-%m"); valid=[r for r in rates if r.get("effective_from","")<=key]
        if valid: total+=float(valid[-1].get("amount",0))
        cursor=date(cursor.year+1,1,1) if cursor.month==12 else date(cursor.year,cursor.month+1,1)
    return round(total,2)


def get_monthly_advance(data: dict, *, meter_id: str, direction: str, month: str, default: float = 0.0) -> float:
    """Return the exact monthly override, falling back to the legacy rate/default."""
    key = str(month)[:7]
    records = [
        x for x in data.get("monthly_advances", [])
        if x.get("meter_id") == meter_id
        and x.get("direction") == direction
        and x.get("month") == key
        and not x.get("superseded")
    ]
    if records:
        latest = records[-1]
        amount = float(latest.get("amount", 0))
        # R128's feed-in editor incorrectly prefilled months with zero because
        # it read the default from the meter instead of the contract. If such
        # a legacy zero was saved, use the non-zero contract default until the
        # user explicitly edits that month. New manual records are tagged
        # below, so a deliberately entered zero remains a valid override.
        if (
            direction == "feed_in"
            and amount == 0
            and float(default or 0) > 0
            and latest.get("source") != "manual"
        ):
            return float(default)
        return amount
    rates = [x for x in data.get("advance_rates", []) if x.get("meter_id") == meter_id and x.get("direction") == direction and x.get("effective_from", "") <= key]
    return float(sorted(rates, key=lambda x: x.get("effective_from", ""))[-1]["amount"]) if rates else float(default or 0)

def next_distinct_monthly_advance(records: list[dict], *, meter_id: str, direction: str, after_month: str, current_amount: float) -> dict | None:
    """Return the next future amount transition, not repeated monthly rows.

    Manual advance changes are persisted for each month through the billing
    period. Consecutive rows with the currently active amount are not a new
    pending change and must not keep the dialog notice visible.
    """
    current = Decimal(str(current_amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    candidates = sorted(
        (item for item in records
         if item.get("meter_id") == meter_id
         and item.get("direction") == direction
         and item.get("source") == "manual"
         and not item.get("superseded")
         and str(item.get("month", "")) > str(after_month)),
        key=lambda item: str(item.get("month", "")),
    )
    for item in candidates:
        amount = Decimal(str(item.get("amount", 0))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if amount != current:
            return item
    return None


def record_monthly_advances(hass: HomeAssistant, *, meter_id: str, direction: str, contract_id: str, amounts: dict[str, float]) -> list[dict]:
    """Atomically save changed monthly advances and retain every prior version.

    All input values are validated before the database is modified. Unchanged
    month values are ignored, so submitting an untouched form does not create
    audit records or update the database snapshot.
    """
    from decimal import Decimal, ROUND_HALF_UP
    from datetime import datetime, timezone

    if direction not in ("consumption", "feed_in"):
        raise ValueError("Ungültiger Abrechnungsbereich")

    validated: dict[str, Decimal] = {}
    for month, amount in amounts.items():
        key = str(month)[:7]
        if len(key) != 7 or key[4] != "-" or not key[:4].isdigit() or not key[5:].isdigit() or not 1 <= int(key[5:]) <= 12:
            raise ValueError("Monat muss YYYY-MM sein")
        value = Decimal(str(amount))
        if not value.is_finite() or value < 0:
            raise ValueError("Abschlag darf nicht negativ sein")
        validated[key] = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    data = _read(database_path(hass))
    records = data.setdefault("monthly_advances", [])
    now = datetime.now(timezone.utc).isoformat()
    changed: list[dict] = []

    # Validate first, then update the in-memory snapshot, then commit once.
    for key, value in validated.items():
        existing = next((x for x in reversed(records) if x.get("meter_id") == meter_id and x.get("direction") == direction and x.get("month") == key and not x.get("superseded")), None)
        if existing and Decimal(str(existing.get("amount", 0))) == value:
            continue
        if existing:
            existing["superseded"] = True
            existing["superseded_at"] = now
        item = {
            "id": str(uuid.uuid4()), "meter_id": meter_id,
            "direction": direction, "contract_id": contract_id,
            "month": key, "amount": float(value), "created_at": now,
            "source": "manual",
            "supersedes": existing.get("id") if existing else None,
        }
        records.append(item)
        changed.append(item)

    if changed:
        _write(database_path(hass), data)
    return changed


def migrate_legacy_zero_feed_in_advances(
    hass: HomeAssistant, *, meter_id: str, contract_id: str, default_gross_amount: float,
) -> dict:
    """Repair R128/R129 feed-in editor zero overrides exactly once per meter/contract.

    Earlier releases could save the empty/default feed-in editor values as manual
    zero overrides even though the contract had a positive payout advance. The user
    confirmed those historical zeros were not intentional. This one-time migration
    replaces only the latest active zero value for each affected month with the
    contract's gross payout amount, retaining every old row in the audit history.

    A persistent migration marker prevents later intentional zero overrides from
    being rewritten on subsequent editor openings.
    """
    from decimal import Decimal, ROUND_HALF_UP
    from datetime import datetime, timezone

    default = Decimal(str(default_gross_amount or 0))
    if not default.is_finite() or default <= 0:
        return {"migrated": 0, "already_migrated": False, "skipped": "no_positive_contract_default"}
    default = default.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    data = _read(database_path(hass))
    migration = data.setdefault("migration", {})
    completed = migration.setdefault("r131_feed_in_zero_advance_repairs", [])
    marker = f"{meter_id}:{contract_id}"
    if marker in completed:
        return {"migrated": 0, "already_migrated": True}

    records = data.setdefault("monthly_advances", [])
    active_by_month: dict[str, list[dict]] = {}
    for record in records:
        if (record.get("meter_id") == meter_id
                and record.get("contract_id") == contract_id
                and record.get("direction") == "feed_in"
                and not record.get("superseded")):
            active_by_month.setdefault(str(record.get("month", ""))[:7], []).append(record)

    now = datetime.now(timezone.utc).isoformat()
    migrated = 0
    for month, active in active_by_month.items():
        if not month or not active:
            continue
        latest = active[-1]
        try:
            latest_amount = Decimal(str(latest.get("amount", 0) or 0))
        except Exception:  # malformed legacy data must not be silently rewritten
            continue
        if latest_amount != 0:
            continue
        # Preserve the complete history, including duplicate active legacy rows.
        for record in active:
            record["superseded"] = True
            record["superseded_at"] = now
        replacement = {
            "id": str(uuid.uuid4()),
            "meter_id": meter_id,
            "direction": "feed_in",
            "contract_id": contract_id,
            "month": month,
            "amount": float(default),
            "created_at": now,
            "source": "migration_r131_contract_default",
            "migration_reason": "legacy_feed_in_editor_saved_contract_default_as_zero",
            "supersedes": latest.get("id"),
        }
        records.append(replacement)
        migrated += 1

    completed.append(marker)
    migration["r131_feed_in_zero_advance_repairs"] = completed
    _write(database_path(hass), data)
    return {"migrated": migrated, "already_migrated": False}


def record_monthly_advance(hass: HomeAssistant, *, meter_id: str, direction: str, contract_id: str, month: str, amount: float) -> dict | None:
    """Save one month using the same atomic validation and audit semantics."""
    changed = record_monthly_advances(
        hass, meter_id=meter_id, direction=direction, contract_id=contract_id,
        amounts={month: amount},
    )
    if changed:
        return changed[0]
    return get_monthly_advance_record(
        load_data(hass), meter_id=meter_id, direction=direction, month=month,
    )


def get_monthly_advance_record(data: dict, *, meter_id: str, direction: str, month: str) -> dict | None:
    """Return the active audit record for one meter, direction and month."""
    key = str(month)[:7]
    return next((x for x in reversed(data.get("monthly_advances", []))
                 if x.get("meter_id") == meter_id and x.get("direction") == direction
                 and x.get("month") == key and not x.get("superseded")), None)

