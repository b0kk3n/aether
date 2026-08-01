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
    Category,
    CategoryBase,
    CategoryCreate,
    CategoryUpdate,
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
    VacationOverride,
    VacationStatus,
    VacationEndResult,
    VacationLogEntry,
    ChoreEligibility,
    is_vacation_eligible,
)

from .database import init_db, reset_db, get_db, migrate_db

from .services import (
    RoomService,
    ChoreService,
    CategoryService,
    ChecklistService,
    Prioritizer,
    VacationService,
)

__all__ = [
    # Models
    "Room",
    "RoomCreate",
    "RoomWithFreshness",
    "Category",
    "CategoryBase",
    "CategoryCreate",
    "CategoryUpdate",
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
    "VacationOverride",
    "VacationStatus",
    "VacationEndResult",
    "VacationLogEntry",
    "ChoreEligibility",
    "is_vacation_eligible",
    # Database
    "init_db",
    "reset_db",
    "get_db",
    "migrate_db",
    # Services
    "RoomService",
    "ChoreService",
    "CategoryService",
    "ChecklistService",
    "Prioritizer",
    "VacationService",
]
