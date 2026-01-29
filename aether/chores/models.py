"""Data models for the house management system."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any
import uuid


class Urgency(Enum):
    """Urgency level for tasks."""
    CRITICAL = 1  # Must do ASAP
    NORMAL = 2    # Regular schedule
    LOW = 3       # Can wait


@dataclass
class ChoreType:
    """A type of chore (vacuum, mop, dust, etc.)."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    icon: str = "🧹"
    description: str = ""

    # Default settings (can be overridden per room)
    default_interval_days: int = 7
    default_duration_minutes: int = 15

    # Metadata
    color: str = "#6B7280"  # Gray default
    active: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "icon": self.icon,
            "description": self.description,
            "default_interval_days": self.default_interval_days,
            "default_duration_minutes": self.default_duration_minutes,
            "color": self.color,
            "active": self.active,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ChoreType":
        return cls(
            id=data["id"],
            name=data["name"],
            icon=data.get("icon", "🧹"),
            description=data.get("description", ""),
            default_interval_days=data.get("default_interval_days", 7),
            default_duration_minutes=data.get("default_duration_minutes", 15),
            color=data.get("color", "#6B7280"),
            active=data.get("active", True),
        )


@dataclass
class Room:
    """A room in the house."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    icon: str = "🏠"
    zone: str = "indoor"  # indoor, outdoor, garage, etc.

    # Display
    color: str = "#6B7280"
    sort_order: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "icon": self.icon,
            "zone": self.zone,
            "color": self.color,
            "sort_order": self.sort_order,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Room":
        return cls(
            id=data["id"],
            name=data["name"],
            icon=data.get("icon", "🏠"),
            zone=data.get("zone", "indoor"),
            color=data.get("color", "#6B7280"),
            sort_order=data.get("sort_order", 0),
        )


@dataclass
class ChoreInstance:
    """A specific chore for a specific room.

    This is the core entity - each room can have different settings
    for the same chore type.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    chore_type_id: str = ""
    room_id: str = ""

    # Per-room settings (override defaults)
    interval_days: int | None = None  # None = use chore type default
    duration_minutes: int | None = None  # None = use chore type default

    # Tracking
    last_completed: datetime | None = None
    completion_count: int = 0
    streak: int = 0

    # Urgency
    urgency: Urgency = Urgency.NORMAL

    # State
    enabled: bool = True

    # Metadata
    notes: str = ""
    created_at: datetime = field(default_factory=datetime.now)

    def get_interval(self, chore_type: ChoreType) -> int:
        """Get interval, using override or default."""
        return self.interval_days if self.interval_days is not None else chore_type.default_interval_days

    def get_duration(self, chore_type: ChoreType) -> int:
        """Get duration, using override or default."""
        return self.duration_minutes if self.duration_minutes is not None else chore_type.default_duration_minutes

    def due_date(self, chore_type: ChoreType) -> datetime:
        """Calculate when this chore is due."""
        if not self.last_completed:
            return datetime.now()  # Never done = due now
        return self.last_completed + timedelta(days=self.get_interval(chore_type))

    def days_until_due(self, chore_type: ChoreType) -> int:
        """Days until due (negative if overdue)."""
        return (self.due_date(chore_type) - datetime.now()).days

    def is_due(self, chore_type: ChoreType, flexibility_days: int = 2) -> bool:
        """Check if chore is due (within flexibility window)."""
        due = self.due_date(chore_type)
        window_start = due - timedelta(days=flexibility_days)
        return datetime.now() >= window_start

    def is_overdue(self, chore_type: ChoreType, flexibility_days: int = 2) -> bool:
        """Check if chore is overdue."""
        due = self.due_date(chore_type)
        window_end = due + timedelta(days=flexibility_days)
        return datetime.now() > window_end

    def urgency_score(self, chore_type: ChoreType) -> float:
        """Calculate urgency score (0-1, higher = more urgent)."""
        days = self.days_until_due(chore_type)

        # Critical chores get a boost
        urgency_multiplier = {
            Urgency.CRITICAL: 1.3,
            Urgency.NORMAL: 1.0,
            Urgency.LOW: 0.7,
        }[self.urgency]

        if days < -5:
            base = 1.0
        elif days < 0:
            base = 0.7 + (abs(days) / 5) * 0.3
        elif days < 3:
            base = 0.4 + ((3 - days) / 3) * 0.3
        else:
            base = max(0.1, 0.4 - (days / 14) * 0.3)

        return min(1.0, base * urgency_multiplier)

    def freshness_percent(self, chore_type: ChoreType) -> int:
        """How 'fresh' is this chore (100% = just done, 0% = very overdue)."""
        if not self.last_completed:
            return 0

        interval = self.get_interval(chore_type)
        days_since = (datetime.now() - self.last_completed).days

        if days_since <= 0:
            return 100
        elif days_since >= interval * 2:
            return 0
        else:
            return max(0, int(100 - (days_since / interval) * 100))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "chore_type_id": self.chore_type_id,
            "room_id": self.room_id,
            "interval_days": self.interval_days,
            "duration_minutes": self.duration_minutes,
            "last_completed": self.last_completed.isoformat() if self.last_completed else None,
            "completion_count": self.completion_count,
            "streak": self.streak,
            "urgency": self.urgency.value,
            "enabled": self.enabled,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ChoreInstance":
        return cls(
            id=data["id"],
            chore_type_id=data["chore_type_id"],
            room_id=data["room_id"],
            interval_days=data.get("interval_days"),
            duration_minutes=data.get("duration_minutes"),
            last_completed=datetime.fromisoformat(data["last_completed"]) if data.get("last_completed") else None,
            completion_count=data.get("completion_count", 0),
            streak=data.get("streak", 0),
            urgency=Urgency(data.get("urgency", 2)),
            enabled=data.get("enabled", True),
            notes=data.get("notes", ""),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
        )


