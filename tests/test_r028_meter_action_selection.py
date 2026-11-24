from pathlib import Path


FLOW = (Path(__file__).parents[1] / "custom_components" / "verbrauchsmonitor" / "config_flow.py").read_text()


def test_meter_dropdown_is_conditional_for_edit_and_delete():
    assert 'if action in ("edit", "delete") and meters:' in FLOW
    assert 'fields[vol.Required("selected", default=options[0]["value"])]' in FLOW


def test_new_meter_does_not_get_a_dropdown():
    assert 'if action == "new":' in FLOW
    assert 'return await self.async_step_meter_edit()' in FLOW
    assert 'if action in ("edit", "delete") and meters:' in FLOW


def test_old_separate_meter_select_step_is_removed():
    assert "async_step_meter_select" not in FLOW
    assert "step_id=\"meter_select\"" not in FLOW


def test_edit_and_delete_continue_from_selected_value():
    assert 'if action == "delete":' in FLOW
    assert 'self._meter_edit_id = selected' in FLOW
    assert 'return await self.async_step_meter_edit()' in FLOW
