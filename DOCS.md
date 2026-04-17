# Aether

Home Concierge – your home, managed. Your mind, free.

Aether tracks household chores by room, suggests what to do based on how long
you have, and keeps freshness scores so nothing gets forgotten.

## Setup

1. Install the add-on and start it.
2. Open the **Aether** sidebar panel that appears in Home Assistant.
3. Aether is accessible from anywhere you can reach Home Assistant, including
   via Nabu Casa remote access.

## Home Assistant sensors and services

Install the Aether custom component from the `homeassistant/custom_components/`
folder in the repository to get HA sensors and services:

**Sensors** (update every 5 minutes):
- `sensor.aether_overdue_chores` — number of overdue chores
- `sensor.aether_chores_due_soon` — chores due in the next 3 days

Add this to your `configuration.yaml` to connect the component to the add-on:

```yaml
aether:
  host: aether
  port: 8099
```

**Services**:
- `aether.complete_chore` — mark a chore complete by ID
- `aether.what_now` — get suggestions for available time (fires an `aether_what_now` event)

## Configuration

| Option | Default | Description |
|---|---|---|
| `log_level` | `info` | Logging verbosity: `debug`, `info`, `warning`, `error` |

## Data persistence

Aether stores its database at `/data/aether.db` inside the add-on container,
which is mapped to persistent storage by the HA supervisor. Your data survives
add-on restarts and updates.

## Notes

- Voice (Whisper) and Google Calendar integrations are not available in the
  add-on — they require optional dependencies that are not Pi-compatible.
- The PWA "Add to Home Screen" feature works but the saved shortcut may stop
  working after an add-on restart, because HA's ingress token changes. Use the
  HA sidebar panel as the primary access point instead.
