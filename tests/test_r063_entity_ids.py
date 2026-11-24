from pathlib import Path
import ast

ROOT = Path(__file__).parents[1]
NAMING = ROOT / "custom_components/verbrauchsmonitor/naming.py"
REGISTRY = ROOT / "custom_components/verbrauchsmonitor/registry_cleanup.py"

def _load_naming():
    tree = ast.parse(NAMING.read_text())
    nodes = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.Assign, ast.AnnAssign))]
    module = ast.Module(body=nodes, type_ignores=[])
    namespace = {"re": __import__("re"), "unicodedata": __import__("unicodedata")}
    exec(compile(module, str(NAMING), "exec"), namespace)
    return namespace

def test_all_meter_entity_ids_use_integration_prefix():
    helpers = _load_naming()
    ids = helpers["meter_entity_object_ids"]("Verbrauch - neu")
    assert ids
    assert all(value.startswith("verbrauchsmonitor_verbrauch_neu_") for value in ids.values())

def test_balance_entity_ids_are_canonical_and_directional():
    helpers = _load_naming()
    ids = helpers["balance_entity_ids"]("Verbrauch - neu", feed_in=True)
    assert ids["consumption"] == "sensor.verbrauchsmonitor_verbrauch_neu_verbrauch_kontostand"
    assert ids["feed_in"] == "sensor.verbrauchsmonitor_verbrauch_neu_einspeisung_kontostand"

def test_registry_cleanup_migrates_known_ids_and_removes_obsolete_ids():
    init_source = (ROOT / "custom_components/verbrauchsmonitor/__init__.py").read_text()
    registry_source = REGISTRY.read_text()
    assert "expected_entity_ids" in init_source
    assert "registry.async_update_entity" in init_source
    assert "registry.async_remove" in init_source
    assert "meter_entity_object_ids" in registry_source

def test_billing_period_is_rendered_as_a_non_wrapping_line():
    source = (ROOT / "custom_components/verbrauchsmonitor/frontend/verbrauchsmonitor-card.js").read_text()
    assert 'class="billing-period-line"' in source
    assert ".billing-period-line{display:inline-block;white-space:nowrap}" in source
