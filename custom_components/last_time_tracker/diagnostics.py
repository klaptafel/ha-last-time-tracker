"""Diagnostics for Last Time Tracker."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_ICON, DEFAULT_ICON, DOMAIN


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict:
    """Return diagnostics for a config entry."""
    data = hass.data[DOMAIN]["data"]
    history = data.get_history(entry.entry_id)
    name = entry.options.get("name") or entry.data.get("name")
    icon = entry.options.get(CONF_ICON) or entry.data.get(CONF_ICON, DEFAULT_ICON)

    return {
        "entry_id": entry.entry_id,
        "name": name,
        "icon": icon,
        "history_count": len(history),
        "history": history,
    }
