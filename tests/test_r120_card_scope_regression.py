from pathlib import Path

ROOT = Path(__file__).parents[1]
CARD = ROOT / "custom_components/verbrauchsmonitor/frontend/verbrauchsmonitor-card.js"


def test_billing_card_uses_its_own_validity_helper_for_power_rows():
    source = CARD.read_text(encoding="utf-8")
    billing = source.split("class VerbrauchsMonitorBillingCard", 1)[1]
    render = billing.split("render() {", 1)[1]
    assert "const valid = s =>" in render
    assert "if (!valid(power)) return \"\";" in render
    assert "hasValue(power)" not in render


def test_power_row_remains_optional_for_missing_or_unavailable_entities():
    source = CARD.read_text(encoding="utf-8")
    assert "if (!valid(power)) return \"\";" in source
    assert ': ""; })()} ' not in source  # no unconditional placeholder row
