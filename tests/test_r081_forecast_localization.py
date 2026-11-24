import json
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_forecast_uses_read_only_automatic_season_description_in_both_languages():
    de = json.loads((ROOT / "custom_components/verbrauchsmonitor/translations/de.json").read_text())
    en = json.loads((ROOT / "custom_components/verbrauchsmonitor/translations/en.json").read_text())
    de_text = de["options"]["step"]["forecast"]["description"]
    en_text = en["options"]["step"]["forecast"]["description"]
    assert "astronomische Jahreszeit" in de_text
    assert "Home-Assistant-Standorts" in de_text
    assert "astronomical season" in en_text
    assert "Home Assistant location" in en_text
    assert "season_mode" not in de["options"]["step"]["forecast"].get("data", {})
    assert "manual_season" not in de["options"]["step"]["forecast"].get("data", {})


def test_forecast_form_shows_current_season_without_manual_selection():
    flow = (ROOT / "custom_components/verbrauchsmonitor/config_flow.py").read_text()
    start = flow.index("    async def async_step_forecast(")
    end = flow.index("    async def async_step_billing(", start)
    forecast_flow = flow[start:end]
    assert '"current_season": self._labels(de, en)' in forecast_flow
    assert "season_mode" not in forecast_flow
    assert "manual_season" not in forecast_flow
