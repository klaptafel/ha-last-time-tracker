"""Diagnostics for Last Time Tracker."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .data import topic_icon, topic_name


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict:
    """Return diagnostics for a config entry."""
    data = hass.data[DOMAIN]["data"]
    history = data.get_history(entry.entry_id)
    name = topic_name(entry)
    icon = topic_icon(entry)

    return {
        "entry_id": entry.entry_id,
        "name": name,
        "icon": icon,
        "history_count": len(history),
        "history": history,
    }
