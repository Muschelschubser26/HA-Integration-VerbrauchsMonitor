"""Serve and register the VerbrauchsMonitor Lovelace card.

    Cache headers are disabled intentionally: frontend-only updates can be picked
    up by refreshing the dashboard/browser without reloading Home Assistant.
    """
from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from ..const import CARD_URL, INTEGRATION_VERSION

_LOGGER = logging.getLogger(__name__)
_CARD_PATH = Path(__file__).parent / "verbrauchsmonitor-card.js"


async def async_register_card(hass: HomeAssistant) -> None:
    """Register card JS and add it to Lovelace resources in storage mode."""
    try:
        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_URL.rsplit("/", 1)[0], _CARD_PATH.parent, False)]
        )
    except Exception as err:  # noqa: BLE001 - never let card serving break integration setup
        _LOGGER.warning("VerbrauchsMonitor card static path could not be registered: %s", err)
        return

    lovelace = hass.data.get("lovelace")
    if lovelace is None or getattr(lovelace, "resource_mode", None) != "storage":
        return

    resources = getattr(lovelace, "resources", None)
    if resources is None:
        _LOGGER.warning("Lovelace resource collection unavailable; card URL: %s", CARD_URL)
        return

    resource_url = f"{CARD_URL}?v={INTEGRATION_VERSION}"
    try:
        # Ensure the storage collection has loaded before inspecting or mutating it.
        await resources.async_get_info()
        existing = resources.async_items()
        for item in existing:
            if item.get("url", "").split("?", 1)[0] == CARD_URL:
                if item.get("url") != resource_url:
                    await resources.async_update_item(
                        item["id"], {"res_type": "module", "url": resource_url}
                    )
                return
        await resources.async_create_item({"res_type": "module", "url": resource_url})
    except Exception as err:  # noqa: BLE001 - frontend registration must not break integration setup
        _LOGGER.warning(
            "Lovelace-Karte konnte nicht automatisch registriert werden: %s. "
            "Ressource manuell hinzufügen: %s",
            err, resource_url,
        )
