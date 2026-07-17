"""Service registration for Last Time Tracker."""
from __future__ import annotations

from datetime import datetime

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.util import dt as dt_util
from homeassistant.util import slugify

from .const import (
    CONF_ICON,
    DEFAULT_ICON,
    DOMAIN,
    SERVICE_ADD_TOPIC,
    SERVICE_DELETE_EVENT,
    SERVICE_DELETE_LAST_EVENT,
    SERVICE_EDIT_EVENT,
    SERVICE_LOG_EVENT,
)
from .data import LastTimeTrackerData, topic_name


def _raise_event_not_found(event_id: str) -> None:
    raise ServiceValidationError(
        f"Event '{event_id}' not found.",
        translation_domain=DOMAIN,
        translation_key="event_not_found",
    )


def _resolve_entry_ids(hass: HomeAssistant, call: ServiceCall) -> set[str]:
    """Resolve entity_ids and device_ids from call.data to entry_ids."""
    entry_ids: set[str] = set()
    domain_data = hass.data.get(DOMAIN, {})
    if "data" not in domain_data:
        raise ServiceValidationError(
            "No Last Time Tracker topics are configured yet.",
            translation_domain=DOMAIN,
            translation_key="no_topics_configured",
        )
    entity_map: dict = domain_data["entity_map"]
    data: LastTimeTrackerData = domain_data["data"]

    for entity_id in cv.ensure_list(call.data.get("entity_id", [])):
        entry_id = entity_map.get(entity_id)
        if entry_id:
            entry_ids.add(entry_id)
        else:
            raise ServiceValidationError(
                f"No Last Time Tracker topic found for entity '{entity_id}'",
                translation_domain=DOMAIN,
                translation_key="unknown_entity",
            )

    device_registry = dr.async_get(hass)
    for device_id in cv.ensure_list(call.data.get("device_id", [])):
        device = device_registry.async_get(device_id)
        if not device:
            raise ServiceValidationError(
                f"Device '{device_id}' not found",
                translation_domain=DOMAIN,
                translation_key="unknown_device",
            )
        for entry_id in device.config_entries:
            if data.has_entry(entry_id):
                entry_ids.add(entry_id)

    return entry_ids


async def async_setup_services(hass: HomeAssistant) -> None:
    """Register Last Time Tracker services."""
    if hass.services.has_service(DOMAIN, SERVICE_LOG_EVENT):
        return

    async def handle_add_topic(call: ServiceCall) -> None:
        name: str = call.data["name"].strip()
        icon: str = call.data.get(CONF_ICON, DEFAULT_ICON)
        unique_id = slugify(name)

        # Check for duplicate
        for entry in hass.config_entries.async_entries(DOMAIN):
            if slugify(topic_name(entry)) == unique_id:
                raise ServiceValidationError(
                    f"A topic named '{name}' already exists.",
                    translation_domain=DOMAIN,
                    translation_key="topic_already_exists",
                )

        await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={"name": name, CONF_ICON: icon},
        )

    async def handle_log_event(call: ServiceCall) -> None:
        note: str = call.data.get("note", "")
        date: datetime | None = call.data.get("date")
        dt = date if date else dt_util.utcnow()

        data: LastTimeTrackerData = hass.data[DOMAIN]["data"]
        for entry_id in _resolve_entry_ids(hass, call):
            await data.async_log_event(entry_id, dt, note)

    async def handle_delete_last_event(call: ServiceCall) -> None:
        data: LastTimeTrackerData = hass.data[DOMAIN]["data"]
        for entry_id in _resolve_entry_ids(hass, call):
            await data.async_delete_last_event(entry_id)

    hass.services.async_register(
        DOMAIN,
        SERVICE_ADD_TOPIC,
        handle_add_topic,
        schema=vol.Schema({
            vol.Required("name"): cv.string,
            vol.Optional(CONF_ICON, default=DEFAULT_ICON): cv.string,
        }),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_LOG_EVENT,
        handle_log_event,
        schema=vol.Schema({
            vol.Optional("entity_id"): cv.entity_ids,
            vol.Optional("device_id"): vol.All(cv.ensure_list, [cv.string]),
            vol.Optional("note", default=""): cv.string,
            vol.Optional("date"): cv.datetime,
        }),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_DELETE_LAST_EVENT,
        handle_delete_last_event,
        schema=vol.Schema({
            vol.Optional("entity_id"): cv.entity_ids,
            vol.Optional("device_id"): vol.All(cv.ensure_list, [cv.string]),
        }),
    )

    async def handle_edit_event(call: ServiceCall) -> None:
        event_id: str = call.data["event_id"]
        date: datetime | None = call.data.get("date")
        dt = date if date else dt_util.utcnow()
        note: str = call.data.get("note", "")

        data: LastTimeTrackerData = hass.data[DOMAIN]["data"]
        for entry_id in _resolve_entry_ids(hass, call):
            found = await data.async_edit_event(entry_id, event_id, dt, note)
            if not found:
                _raise_event_not_found(event_id)

    async def handle_delete_event(call: ServiceCall) -> None:
        event_id: str = call.data["event_id"]
        data: LastTimeTrackerData = hass.data[DOMAIN]["data"]
        for entry_id in _resolve_entry_ids(hass, call):
            found = await data.async_delete_event_by_id(entry_id, event_id)
            if not found:
                _raise_event_not_found(event_id)

    hass.services.async_register(
        DOMAIN,
        SERVICE_EDIT_EVENT,
        handle_edit_event,
        schema=vol.Schema({
            vol.Optional("entity_id"): cv.entity_ids,
            vol.Optional("device_id"): vol.All(cv.ensure_list, [cv.string]),
            vol.Required("event_id"): cv.string,
            vol.Optional("date"): cv.datetime,
            vol.Optional("note", default=""): cv.string,
        }),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_DELETE_EVENT,
        handle_delete_event,
        schema=vol.Schema({
            vol.Optional("entity_id"): cv.entity_ids,
            vol.Optional("device_id"): vol.All(cv.ensure_list, [cv.string]),
            vol.Required("event_id"): cv.string,
        }),
    )
