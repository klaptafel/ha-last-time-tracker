"""Data management for Last Time Tracker."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import uuid4

from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.storage import Store

from .const import (
    DISPATCHER_UPDATED,
    EVENT_DELETED,
    EVENT_LOGGED,
    MAX_HISTORY,
    STORAGE_KEY,
    STORAGE_VERSION,
)

_LOGGER = logging.getLogger(__name__)


def _ensure_event_ids(history: dict[str, list]) -> bool:
    """Add a stable UUID to any event that is missing one. Returns True if migrated."""
    migrated = False
    for events in history.values():
        for event in events:
            if "id" not in event:
                event["id"] = str(uuid4())
                migrated = True
    return migrated


class LastTimeTrackerData:
    """Manages persistent storage for all Last Time Tracker topics."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._store: Store | None = None
        self._history: dict[str, list] = {}

    async def async_load(self) -> None:
        """Load history from .storage file, migrating legacy events if needed."""
        self._store = Store(self.hass, STORAGE_VERSION, STORAGE_KEY)
        self._history = await self._store.async_load() or {}
        if _ensure_event_ids(self._history):
            await self._store.async_save(self._history)
            _LOGGER.debug("Migrated existing events: added missing UUIDs")

    def ensure_entry(self, entry_id: str) -> None:
        """Initialize history list for a new entry if not present."""
        self._history.setdefault(entry_id, [])

    def get_history(self, entry_id: str) -> list:
        """Return history list for an entry."""
        return self._history.get(entry_id, [])

    def has_entry(self, entry_id: str) -> bool:
        """Return whether an entry_id is known."""
        return entry_id in self._history

    def _topic_name(self, entry_id: str) -> str:
        """Resolve a human-readable topic name from entry_id."""
        entry = self.hass.config_entries.async_get_entry(entry_id)
        if not entry:
            return entry_id
        return entry.options.get("name") or entry.data.get("name", entry_id)

    async def async_log_event(
        self,
        entry_id: str,
        dt: datetime,
        note: str = "",
    ) -> None:
        """Add a new event to the history, persist, and fire HA event."""
        if not dt.tzinfo:
            dt = dt.replace(tzinfo=timezone.utc)

        event = {"id": str(uuid4()), "datetime": dt.isoformat(), "note": note}
        self._history.setdefault(entry_id, []).insert(0, event)
        self._history[entry_id] = self._history[entry_id][:MAX_HISTORY]
        await self._store.async_save(self._history)

        topic = self._topic_name(entry_id)
        async_dispatcher_send(self.hass, f"{DISPATCHER_UPDATED}_{entry_id}")
        self.hass.bus.async_fire(
            EVENT_LOGGED,
            {"entry_id": entry_id, "topic": topic, "datetime": dt.isoformat(), "note": note},
        )
        _LOGGER.debug("Logged event for '%s' at %s", topic, dt.isoformat())

    async def async_edit_event(
        self,
        entry_id: str,
        event_id: str,
        dt: datetime,
        note: str = "",
    ) -> bool:
        """Edit an existing event by UUID. Returns False if not found."""
        if not dt.tzinfo:
            dt = dt.replace(tzinfo=timezone.utc)

        for event in self._history.get(entry_id, []):
            if event.get("id") == event_id:
                event["datetime"] = dt.isoformat()
                event["note"] = note
                # Re-sort: newest first
                self._history[entry_id].sort(
                    key=lambda e: e["datetime"], reverse=True
                )
                await self._store.async_save(self._history)
                async_dispatcher_send(self.hass, f"{DISPATCHER_UPDATED}_{entry_id}")
                _LOGGER.debug("Edited event %s for '%s'", event_id, self._topic_name(entry_id))
                return True
        return False

    async def async_delete_event_by_id(
        self,
        entry_id: str,
        event_id: str,
    ) -> bool:
        """Delete an event by UUID. Returns False if not found."""
        events = self._history.get(entry_id, [])
        original_len = len(events)
        self._history[entry_id] = [e for e in events if e.get("id") != event_id]

        if len(self._history[entry_id]) == original_len:
            return False

        await self._store.async_save(self._history)
        topic = self._topic_name(entry_id)
        async_dispatcher_send(self.hass, f"{DISPATCHER_UPDATED}_{entry_id}")
        self.hass.bus.async_fire(EVENT_DELETED, {"entry_id": entry_id, "topic": topic})
        _LOGGER.debug("Deleted event %s for '%s'", event_id, topic)
        return True

    async def async_delete_last_event(self, entry_id: str) -> None:
        """Remove the most recent event, persist, and fire HA event."""
        if not self._history.get(entry_id):
            return
        self._history[entry_id].pop(0)
        await self._store.async_save(self._history)

        topic = self._topic_name(entry_id)
        async_dispatcher_send(self.hass, f"{DISPATCHER_UPDATED}_{entry_id}")
        self.hass.bus.async_fire(EVENT_DELETED, {"entry_id": entry_id, "topic": topic})
        _LOGGER.debug("Deleted last event for '%s'", topic)

    async def async_remove_entry(self, entry_id: str) -> None:
        """Remove all history for an entry and persist."""
        if entry_id in self._history:
            del self._history[entry_id]
            await self._store.async_save(self._history)
