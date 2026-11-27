from pathlib import Path

ROOT = Path(__file__).parents[1]
CARD = ROOT / "custom_components" / "verbrauchsmonitor" / "frontend" / "verbrauchsmonitor-card.js"

def test_forecast_box_is_rendered_under_each_direction_balance():
    source = CARD.read_text()
    assert 'forecastBalance = get(`${isFeed ? "feed_in" : "consumption"}_forecast_annual_balance`)' in source
    assert 'forecastAdvance = get(`${isFeed ? "feed_in" : "consumption"}_forecast_monthly_advance`)' in source
    assert '${forecastEnabled ? forecastBox : ""}' in source
    assert 'Voraussichtlicher monatlicher Abschlag:' in source
    assert 'Erwarteter Abrechnungssaldo' in source

def test_forecast_visual_style_prioritizes_readability_and_monthly_advance():
    source = CARD.read_text()
    assert '.forecast-box{margin-top:10px' in source
    assert '.forecast-advance{margin-top:10px;padding:12px 14px;border-radius:8px;color:#202020;border:1px solid rgba(0,0,0,.08);background:#e5eff8}' in source
    assert 'font-size:1.9rem' in source
    assert 'font-weight:800' in source
    assert 'Abschlag sollte erhöht werden' not in source
    assert 'Abschlag könnte verringert werden' not in source
    assert 'Der Abschlag muss nicht geändert werden' not in source
    assert 'forecast-separator' not in source
    assert 'gap:2px' in source

def test_forecast_remains_visible_with_diagnostic_when_values_are_missing():
    source = CARD.read_text()
    assert 'const forecastAvailable = valid(forecastBalance) || valid(forecastAdvance)' in source
    assert 'const forecastBox = `<section class="forecast-box"' in source
    assert 'forecast sensors are missing or unavailable' not in source.lower()
    assert 'class="forecast-unavailable"' in source[source.index('const forecastBox ='):source.index('const meterChangeRows =')]
