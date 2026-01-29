# Aether

**House Manager** — Keep your home running smoothly without the mental load.

## Philosophy

Your home shouldn't require a second job to maintain. Aether tracks what needs doing, when, and helps you tackle it in a way that works with ADHD — not against it.

## Core Features

### 🧹 Chores
Regular cleaning tasks organized by **type** and **room**.

- **Filter by chore**: "I want to vacuum today" → see all rooms that need vacuuming
- **Filter by room**: "Let me tackle the bathroom" → see all chores for that room
- **Per-room settings**: Vacuum the living room weekly (20min), bedroom bi-weekly (10min)
- **Smart urgency**: Overdue tasks bubble up, but nothing nags

### 🔧 Home Maintenance
Periodic tasks that keep your home healthy.

- Oil hardwood floors (yearly)
- Change HVAC filter (monthly)
- Schedule boiler service (yearly)
- Clean dryer vent (6 months)

### 🏗️ Home Projects
Larger improvements broken into steps.

- Renovate kitchen
- Fix bathroom tiles
- Install smart thermostat

### 📋 Checklists
Pre-defined scenarios for when life happens.

- **Sleepover**: Fresh sheets, clean bathroom, tidy bedroom
- **Guests visiting**: Vacuum main areas, clean toilet, declutter living room
- **Quick tidy**: The essentials when you have 15 minutes

## Data Model

```
ChoreType (vacuum, mop, dust, declutter...)
    │
    └── ChoreInstance (chore + room combination)
            ├── room: living_room
            ├── duration: 20min (per-room)
            ├── interval: 7 days (per-room)
            ├── last_completed
            └── streak
```

## Quick Start

```bash
pip install -e .
aether serve
# Open http://localhost:8080 on your phone
```

## Design

Mediterranean-inspired palette:
- Warm terracotta accents
- Sandy/cream backgrounds
- Olive and sage greens
- Ocean blue highlights
- Warm, inviting feel

ADHD-friendly:
- Gamification (streaks, scores)
- Satisfying interactions
- Visual progress
- No overwhelming lists

## License

MIT
