"""R134 regression tests: forecast reliability and advance section never disappear."""
from pathlib import Path

ROOT = Path(__file__).parents[1]
CARD = ROOT / "custom_components/verbrauchsmonitor/frontend/verbrauchsmonitor-card.js"


def test_reliability_row_is_rendered_whenever_forecast_is_enabled():
    source = CARD.read_text(encoding="utf-8")
    assert 'const showForecastReliability = forecastEnabled || hasForecastReliability || reliabilityPending;' in source
    assert 'class="forecast-reliability"' in source
    assert 'class="reliability-spinner"' in source


def test_advance_section_has_explanation_even_without_available_sensor_value():
    source = CARD.read_text(encoding="utf-8")
    assert 'if (forecastEnabled && !recommendationAvailable)' in source
    assert 'Ein voraussichtlicher monatlicher Abschlag wird gerade berechnet.' in source
    assert 'class="forecast-unavailable"' in source


def test_both_sections_remain_inside_the_forecast_box():
    source = CARD.read_text(encoding="utf-8")
    block = source.split('const forecastBox = `', 1)[1].split('</section>`;', 1)[0]
    assert 'class="forecast-reliability"' in block
    assert 'class="forecast-advance"' in block
    assert 'class="forecast-unavailable"' in block
