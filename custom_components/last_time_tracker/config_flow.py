"""Config flow for Last Time Tracker."""
from __future__ import annotations

from datetime import datetime

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    DateTimeSelector,
    IconSelector,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
from homeassistant.util import dt as dt_util, slugify

from .const import CONF_ICON, DEFAULT_ICON, DOMAIN
from .data import ensure_utc, topic_icon, topic_name

# Schema used by both config and options topic step
TOPIC_SCHEMA = vol.Schema({
    vol.Required("name"): TextSelector(
        TextSelectorConfig(type=TextSelectorType.TEXT)
    ),
    vol.Optional(CONF_ICON): IconSelector(),
})

_MENU_OPTIONS = [
    SelectOptionDict(value="topic",   label="Edit name & icon"),
    SelectOptionDict(value="history", label="Manage history"),
    SelectOptionDict(value="done",    label="Save & close"),
]

_HISTORY_ACTIONS = [
    SelectOptionDict(value="add",    label="Add event"),
    SelectOptionDict(value="edit",   label="Edit event"),
    SelectOptionDict(value="delete", label="Delete event"),
    SelectOptionDict(value="back",   label="« Back"),
]


def _format_event_label(event: dict) -> str:
    """Format a history event for display in a dropdown (local time)."""
    raw = event.get("datetime", "")
    try:
        dt_local = dt_util.as_local(ensure_utc(datetime.fromisoformat(raw)))
        date_str = dt_local.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        date_str = raw[:16]
    note = event.get("note", "")
    return f"{date_str} ({note})" if note else date_str


def _parse_form_datetime(user_input: dict) -> tuple[datetime, str]:
    """Parse a DateTimeSelector value plus its optional note.

    A naive value (no tzinfo) comes from the picker showing local time
    with no offset, so it's interpreted as local, not UTC (unlike
    ensure_utc's assumption, which is for values that are already
    internally-generated UTC, e.g. when re-parsing a stored event).
    Attach the local zone directly rather than going through
    dt_util.as_local(), which assumes a *naive* input is already UTC
    (the opposite of what's needed here) and would otherwise leave the
    value unchanged instead of converting it.
    """
    raw = user_input["datetime"]
    dt = datetime.fromisoformat(raw) if isinstance(raw, str) else raw
    if not dt.tzinfo:
        dt = dt_util.as_utc(dt.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE))
    return dt, user_input.get("note", "")


class LastTimeTrackerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Last Time Tracker."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return LastTimeTrackerOptionsFlow()

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step, from UI or from service."""
        errors: dict[str, str] = {}

        if user_input is not None:
            name = user_input["name"].strip()
            if not name:
                errors["name"] = "name_required"
            else:
                await self.async_set_unique_id(slugify(name))
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=name,
                    data={
                        "name": name,
                        CONF_ICON: user_input.get(CONF_ICON, DEFAULT_ICON),
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                TOPIC_SCHEMA, {CONF_ICON: DEFAULT_ICON}
            ),
            errors=errors,
        )


class LastTimeTrackerOptionsFlow(config_entries.OptionsFlow):
    """Handle options for an existing topic: settings + full history CRUD."""

    def __init__(self) -> None:
        self._pending_options: dict | None = None  # set when topic settings change
        self._selected_event_id: str | None = None  # carries selection between steps

    # ------------------------------------------------------------------ #
    # Top-level menu                                                       #
    # ------------------------------------------------------------------ #

    async def async_step_init(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        """Show the top-level menu."""
        if user_input is not None:
            action = user_input["action"]
            if action == "done":
                return await self.async_step_done()
            return await getattr(self, f"async_step_{action}")()

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required("action"): SelectSelector(SelectSelectorConfig(
                    options=_MENU_OPTIONS,
                    mode=SelectSelectorMode.LIST,
                    translation_key="options_menu",
                )),
            }),
        )

    async def async_step_done(self) -> ConfigFlowResult:
        """Close the flow, saving pending options and reloading if needed."""
        options = self._pending_options or self.config_entry.options
        title = options.get("name", self.config_entry.title)
        result = self.async_create_entry(title=title, data=options)

        # Only reload when settings actually changed
        if self._pending_options is not None:
            self.hass.async_create_task(
                self.hass.config_entries.async_reload(self.config_entry.entry_id)
            )
        return result

    # ------------------------------------------------------------------ #
    # Topic settings                                                       #
    # ------------------------------------------------------------------ #

    async def async_step_topic(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        """Edit name and icon."""
        errors: dict[str, str] = {}

        if user_input is not None:
            name = user_input["name"].strip()
            if not name:
                errors["name"] = "name_required"
            else:
                self._pending_options = {
                    "name": name,
                    CONF_ICON: user_input.get(CONF_ICON, DEFAULT_ICON),
                }
                return await self.async_step_init()

        current_name = (self._pending_options or {}).get("name") or topic_name(self.config_entry)
        current_icon = (self._pending_options or {}).get(CONF_ICON) or topic_icon(self.config_entry)

        return self.async_show_form(
            step_id="topic",
            data_schema=self.add_suggested_values_to_schema(
                TOPIC_SCHEMA, {"name": current_name, CONF_ICON: current_icon}
            ),
            errors=errors,
        )

    # ------------------------------------------------------------------ #
    # History sub-menu                                                     #
    # ------------------------------------------------------------------ #

    async def async_step_history(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        """Show history action menu."""
        if user_input is not None:
            action = user_input["action"]
            if action == "back":
                return await self.async_step_init()
            return await getattr(self, f"async_step_history_{action}")()

        return self.async_show_form(
            step_id="history",
            data_schema=vol.Schema({
                vol.Required("action"): SelectSelector(SelectSelectorConfig(
                    options=_HISTORY_ACTIONS,
                    mode=SelectSelectorMode.LIST,
                    translation_key="history_menu",
                )),
            }),
        )

    # ------------------------------------------------------------------ #
    # Add event                                                            #
    # ------------------------------------------------------------------ #

    async def async_step_history_add(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        """Add a new event manually."""
        if user_input is not None:
            dt, note = _parse_form_datetime(user_input)
            data = self.hass.data[DOMAIN]["data"]
            await data.async_log_event(self.config_entry.entry_id, dt, note)
            return await self.async_step_history()

        return self.async_show_form(
            step_id="history_add",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema({
                    vol.Required("datetime"): DateTimeSelector(),
                    vol.Optional("note"): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.TEXT)
                    ),
                }),
                {"datetime": dt_util.utcnow().strftime("%Y-%m-%d %H:%M:%S")},
            ),
        )

    # ------------------------------------------------------------------ #
    # Edit event                                                           #
    # ------------------------------------------------------------------ #

    async def _step_pick_event(
        self, user_input: dict | None, step_id: str, next_step: str
    ) -> ConfigFlowResult:
        """Shared "pick an event from a dropdown" step for edit/delete."""
        history = self.hass.data[DOMAIN]["data"].get_history(self.config_entry.entry_id)
        if not history:
            return await self.async_step_history()

        if user_input is not None:
            event_id = user_input.get("event_id")
            if not event_id:
                return await self.async_step_history()
            self._selected_event_id = event_id
            return await getattr(self, f"async_step_{next_step}")()

        options = [
            SelectOptionDict(value=e["id"], label=_format_event_label(e))
            for e in history if e.get("id")
        ]

        return self.async_show_form(
            step_id=step_id,
            data_schema=vol.Schema({
                vol.Required("event_id"): SelectSelector(SelectSelectorConfig(
                    options=options,
                    mode=SelectSelectorMode.LIST,
                    translation_key="event_picker",
                )),
            }),
        )

    async def async_step_history_edit(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        """Pick which event to edit."""
        return await self._step_pick_event(user_input, "history_edit", "history_edit_form")

    async def async_step_history_edit_form(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        """Edit the selected event."""
        data = self.hass.data[DOMAIN]["data"]
        history = data.get_history(self.config_entry.entry_id)
        event = next(
            (e for e in history if e.get("id") == self._selected_event_id), None
        )
        if not event:
            return await self.async_step_history()

        errors: dict[str, str] = {}

        if user_input is not None:
            dt, note = _parse_form_datetime(user_input)
            await data.async_edit_event(
                self.config_entry.entry_id, self._selected_event_id, dt, note
            )
            self._selected_event_id = None
            return await self.async_step_history()

        dt_str = dt_util.as_local(ensure_utc(datetime.fromisoformat(event["datetime"]))).strftime("%Y-%m-%d %H:%M:%S")

        return self.async_show_form(
            step_id="history_edit_form",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema({
                    vol.Required("datetime"): DateTimeSelector(),
                    vol.Optional("note"): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.TEXT)
                    ),
                }),
                {"datetime": dt_str, "note": event.get("note", "")},
            ),
            errors=errors,
        )

    # ------------------------------------------------------------------ #
    # Delete event                                                         #
    # ------------------------------------------------------------------ #

    async def async_step_history_delete(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        """Pick which event to delete."""
        return await self._step_pick_event(user_input, "history_delete", "history_delete_confirm")

    async def async_step_history_delete_confirm(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        """Confirm deletion of the selected event."""
        history = self.hass.data[DOMAIN]["data"].get_history(self.config_entry.entry_id)
        event = next(
            (e for e in history if e.get("id") == self._selected_event_id), None
        )
        if not event:
            return await self.async_step_history()

        if user_input is not None:
            if user_input.get("confirm"):
                await self.hass.data[DOMAIN]["data"].async_delete_event_by_id(
                    self.config_entry.entry_id, self._selected_event_id
                )
            self._selected_event_id = None
            return await self.async_step_history()

        return self.async_show_form(
            step_id="history_delete_confirm",
            data_schema=vol.Schema({
                vol.Required("confirm", default=False): bool,
            }),
            description_placeholders={
                "event_label": _format_event_label(event),
            },
        )
