import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
INTEGRATION = ROOT / "custom_components/verbrauchsmonitor"

def test_contract_flow_uses_two_step_wizard_and_native_date_selectors():
    source = (INTEGRATION / "config_flow.py").read_text()
    assert "async_step_contract_wizard_identity" in source
    assert "async_step_contract_wizard_prices" in source
    assert "async_step_contract_edit" not in source
    assert "billing_period_months" in source
    assert "billing_period_end" in source
    assert "selector.DateSelector(selector.DateSelectorConfig())" in source
    assert 'errors={"base": "required_identity"}' in source

def test_price_wizard_defaults_and_vat_flags():
    source = (INTEGRATION / "config_flow.py").read_text()
    assert 'data.get("vat_rate", 19)' in source
    assert 'billing_period_months' in source
    assert 'billing_period_start' in source
    assert 'base_price_period' not in source
    assert 'data.get("monthly_advance_includes_vat", True)' in source
    assert '"base_price_includes_vat"' in source
    assert '"purchase_price_includes_vat"' in source
    assert '"monthly_advance_includes_vat"' in source
    assert 'net_value = raw / factor if merged.get(includes) else raw' in source
    assert 'quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)' in source
    assert '_parse_tariff_input(merged.get(source, 0))' in source

def test_wizard_fields_have_german_and_english_translations():
    expected = {"contract_wizard_identity", "contract_wizard_prices"}
    for language in ("de", "en"):
        data = json.loads((INTEGRATION / f"translations/{language}.json").read_text())
        steps = data["options"]["step"]
        assert expected <= set(steps)
        assert steps["contract_wizard_identity"]["data"]["name"]
        assert steps["contract_wizard_prices"]["data"]["monthly_advance_includes_vat"]
        assert "contract_edit" not in steps
        assert "billing_period_months" in steps["contract_wizard_identity"]["data"]
        assert steps["contract_wizard_prices"]["submit"] in ("Fertigstellen", "Finish")

def test_first_contract_starts_wizard_without_action_screen():
    source = (INTEGRATION / "config_flow.py").read_text()
    assert 'if not contracts and user_input is None:' in source
    assert 'return await self.async_step_contract_wizard_identity()' in source


def test_contract_and_meter_selection_are_real_dropdowns_without_custom_values():
    source = (INTEGRATION / "config_flow.py").read_text()
    assert 'custom_value=False' in source
    assert 'selector.SelectSelector(selector.SelectSelectorConfig(options=actions' in source
    assert '"value": "delete"' in source
    assert '"value": "edit"' in source


def test_contract_save_persists_to_config_entry_options():
    source = (INTEGRATION / "config_flow.py").read_text()
    assert 'options = {**dict(self.config_entry.options), **changes}' in source
    assert 'return self.async_create_entry(title="", data=options)' in source
    assert 'contracts=contracts' in source


def test_provider_is_required_and_persisted_in_contract_identity():
    source = (INTEGRATION / "config_flow.py").read_text()
    assert 'vol.Required("provider", default=str(data.get("provider", ""))): str' in source
    assert 'user_input.get("provider", "")' in source
    for language, expected in (("de", "Anbieter"), ("en", "Provider")):
        data = json.loads((INTEGRATION / f"translations/{language}.json").read_text())
        step = data["options"]["step"]["contract_wizard_identity"]
        assert step["data"]["provider"] == expected
        assert expected.lower() in step["description"].lower() or "contract" in step["description"].lower()
