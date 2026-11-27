"""R127 regressions for forecast card order and suppressed recommendation explanations."""
from pathlib import Path

ROOT = Path(__file__).parents[1]
CARD = ROOT / "custom_components/verbrauchsmonitor/frontend/verbrauchsmonitor-card.js"
SENSOR = ROOT / "custom_components/verbrauchsmonitor/sensor.py"
FORECAST = ROOT / "custom_components/verbrauchsmonitor/forecast.py"


def test_forecast_heading_precedes_reliability_and_balance():
    source = CARD.read_text(encoding="utf-8")
    block = source.split('const forecastBox = `', 1)[1].split('</section>`;', 1)[0]
    positions = [block.index(token) for token in (
        'class="forecast-season"',
        'class="forecast-heading"',
        'class="forecast-reliability"',
        'class="forecast-balance"',
    )]
    assert positions == sorted(positions)


def test_unavailable_recommendations_have_reason_specific_german_and_english_explanations():
    source = CARD.read_text(encoding="utf-8")
    assert "final_payment_period" in source
    assert "no_remaining_payment_gap" in source
    assert "insufficient_reliability" in source
    assert "Der finanzielle Ausgleich erfolgt über die Jahresabrechnung." in source
    assert "The financial balance will be settled through the annual bill." in source
    assert "Keine Abschlagsempfehlung" not in source
    assert "Voraussichtlicher monatlicher Abschlag:" in source
    assert '.forecast-unavailable{margin-top:12px;padding-top:12px;border-top:1px solid var(--divider-color)' in source
    assert 'class="forecast-unavailable"' in source


def test_sensor_does_not_gate_advance_recommendation_by_reliability():
    source = SENSOR.read_text(encoding="utf-8")
    assert '"forecast_recommendation_available": bool(\n                        result.get("forecast_recommendation_available")\n                    )' in source
    assert "insufficient_reliability" not in source


def test_final_payment_protection_diagnostic_matches_actual_rule():
    source = FORECAST.read_text(encoding="utf-8")
    assert '"advance_recommendation_final_period_protection": months_remaining < 2' in source
