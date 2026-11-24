from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARD = ROOT / "custom_components/verbrauchsmonitor/frontend/verbrauchsmonitor-card.js"


def test_monthly_average_uses_billing_period_start_not_baseline_entry_date():
    source = CARD.read_text()
    assert 'a.billing_period_start || a.billing_start || a.contract_start' in source
    assert 'consumption_baseline_updated_at' not in source
    assert 'const today = new Date();' in source
    assert 'const billingStartTimestamp = periodStart;' in source
    assert 'consumption_baseline_updated_at' not in source


def test_monthly_average_has_its_own_visual_separator():
    source = CARD.read_text()
    assert '.cost-average{margin-top:4px;padding-top:10px;border-top:1px solid var(--divider-color)}' in source
    assert 'class="row cost-average"' in source


def test_monthly_average_has_no_unrequested_icon():
    source = CARD.read_text()
    assert '<ha-icon icon="mdi:chart-box-outline"></ha-icon>' not in source


def test_monthly_average_uses_total_accrued_period_costs():
    source = CARD.read_text()
    assert 'totalCosts / elapsedDays * 30.436875' in source
    assert 'base / 12 * 30.436875' not in source
