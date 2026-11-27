"""Regression tests for reliable Lovelace resource registration (R130)."""
from __future__ import annotations

import asyncio
import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).parents[1]
INTEGRATION = ROOT / "custom_components/verbrauchsmonitor"


def _load_frontend_module(monkeypatch):
    """Load frontend registration with small Home Assistant API doubles."""
    package_name = "_vm_registration_test"
    package = types.ModuleType(package_name)
    package.__path__ = []
    frontend_package = types.ModuleType(f"{package_name}.frontend")
    frontend_package.__path__ = []
    const_module = types.ModuleType(f"{package_name}.const")
    const_module.CARD_URL = "/verbrauchsmonitor/verbrauchsmonitor-card.js"
    const_module.DOMAIN = "verbrauchsmonitor"
    const_module.INTEGRATION_VERSION = "0.0.2-beta-r131"

    class StaticPathConfig:
        def __init__(self, url_path, path, cache_headers):
            self.url_path = url_path
            self.path = path
            self.cache_headers = cache_headers

    http_module = types.ModuleType("homeassistant.components.http")
    http_module.StaticPathConfig = StaticPathConfig
    core_module = types.ModuleType("homeassistant.core")
    core_module.HomeAssistant = object
    scheduled = []

    def async_call_later(hass, delay, callback):
        item = {"delay": delay, "callback": callback, "cancelled": False}
        scheduled.append(item)

        def cancel():
            item["cancelled"] = True

        return cancel

    event_module = types.ModuleType("homeassistant.helpers.event")
    event_module.async_call_later = async_call_later

    modules = {
        package_name: package,
        f"{package_name}.frontend": frontend_package,
        f"{package_name}.const": const_module,
        "homeassistant": types.ModuleType("homeassistant"),
        "homeassistant.components": types.ModuleType("homeassistant.components"),
        "homeassistant.components.http": http_module,
        "homeassistant.core": core_module,
        "homeassistant.helpers": types.ModuleType("homeassistant.helpers"),
        "homeassistant.helpers.event": event_module,
    }
    for name, module in modules.items():
        monkeypatch.setitem(sys.modules, name, module)

    path = INTEGRATION / "frontend/__init__.py"
    spec = importlib.util.spec_from_file_location(
        f"{package_name}.frontend", path, submodule_search_locations=[]
    )
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, f"{package_name}.frontend", module)
    spec.loader.exec_module(module)
    return module, scheduled


class FakeResources:
    def __init__(self, items=None):
        self.items = list(items or [])
        self.created = []
        self.updated = []

    async def async_get_info(self):
        return None

    def async_items(self):
        return list(self.items)

    async def async_create_item(self, item):
        created = {**item, "id": f"resource-{len(self.items) + 1}"}
        self.items.append(created)
        self.created.append(created)

    async def async_update_item(self, item_id, values):
        self.updated.append((item_id, values))
        for item in self.items:
            if item["id"] == item_id:
                item.update(values)
                return
        raise KeyError(item_id)


class FakeHttp:
    def __init__(self):
        self.paths = []

    async def async_register_static_paths(self, configs):
        self.paths.extend(configs)


class FakeHass:
    def __init__(self):
        self.data = {}
        self.http = FakeHttp()
        self.tasks = []

    def async_create_task(self, coro):
        task = asyncio.create_task(coro)
        self.tasks.append(task)
        return task


def test_card_asset_is_packaged():
    card = INTEGRATION / "frontend/verbrauchsmonitor-card.js"
    assert card.is_file() and card.stat().st_size > 1000
    source = card.read_text()
    assert 'customElements.define("verbrauchsmonitor-card"' in source
    assert 'customElements.define("verbrauchsmonitor-billing-card"' in source
    assert 'window.customCards.push' in source


