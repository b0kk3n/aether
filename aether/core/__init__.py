"""Core module for Aether Home Concierge.

Contains:
- models: Data models (Room, Chore, Checklist, etc.)
- database: SQLite setup and connection
- services: Business logic (RoomService, ChoreService, etc.)
"""

from .models import (
    Room,
    RoomCreate,
    RoomWithFreshness,
    Chore,
    ChoreCreate,
    ChoreUpdate,
    ChoreWithRoom,
    ChoreStatus,
    CompletionLog,
    CompletionLogCreate,
    Checklist,
    ChecklistCreate,
    ChecklistUpdate,
    ChecklistWithChores,
    Dashboard,
    DashboardRoom,
    Briefing,
    QuickCleanList,
    Priority,
    Category,
)

from .database import init_db, reset_db, get_db, migrate_db

from .services import (
    RoomService,
    ChoreService,
    ChecklistService,
    Prioritizer,
)

__all__ = [
    # Models
    "Room",
    "RoomCreate",
    "RoomWithFreshness",
    "Chore",
    "ChoreCreate",
    "ChoreUpdate",
    "ChoreWithRoom",
    "ChoreStatus",
    "CompletionLog",
    "CompletionLogCreate",
    "Checklist",
    "ChecklistCreate",
    "ChecklistUpdate",
    "ChecklistWithChores",
    "Dashboard",
    "DashboardRoom",
    "Briefing",
    "QuickCleanList",
    "Priority",
    "Category",
    # Database
    "init_db",
    "reset_db",
    "get_db",
    "migrate_db",
    # Services
    "RoomService",
    "ChoreService",
    "ChecklistService",
    "Prioritizer",
]
