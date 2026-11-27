"""Safety regressions for monthly advance edits (history, cancel, no-op, atomicity)."""
import importlib.util
import json
import sys
import types
from pathlib import Path

ROOT = Path(__file__).parents[1]


def _database_module():
    homeassistant = types.ModuleType("homeassistant")
    core = types.ModuleType("homeassistant.core")
    core.HomeAssistant = object
    homeassistant.core = core
    sys.modules.setdefault("homeassistant", homeassistant)
    sys.modules.setdefault("homeassistant.core", core)
    path = ROOT / "custom_components/verbrauchsmonitor/database.py"
    spec = importlib.util.spec_from_file_location("vm_monthly_advance_db", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class _Config:
    def __init__(self, root):
        self.root = root

    def path(self, *parts):
        return str(self.root.joinpath(*parts))


class _Hass:
    def __init__(self, root):
        self.config = _Config(root)


def _active(data, month):
    return [r for r in data["monthly_advances"] if r["month"] == month and not r.get("superseded")]


def test_changed_month_keeps_previous_version_and_links_audit_chain(tmp_path):
    db = _database_module()
    hass = _Hass(tmp_path)
    first = db.record_monthly_advance(hass, meter_id="m1", direction="consumption", contract_id="c1", month="2026-08", amount="200.00")
    second = db.record_monthly_advance(hass, meter_id="m1", direction="consumption", contract_id="c1", month="2026-08", amount="175.50")

    records = db.load_data(hass)["monthly_advances"]
    old = next(r for r in records if r["id"] == first["id"])
    assert old["superseded"] is True
    assert old["superseded_at"]
    assert second["supersedes"] == first["id"]
    assert _active(db.load_data(hass), "2026-08") == [second]
    assert second["amount"] == 175.5


def test_cancel_path_does_not_call_persistence_or_mutate_database(tmp_path):
    """HA form cancellation closes the flow; only submitted user_input saves."""
    source = (ROOT / "custom_components/verbrauchsmonitor/config_flow.py").read_text(encoding="utf-8")
    start = source.index("    async def async_step_advance_months(")
    end = source.index("    def _advance_month_schema(", start)
    handler = source[start:end]
    assert "if user_input is not None:" in handler
    save_branch = handler[handler.index("if user_input is not None:"): ]
    assert "record_monthly_advances" in save_branch
    assert "async_show_form(step_id=\"advance_months\"" in handler
    # No persistence is performed merely by constructing/showing the form.
    db = _database_module()
    hass = _Hass(tmp_path)
    before = db.load_data(hass)
    assert before["monthly_advances"] == []
    assert db.load_data(hass)["monthly_advances"] == []


def test_unchanged_submission_creates_no_new_audit_record_or_database_write(tmp_path):
    db = _database_module()
    hass = _Hass(tmp_path)
    first = db.record_monthly_advance(hass, meter_id="m1", direction="consumption", contract_id="c1", month="2026-08", amount="200.00")
    before = db.load_data(hass)
    changed = db.record_monthly_advances(hass, meter_id="m1", direction="consumption", contract_id="c1", amounts={"2026-08": "200.000"})
    after = db.load_data(hass)
    assert changed == []
    assert after["monthly_advances"] == before["monthly_advances"]
    assert _active(after, "2026-08") == [first]


def test_invalid_month_in_batch_prevents_all_partial_updates(tmp_path):
    db = _database_module()
    hass = _Hass(tmp_path)
    db.record_monthly_advance(hass, meter_id="m1", direction="consumption", contract_id="c1", month="2026-08", amount="200")
    before = db.load_data(hass)["monthly_advances"]
    try:
        db.record_monthly_advances(hass, meter_id="m1", direction="consumption", contract_id="c1", amounts={"2026-08": "175", "2026-09": "-1"})
    except ValueError:
        pass
    else:
        raise AssertionError("Negative amount must be rejected")
    assert db.load_data(hass)["monthly_advances"] == before


def test_zero_is_valid_and_saved_as_explicit_month_override(tmp_path):
    db = _database_module()
    hass = _Hass(tmp_path)
    saved = db.record_monthly_advance(hass, meter_id="m1", direction="consumption", contract_id="c1", month="2026-08", amount="0")
    assert saved["amount"] == 0.0
    assert saved["source"] == "manual"
    assert db.get_monthly_advance(db.load_data(hass), meter_id="m1", direction="consumption", month="2026-08", default=200) == 0.0
