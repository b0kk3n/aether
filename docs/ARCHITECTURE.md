# Aether Architecture

## Overview

Aether is a self-hosted web application with a mobile-first PWA frontend and a Python/FastAPI backend.

```
┌─────────────────────────────────────────┐
│           Mobile Device                 │
│     (PWA - Progressive Web App)         │
│     iOS Safari / Android Chrome         │
└─────────────────────────────────────────┘
                    │
                    │ HTTPS
                    ▼
┌─────────────────────────────────────────┐
│            Aether Server                │
│  ┌───────────────────────────────────┐  │
│  │      FastAPI (Python 3.11+)       │  │
│  │      REST API + Static Files      │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │      SQLite (Local Database)      │  │
│  │      ~/.aether/aether.db          │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

## Data Model

### Entity Relationship

```
┌──────────────┐       ┌──────────────────────────────────────┐
│    Room      │       │              Chore                   │
│──────────────│       │──────────────────────────────────────│
│ id           │◄──────│ room_id (nullable for house-wide)    │
│ name         │   1:N │ name                                 │
│ icon         │       │ interval_days                        │
│ sort_order   │       │ estimated_minutes                    │
└──────────────┘       │ priority (high/normal/low)           │
                       │ category                              │
                       │ last_completed_at                     │
                       │ streak                                │
                       │ duration_confirmed (bool)             │
                       │ duration_confirmations (int)          │
                       └──────────────────────────────────────┘
                                         │
                                         │ 1:N
                                         ▼
                       ┌──────────────────────────────────────┐
                       │          CompletionLog               │
                       │──────────────────────────────────────│
                       │ chore_id                             │
                       │ completed_at                         │
                       │ actual_minutes (nullable)            │
                       │ notes                                │
                       └──────────────────────────────────────┘

┌──────────────┐       ┌──────────────────────────────────────┐
│  Checklist   │       │          ChecklistChore              │
│──────────────│       │──────────────────────────────────────│
│ id           │◄──────│ checklist_id                         │
│ name         │   1:N │ chore_id ─────────────────────────►  │
│ description  │       └──────────────────────────────────────┘
│ icon         │                         │
└──────────────┘                         │ references
                                         ▼
                                   Actual Chore
                              (shows real status)
```

### Priority Calculation

Priority is auto-assigned based on interval:
- **High**: interval <= 10 days (frequent, important to keep up)
- **Normal**: interval 11-59 days (regular maintenance)
- **Low**: interval >= 60 days (rare, can wait)

### Freshness Calculation

Room freshness is calculated as the average freshness of all chores in that room.

Chore freshness: `100 - (days_since_completed / interval_days * 100)`
- 100% = just completed
- 0% = due now
- Negative = overdue

### Categories

Chores are categorized for filtering:
- `vacuum` - Vacuuming tasks
- `mop` - Mopping/floor washing
- `dust` - Dusting surfaces
- `declutter` - Tidying and organizing
- `clean` - General cleaning (sinks, mirrors, surfaces, etc.)
- `wash` - Washing fabrics (curtains, blankets, rugs)
- `wipe` - Quick wipe-downs (counters, tables)
- `maintain` - Maintenance tasks (smoke detectors, oil floors)

## Directory Structure

```
aether/
├── api/
│   ├── __init__.py
│   ├── app.py                 # FastAPI application
│   ├── dependencies.py        # Dependency injection
│   └── routes/
│       ├── __init__.py
│       ├── rooms.py           # Room endpoints
│       ├── chores.py          # Chore endpoints
│       ├── checklists.py      # Checklist endpoints
│       └── dashboard.py       # Dashboard/briefing endpoints
├── core/
│   ├── __init__.py
│   ├── models.py              # Pydantic models
│   ├── database.py            # SQLite setup and connection
│   └── services/
│       ├── __init__.py
│       ├── room_service.py    # Room business logic
│       ├── chore_service.py   # Chore business logic
│       ├── checklist_service.py
│       └── prioritizer.py     # Smart list generation
├── web/
│   ├── static/
│   │   ├── css/
│   │   ├── js/
│   │   └── icons/
│   ├── templates/
│   │   └── index.html
│   └── manifest.json          # PWA manifest
├── seed/
│   └── data.py                # Initial chore data
├── cli.py                     # CLI entry point
└── config.py                  # Configuration
```

## API Endpoints

### Rooms
- `GET /api/rooms` - List all rooms with freshness
- `GET /api/rooms/{id}` - Get room with all chores
- `PUT /api/rooms/{id}` - Update room (reorder, rename)

### Chores
- `GET /api/chores` - List chores (filter by room, category, status)
- `GET /api/chores/{id}` - Get chore details
- `POST /api/chores` - Create chore
- `PUT /api/chores/{id}` - Update chore
- `POST /api/chores/{id}/complete` - Mark complete
- `DELETE /api/chores/{id}` - Delete chore

### Dashboard
- `GET /api/dashboard` - Home overview (all rooms with freshness)
- `GET /api/dashboard/briefing` - Morning briefing (~15 min of tasks)
- `GET /api/dashboard/quick-clean?minutes=30` - Prioritized list for time budget

### Checklists
- `GET /api/checklists` - List all checklists
- `GET /api/checklists/{id}` - Get checklist with live chore status
- `POST /api/checklists` - Create checklist
- `PUT /api/checklists/{id}` - Update checklist
- `DELETE /api/checklists/{id}` - Delete checklist

## Duration Estimation Flow

1. Each chore has `estimated_minutes` (initial estimate)
2. On completion, optionally ask: "Was this about right? (15 min)"
3. Track `duration_confirmations` count
4. After 2 confirmations, set `duration_confirmed = true`
5. Confirmed durations are used for "I have X minutes" calculations

## Future Considerations

### Planned (Post-MVP)
- Push notifications for morning briefing
- iPhone home screen widget
- Google Calendar export for select reminders
- Home Assistant integration

### Explicitly Out of Scope
- General task management
- Project tracking
- Inventory management
- Multi-user/household
- Daily tasks (bed, laundry, garbage)
