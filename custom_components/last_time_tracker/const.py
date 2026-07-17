"""Constants for Last Time Tracker."""
DOMAIN = "last_time_tracker"
PLATFORMS = ["sensor", "button"]

STORAGE_VERSION = 1
STORAGE_KEY = "last_time_tracker.history"
MAX_HISTORY = 50

CONF_ICON = "icon"
DEFAULT_ICON = "mdi:clock-check"

SERVICE_LOG_EVENT = "log_event"
SERVICE_DELETE_LAST_EVENT = "delete_last_event"
SERVICE_ADD_TOPIC = "add_topic"
SERVICE_EDIT_EVENT = "edit_event"
SERVICE_DELETE_EVENT = "delete_event"

DISPATCHER_UPDATED = "last_time_tracker_updated"

# HA event bus events
EVENT_LOGGED = "last_time_tracker_event_logged"
EVENT_DELETED = "last_time_tracker_event_deleted"
