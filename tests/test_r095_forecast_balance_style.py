"""Regression checks for expected billing balance styling."""
from pathlib import Path

ROOT = Path(__file__).parents[1]
CARD = ROOT / "custom_components/verbrauchsmonitor/frontend/verbrauchsmonitor-card.js"

def test_expected_balance_uses_red_only_for_negative_and_black_double_underline():
    source = CARD.read_text()
    assert 'Number(forecastBalance.state) < 0 ? "negative" : "positive"' in source
    assert 'text-decoration-style:double' in source
    assert 'text-decoration-color:#000' in source
    assert '.forecast-balance strong.positive{color:#000}' in source
    assert '.forecast-balance strong.negative{color:#d32f2f}' in source
