from pathlib import Path

ROOT = Path(__file__).parents[1]
SENSOR = ROOT / "custom_components/verbrauchsmonitor/sensor.py"


def test_recorder_history_and_statistics_use_recorder_executor():
    source = SENSOR.read_text(encoding="utf-8")
    # Each blocking Recorder API must run on Recorder's dedicated executor.
    assert source.count("recorder.async_add_executor_job(") >= 3
    assert "statistics.statistics_during_period" in source
    assert "history.get_significant_states" in source
    assert "self.hass.async_add_executor_job(\n                statistics.statistics_during_period" not in source
    assert "self.hass.async_add_executor_job(\n                    statistics.statistics_during_period" not in source
    assert "self.hass.async_add_executor_job(\n                    history.get_significant_states" not in source


def test_all_recorder_executor_calls_obtain_recorder_instance():
    source = SENSOR.read_text(encoding="utf-8")
    assert source.count("from homeassistant.components.recorder import get_instance") >= 3
    assert source.count("recorder = get_instance(self.hass)") >= 3


def test_temporary_unavailable_source_states_are_ignored_before_validation():
    source = SENSOR.read_text(encoding="utf-8")
    assert "def _is_transient_unavailable_state(state) -> bool:" in source
    assert 'in ("unknown", "unavailable")' in source
    # Both meter-source listeners must short-circuit before strict validation.
    assert source.count("if _is_transient_unavailable_state(state):") == 2
    assert source.count("value, status = validate_reading(state.state, self._current)") == 2


def test_invalid_numeric_measurements_remain_logged_and_rejected():
    source = SENSOR.read_text(encoding="utf-8")
    assert "ungültiger Messwert ignoriert" in source
    assert "rückläufiger Messwert ignoriert" in source


def test_database_information_shows_dynamic_path_and_visual_spacing():
    """Database dialog exposes the actual DB path and separates information groups."""
    from pathlib import Path

    source = Path(
        "custom_components/verbrauchsmonitor/config_flow.py"
    ).read_text(encoding="utf-8")
    start = source.index("    async def async_step_database(")
    end = source.index("    async def async_step_database_optimize(", start)
    method = source[start:end]

    assert "from .database import database_path, status" in method
    assert 'db_path = str(database_path(self.hass))' in method
    assert 'f"Datenbank: {db_path}\\n\\n"' in method
    assert 'f"Buchungen: {details.get(\'bookings\', 0)}\\n\\n"' in method
