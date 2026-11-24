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
