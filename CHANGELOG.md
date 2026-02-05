# Changelog

All notable changes to Aether will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2026-02-05

Complete architecture redesign focused on Home Concierge functionality.

### Added
- **Documentation**
  - CHANGELOG.md for tracking changes
  - docs/VISION.md defining philosophy and goals
  - docs/ARCHITECTURE.md with technical details
  - Updated README.md with new focus

- **Core Models** (`aether/core/models.py`)
  - Room: Physical spaces with icons and ordering
  - Chore: Recurring tasks with intervals, categories, priorities
  - CompletionLog: History tracking for analysis
  - Checklist: Scenario-based views referencing real chores
  - Dashboard, Briefing, QuickCleanList response models

- **Database** (`aether/core/database.py`)
  - SQLite schema with rooms, chores, completion_logs, checklists
  - Migration support for future schema changes
  - Foreign key constraints and indexes

- **Services** (`aether/core/services/`)
  - RoomService: Room CRUD, freshness calculations
  - ChoreService: Chore management, completion with streak tracking
  - ChecklistService: Checklist management with live chore status
  - Prioritizer: Smart list generation, briefings, quick-clean mode

- **REST API** (`aether/api/`)
  - `/api/rooms` - Room endpoints with freshness
  - `/api/chores` - Chore CRUD, completion, filtering
  - `/api/checklists` - Checklist management
  - `/api/dashboard` - Overview, briefing, quick-clean

- **Seed Data** (`aether/seed/`)
  - 10 rooms with icons
  - 77 chores (69 room-specific + 8 house-wide/maintenance)
  - 2 checklists (Visitors, Sleepover)
  - Duration estimates for all chores

- **CLI Commands**
  - `aether serve` - Start web server
  - `aether seed` - Populate database
  - `aether dashboard` - Home overview
  - `aether briefing` - Morning briefing
  - `aether quick <minutes>` - Prioritized list
  - `aether done <id>` - Mark complete
  - `aether rooms`, `aether overdue`, `aether checklists`

- **Features**
  - Auto-priority based on interval (high/normal/low)
  - Freshness percentage per chore and room
  - Streak tracking with 2-day grace period
  - Duration estimation with user confirmation flow
  - "I have X minutes" smart prioritization
  - Checklists showing live chore status

### Changed
- Complete focus shift from "Personal Command Center" to "Home Concierge"
- Simplified data model: direct Chore entity instead of ChoreType + ChoreInstance
- Version bump to 0.3.0

### Removed
- Task, Reminder, Event, Pattern, Memory, Context models
- Engine, briefing generator, pattern learning modules
- Todoist integration
- Complex urgency calculations with multiple factors
- All "personal assistant" functionality

## [0.2.0] - Previous Version

Legacy version with dual "House Manager" + "Personal Command Center" architecture.
This version is being replaced with a focused Home Concierge approach.
