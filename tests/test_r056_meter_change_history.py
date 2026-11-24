from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
def test_meter_change_history_is_exposed_by_sensor_attributes():
    source = (ROOT / "custom_components/verbrauchsmonitor/sensor.py").read_text(encoding="utf-8")
    assert '"meter_changes": entry.data.get("meter_changes", [])' in source
def test_update_service_validates_and_persists_multiple_meter_changes():
    source = (ROOT / "custom_components/verbrauchsmonitor/__init__.py").read_text(encoding="utf-8")
    assert 'if "meter_changes" in call.data:' in source
    assert 'changes.sort(key=lambda item: item["date"])' in source
    assert 'meter["meter_changes"] = changes' in source
def test_card_preserves_meter_changes_outside_current_period():
    source = (ROOT / "custom_components/verbrauchsmonitor/frontend/verbrauchsmonitor-card.js").read_text(encoding="utf-8")
    assert 'const outsidePeriod=allMeterChanges.filter' in source
    assert 'payload.meter_changes=[...outsidePeriod,...meterChanges]' in source
