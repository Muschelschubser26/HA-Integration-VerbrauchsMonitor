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
from decimal import Decimal
from datetime import datetime, timezone
from pathlib import Path
from homeassistant.core import HomeAssistant

SCHEMA_VERSION = 3
SQLITE_SCHEMA_VERSION = 1
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
    if current_version < SQLITE_SCHEMA_VERSION:
        # Version 0 is the initial SQLite layout; CREATE TABLE above is its
        # complete migration. Future schema changes must add explicit steps.
        connection.execute(f"PRAGMA user_version = {SQLITE_SCHEMA_VERSION}")
    return connection


def _read(path: Path) -> dict:
    """Read the current snapshot, or return an empty validated structure."""
    if not path.exists():
        return copy.deepcopy(_EMPTY)
    with closing(_connect(path)) as connection:
        with connection:
            row = connection.execute("SELECT payload FROM vm_state WHERE id = 1").fetchone()
    if row is None:
        return copy.deepcopy(_EMPTY)
    try:
        data = json.loads(row[0])
    except (TypeError, json.JSONDecodeError) as err:
        raise ValueError("SQLite-Datenbank enthält einen ungültigen Datenbestand") from err
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

def status(hass: HomeAssistant) -> dict:
    """Return database metadata and integrity information for diagnostics."""
    p=database_path(hass)
    try:
        data=load_data(hass)
        with closing(_connect(p)) as connection:
            integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise sqlite3.DatabaseError(f"SQLite-Integritätsprüfung fehlgeschlagen: {integrity}")
        return {"status":"ok", "integrity_check":integrity, "exists":p.exists(), "size_bytes":p.stat().st_size if p.exists() else 0,
          "schema_version":SCHEMA_VERSION, "contracts":len(data['contracts']), "meters":len(data['meters']),
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
    records = [x for x in data.get("monthly_advances", []) if x.get("meter_id") == meter_id and x.get("direction") == direction and x.get("month") == key]
    if records:
        return float(records[-1].get("amount", 0))
    rates = [x for x in data.get("advance_rates", []) if x.get("meter_id") == meter_id and x.get("direction") == direction and x.get("effective_from", "") <= key]
    return float(sorted(rates, key=lambda x: x.get("effective_from", ""))[-1]["amount"]) if rates else float(default or 0)

def record_monthly_advance(hass: HomeAssistant, *, meter_id: str, direction: str, contract_id: str, month: str, amount: float) -> dict:
    """Save one month only and retain prior values in an audit trail."""
    from decimal import Decimal, ROUND_HALF_UP
    from datetime import datetime, timezone
    if direction not in ("consumption", "feed_in"):
        raise ValueError("Ungültiger Abrechnungsbereich")
    key = str(month)[:7]
    if len(key) != 7 or key[4] != "-":
        raise ValueError("Monat muss YYYY-MM sein")
    value = Decimal(str(amount))
    if not value.is_finite() or value < 0:
        raise ValueError("Abschlag darf nicht negativ sein")
    value = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    data = _read(database_path(hass))
    records = data.setdefault("monthly_advances", [])
    existing = next((x for x in reversed(records) if x.get("meter_id") == meter_id and x.get("direction") == direction and x.get("month") == key and not x.get("superseded")), None)
    if existing and Decimal(str(existing.get("amount", 0))) == value:
        return existing
    if existing:
        existing["superseded"] = True
        existing["superseded_at"] = datetime.now(timezone.utc).isoformat()
    item = {"id": str(uuid.uuid4()), "meter_id": meter_id, "direction": direction, "contract_id": contract_id, "month": key, "amount": float(value), "created_at": datetime.now(timezone.utc).isoformat(), "supersedes": existing.get("id") if existing else None}
    records.append(item)
    _write(database_path(hass), data)
    return item
