"""Regression tests for the R144 monthly-advance dialog behavior."""
import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
FLOW = (ROOT / "custom_components/verbrauchsmonitor/config_flow.py").read_text()
CARD = (ROOT / "custom_components/verbrauchsmonitor/frontend/verbrauchsmonitor-card.js").read_text()


def test_advance_editor_offers_at_most_seven_future_months():
    assert "while len(choices) < 7:" in FLOW
    assert "configured billing-period end" not in FLOW
    assert "next_index = today.year * 12 + today.month" in FLOW


def test_advance_editor_revalidates_selected_month_server_side():
    assert 'allowed_months = {choice["value"] for choice in choices}' in FLOW
    assert 'selected.strftime("%Y-%m") not in allowed_months' in FLOW
    assert 'selected <= date(today.year, today.month, 1)' in FLOW


def test_dialog_descriptions_use_real_line_breaks_and_explain_future_only():
    for lang in ("de", "en"):
        data = json.loads((ROOT / f"custom_components/verbrauchsmonitor/translations/{lang}.json").read_text())
        description = data["options"]["step"]["advance_change_value"]["description"]
        assert "\\n" not in description
        assert "{current_advance}\n{scheduled_advance}" in description
        assert "next month" in description.lower() or "Folgemonat" in description


def test_payment_totals_have_explicit_bold_class_on_both_directions():
    assert 'class="row total-row"' in CARD
    assert ".total-row strong{font-weight:700}" in CARD
    assert "Gesamt geleistete Zahlungen" in CARD
    assert "Gesamt erhaltene Zahlungen" in CARD


def test_advance_editor_saves_through_the_selected_months_own_billing_period():
    assert "period_number = max(0, (selected_index - start_index) // duration)" in FLOW
    assert "while cursor.year * 12 + cursor.month - 1 <= period_end_index:" in FLOW