@dataclass
class MaintenanceTask:
    """A home maintenance task (oil floors, change filter, etc.)."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    icon: str = "🔧"

    # Scheduling
    interval_days: int = 365  # Default yearly
    last_completed: datetime | None = None
    next_due: datetime | None = None  # Can override calculated due date

    # Details
    provider: str = ""  # Company/person who does it
    estimated_cost: float | None = None
    notes: str = ""

    # State
    enabled: bool = True

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def due_date(self) -> datetime:
        """Get due date."""
        if self.next_due:
            return self.next_due
        if not self.last_completed:
            return datetime.now()
        return self.last_completed + timedelta(days=self.interval_days)

    @property
    def days_until_due(self) -> int:
        return (self.due_date - datetime.now()).days

    @property
    def is_overdue(self) -> bool:
        return datetime.now() > self.due_date

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "interval_days": self.interval_days,
            "last_completed": self.last_completed.isoformat() if self.last_completed else None,
            "next_due": self.next_due.isoformat() if self.next_due else None,
            "provider": self.provider,
            "estimated_cost": self.estimated_cost,
            "notes": self.notes,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MaintenanceTask":
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            icon=data.get("icon", "🔧"),
            interval_days=data.get("interval_days", 365),
            last_completed=datetime.fromisoformat(data["last_completed"]) if data.get("last_completed") else None,
            next_due=datetime.fromisoformat(data["next_due"]) if data.get("next_due") else None,
            provider=data.get("provider", ""),
            estimated_cost=data.get("estimated_cost"),
            notes=data.get("notes", ""),
            enabled=data.get("enabled", True),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
        )


class ProjectStatus(Enum):
    """Status of a home project."""
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    ON_HOLD = "on_hold"
    DONE = "done"


@dataclass
class ProjectStep:
    """A step in a home project."""
    name: str = ""
    done: bool = False
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "done": self.done, "notes": self.notes}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProjectStep":
        return cls(name=data["name"], done=data.get("done", False), notes=data.get("notes", ""))


@dataclass
class HomeProject:
    """A larger home improvement project."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    icon: str = "🏗️"

    # Status
    status: ProjectStatus = ProjectStatus.PLANNING
    steps: list[ProjectStep] = field(default_factory=list)

    # Budget
    budget: float | None = None
    spent: float = 0.0

    # Timeline
    target_date: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    # Metadata
    notes: str = ""
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def progress_percent(self) -> int:
        """Calculate progress based on completed steps."""
        if not self.steps:
            return 0
        done = sum(1 for s in self.steps if s.done)
        return int((done / len(self.steps)) * 100)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "status": self.status.value,
            "steps": [s.to_dict() for s in self.steps],
            "budget": self.budget,
            "spent": self.spent,
            "target_date": self.target_date.isoformat() if self.target_date else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HomeProject":
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            icon=data.get("icon", "🏗️"),
            status=ProjectStatus(data.get("status", "planning")),
            steps=[ProjectStep.from_dict(s) for s in data.get("steps", [])],
            budget=data.get("budget"),
            spent=data.get("spent", 0.0),
            target_date=datetime.fromisoformat(data["target_date"]) if data.get("target_date") else None,
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            notes=data.get("notes", ""),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
        )


class ChecklistItemImportance(Enum):
    """Importance of an item in a checklist."""
    MUST = "must"      # Must do
    NICE = "nice"      # Nice to have
    OPTIONAL = "optional"  # Only if time


@dataclass
class ChecklistItem:
    """An item in a checklist."""
    chore_instance_id: str = ""
    importance: ChecklistItemImportance = ChecklistItemImportance.MUST

    def to_dict(self) -> dict[str, Any]:
        return {
            "chore_instance_id": self.chore_instance_id,
            "importance": self.importance.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ChecklistItem":
        return cls(
            chore_instance_id=data["chore_instance_id"],
            importance=ChecklistItemImportance(data.get("importance", "must")),
        )


@dataclass
class Checklist:
    """A predefined checklist for a scenario (sleepover, guests, etc.)."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    icon: str = "📋"
    color: str = "#6B7280"

    # Items
    items: list[ChecklistItem] = field(default_factory=list)

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "color": self.color,
            "items": [i.to_dict() for i in self.items],
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Checklist":
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            icon=data.get("icon", "📋"),
            color=data.get("color", "#6B7280"),
            items=[ChecklistItem.from_dict(i) for i in data.get("items", [])],
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
        )
