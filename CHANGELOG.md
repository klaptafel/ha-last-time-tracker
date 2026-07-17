# Changelog

All notable changes to this project are documented here. Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

## [1.0.0] - 2026-07-17

First release of Last Time Tracker: create "topics" (e.g. "Replace toothbrush", "Watered plants") and log when you last did them, either with a button press or a service call. Each topic gets sensors for the last time it happened, how many days ago that was, the typical interval between times, and a predicted next date once enough history exists. Full history management (add, edit, delete past entries) is available from the topic's own settings, in English and Dutch.

### Added
- Every sensor of a topic (not just "Last time") registers as a valid target for the `log_event`/`delete_last_event`/`edit_event`/`delete_event` services, so "Days ago", "Median interval", or "Predicted next" can be picked as a service target too.
- Dutch translation (`translations/nl.json`) alongside the existing English base.
- `hacs.json`, GitHub Actions (`validate.yml`, `hassfest.yaml`) and `dependabot.yml`; this project had none before.
- `manifest.json` completed with `codeowners`, `issue_tracker`, a real `documentation` URL, and `integration_type: device` (each topic creates its own device grouping several entities, one device per config entry, unlike a bare "helper" like `min_max`/`utility_meter`, which never create a device at all).
- `PARALLEL_UPDATES = 0` on both platforms (sensor, button): was missing, unlike this project's siblings.
- A full README: features, installation, configuration, removal, a services table, an example automation, troubleshooting, and known limitations.

### Quality Scale
- Self-assessed against Home Assistant's Integration Quality Scale for the first time: 29 done / 16 exempt / 6 todo. Remaining gaps: no test suite, no `brand/` folder (needs real icon artwork), shared state lives in `hass.data[DOMAIN]` rather than `ConfigEntry.runtime_data`, fixed-icon sensors use `_attr_icon` instead of `icons.json`, and no CI `mypy` step.
