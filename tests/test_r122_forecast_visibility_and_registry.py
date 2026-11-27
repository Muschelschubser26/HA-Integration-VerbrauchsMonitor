"""Regression coverage for R122 forecast visibility and stable entity IDs."""
from pathlib import Path

DOMAIN = "verbrauchsmonitor"

ROOT = Path(__file__).parents[1]
SENSOR = ROOT / "custom_components/verbrauchsmonitor/sensor.py"
CARD = ROOT / "custom_components/verbrauchsmonitor/frontend/verbrauchsmonitor-card.js"


def test_no_synthetic_initial_reliability_is_persisted():
    source = SENSOR.read_text(encoding="utf-8")
    assert "calculate_initial_reliability(self._history)" not in source
    assert "initial_score_created_at" not in source
    assert "No synthetic starting score is stored" in source
    assert "resolve_forecast_reliability(" in source



def test_monthly_forecast_sensor_reloads_shared_hourly_learning_results():
    source = SENSOR.read_text(encoding="utf-8")
    assert 'self._periodic_learning_state_refresh, timedelta(hours=1)' in source
    assert 'async def _async_refresh_learning_state(self):' in source
    assert '_normalize_learning_state(await self._learning_store.async_load())' in source
    assert 'f"{DOMAIN}_{self._entry_id}_{self._direction}_hourly_learning"' in source
    assert 'await self._learning_store.async_save(self._learning_state)' in source


def test_initial_reliability_and_provisional_recommendation_are_rendered():
    source = CARD.read_text(encoding="utf-8")
    assert 'const hasForecastReliability = Number.isFinite(forecastReliability) &&' in source
    assert 'forecastReliability >= 37.6' not in source
    assert 'reliability-spinner' in source
    assert 'forecast_recommendation_available !== false' in source
    assert 'Vorläufige Berechnung auf Basis des Startmodells.' in source


def test_money_sensors_suggest_exactly_two_display_decimals():
    source = SENSOR.read_text(encoding="utf-8")
    assert source.count('_attr_suggested_display_precision = 2') >= 2


def test_entity_registry_migration_preserves_unique_id_and_rejects_conflicts():
    source = SENSOR.read_text(encoding="utf-8")
    assert 'async def _async_migrate_entity_id(entity, hass=None)' in source
    assert 'registry.async_update_entity(suggested, new_entity_id=target)' in source
    assert 'target_entry.unique_id != current_entry.unique_id' in source
    assert 'await _async_migrate_entity_id(self)' in source
