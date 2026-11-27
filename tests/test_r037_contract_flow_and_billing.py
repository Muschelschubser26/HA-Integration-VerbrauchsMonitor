from pathlib import Path
import json

ROOT = Path(__file__).parents[1]
INTEGRATION = ROOT / "custom_components/verbrauchsmonitor"

def test_contract_action_is_persisted_across_selection_step():
    source = (INTEGRATION / "config_flow.py").read_text()
    assert "self._contract_action = action" in source
    assert "async_step_contract_select" in source
    select_step = source.split("async def async_step_contract_select", 1)[1].split("async def async_step_contract_delete_confirm", 1)[0]
    assert "action = getattr(self, \"_contract_action\", None)" in select_step
    assert 'step_id="contract_select"' in select_step
    assert 'step_id="contracts"' not in select_step

def test_contract_new_action_does_not_show_contract_selector():
    source = (INTEGRATION / "config_flow.py").read_text()
    contracts = source.split("async def async_step_contracts", 1)[1].split("def _contract_action_schema", 1)[0]
    assert 'if action == "new":' in contracts
    assert "async_step_contract_wizard_identity" in contracts

def test_purchase_price_defaults_use_german_decimal_comma():
    source = (INTEGRATION / "config_flow.py").read_text()
    assert 'input_value("purchase_price_input", "purchase_price_net", "purchase_price_includes_vat", False)' in source

def test_additional_values_is_not_in_management_menu():
    source = (INTEGRATION / "config_flow.py").read_text()
    assert 'menu_options=["contracts", "meters", "forecast", "settlement", "billing", "data_management", "about"]' in source
    for language in ("de", "en"):
        data = json.loads((INTEGRATION / f"translations/{language}.json").read_text())
        assert "additional_values" not in data["options"]["step"]["init"]["menu_options"]

def test_billing_card_groups_costs_payments_and_total_balance():
    card = (INTEGRATION / "frontend/verbrauchsmonitor-card.js").read_text()
    for label in ("Aktueller Abrechnungszeitraum", "Bereits bezahlt", "Offener Betrag", "Anteiliger Grundpreis"):
        assert label in card


def test_annual_base_price_is_prorated_and_additional_payments_are_counted():
    sensor = (INTEGRATION / "sensor.py").read_text()
    assert "accrued_annual_base_price(base_gross_annual, billing_start_dt, now_local)" in sensor
    ledger = (INTEGRATION / "ledger.py").read_text()
    assert 'elif kind == "payment":' in ledger
    assert "additional_payments += amount" in ledger
