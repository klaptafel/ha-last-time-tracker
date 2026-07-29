"""Diagnostics for Last Time Tracker."""
from __future__ import annotations

from homeassistant.core import HomeAssistant

from .data import LastTimeTrackerConfigEntry, topic_icon, topic_name


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: LastTimeTrackerConfigEntry
) -> dict:
    """Return diagnostics for a config entry."""
    name = topic_name(entry)
    icon = topic_icon(entry)
    # None-guarded the same way ha-update-manager's own diagnostics.py is:
    # entry.runtime_data is None both before setup completes and after a
    # clean unload (see __init__.py's own async_unload_entry) -- HA's UI
    # normally only offers "Download diagnostics" for a currently-loaded
    # entry, but this degrades gracefully instead of raising AttributeError
    # on the narrower race windows around that.
    if entry.runtime_data is None:
        return {"entry_id": entry.entry_id, "name": name, "icon": icon}
    history = entry.runtime_data.get_history(entry.entry_id)

    return {
        "entry_id": entry.entry_id,
        "name": name,
        "icon": icon,
        "history_count": len(history),
        "history": history,
    }
