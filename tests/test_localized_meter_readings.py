from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_meter_reading_parser_supports_german_decimal_comma_and_legacy_dot():
    source = (ROOT / "custom_components/verbrauchsmonitor/config_flow.py").read_text()
    assert "def _parse_localized_meter_reading" in source
    assert 'text.replace(".", "").replace(",", ".")' in source
    assert 'selector.TextSelector(selector.TextSelectorConfig())' in source
    assert 'errors[field] = "invalid_reading"' in source


def test_both_meter_baselines_use_text_input_for_locale_independent_decimal_parsing():
    source = (ROOT / "custom_components/verbrauchsmonitor/config_flow.py").read_text()
    assert '"previous_consumption_reading", default=str(data.get("previous_consumption_reading", 0)).replace(".", ",")): selector.TextSelector' in source
    assert 'vol.Optional("previous_feed_in_reading", default=str(data.get("previous_feed_in_reading", 0)).replace(".", ","))' in source


def test_invalid_reading_translation_exists_in_both_languages():
    import json
    for language in ("de", "en"):
        data = json.loads((ROOT / f"custom_components/verbrauchsmonitor/translations/{language}.json").read_text())
        assert data["options"]["error"]["invalid_reading"]


def test_parser_values_are_normalized_as_expected():
    import ast
    from decimal import Decimal, InvalidOperation
    source = (ROOT / "custom_components/verbrauchsmonitor/config_flow.py").read_text()
    tree = ast.parse(source)
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_parse_localized_meter_reading")
    module = ast.Module(body=[function], type_ignores=[])
    namespace = {"Decimal": Decimal, "InvalidOperation": InvalidOperation}
    exec(compile(module, "config_flow.py", "exec"), namespace)
    parse = namespace["_parse_localized_meter_reading"]
    assert parse("4798,996") == 4798.996
    assert parse("5.372,28") == 5372.28
    assert parse("4798.996") == 4798.996
    assert parse(4798.996) == 4798.996
    for invalid in ("", "abc", "-1", "1,2,3", "1000001"):
        try:
            parse(invalid)
        except (InvalidOperation, ValueError):
            pass
        else:
            raise AssertionError(f"Invalid reading accepted: {invalid!r}")
