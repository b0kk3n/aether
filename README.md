# Aether

Your personal command center. One interface for everything that needs doing.

## What Aether Does

Aether sits on top of your existing tools (Todoist, Google Calendar, Home Assistant) and provides:

- **Morning Briefing** - What matters today, what's at risk
- **"I have 20 minutes"** - Instant task recommendations for available time
- **Voice Capture** - Add tasks, notes, or queries by voice
- **Smart Chores** - Interval-based tasks that surface when due (like Kaji)
- **Project Tracking** - Multi-step projects with progress
- **Home Integration** - Triggers and context from Home Assistant

## Philosophy

**The system manages itself.** You dump everything in, Aether organizes and surfaces what matters. No filing, no tagging marathons, no system maintenance.

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                    Aether Core                        │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐    │
│  │  Briefings  │ │  Scheduler  │ │   Context   │    │
│  └─────────────┘ └─────────────┘ └─────────────┘    │
├──────────────────────────────────────────────────────┤
│                   Integrations                        │
│  ┌─────────┐ ┌──────────┐ ┌────────────────────┐    │
│  │ Todoist │ │ Google   │ │  Home Assistant    │    │
│  │  Sync   │ │ Calendar │ │  Sensors/Triggers  │    │
│  └─────────┘ └──────────┘ └────────────────────┘    │
├──────────────────────────────────────────────────────┤
│                    Interfaces                         │
│  ┌─────────┐ ┌──────────┐ ┌────────────────────┐    │
│  │ Mobile  │ │    HA    │ │   Voice/Whisper    │    │
│  │   PWA   │ │Dashboard │ │                    │    │
│  └─────────┘ └──────────┘ └────────────────────┘    │
└──────────────────────────────────────────────────────┘
```

## Quick Start

```bash
# Install
pip install -e .

# Configure integrations
aether setup

# Start server
aether serve

# Access UI at http://localhost:8080
# Or add to Home Assistant
```

## Configuration

Create `~/.aether/config.yaml`:

```yaml
# Todoist integration
todoist:
  api_token: "your_token_here"
  sync_interval: 300  # seconds

# Google Calendar
google:
  credentials_file: "~/.aether/google_credentials.json"
  calendars:
    - primary
    - family

# Home Assistant
homeassistant:
  url: "http://homeassistant.local:8123"
  token: "your_long_lived_token"

# Voice transcription
voice:
  provider: "whisper"  # or "google", "azure"
  language: "en"

# Server
server:
  host: "0.0.0.0"
  port: 8080
```

## Features

### Morning Briefing
Start your day knowing exactly what matters:
- Calendar events with prep time
- Birthdays and social reminders
- Overdue and due-today tasks
- Chores that need attention
- Weather and commute (via HA)

### Time-Based Recommendations
"I have 20 minutes" → Get tasks that fit:
- Considers energy level
- Accounts for location (home vs out)
- Prioritizes overdue items
- Suggests quick wins when time is short

### Smart Chores (Kaji-style)
Define once, forget about tracking:
```yaml
chores:
  - name: "Vacuum living room"
    interval: 7  # days
    duration: 15  # minutes
    room: living_room

  - name: "Clean bathroom"
    interval: 14
    duration: 30
    room: bathroom
```

Chores surface automatically when due. Complete them for satisfaction.

### Voice Input
Speak naturally:
- "Add buy milk to groceries"
- "Remind me to call mom on Sunday"
- "What do I need to do today?"
- "I finished vacuuming"

### Home Assistant Integration

**Dashboard Card:**
```yaml
type: custom:aether-card
show_briefing: true
show_tasks: 5
show_chores: true
```

**Automations:**
```yaml
automation:
  - alias: "Morning Briefing"
    trigger:
      - platform: time
        at: "07:00:00"
    action:
      - service: aether.speak_briefing
        data:
          target: media_player.bedroom_speaker
```

**Sensors:**
- `sensor.aether_tasks_due_today`
- `sensor.aether_overdue_count`
- `sensor.aether_next_event`
- `sensor.aether_chores_due`

## Mobile PWA

Access via browser, install as app:
- Works offline (syncs when connected)
- Voice input button
- Quick capture
- Swipe to complete
- Pull to refresh briefing

## The Anti-Entropy System

Aether prevents system collapse through:

1. **Auto-organization** - Tasks are categorized by context, not manual folders
2. **Decay prevention** - Nothing gets buried; old tasks surface with increasing urgency
3. **Smart defaults** - New items get sensible due dates and priorities
4. **Weekly review prompts** - Gentle nudges to process accumulated items
5. **Project health** - Stalled projects get flagged

## License

MIT
