# Aether

> **Home Concierge** — Your home, managed. Your mind, free.

Aether lifts the mental burden of remembering what needs to be done around your home, when, and how urgently. It's not a personal assistant or task manager — it's a knowledgeable concierge who knows the state of your home and advises when asked.

## Philosophy

- **Offload, don't add** — Reduces mental load, never creates more
- **Flexible, not strict** — Life happens. Soft deadlines, no nagging
- **Adaptive** — Learns your patterns, asks before adjusting intervals
- **Room-first thinking** — Matches how you experience your home
- **Classy gamification** — Satisfying completions, not cartoon rewards

## Features

### Core

- **80 chores** organized by room with smart intervals
- **Freshness scores** — Room health at a glance; stays green while you have plenty of time, decays only in the final stretch before a task is due
- **"I have X minutes"** — Get prioritized tasks that fit your time
- **Morning briefing** — ~15 min of high-impact suggestions
- **Checklists** — Scenarios like "Parents visiting" or "Sleepover"; create, edit, and delete them; items sorted by due date so the most urgent always floats to the top; at-a-glance overdue count and estimated time on the list view

### Smart

- **Priority auto-calculation** — Based on interval frequency
- **Streak tracking** — Gamified consistency
- **Duration estimation** — Learns accurate times from your feedback
- **Overdue tracking** — Nothing nags, but you can see what needs attention
- **Graceful new-chore handling** — Freshly added tasks start at 100% fresh and decay from their creation date, not from zero

## Home Assistant Add-on

The recommended way to run Aether is as a Home Assistant add-on — it runs on
your Pi alongside HA and is accessible anywhere via Nabu Casa.

1. In HA go to **Settings → Add-ons → Add-on Store → ⋮ → Repositories**
2. Add `https://github.com/b0kk3n/aether`
3. Install **Aether** and click **Start**
4. The **Aether** panel appears in the HA sidebar

Optionally install the custom component from
`homeassistant/custom_components/aether/` for HA sensors and services.
See [DOCS.md](DOCS.md) for details.

## Local / Development Quick Start

```bash
# Install
pip install -e .

# Seed with initial data
aether seed

# Start the server
aether serve

# Open http://localhost:8080 on your phone
```

## CLI Commands

```bash
aether dashboard    # Home overview
aether briefing     # Morning briefing
aether quick 30     # "I have 30 minutes"
aether rooms        # List all rooms
aether overdue      # List overdue chores
aether done <id>    # Mark chore complete
aether checklists   # List checklists
aether checklist <id>  # View checklist
```

## API

All endpoints available at `/api`:

- `GET /api/dashboard` — Home overview
- `GET /api/dashboard/briefing` — Morning briefing
- `GET /api/dashboard/quick-clean?minutes=30` — Prioritized list
- `GET /api/rooms` — List rooms with freshness
- `GET /api/rooms/{id}/chores` — Chores for a room
- `GET /api/chores` — List all chores
- `POST /api/chores/{id}/complete` — Mark complete
- `GET /api/checklists` — List checklists with overdue count and estimated time
- `GET /api/checklists/{id}` — Checklist with live chore status, sorted by due date
- `POST /api/checklists` — Create checklist
- `PUT /api/checklists/{id}` — Update checklist name, description, or icon
- `DELETE /api/checklists/{id}` — Delete checklist

## Tech Stack

- **Backend**: Python 3.11+ / FastAPI
- **Database**: SQLite
- **Frontend**: PWA (Progressive Web App)
- **CLI**: Click + Rich

## Project Structure

```text
aether/
├── api/           # FastAPI routes
├── core/
│   ├── models.py    # Data models
│   ├── database.py  # SQLite setup
│   └── services/    # Business logic
├── seed/          # Initial data
├── web/           # PWA frontend
└── cli.py         # Command-line interface
```

## License

MIT
