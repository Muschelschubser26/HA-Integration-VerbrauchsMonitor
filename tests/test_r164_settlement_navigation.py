import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
INTEGRATION = ROOT / "custom_components/verbrauchsmonitor"


def test_settlement_and_monthly_advance_main_menu_order_and_translations():
    expected = ["contracts", "meters", "forecast", "settlement", "billing", "data_management", "about"]
    for language in ("de", "en"):
        data = json.loads((INTEGRATION / f"translations/{language}.json").read_text())
        steps = data["options"]["step"]
        assert list(steps["init"]["menu_options"]) == expected
        assert list(steps["settlement"]["menu_options"]) == ["settlement_create", "settlement_view"]
        assert list(steps["billing"]["menu_options"]) == ["advance_change", "advance_meter", "billing_bookings"]


def test_settlement_menu_routes_to_direct_destination_dialogs_with_ok():
    source = (INTEGRATION / "config_flow.py").read_text()
    assert 'menu_options=["settlement_create", "settlement_view"]' in source
    assert "async_step_settlement_create" in source
    assert "async_step_settlement_view" in source
    for language in ("de", "en"):
        steps = json.loads((INTEGRATION / f"translations/{language}.json").read_text())["options"]["step"]
        assert steps["settlement_create"]["submit"] == "OK"
        assert steps["settlement_view"]["submit"] == "OK"
