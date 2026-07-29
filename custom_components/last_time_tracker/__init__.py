"""Last Time Tracker integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .data import LastTimeTrackerConfigEntry, LastTimeTrackerData
from .services import async_setup_services

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Last Time Tracker integration and register services.

    The one shared LastTimeTrackerData instance (see its own docstring: a
    single Store covering every topic, not one per entry) is built here,
    not lazily in async_setup_entry -- async_setup always runs exactly once,
    before any topic's own config entry, so there's no "first entry creates
    it" race to guard against anymore. entity_map (arbitrary entity_id ->
    entry_id, used by services.py's own cross-entry target resolution, which
    has no single entry of its own to work from) has nowhere else to live
    but this domain-wide dict either."""
    data = LastTimeTrackerData(hass)
    await data.async_load()
    hass.data[DOMAIN] = {"data": data, "entity_map": {}}
    await async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: LastTimeTrackerConfigEntry) -> bool:
    """Set up a topic from a config entry."""
    data = hass.data[DOMAIN]["data"]
    data.ensure_entry(entry.entry_id)
    entry.runtime_data = data
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: LastTimeTrackerConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        entry.runtime_data = None
    return unloaded


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old config entry to a new version."""
    _LOGGER.debug("Migrating Last Time Tracker entry from version %s", entry.version)
    return True


async def async_remove_entry(hass: HomeAssistant, entry: LastTimeTrackerConfigEntry) -> None:
    """Clean up storage when a topic is deleted."""
    await hass.data[DOMAIN]["data"].async_remove_entry(entry.entry_id)
