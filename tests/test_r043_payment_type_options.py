from pathlib import Path


def test_payment_editor_exposes_regular_advance_booking_type():
    source = (Path(__file__).parents[1] / "custom_components" / "verbrauchsmonitor" / "config_flow.py").read_text(encoding="utf-8")
    start = source.index("def _booking_edit_schema")
    end = source.index("async def async_step_database", start)
    schema = source[start:end]
    assert '"value": "payment"' in schema
    assert '"value": "credit"' in schema
    assert '"value": "extra_charge"' in schema
    assert '"value": "advance"' in schema
    assert '"value": "correction"' in schema
