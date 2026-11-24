from decimal import Decimal
from pathlib import Path
import importlib.util

ROOT = Path(__file__).parents[1]
INTEGRATION = ROOT / "custom_components/verbrauchsmonitor"


def test_per_kwh_tariff_selectors_allow_six_decimal_places():
    source = (INTEGRATION / "config_flow.py").read_text()
    assert 'input_value("purchase_price_input", "purchase_price_net", "purchase_price_includes_vat", False)' in source
    assert 'input_value("feed_in_price_input", "feed_in_price_net", "feed_in_price_includes_vat", True)' in source
    assert "def _parse_tariff_input(value):" in source
    assert "max(0, -parsed.as_tuple().exponent) > 6" in source


def test_gross_tariff_conversion_does_not_truncate_precision():
    spec = importlib.util.spec_from_file_location("pricing", INTEGRATION / "pricing.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.gross_from_net("12.345678", "0")
    assert Decimal(str(result)) == Decimal("12.345678")


def test_tariff_conversion_preserves_six_places_with_vat():
    spec = importlib.util.spec_from_file_location("pricing", INTEGRATION / "pricing.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.gross_from_net("12.345678", "19")
    assert Decimal(str(result)).quantize(Decimal("0.000001")) == Decimal("14.691357")
