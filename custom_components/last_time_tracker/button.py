"""Button platform for Last Time Tracker."""
from __future__ import annotations

from datetime import datetime, timezone

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_ICON, DEFAULT_ICON, DOMAIN
from .data import LastTimeTrackerData

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up button for a topic."""
    name: str = entry.options.get("name") or entry.data["name"]
    icon: str = entry.options.get(CONF_ICON) or entry.data.get(CONF_ICON, DEFAULT_ICON)
    async_add_entities([LogNowButton(hass, entry, name, icon)])


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
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=name,
        )

    async def async_press(self) -> None:
        """Log the current datetime without a note."""
        data: LastTimeTrackerData = self.hass.data[DOMAIN]["data"]
        await data.async_log_event(self._entry_id, datetime.now(timezone.utc))
