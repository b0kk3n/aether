# Changelog

## 0.6.0

### Settings tab, editable categories, room pause

- New **Settings** tab: vacation mode controls + history, category management, and a browsable list of all chores (including house-wide ones not yet due, previously only reachable by stumbling into them via a checklist)
- **Categories** are now user-editable instead of a fixed set: add, rename, delete, and reorder them, and set whether each one pauses by default during vacation mode (was previously hardcoded in code)
- **Room pause** — pause an individual room (e.g. while remodeling) to freeze all of its chores' countdowns regardless of category, independent of vacation mode; unpausing shifts due dates forward by the paused length
- Rooms can now be added, renamed, re-iconed, reordered, and deleted from the app — the API already supported this, but there was no UI for it
- Checklists: adding chores is now multi-select instead of one at a time
- Vacation mode moved off the Home dashboard: replaced by a small status chip, with the actual start/end controls and a new history view living in Settings
- Home dashboard decluttered: the "N things worth ~M minutes" line merged into the "Suggested" section header instead of duplicating it, and "Rooms needing attention" was removed (the Rooms tab's per-room freshness bar already covers this)
- Visual refresh: a display serif font for headings, room/category/checklist icons switched from emoji to a consistent line-icon set (existing emoji data still renders), and refined freshness bar/status-dot styling
- Fixed: seeded room-specific chores were being created as house-wide due to a bug in the seeder; `GET /chores` now returns room details even when a filter is applied
- Fixed: `aether --version` reported a stale `0.3.0` regardless of the actual package version

## 0.5.0

### Vacation mode

- Pause chore countdowns while you're away: occupancy-driven chores (vacuum, mop, dust, declutter, clean, wash, wipe) stop accruing overdue time by default; maintenance chores keep ticking since that decay happens regardless of occupancy
- Per-chore override to force-pause or force-exclude a chore regardless of its category default
- Manual start/end from a new Home view banner, or via `aether vacation start/end/status`
- Ending vacation shifts eligible chores' due dates forward by exactly the trip length, resuming the countdown where it left off

## 0.4.2

### Checklist time-to-complete and smarter check questions

- Checklist now shows time to complete (remaining chores only) instead of total time
- Duration check question asked every 3rd completion instead of every 2nd
- Interval check question only triggers when completion is 50%+ or 7+ days off schedule
- Fixed duplicate modal bug causing 'No' responses to not always save

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
