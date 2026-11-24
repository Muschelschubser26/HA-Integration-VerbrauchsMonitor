import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
INTEGRATION = ROOT / "custom_components/verbrauchsmonitor"

def test_direction_is_selected_before_direction_specific_price_fields():
    source = (INTEGRATION / "config_flow.py").read_text()
    assert "def _contract_direction_schema" not in source
    assert 'vol.Required("primary_billing_type"' in source
    assert 'vol.Required("feed_in_price_input"' in source
    assert 'if has_feed_in:' in source
    assert 'if has_consumption:' in source
    assert 'vol.Required("purchase_price_input"' in source

def test_feed_in_primary_tariff_is_saved_to_feed_in_net():
    source = (INTEGRATION / "config_flow.py").read_text()
    assert 'net_feed_in = raw / factor if includes else raw' in source
    assert 'merged["feed_in_price_net"] = str(net_feed_in.quantize' in source
    assert 'merged["feed_in_monthly_advance"] = str(net_advance.quantize' in source
    assert 'merged.pop("monthly_advance", None)' in source
    assert 'merged["base_price_net"] = 0.0' in source

def test_feed_in_balance_does_not_include_consumption_base_price():
    source = (INTEGRATION / "sensor.py").read_text()
    assert 'if self._direction == "consumption"' in source
    assert 'else Decimal("0")' in source

def test_feed_in_wizard_labels_are_translated_in_both_languages():
    for language, expected in (("de", "Einspeisevergütung (ct/kWh)"), ("en", "Feed-in tariff (ct/kWh)")):
        data = json.loads((INTEGRATION / f"translations/{language}.json").read_text())
        fields = data["options"]["step"]["contract_wizard_prices"]["data"]
        assert fields["feed_in_price_input"] == expected
        assert fields["feed_in_price_includes_vat"]

def test_edit_default_converts_stored_net_feed_in_price_back_to_gross_input():
    source = (INTEGRATION / "config_flow.py").read_text()
    assert 'input_value("feed_in_price_input", "feed_in_price_net", "feed_in_price_includes_vat", True)' in source
