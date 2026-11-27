from datetime import datetime, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

PATH = Path(__file__).parents[1] / "custom_components" / "verbrauchsmonitor" / "forecast.py"
spec = spec_from_file_location("vm_r086_revised", PATH)
forecast = module_from_spec(spec)
sys.modules[spec.name] = forecast
spec.loader.exec_module(forecast)


def test_initial_state_contains_no_fabricated_score():
    state = forecast.initial_reliability_state(now=datetime(2026, 11, 25, tzinfo=timezone.utc))
    assert state["score"] is None


def test_update_recomputes_from_evidence_instead_of_smoothing_legacy_score():
    now = datetime(2026, 11, 25, tzinfo=timezone.utc)
    history = {"usable": True, "history_months": 24, "sample_count": 200,
               "coverage_percent": 100, "gap_days_max": 1, "quality": 100}
    state = forecast.update_reliability_state(
        {"score": 41.7, "last_evaluated": now.isoformat()},
        history=history, method="seasonal_24m", now=now,
    )
    assert state["score"] == forecast.reliability_score(history=history, method="seasonal_24m")["forecast_reliability_percent"]
