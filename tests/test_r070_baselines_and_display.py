import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
INTEGRATION = ROOT / "custom_components" / "verbrauchsmonitor"


def test_billing_card_shows_start_reading_and_three_provenance_states():
    card = (INTEGRATION / "frontend" / "verbrauchsmonitor-card.js").read_text(encoding="utf-8")
    assert 'Zählerstand Abrechnungsbeginn' in card
    assert 'Manuell eingetragen' in card
    assert 'Abrechnungsroutine' in card
    assert 'Korrigiert' in card
    assert '.baseline-badge.routine' in card
    assert '.baseline-badge.manual' in card


def test_feed_in_monthly_advance_is_inline_and_not_a_separate_row():
    card = (INTEGRATION / "frontend" / "verbrauchsmonitor-card.js").read_text(encoding="utf-8")
    assert 'Einspeisevergütung' in card and 'monthlyAdvanceGroups.map(group =>' in card
    assert 'isFeed && monthlyAdvance>0?field(t("Monatlicher Abschlag"' not in card


def test_all_billing_row_labels_receive_colon_and_parenthetical_text_is_grey():
    card = (INTEGRATION / "frontend" / "verbrauchsmonitor-card.js").read_text(encoding="utf-8")
    assert 'const withColon = label =>' in card
    assert 'esc(withColon(label))' in card
    assert '.row .informational{color:var(--disabled-text-color' in card
    assert 'withColon(t("Anteiliger Grundpreis"' in card


def test_baseline_manual_corrections_keep_history_and_dates():
    init = (INTEGRATION / "__init__.py").read_text(encoding="utf-8")
    flow = (INTEGRATION / "config_flow.py").read_text(encoding="utf-8")
    sensor = (INTEGRATION / "sensor.py").read_text(encoding="utf-8")
    assert '"corrected" if previous_source == "routine" else "manual"' in init
    assert 'history.append({"value": str(old_value)' in init
    assert 'item[source_key] = "corrected" if old_source == "routine" else "manual"' in flow
    assert '"consumption_baseline_history": entry.data.get' in sensor
    assert '"feed_in_baseline_history": entry.data.get' in sensor


def test_routine_baseline_is_captured_only_on_billing_period_boundary():
    init = (INTEGRATION / "__init__.py").read_text(encoding="utf-8")
    assert 'def _period_start_for_date' in init
    assert 'if current_period_start != today:' in init
    assert 'meter["baseline_period_start"]' not in init
    assert 'async_track_time_change' in init


def test_price_and_money_inputs_allow_six_decimal_places():
    card = (INTEGRATION / "frontend" / "verbrauchsmonitor-card.js").read_text(encoding="utf-8")
    init = (INTEGRATION / "__init__.py").read_text(encoding="utf-8")
    assert r'\d{1,6}' in card
    assert 'höchstens sechs Nachkommastellen' in init


def test_translations_are_valid_and_have_matching_meter_edit_keys():
    de = json.loads((INTEGRATION / "translations" / "de.json").read_text(encoding="utf-8"))
    en = json.loads((INTEGRATION / "translations" / "en.json").read_text(encoding="utf-8"))
    de_keys = set(de["options"]["step"]["meter_edit"]["data"])
    en_keys = set(en["options"]["step"]["meter_edit"]["data"])
    assert de_keys == en_keys
    assert "Zählerstand Abrechnungsbeginn" in de["options"]["step"]["meter_edit"]["data"]["previous_consumption_reading"]


def test_period_start_calculation_handles_month_end_and_year_rollover():
    import ast
    from calendar import monthrange
    from datetime import date

    source = (INTEGRATION / "__init__.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    function = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_period_start_for_date"
    )
    module = ast.Module(body=[function], type_ignores=[])
    namespace = {"date": date, "monthrange": monthrange}
    exec(compile(module, "__init__.py", "exec"), namespace)
    period_start = namespace["_period_start_for_date"]
    assert period_start(date(2026, 1, 31), 1, date(2026, 2, 28)) == date(2026, 2, 28)
    assert period_start(date(2026, 1, 1), 12, date(2027, 1, 1)) == date(2027, 1, 1)
    assert period_start(date(2026, 1, 1), 12, date(2026, 12, 31)) == date(2026, 1, 1)
