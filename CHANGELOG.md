# Changelog

## 0.3.1

- Fix `ModuleNotFoundError: No module named 'aether.core.engine'` crash on startup
- Remove stale `aether.web` module import from `app.py`; path resolution now uses env vars set in Dockerfile
- Restore missing custom component files (`__init__.py`, `sensor.py`, `manifest.json`)
- Simplify HA services to the two that have real API backing (`complete_chore`, `what_now`)
- Sensors now use `/api/dashboard` for overdue and chores-due-soon counts

## 0.3.0

- Initial Home Assistant add-on release
- Ingress support for access via Nabu Casa remote
- Persistent SQLite storage at `/data/aether.db`
- ARM-compatible build (aarch64 + armv7) for Raspberry Pi
