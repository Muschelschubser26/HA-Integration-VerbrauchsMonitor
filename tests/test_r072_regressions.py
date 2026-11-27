from pathlib import Path
import json

ROOT = Path(__file__).parents[1]
INTEGRATION = ROOT / "custom_components" / "verbrauchsmonitor"

def test_contract_wizard_uses_text_fields_for_six_decimal_money_inputs():
    source = (INTEGRATION / "config_flow.py").read_text()
    assert 'vol.Required("base_price_input", default=format_tariff_de' in source
    assert 'vol.Required("monthly_advance_input", default=format_tariff_de' in source
    assert '): _num(step=0.000001)' not in source
    assert 'def _parse_tariff_input' in source and 'max(0, -parsed.as_tuple().exponent) > 6' in source

def test_baseline_metadata_is_inline_and_compact_without_extra_row():
    source = (INTEGRATION / "frontend" / "verbrauchsmonitor-card.js").read_text()
    assert 'class="row baseline-row"' in source
    assert 'class="baseline-meta-inline"' in source
    assert 'font-size:9px' in source
    assert source.count('class="row baseline-row"') == 1
    assert '${field(t("Zählerstand Abrechnungsbeginn"' not in source

def test_due_advance_label_only_drops_word_faellige():
    source = (INTEGRATION / "frontend" / "verbrauchsmonitor-card.js").read_text()
    assert 'monthlyAdvanceGroups.map(group =>' in source
    assert 'Fällige Abschläge' not in source
    assert 'money(finance.advancePaid+finance.additionalPayments+finance.corrections)' in source

def test_reset_labels_changed_only_for_meter_and_billing_in_both_languages():
    for lang, expected in (("de", ("Zähler zurücksetzen", "Abrechnungen zurücksetzen")), ("en", ("Reset meters", "Reset billing"))):
        data = json.loads((INTEGRATION / "translations" / f"{lang}.json").read_text())["options"]["step"]["reset_data"]["data"]
        assert data["meters"] == expected[0] and data["billing"] == expected[1]
        assert data["contracts"] == ("Vertrag zurücksetzen" if lang == "de" else "Reset contracts")
        assert "database" not in data

def test_database_time_is_localized_and_description_uses_real_newlines():
    flow = (INTEGRATION / "config_flow.py").read_text()
    de = json.loads((INTEGRATION / "translations" / "de.json").read_text())
    assert 'dt_util.as_local(parsed_modified)' in flow
    assert '%d.%m.%Y, %H:%M:%S Uhr' in flow
    description = de["options"]["step"]["database"]["description"]
    assert "\n\n" in description
    assert "\\n" not in description

def test_balance_sensor_name_does_not_duplicate_meter_name():
    source = (INTEGRATION / "sensor.py").read_text()
    assert 'self._attr_name = f"Kontostand {suffix}"' in source
    assert 'self._attr_name = f"Kontostand-{name}-{suffix}"' not in source
