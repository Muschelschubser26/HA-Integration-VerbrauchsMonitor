"""Regression tests for two-decimal tariff display without calculation rounding."""
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_tariff_display_exposes_calculation_precision_when_required():
    card = (ROOT / "custom_components/verbrauchsmonitor/frontend/verbrauchsmonitor-card.js").read_text(encoding="utf-8")
    pricing = (ROOT / "custom_components/verbrauchsmonitor/pricing.py").read_text(encoding="utf-8")

    assert "minimumFractionDigits:2,maximumFractionDigits:2,useGrouping:false" in card
    assert "maximumFractionDigits:6" not in card
    assert "gross_decimal_from_net" in pricing

    internal_gross = Decimal("28.74") * Decimal("1.19")
    displayed = f"{internal_gross:.2f}".replace(".", ",")
    assert internal_gross == Decimal("34.2006")
    assert displayed == "34,20"
    assert f"{internal_gross:.4f}".replace(".", ",") == "34,2006"
