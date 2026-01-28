# Aether

Adaptive personal assistant designed for ADHD-friendly task and life management.

## Philosophy

Aether reduces cognitive load by surfacing the right thing at the right time, adapting to your energy and motivation levels rather than rigid schedules.

**Core principles:**
- Proactive, not reactive - surfaces what matters before you ask
- Energy-aware - matches tasks to your current capacity
- Pattern-learning - gets better the more you use it
- Zero fluff - fast, structured responses

## Installation

```bash
# Install from source
pip install -e .

# Or with AI features (optional)
pip install -e ".[ai]"
```

## Quick Start

```bash
# Add tasks quickly
aether add "Buy groceries #shopping @errands"
aether add "Review PR !high due:tomorrow @work est:30m"

# See what to do next (context-aware)
aether next

# Morning briefing
aether morning

# Set your energy level
aether energy low

# Quick wins for low energy moments
aether quick

# Mark complete
aether done <task-id>
```

## Task Syntax

Quick add supports shortcuts:
- `#tag` - Add tags
- `@area` - Set area (work, home, training, etc.)
- `+project` - Set project
- `!priority` - Set priority (critical, high, med, low, someday)
- `due:DATE` - Set due date (today, tomorrow, mon-sun, YYYY-MM-DD, 3d)
- `est:TIME` - Set time estimate (30m, 2h)
- `type:TYPE` - Set task type (creative, admin, routine, deep, quick, errand, comm)

## Commands

### Tasks

| Command | Description |
|---------|-------------|
| `add <text>` | Quick add a task |
| `done <id>` | Complete a task |
| `start <id>` | Start working on a task |
| `block <id>` | Mark task as blocked |
| `unblock <id>` | Unblock a task |
| `list` | List all active tasks |
| `inbox` | Show inbox items |
| `promote <id>` | Move from inbox to TODO |
| `next` | Get recommended next tasks |
| `quick` | Get quick win tasks |
| `today` | Tasks due today |
| `overdue` | Show overdue tasks |
| `blocked` | Show blocked tasks |

### Context & Energy

| Command | Description |
|---------|-------------|
| `energy <level>` | Set energy (peak/good/low/depleted) |
| `focus` | Toggle focus mode |
| `break` | Record taking a break |

### Briefings

| Command | Description |
|---------|-------------|
| `morning` | Daily briefing |
| `weekly` | Weekly review |
| (no command) | Quick status |

### Reminders

| Command | Description |
|---------|-------------|
| `remind <text> --at <time>` | Add reminder |
| `med <name> --at <time>` | Medication reminder |
| `reminders` | Show upcoming |
| `snooze <id>` | Snooze reminder |
| `ack <id>` | Acknowledge reminder |

### Memory

| Command | Description |
|---------|-------------|
| `remember <key> <value>` | Store a memory |
| `recall <key>` | Retrieve a memory |

### Analytics

| Command | Description |
|---------|-------------|
| `workload` | Analyze current workload |
| `productivity` | Today's productivity score |
| `stats` | Overall statistics |

### Organization

| Command | Description |
|---------|-------------|
| `areas` | List all areas |
| `projects` | List all projects |
| `show <name>` | Show tasks for area/project |

## Energy Levels

Aether adapts recommendations to your energy:

- **Peak** ⚡ - Creative work, complex decisions, deep focus
- **Good** ✨ - Normal productive work
- **Low** 🔋 - Admin tasks, routine work
- **Depleted** 😴 - Only essentials, quick wins

Set your energy and Aether will prioritize matching tasks:

```bash
aether energy peak  # Ready for creative work
aether energy low   # Show me admin tasks
```

## Adaptive Reminders

Medication and other critical reminders use adaptive timing:
- Set a target time and window
- Aether triggers when you're in a good state within the window
- Falls back to hard trigger if approaching window end

```bash
# Medication at 9am with 2-hour window, repeating daily
aether med "Adderall" --at 09:00 --window 2 --daily
```

## Task Types

| Type | Best Energy | Description |
|------|-------------|-------------|
| creative | Peak | New ideas, design, writing |
| deep_work | Peak | Complex problem-solving |
| admin | Low | Email, filing, updates |
| routine | Low | Regular maintenance |
| quick_win | Any | Under 15 minutes |
| errand | Good | Location-dependent |
| communication | Good | Calls, messages |

## Pattern Learning

Aether learns from your behavior:
- When you complete different task types
- Your energy patterns throughout the day
- How accurate your time estimates are
- Your most productive periods

This improves recommendations over time without manual configuration.

## Data Storage

All data is stored locally in `~/.aether/`:
- `aether.db` - SQLite database
- `config.yaml` - User configuration (optional)

## Configuration

Copy `config/default.yaml` to `~/.aether/config.yaml` and customize.

## Python API

```python
from aether import Aether

ae = Aether()

# Add task
task = ae.add("Review PR @work !high due:tomorrow")

# Get recommendations
for task, score, reasoning in ae.next(5):
    print(f"{task.title}: {score}")

# Set energy
ae.energy("peak")

# Morning briefing
briefing = ae.morning()
```

## License

MIT
