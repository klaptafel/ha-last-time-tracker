"""Last Time Tracker integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .data import LastTimeTrackerData
from .services import async_setup_services

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Last Time Tracker integration and register services."""
    hass.data.setdefault(DOMAIN, {"entity_map": {}})
    await async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a topic from a config entry."""
    if "data" not in hass.data[DOMAIN]:
        data = LastTimeTrackerData(hass)
        await data.async_load()
        hass.data[DOMAIN]["data"] = data

    hass.data[DOMAIN]["data"].ensure_entry(entry.entry_id)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old config entry to a new version."""
    _LOGGER.debug("Migrating Last Time Tracker entry from version %s", entry.version)
    return True


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Clean up storage when a topic is deleted."""
    if "data" in hass.data.get(DOMAIN, {}):
        await hass.data[DOMAIN]["data"].async_remove_entry(entry.entry_id)
