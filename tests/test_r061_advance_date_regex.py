from pathlib import Path


def test_frontend_advance_date_regex_matches_iso_dates():
    root = Path(__file__).resolve().parents[1]
    source = (root / "custom_components/verbrauchsmonitor/frontend/verbrauchsmonitor-card.js").read_text()
    assert r"/^\d{4}-\d{2}-\d{2}$/" in source
    assert r"/^\\d{4}-\\d{2}-\\d{2}$/" not in source
