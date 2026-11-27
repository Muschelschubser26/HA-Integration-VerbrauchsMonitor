from pathlib import Path
import json

ROOT = Path(__file__).parents[1]
INTEGRATION = ROOT / "custom_components/verbrauchsmonitor"


def test_user_flow_does_not_reserve_domain_wide_flow_unique_id():
    source = (INTEGRATION / "config_flow.py").read_text()
    user_step = source.split("async def async_step_user", 1)[1].split("@staticmethod", 1)[0]
    assert "async_set_unique_id" not in user_step
    assert "async_entries(DOMAIN)" in user_step
    assert 'async_abort(reason="already_configured")' in user_step
    assert 'async_create_entry(title="VerbrauchsMonitor", data={})' in user_step


def test_already_configured_abort_is_translated():
    for language, expected in (
        ("de", "VerbrauchsMonitor ist bereits eingerichtet."),
        ("en", "VerbrauchsMonitor is already configured."),
    ):
        data = json.loads((INTEGRATION / f"translations/{language}.json").read_text())
        assert data["config"]["abort"]["already_configured"] == expected


def test_release_version_is_r011():
    manifest = json.loads((INTEGRATION / "manifest.json").read_text())
    assert manifest["version"] == "0.0.1"
