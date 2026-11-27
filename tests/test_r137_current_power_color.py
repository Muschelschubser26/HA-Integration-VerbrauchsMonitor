"""R139 regression tests for current Watt-value color coding."""
from pathlib import Path

ROOT = Path(__file__).parents[1]
CARD = ROOT / "custom_components/verbrauchsmonitor/frontend/verbrauchsmonitor-card.js"
CONST = ROOT / "custom_components/verbrauchsmonitor/const.py"


def test_current_power_color_compares_feed_in_with_consumption():
    source = CARD.read_text(encoding="utf-8")
    assert 'const feedInValue = valid(feedPower) ? Math.abs(Number(feedPower.state)) : null;' in source
    assert 'const difference = feedInValue - consumptionValue;' in source
    assert 'difference > 0 ? "power-higher" : "power-lower"' in source
    assert 'Math.abs(difference) <= 0.01 ? "power-equal"' in source


def test_no_positive_feed_in_keeps_default_gray_value():
    source = CARD.read_text(encoding="utf-8")
    assert 'if (feedInValue !== null && feedInValue > 0 && consumptionValue !== null)' in source
    assert 'let comparisonClass = "";' in source
    assert '.current-power strong.power-equal{color:var(--secondary-text-color)}' in source


def test_only_watt_text_gets_color_and_no_icon_is_added():
    source = CARD.read_text(encoding="utf-8")
    assert '<strong class="${comparisonClass}">' in source
    assert '.current-power strong.power-higher{color:var(--success-color,#2e7d32)}' in source
    assert '.current-power strong.power-lower{color:var(--error-color,#c62828)}' in source
    assert 'class="${comparisonClass}"' in source
    assert '<ha-icon' not in source[source.index('let comparisonClass'):source.index('class="${comparisonClass}"', source.index('let comparisonClass'))]


def test_release_revision_is_r142():
    source = CONST.read_text(encoding="utf-8")
    assert 'RELEASE_REVISION: Final = "R0171"' in source
    assert 'INTEGRATION_VERSION: Final = "0.0.1"' in source
