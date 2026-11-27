"""Regression tests for the dedicated monthly-advance change workflow."""
import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
FLOW = (ROOT / "custom_components/verbrauchsmonitor/config_flow.py").read_text()


def test_billing_menu_order_is_bookings_change_then_monthly_editor():
    assert 'menu_options=["advance_change", "advance_meter", "billing_bookings"]' in FLOW
    for language, expected in (("de", "Monatsabschlag ändern"), ("en", "Change monthly advance")):
        data = json.loads((ROOT / f"custom_components/verbrauchsmonitor/translations/{language}.json").read_text())
        menu = data["options"]["step"]["billing"]["menu_options"]
        assert menu["advance_change"] == expected


def test_change_flow_supports_meter_and_billing_area_selection():
    assert "async_step_advance_change" in FLOW
    assert "async_step_advance_change_direction" in FLOW
    assert 'if len(directions) == 1:' in FLOW
    assert 'self._change_advance_direction = directions[0]["value"]' in FLOW


def test_change_flow_offers_seven_future_months_across_billing_period_boundaries():
    assert "next_index = today.year * 12 + today.month" in FLOW
    assert "while len(choices) < 7:" in FLOW
    assert "selected_index = selected.year * 12 + selected.month - 1" in FLOW
    assert "period_end_index = start_index + (period_number + 1) * duration - 1" in FLOW
    assert 'vol.Required("effective_month"' in FLOW


def test_change_flow_applies_new_rate_from_selected_month_to_period_end():
    assert 'values[cursor.strftime("%Y-%m")] = amount' in FLOW
    assert "record_monthly_advances" in FLOW
    assert 'source": "manual"' in (ROOT / "custom_components/verbrauchsmonitor/database.py").read_text()


def test_change_flow_validates_non_negative_amount_and_reloads_dashboard():
    assert 'if amount < 0:' in FLOW
    assert 'async_reload(self.config_entry.entry_id)' in FLOW
    assert 'errors={"base": "invalid_advance_amount"}' in FLOW


def test_change_flow_shows_current_amount_and_effective_date_when_changed():
    assert "Aktueller Abschlag:" in FLOW
    assert "Aktueller Abschlag (seit {effective}):" in FLOW
    assert "Bereits vorgemerkter Abschlag: Ab" in FLOW
    assert "save_notice" in FLOW
    assert "month_name_de" in FLOW and "month_name_en" in FLOW
    assert '"current_advance": current_label' in FLOW


def test_change_flow_translations_are_synchronized():
    de = json.loads((ROOT / "custom_components/verbrauchsmonitor/translations/de.json").read_text())
    en = json.loads((ROOT / "custom_components/verbrauchsmonitor/translations/en.json").read_text())
    de_steps = de["options"]["step"]
    en_steps = en["options"]["step"]
    for key in ("advance_change", "advance_change_direction", "advance_change_value"):
        assert key in de_steps and key in en_steps
        assert set(de_steps[key].get("data", {})) == set(en_steps[key].get("data", {}))
