"""R131 migration for feed-in monthly advances incorrectly stored as zero."""
import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).parents[1]
INTEGRATION = ROOT / "custom_components" / "verbrauchsmonitor"


def _database_module():
    homeassistant = types.ModuleType("homeassistant")
    core = types.ModuleType("homeassistant.core")
    core.HomeAssistant = object
    homeassistant.core = core
    sys.modules.setdefault("homeassistant", homeassistant)
    sys.modules.setdefault("homeassistant.core", core)
    path = INTEGRATION / "database.py"
    spec = importlib.util.spec_from_file_location("vm_r131_feed_in_db", path)
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


def test_legacy_zero_feed_in_months_are_repaired_to_contract_gross_and_audited(tmp_path):
    db = _database_module()
    hass = _Hass(tmp_path)
    old_jan = db.record_monthly_advance(
        hass, meter_id="meter-1", direction="feed_in", contract_id="contract-1",
        month="2026-01", amount="0.00",
    )
    old_feb = db.record_monthly_advance(
        hass, meter_id="meter-1", direction="feed_in", contract_id="contract-1",
        month="2026-02", amount="0.00",
    )

    result = db.migrate_legacy_zero_feed_in_advances(
        hass, meter_id="meter-1", contract_id="contract-1", default_gross_amount="136.00",
    )

    assert result == {"migrated": 2, "already_migrated": False}
    data = db.load_data(hass)
    assert db.get_monthly_advance(data, meter_id="meter-1", direction="feed_in", month="2026-01", default=136) == 136.0
    assert db.get_monthly_advance(data, meter_id="meter-1", direction="feed_in", month="2026-02", default=136) == 136.0
    records = data["monthly_advances"]
    assert next(x for x in records if x["id"] == old_jan["id"])["superseded"] is True
    assert next(x for x in records if x["id"] == old_feb["id"])["superseded"] is True
    replacements = [x for x in records if x.get("source") == "migration_r131_contract_default"]
    assert len(replacements) == 2
    assert all(x["amount"] == 136.0 for x in replacements)
    assert all(x["migration_reason"] == "legacy_feed_in_editor_saved_contract_default_as_zero" for x in replacements)


def test_migration_is_idempotent_and_does_not_overwrite_a_future_intentional_zero(tmp_path):
    db = _database_module()
    hass = _Hass(tmp_path)
    db.record_monthly_advance(
        hass, meter_id="meter-1", direction="feed_in", contract_id="contract-1",
        month="2026-01", amount="0.00",
    )
    first = db.migrate_legacy_zero_feed_in_advances(
        hass, meter_id="meter-1", contract_id="contract-1", default_gross_amount="136.00",
    )
    assert first["migrated"] == 1

    # A zero entered after the one-time migration is a valid explicit override.
    db.record_monthly_advance(
        hass, meter_id="meter-1", direction="feed_in", contract_id="contract-1",
        month="2026-02", amount="0.00",
    )
    second = db.migrate_legacy_zero_feed_in_advances(
        hass, meter_id="meter-1", contract_id="contract-1", default_gross_amount="136.00",
    )
    assert second == {"migrated": 0, "already_migrated": True}
    data = db.load_data(hass)
    assert db.get_monthly_advance(data, meter_id="meter-1", direction="feed_in", month="2026-02", default=136) == 0.0


def test_migration_is_scoped_to_meter_and_contract_and_skips_nonzero_values(tmp_path):
    db = _database_module()
    hass = _Hass(tmp_path)
    db.record_monthly_advance(
        hass, meter_id="meter-1", direction="feed_in", contract_id="contract-1",
        month="2026-01", amount="25.00",
    )
    db.record_monthly_advance(
        hass, meter_id="meter-2", direction="feed_in", contract_id="contract-2",
        month="2026-01", amount="0.00",
    )
    result = db.migrate_legacy_zero_feed_in_advances(
        hass, meter_id="meter-1", contract_id="contract-1", default_gross_amount="136.00",
    )
    assert result["migrated"] == 0
    data = db.load_data(hass)
    assert db.get_monthly_advance(data, meter_id="meter-1", direction="feed_in", month="2026-01", default=136) == 25.0
    assert db.get_monthly_advance(data, meter_id="meter-2", direction="feed_in", month="2026-01", default=136) == 0.0


def test_monthly_editor_runs_one_time_migration_before_building_feed_in_form():
    source = (INTEGRATION / "config_flow.py").read_text(encoding="utf-8")
    start = source.index("    async def async_step_advance_months(")
    end = source.index("    def _advance_month_schema(", start)
    handler = source[start:end]
    assert "migrate_legacy_zero_feed_in_advances" in handler
    assert 'if self._advance_direction == "feed_in":' in handler
    assert '_feed_in_monthly_advance_net(contract)' in handler
    assert "gross_from_net(" in handler
    assert 'ledger = await self.hass.async_add_executor_job(load_data, self.hass)' in handler
