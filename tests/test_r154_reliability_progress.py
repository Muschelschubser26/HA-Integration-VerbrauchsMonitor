from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SENSOR = (ROOT / "custom_components/verbrauchsmonitor/sensor.py").read_text(encoding="utf-8")
CARD = (ROOT / "custom_components/verbrauchsmonitor/frontend/verbrauchsmonitor-card.js").read_text(encoding="utf-8")


def test_progress_is_separate_from_reliability_and_monotonic():
    assert "self._reliability_progress_percent = max(" in SENSOR
    assert '"forecast_reliability_progress_percent"' in SENSOR
    assert '"forecast_reliability_pending": not complete' in SENSOR
    assert "self._set_reliability_progress(20)" in SENSOR
    assert "self._set_reliability_progress(65)" in SENSOR
    assert "self._set_reliability_progress(90)" in SENSOR
    assert "self._set_reliability_progress(100, complete=True)" in SENSOR


def test_card_displays_progress_between_status_and_spinner():
    assert "reliabilityProgress" in CARD
    assert "wird ermittelt" in CARD
    assert "Math.round(reliabilityProgress)" in CARD
    assert "reliability-spinner" in CARD
