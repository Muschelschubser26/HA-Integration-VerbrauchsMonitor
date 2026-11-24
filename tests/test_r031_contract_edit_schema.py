from pathlib import Path

ROOT = Path(__file__).parents[1]
SOURCE = ROOT / "custom_components/verbrauchsmonitor/config_flow.py"

def test_contract_identity_date_fields_are_declared_only_once_with_existing_defaults():
    source = SOURCE.read_text()
    block = source.split("def _contract_identity_schema", 1)[1].split("async def async_step_contract_wizard_prices", 1)[0]
    assert "_date_default(stored)" in block and "selector.DateSelector(selector.DateSelectorConfig())" in block
    assert 'vol.Optional("contract_start"): selector.DateSelector' not in block
    assert 'vol.Optional("contract_change_date"): selector.DateSelector' not in block

def test_billing_period_and_contract_end_are_in_step_one():
    source = SOURCE.read_text()
    block = source.split("def _contract_identity_schema", 1)[1].split("async def async_step_contract_wizard_prices", 1)[0]
    for key in ("contract_end", "billing_period_start", "billing_period_months"):
        assert key in block
    assert "_date_default(stored)" in block


def test_contract_edit_keeps_billing_period_start_and_duration_fields():
    source = SOURCE.read_text()
    assert '"billing_period_start"' in source
    assert '"billing_period_months"' in source
