"""R127 regression tests for billing separators and forecast-card order."""
from pathlib import Path

ROOT = Path(__file__).parents[1]
CARD = ROOT / "custom_components/verbrauchsmonitor/frontend/verbrauchsmonitor-card.js"
CONST = ROOT / "custom_components/verbrauchsmonitor/const.py"
README = ROOT / "README.md"


def test_period_metadata_has_one_divider_before_tariff():
    source = CARD.read_text(encoding="utf-8")
    assert '.period-meta-row{display:flex;align-items:center;justify-content:space-between;gap:8px;min-height:12px;padding:0 0 5px;border-bottom:1px solid var(--divider-color)}' in source
    assert source.index('class="period-meta-row"') < source.index('"tariff-row"')
    # The tariff row itself stays borderless because the thicker finance divider follows.
    assert '.tariff-row{border-bottom:0;padding-bottom:2px}' in source


def test_current_power_is_slightly_larger_and_keeps_value_right_aligned():
    source = CARD.read_text(encoding="utf-8")
    assert '.current-power{display:inline-flex;justify-content:flex-end;align-items:baseline;gap:8px;font-size:10px;line-height:12px;white-space:nowrap}' in source
    assert '.current-power span,.current-power strong{font-size:10px;line-height:12px;color:var(--secondary-text-color);font-weight:400;white-space:nowrap}' in source


def test_forecast_reliability_is_directly_below_forecast_heading():
    source = CARD.read_text(encoding="utf-8")
    block = source.split('const forecastBox = `', 1)[1].split('</section>`;', 1)[0]
    positions = [block.index(token) for token in (
        'class="forecast-season"',
        'class="forecast-heading"',
        'class="forecast-reliability"',
        'class="forecast-balance"',
        'class="forecast-advance', 
    )]
    assert positions == sorted(positions)


def test_release_metadata_and_documentation_are_r127():
    const = CONST.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")
    card = CARD.read_text(encoding="utf-8")
    assert 'RELEASE_REVISION: Final = "R0171"' in const
    assert 'INTEGRATION_VERSION: Final = "0.0.1"' in const
    assert 'v0.0.1 Prod R0171' in card
    assert 'Beta R161' in readme