def test_card_registration_recovers_when_lovelace_is_not_ready(monkeypatch):
    module, scheduled = _load_frontend_module(monkeypatch)
    hass = FakeHass()

    async def scenario():
        # Integration setup can happen before Lovelace creates its storage manager.
        assert await module.async_register_card(hass) is False
        assert len(hass.http.paths) == 1
        assert len(scheduled) == 1
        assert scheduled[0]["delay"] == 15

        resources = FakeResources()
        hass.data["lovelace"] = types.SimpleNamespace(
            resource_mode="storage", resources=resources
        )
        # Config-entry setup can safely call registration again before timer fires.
        assert await module.async_register_card(hass) is True
        assert len(hass.http.paths) == 1  # static route is never registered twice
        assert len(resources.created) == 1
        assert resources.created[0]["url"].endswith("?v=0.0.2-beta-r131")
        assert resources.created[0]["res_type"] == "module"
        assert scheduled[0]["cancelled"] is True

    asyncio.run(scenario())


def test_delayed_retry_registers_resource_after_lovelace_initializes(monkeypatch):
    module, scheduled = _load_frontend_module(monkeypatch)
    hass = FakeHass()

    async def scenario():
        assert await module.async_register_card(hass) is False
        resources = FakeResources()
        hass.data["lovelace"] = types.SimpleNamespace(
            resource_mode="storage", resources=resources
        )
        scheduled[0]["callback"](None)
        await asyncio.gather(*hass.tasks)
        assert len(resources.created) == 1
        assert hass.data["verbrauchsmonitor_frontend_registration"]["retry_cancel"] is None

    asyncio.run(scenario())


def test_existing_resource_is_version_updated_not_duplicated(monkeypatch):
    module, _scheduled = _load_frontend_module(monkeypatch)
    hass = FakeHass()
    resources = FakeResources([
        {"id": "old-resource", "res_type": "module", "url": "/verbrauchsmonitor/verbrauchsmonitor-card.js?v=old"}
    ])
    hass.data["lovelace"] = types.SimpleNamespace(resource_mode="storage", resources=resources)

    async def scenario():
        assert await module.async_register_card(hass) is True
        assert resources.created == []
        assert len(resources.updated) == 1
        assert resources.updated[0][0] == "old-resource"
        assert resources.items[0]["url"].endswith("?v=0.0.2-beta-r131")

    asyncio.run(scenario())


def test_yaml_resource_mode_does_not_create_storage_resource(monkeypatch):
    module, _scheduled = _load_frontend_module(monkeypatch)
    hass = FakeHass()
    resources = FakeResources()
    hass.data["lovelace"] = types.SimpleNamespace(resource_mode="yaml", resources=resources)

    async def scenario():
        assert await module.async_register_card(hass) is True
        assert resources.created == []

    asyncio.run(scenario())


def test_duplicate_static_route_error_does_not_abort_lovelace_registration(monkeypatch):
    module, _scheduled = _load_frontend_module(monkeypatch)
    hass = FakeHass()
    resources = FakeResources()
    hass.data["lovelace"] = types.SimpleNamespace(resource_mode="storage", resources=resources)

    async def duplicate_route(_configs):
        raise RuntimeError("Static path /verbrauchsmonitor is already registered")

    hass.http.async_register_static_paths = duplicate_route

    async def scenario():
        assert await module.async_register_card(hass) is True
        assert len(resources.created) == 1
        assert hass.data["verbrauchsmonitor_frontend_registration"]["static_registered"] is True

    asyncio.run(scenario())


def test_concurrent_setup_calls_create_only_one_resource(monkeypatch):
    module, _scheduled = _load_frontend_module(monkeypatch)
    hass = FakeHass()
    resources = FakeResources()
    hass.data["lovelace"] = types.SimpleNamespace(resource_mode="storage", resources=resources)

    async def scenario():
        results = await asyncio.gather(
            module.async_register_card(hass),
            module.async_register_card(hass),
            module.async_register_card(hass),
        )
        assert results == [True, True, True]
        assert len(hass.http.paths) == 1
        assert len(resources.created) == 1

    asyncio.run(scenario())
