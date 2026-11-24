from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FLOW = ROOT / "custom_components" / "verbrauchsmonitor" / "config_flow.py"

def test_options_flow_returns_complete_payload():
    source = FLOW.read_text(encoding="utf-8")
    assert "options = {**dict(self.config_entry.options), **changes}" in source
    assert 'return self.async_create_entry(title="", data=options)' in source

