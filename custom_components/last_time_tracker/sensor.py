"""Sensor platform for Last Time Tracker."""
from __future__ import annotations

from datetime import datetime, timedelta
from statistics import median

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.util import dt as dt_util

from .const import DISPATCHER_UPDATED, DOMAIN
from .data import LastTimeTrackerConfigEntry, build_device_info, ensure_utc, topic_icon, topic_name

PARALLEL_UPDATES = 0

MIN_EVENTS_FOR_PREDICTION = 2


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LastTimeTrackerConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors for a topic."""
    name = topic_name(entry)
    icon = topic_icon(entry)

    async_add_entities([
        LastTimeSensor(hass, entry, name, icon),
        DaysAgoSensor(hass, entry, name),
        AvgIntervalSensor(hass, entry, name),
        PredictedNextSensor(hass, entry, name),
    ])


def _parse_dt(raw: str) -> datetime:
    """Parse an ISO datetime string, ensuring timezone info is present."""
    return ensure_utc(datetime.fromisoformat(raw))


def _median_interval_days(history: list) -> float | None:
    """Calculate the median interval in days from a history list.

    Returns None if fewer than MIN_EVENTS_FOR_PREDICTION events are present.
    """
    if len(history) < MIN_EVENTS_FOR_PREDICTION:
        return None

    datetimes = [_parse_dt(e["datetime"]) for e in history]
    intervals = [
        (datetimes[i] - datetimes[i + 1]).total_seconds() / 86400
        for i in range(len(datetimes) - 1)
    ]
    return median(intervals)


class LastTimeTrackerBaseSensor(SensorEntity):
    """Base class shared by all sensors."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    # Set by subclasses whose displayed value depends on "today"/"now" and
    # so needs an extra refresh at local midnight, not just on dispatcher
    # updates (e.g. "days ago" increments even with no new event logged).
    _needs_midnight_refresh = False

    def __init__(
        self,
        hass: HomeAssistant,
        entry: LastTimeTrackerConfigEntry,
        name: str,
    ) -> None:
        self.hass = hass
        self._entry_id = entry.entry_id
        self._data = entry.runtime_data
        self._attr_device_info = build_device_info(entry.entry_id, name)

    def _get_history(self) -> list:
        return self._data.get_history(self._entry_id)

    async def async_added_to_hass(self) -> None:
        """Subscribe to dispatcher updates and register as a valid service target.

        Every sensor of a topic (not just LastTimeSensor) registers here --
        services.yaml only restricts targets to domain: sensor, so a user
        can pick any of the four (Last time / Days ago / Median interval /
        Predicted next) from the entity picker. Only registering one of
        them would make the others fail service calls with a confusing
        "no topic found for entity" error.
        """
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{DISPATCHER_UPDATED}_{self._entry_id}",
                self._handle_update,
            )
        )
        self.hass.data[DOMAIN]["entity_map"][self.entity_id] = self._entry_id
        if self._needs_midnight_refresh:
            self.async_on_remove(
                async_track_time_change(
                    self.hass,
                    self._handle_midnight,
                    hour=0,
                    minute=0,
                    second=0,
                )
            )

    async def async_will_remove_from_hass(self) -> None:
        self.hass.data[DOMAIN]["entity_map"].pop(self.entity_id, None)

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()

    @callback
    def _handle_midnight(self, now=None) -> None:
        self.async_write_ha_state()


class LastTimeSensor(LastTimeTrackerBaseSensor):
    """Sensor showing when the topic was last completed (TIMESTAMP)."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_translation_key = "last_time"

    def __init__(self, hass, entry, name, icon) -> None:
        super().__init__(hass, entry, name)
        self._attr_unique_id = f"{entry.entry_id}_last_time"
        self._attr_icon = icon

    @property
    def native_value(self) -> datetime | None:
        history = self._get_history()
        return _parse_dt(history[0]["datetime"]) if history else None

    @property
    def extra_state_attributes(self) -> dict:
        history = self._get_history()
        return {
            "history": list(history),
            "note": history[0].get("note", "") if history else None,
            "count": len(history),
        }


class DaysAgoSensor(LastTimeTrackerBaseSensor):
    """Sensor showing how many days ago the topic was last completed."""

    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.DAYS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "days_ago"
    _needs_midnight_refresh = True  # the day count increments at midnight

    def __init__(self, hass, entry, name) -> None:
        super().__init__(hass, entry, name)
        self._attr_unique_id = f"{entry.entry_id}_days_ago"

    @property
    def native_value(self) -> int | None:
        history = self._get_history()
        if not history:
            return None
        # Both sides in local time, matching the local-midnight refresh
        # above: comparing a UTC date against a local one would make the
        # count flip a few hours early/late for any zone not on UTC+0.
        last_date = dt_util.as_local(_parse_dt(history[0]["datetime"])).date()
        today = dt_util.now().date()
        return (today - last_date).days


class AvgIntervalSensor(LastTimeTrackerBaseSensor):
    """Sensor showing the median interval between events in days."""

    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.DAYS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "avg_interval"

    def __init__(self, hass, entry, name) -> None:
        super().__init__(hass, entry, name)
        self._attr_unique_id = f"{entry.entry_id}_avg_interval"

    @property
    def native_value(self) -> float | None:
        interval = _median_interval_days(self._get_history())
        return round(interval, 1) if interval is not None else None


class PredictedNextSensor(LastTimeTrackerBaseSensor):
    """Sensor predicting when the topic is next due based on median interval."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_translation_key = "predicted_next"
    _needs_midnight_refresh = True  # relative display should stay current

    def __init__(self, hass, entry, name) -> None:
        super().__init__(hass, entry, name)
        self._attr_unique_id = f"{entry.entry_id}_predicted_next"

    @property
    def native_value(self) -> datetime | None:
        history = self._get_history()
        interval = _median_interval_days(history)
        if interval is None:
            return None
        last_dt = _parse_dt(history[0]["datetime"])
        return last_dt + timedelta(days=interval)
