[![Made for Home Assistant](https://img.shields.io/badge/Made%20for-Home%20Assistant-blue?style=for-the-badge&logo=homeassistant)](https://www.home-assistant.io/)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://github.com/hacs/integration)

# Last Time Tracker: Home Assistant integration

> [!NOTE]
> This integration is vibe coded

A Home Assistant integration to keep track of when you last did something (replace the toothbrush, water the plants, take out the trash) and how long it's been since. No YAML required.

Each thing you want to track is called a **topic**. Create one, and it becomes its own device with a set of sensors and a button, ready to use in automations, dashboards, or just to glance at.

---

## Features

* **Fully UI-driven:** create and manage topics entirely through **Settings > Devices & Services**. No YAML.
* **Log with a tap or a service call:** every topic gets a "Log now" button, plus a `log_event` service for triggering it from an automation (e.g. a smart plug that detects the washing machine finished).
* **Four sensors per topic:**
  * **Last time**: timestamp of the most recent logged event, with the full history and note in its attributes.
  * **Days ago**: how many days since the last event.
  * **Median interval**: the typical number of days between events, once at least two are logged.
  * **Predicted next**: a rough estimate of when the topic is next due, based on that median interval.
* **Full history management:** add, edit, or delete individual past events (with an optional note) straight from the topic's own settings; no need to get it right the first time.
* **Live updates:** sensors update the instant an event is logged, no polling involved.

---

## Installation

This integration isn't in the HACS default store yet, so add it as a custom repository.

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=klaptafel&repository=ha-last-time-tracker&category=integration)

1. In HACS, add `https://github.com/klaptafel/ha-last-time-tracker` as a custom repository
   (category: Integration).
2. Install "Last Time Tracker" and restart Home Assistant.

---

## Configuration

[![Add integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start?domain=last_time_tracker)

1. Navigate to **Settings > Devices & Services**.
2. Click **Add Integration** and search for **Last Time Tracker**.
3. Give your topic a name (e.g. "Replace toothbrush") and, optionally, pick an icon.
4. Repeat for each topic you want to track; each one is its own separate device.

To rename a topic, change its icon, or manage its history afterwards, click the topic's device and choose **Configure**.

---

## Removal

1. Navigate to **Settings > Devices & Services**.
2. Find the topic (device) you want to remove and click it.
3. Click the trash-can icon, then confirm.

This deletes that topic's entire logged history; it cannot be undone.

---

## Services

| Service | What it does |
|---|---|
| `last_time_tracker.add_topic` | Create a new topic without going through the UI, useful for setting up topics from a script or blueprint. |
| `last_time_tracker.log_event` | Log an event for one or more topics (by entity or device), optionally with a specific date/time and a note. Defaults to now if no date is given. |
| `last_time_tracker.delete_last_event` | Remove the most recently logged event for a topic. |
| `last_time_tracker.edit_event` | Edit an existing event by its ID (visible in the "Last time" sensor's `history` attribute). |
| `last_time_tracker.delete_event` | Delete a specific event by its ID. |

Any of a topic's sensor entities (or its device) can be used as the target for these services; you don't need to pick the "Last time" sensor specifically.

---

## Example automation

Log automatically instead of pressing the button yourself, whenever possible. For example, log
"Took out the trash" the moment a door sensor on the bin cupboard closes after being open for a
while:

```yaml
automation:
  - alias: "Log trash taken out"
    trigger:
      - platform: state
        entity_id: binary_sensor.bin_cupboard_door
        to: "off"
    action:
      - service: last_time_tracker.log_event
        target:
          entity_id: sensor.take_out_trash_last_time
```

---

## Troubleshooting

- **A service call fails with "no topic found for entity"**: double-check the target is one of that
  topic's own entities or its device; entities from other topics or unrelated domains aren't valid
  targets.
- **"Median interval"/"Predicted next" show as unavailable**: these need at least two logged events
  to calculate an interval from. Log one more event and they'll populate.
- **Nothing happens after a Home Assistant restart**: history is stored on disk (Home Assistant's own
  storage, not the recorder), so all topics and their history survive restarts automatically.

## Known limitations

- Only the most recent 50 events per topic are kept; older ones are dropped automatically as new
  ones are logged.
- "Median interval" and "Predicted next" use the median of all stored intervals, not a weighted or
  trending average; a single unusually long or short gap can shift the prediction more than you
  might expect until more events even it out.
- Each topic is its own separate device, purely for grouping its entities; there's no way to nest
  topics or group several of them under one shared device.
