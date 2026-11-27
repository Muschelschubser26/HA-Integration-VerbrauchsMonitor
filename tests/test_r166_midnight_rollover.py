from pathlib import Path

ROOT = Path(__file__).parents[1]
INTEGRATION = ROOT / "custom_components" / "verbrauchsmonitor"

def test_period_sensor_has_week_month_year_and_single_midnight_trigger():
    source = (INTEGRATION / "sensor.py").read_text(encoding="utf-8")
    assert '"consumption", "week"' in source
    assert '"feed_in", "week"' in source
    assert 'hour=0, minute=0, second=5' in source
    assert 'local_now.date().weekday()' in source

def test_missing_midnight_reading_does_not_invalidate_sensor():
    source = (INTEGRATION / "sensor.py").read_text(encoding="utf-8")
    boundary = source.split('def _boundary(self, now):', 1)[1].split('@property', 1)[0]
    assert 'if value is None:' in boundary
    assert 'self._ready = False' not in boundary
    assert 'self._period_key != current_key' in source
    assert 'self._partial = True' in source

def test_week_entity_ids_are_german():
    naming = (INTEGRATION / "naming.py").read_text(encoding="utf-8")
    assert '"consumption_week": f"{prefix}_wochenverbrauch"' in naming
    assert '"feed_in_week": f"{prefix}_wocheneinspeisung"' in naming
