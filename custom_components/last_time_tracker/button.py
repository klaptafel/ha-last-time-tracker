"""Button platform for Last Time Tracker."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .data import LastTimeTrackerData, build_device_info, topic_icon, topic_name

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up button for a topic."""
    async_add_entities([LogNowButton(hass, entry, topic_name(entry), topic_icon(entry))])


class LogNowButton(ButtonEntity):
    """Button that logs the current timestamp for a topic."""

    _attr_has_entity_name = True
    _attr_translation_key = "log_now"

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        name: str,
        icon: str,
    ) -> None:
        self.hass = hass
        self._entry_id = entry.entry_id
        self._attr_unique_id = f"{entry.entry_id}_log_now"
        self._attr_icon = icon
        self._attr_device_info = build_device_info(entry.entry_id, name)

    async def async_press(self) -> None:
        """Log the current datetime without a note."""
        data: LastTimeTrackerData = self.hass.data[DOMAIN]["data"]
        await data.async_log_event(self._entry_id, dt_util.utcnow())
