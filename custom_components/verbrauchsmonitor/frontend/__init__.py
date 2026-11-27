"""Serve and reliably register the VerbrauchsMonitor Lovelace cards.

The static HTTP route and the Lovelace resource are separate registrations.
Home Assistant may call integration setup before Lovelace has initialized its
resource collection. Registration is therefore retried until the collection is
ready. Repeated calls are safe and repair a missing or outdated resource.
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_call_later

from ..const import CARD_URL, DOMAIN, INTEGRATION_VERSION

_LOGGER = logging.getLogger(__name__)
_CARD_PATH = Path(__file__).parent / "verbrauchsmonitor-card.js"
_DATA_KEY = f"{DOMAIN}_frontend_registration"
_RETRY_SECONDS = 15


def _state(hass: HomeAssistant) -> dict[str, Any]:
    """Return this integration's process-local frontend registration state."""
    return hass.data.setdefault(
        _DATA_KEY,
        {"static_registered": False, "retry_cancel": None, "lock": asyncio.Lock()},
    )


def _schedule_retry(hass: HomeAssistant) -> None:
    """Schedule one retry; repeated setup calls never create parallel timers."""
    state = _state(hass)
    if state.get("retry_cancel") is not None:
        return

    def _retry(_now) -> None:
        state["retry_cancel"] = None
        hass.async_create_task(async_register_card(hass))

    state["retry_cancel"] = async_call_later(hass, _RETRY_SECONDS, _retry)


async def _ensure_static_path(hass: HomeAssistant, state: dict[str, Any]) -> bool:
    """Register the JS directory once, tolerating HA's duplicate-route guard."""
    if state.get("static_registered"):
        return True

    try:
        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_URL.rsplit("/", 1)[0], _CARD_PATH.parent, False)]
        )
        state["static_registered"] = True
        return True
    except Exception as err:  # noqa: BLE001 - duplicate registration is recoverable
        message = str(err).lower()
        # async_setup and async_setup_entry both call this function. HA rejects
        # the second identical route; that means the static route already works.
        if "already" in message and ("register" in message or "exist" in message):
            state["static_registered"] = True
            return True
        _LOGGER.warning("VerbrauchsMonitor card static path could not be registered: %s", err)
        return False


async def _async_register_card_locked(hass: HomeAssistant, state: dict[str, Any]) -> bool:
    """Perform registration while holding the per-Home-Assistant lock."""
    if not await _ensure_static_path(hass, state):
        _schedule_retry(hass)
        return False

    lovelace = hass.data.get("lovelace")
    if lovelace is None:
        _schedule_retry(hass)
        return False

    resource_mode = getattr(lovelace, "resource_mode", None)
    if resource_mode == "yaml":
        # YAML mode is deliberately user-managed; the static URL remains served.
        cancel = state.get("retry_cancel")
        if cancel:
            cancel()
            state["retry_cancel"] = None
        return True
    if resource_mode != "storage":
        _schedule_retry(hass)
        return False

    resources = getattr(lovelace, "resources", None)
    if resources is None:
        _schedule_retry(hass)
        return False

    resource_url = f"{CARD_URL}?v={INTEGRATION_VERSION}"
    try:
        # ResourceStorageCollection is loaded lazily by Home Assistant.
        await resources.async_get_info()
        existing = list(resources.async_items())
        matching = [
            item for item in existing
            if str(item.get("url", "")).split("?", 1)[0] == CARD_URL
        ]

        if matching:
            primary = matching[0]
            if primary.get("url") != resource_url or primary.get("res_type") != "module":
                await resources.async_update_item(
                    primary["id"], {"res_type": "module", "url": resource_url}
                )
        else:
            await resources.async_create_item({"res_type": "module", "url": resource_url})

        cancel = state.get("retry_cancel")
        if cancel:
            cancel()
            state["retry_cancel"] = None
        return True
    except Exception as err:  # noqa: BLE001 - retry transient storage/startup failures
        _LOGGER.warning(
            "VerbrauchsMonitor Lovelace card registration is not ready: %s. "
            "The integration will retry automatically. Resource URL: %s",
            err,
            resource_url,
        )
        _schedule_retry(hass)
        return False


async def async_register_card(hass: HomeAssistant) -> bool:
    """Ensure the card JS is served and registered as a Lovelace module.

    Concurrent setup paths are serialized, and an unavailable Lovelace storage
    collection is retried automatically. Repeated calls are safe.
    """
    state = _state(hass)
    async with state["lock"]:
        return await _async_register_card_locked(hass, state)
