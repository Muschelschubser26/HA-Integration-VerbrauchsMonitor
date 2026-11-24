from pathlib import Path


def _source():
    return (Path(__file__).parents[1] / "custom_components/verbrauchsmonitor/frontend/verbrauchsmonitor-card.js").read_text()


def test_billing_card_renders_exactly_one_selected_direction():
    source = _source()
    assert 'const directions=[];' in source
    assert 'const selectedDirection = this.config.direction === "feed_in" ? "feed_in" : "consumption";' in source
    assert 'if (selectedCounter || selectedBalance) directions.push({kind:selectedDirection' in source
    assert 'directions.map(d=>d.html).join("")' in source


def test_billing_card_editor_selects_meter_and_direction():
    source = _source()
    assert 'this.config.meter_id' in source
    assert 'id="meter"' in source
    assert 'id="direction"' in source


def test_each_direction_keeps_its_own_financial_bookings_and_labels():
    source = _source()
    assert 'const financeC=financeFor(counter, "consumption", balance), financeF=financeFor(feed, "feed_in", feedBalance);' in source
    assert 'Einspeisung im Abrechnungszeitraum' in source
    assert 'Verbrauch im Abrechnungszeitraum' in source
