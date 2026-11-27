from pathlib import Path

ROOT = Path(__file__).parents[1]
INTEGRATION = ROOT / "custom_components/verbrauchsmonitor"

def test_billing_form_is_not_rebuilt_during_editing():
    source = (INTEGRATION / "frontend/verbrauchsmonitor-card.js").read_text()
    assert 'if (this._editing && this.querySelector("form.contract-edit")) return;' in source
    assert 'this._editing=false;this.render();' in source

def test_billing_edit_inputs_use_german_decimal_format():
    source = (INTEGRATION / "frontend/verbrauchsmonitor-card.js").read_text()
    assert 'new Intl.NumberFormat("de-DE"' in source
    assert 'inputmode="decimal"' in source
    assert 'type="number" min="0" step="0.000001"' not in source
    assert 'type="number" min="0" step="0.01"' not in source

def test_contract_selector_has_disambiguating_labels_and_default():
    source = (INTEGRATION / "config_flow.py").read_text()
    assert 'c.get("contract_number", "")' in source
    assert 'default=opts[0]["value"]' in source

def test_revision_metadata_is_r036():
    const = (INTEGRATION / "const.py").read_text()
    assert 'INTEGRATION_VERSION: Final = "0.0.1"' in const
    source = (INTEGRATION / "config_flow.py").read_text()
    assert 'description_placeholders={"revision": RELEASE_REVISION, "version": RELEASE_VERSION, "stage": RELEASE_STAGE}' in source
