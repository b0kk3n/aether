# Changelog

## 0.4.1

- Fix checklist edit button (JSON in onclick attribute broke the HTML parser; now uses a module-level reference)
- Tune freshness decay threshold from 75% to 50% — rooms felt too positive; a task due tomorrow now correctly shows urgency while long-interval tasks with plenty of time remaining still read as 100%

## 0.4.0

### Checklist improvements
- Edit checklist name, description, and icon directly from the detail view
- Delete checklists with a single tap (with confirmation)
- Checklist items now sorted by due date ascending — most urgent tasks always appear first, regardless of completion status
- Checklist list cards now show overdue count and total estimated time at a glance

### Freshness scoring overhaul
- Freshness stays at 100% for the first 75% of an interval, then decays linearly to 0% over the final 25% — a task due in 84 days on a 90-day interval now correctly reads as fully fresh
- Removed the 50% artificial floor that was propping up scores for tasks due within 3 days, which masked urgency rather than showing it
- Newly added chores start at 100% fresh and decay from their creation date instead of being immediately overdue; all SQL queries updated consistently with `COALESCE(last_completed_at, created_at)`

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
