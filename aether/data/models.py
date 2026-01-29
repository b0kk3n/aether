"""Data models for Aether."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any
import uuid


class TaskStatus(Enum):
    """Task status."""

    INBOX = "inbox"  # Just captured, not processed
    TODO = "todo"  # Ready to work on
    IN_PROGRESS = "in_progress"  # Currently working
    WAITING = "waiting"  # Blocked on something/someone
    DONE = "done"  # Completed
    CANCELLED = "cancelled"  # Not doing


class TaskPriority(Enum):
    """Task priority - based on urgency and importance."""

    CRITICAL = 1  # Must do today, high impact
    HIGH = 2  # Important, do soon
    MEDIUM = 3  # Should do, flexible timing
    LOW = 4  # Nice to do, no pressure
    SOMEDAY = 5  # Maybe eventually


class EnergyLevel(Enum):
    """Energy/motivation level - affects task recommendations."""

    PEAK = "peak"  # Creative work, complex decisions
    GOOD = "good"  # Normal productive work
    LOW = "low"  # Admin, routine tasks
    DEPLETED = "depleted"  # Only essential, easy wins


class TaskType(Enum):
    """Type of task - affects when/how to surface."""

    CREATIVE = "creative"  # Needs peak energy
    ADMIN = "admin"  # Good for low energy
    ROUTINE = "routine"  # Autopilot-friendly
    DEEP_WORK = "deep_work"  # Needs focus blocks
    QUICK_WIN = "quick_win"  # Under 15 min
    ERRAND = "errand"  # Location-dependent
    COMMUNICATION = "communication"  # Emails, calls, messages


class ReminderType(Enum):
    """Reminder type - affects timing strategy."""

    MEDICATION = "medication"  # Adaptive window, critical
    MEETING_PREP = "meeting_prep"  # Before calendar events
    DEADLINE = "deadline"  # Escalating urgency
    RECURRING = "recurring"  # Regular intervals
    CONTEXTUAL = "contextual"  # Triggered by conditions
    FOLLOW_UP = "follow_up"  # After events/tasks


@dataclass
class Task:
    """A task or action item."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str = ""
    description: str = ""
    status: TaskStatus = TaskStatus.INBOX
    priority: TaskPriority = TaskPriority.MEDIUM
    task_type: TaskType = TaskType.ROUTINE

    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    due_date: datetime | None = None
    scheduled_for: datetime | None = None  # When to work on it
    completed_at: datetime | None = None

    # Effort estimation
    estimated_minutes: int | None = None
    actual_minutes: int | None = None
    energy_required: EnergyLevel = EnergyLevel.GOOD

    # Organization
    project: str | None = None
    tags: list[str] = field(default_factory=list)
    area: str | None = None  # work, home, training, etc.

    # Dependencies
    blocked_by: list[str] = field(default_factory=list)  # Task IDs
    blocks: list[str] = field(default_factory=list)  # Task IDs

    # Recurrence
    recurrence: str | None = None  # Cron expression
    recurrence_parent: str | None = None  # Original task ID if recurring

    # Context
    notes: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_overdue(self) -> bool:
        """Check if task is overdue."""
        if not self.due_date or self.status in (TaskStatus.DONE, TaskStatus.CANCELLED):
            return False
        return datetime.now() > self.due_date

    @property
    def days_until_due(self) -> int | None:
        """Days until due date."""
        if not self.due_date:
            return None
        delta = self.due_date - datetime.now()
        return delta.days

    @property
    def is_blocked(self) -> bool:
        """Check if task is blocked."""
        return len(self.blocked_by) > 0 or self.status == TaskStatus.WAITING

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "priority": self.priority.value,
            "task_type": self.task_type.value,
            "created_at": self.created_at.isoformat(),
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "scheduled_for": self.scheduled_for.isoformat() if self.scheduled_for else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "estimated_minutes": self.estimated_minutes,
            "actual_minutes": self.actual_minutes,
            "energy_required": self.energy_required.value,
            "project": self.project,
            "tags": self.tags,
            "area": self.area,
            "blocked_by": self.blocked_by,
            "blocks": self.blocks,
            "recurrence": self.recurrence,
            "recurrence_parent": self.recurrence_parent,
            "notes": self.notes,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Task":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            title=data["title"],
            description=data.get("description", ""),
            status=TaskStatus(data["status"]),
            priority=TaskPriority(data["priority"]),
            task_type=TaskType(data.get("task_type", "routine")),
            created_at=datetime.fromisoformat(data["created_at"]),
            due_date=datetime.fromisoformat(data["due_date"]) if data.get("due_date") else None,
            scheduled_for=datetime.fromisoformat(data["scheduled_for"]) if data.get("scheduled_for") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            estimated_minutes=data.get("estimated_minutes"),
            actual_minutes=data.get("actual_minutes"),
            energy_required=EnergyLevel(data.get("energy_required", "good")),
            project=data.get("project"),
            tags=data.get("tags", []),
            area=data.get("area"),
            blocked_by=data.get("blocked_by", []),
            blocks=data.get("blocks", []),
            recurrence=data.get("recurrence"),
            recurrence_parent=data.get("recurrence_parent"),
            notes=data.get("notes", ""),
            metadata=data.get("metadata", {}),
        )


@dataclass
class Reminder:
    """A reminder with adaptive timing."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str = ""
    description: str = ""
    reminder_type: ReminderType = ReminderType.RECURRING

    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    trigger_at: datetime | None = None  # Base trigger time
    window_start: datetime | None = None  # Earliest to remind
    window_end: datetime | None = None  # Latest to remind (after = missed)
    last_triggered: datetime | None = None

    # Recurrence
    recurrence: str | None = None  # Cron expression

    # Adaptive timing
    adaptive: bool = False  # Adjust based on patterns
    preferred_energy: EnergyLevel | None = None  # When to trigger
    snooze_count: int = 0
    max_snoozes: int = 3

    # Linking
    linked_task: str | None = None  # Task ID
    linked_event: str | None = None  # Event ID

    # State
    active: bool = True
    completed: bool = False

    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "reminder_type": self.reminder_type.value,
            "created_at": self.created_at.isoformat(),
            "trigger_at": self.trigger_at.isoformat() if self.trigger_at else None,
            "window_start": self.window_start.isoformat() if self.window_start else None,
            "window_end": self.window_end.isoformat() if self.window_end else None,
            "last_triggered": self.last_triggered.isoformat() if self.last_triggered else None,
            "recurrence": self.recurrence,
            "adaptive": self.adaptive,
            "preferred_energy": self.preferred_energy.value if self.preferred_energy else None,
            "snooze_count": self.snooze_count,
            "max_snoozes": self.max_snoozes,
            "linked_task": self.linked_task,
            "linked_event": self.linked_event,
            "active": self.active,
            "completed": self.completed,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Reminder":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            title=data["title"],
            description=data.get("description", ""),
            reminder_type=ReminderType(data["reminder_type"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            trigger_at=datetime.fromisoformat(data["trigger_at"]) if data.get("trigger_at") else None,
            window_start=datetime.fromisoformat(data["window_start"]) if data.get("window_start") else None,
            window_end=datetime.fromisoformat(data["window_end"]) if data.get("window_end") else None,
            last_triggered=datetime.fromisoformat(data["last_triggered"]) if data.get("last_triggered") else None,
            recurrence=data.get("recurrence"),
            adaptive=data.get("adaptive", False),
            preferred_energy=EnergyLevel(data["preferred_energy"]) if data.get("preferred_energy") else None,
            snooze_count=data.get("snooze_count", 0),
            max_snoozes=data.get("max_snoozes", 3),
            linked_task=data.get("linked_task"),
            linked_event=data.get("linked_event"),
            active=data.get("active", True),
            completed=data.get("completed", False),
            metadata=data.get("metadata", {}),
        )


@dataclass
class Event:
    """Calendar event or scheduled block."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str = ""
    description: str = ""

    # Timing
    start: datetime = field(default_factory=datetime.now)
    end: datetime | None = None
    all_day: bool = False

    # Categorization
    event_type: str = "meeting"  # meeting, focus, personal, etc.
    area: str | None = None

    # Prep requirements
    prep_time_minutes: int = 0
    prep_tasks: list[str] = field(default_factory=list)  # Task IDs

    # Recurrence
    recurrence: str | None = None

    # External linking
    external_id: str | None = None  # Calendar provider ID
    external_source: str | None = None  # google, outlook, etc.

    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_minutes(self) -> int:
        """Get event duration in minutes."""
        if not self.end:
            return 60  # Default 1 hour
        return int((self.end - self.start).total_seconds() / 60)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "start": self.start.isoformat(),
            "end": self.end.isoformat() if self.end else None,
            "all_day": self.all_day,
            "event_type": self.event_type,
            "area": self.area,
            "prep_time_minutes": self.prep_time_minutes,
            "prep_tasks": self.prep_tasks,
            "recurrence": self.recurrence,
            "external_id": self.external_id,
            "external_source": self.external_source,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Event":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            title=data["title"],
            description=data.get("description", ""),
            start=datetime.fromisoformat(data["start"]),
            end=datetime.fromisoformat(data["end"]) if data.get("end") else None,
            all_day=data.get("all_day", False),
            event_type=data.get("event_type", "meeting"),
            area=data.get("area"),
            prep_time_minutes=data.get("prep_time_minutes", 0),
            prep_tasks=data.get("prep_tasks", []),
            recurrence=data.get("recurrence"),
            external_id=data.get("external_id"),
            external_source=data.get("external_source"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class Pattern:
    """Learned pattern from user behavior."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    pattern_type: str = ""  # energy, completion, preference, etc.

    # Pattern data
    description: str = ""
    conditions: dict[str, Any] = field(default_factory=dict)  # When pattern applies
    observations: list[dict[str, Any]] = field(default_factory=list)  # Raw data points

    # Confidence
    confidence: float = 0.0  # 0-1, how reliable
    sample_size: int = 0

    # Timing
    first_observed: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)

    # State
    active: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "pattern_type": self.pattern_type,
            "description": self.description,
            "conditions": self.conditions,
            "observations": self.observations,
            "confidence": self.confidence,
            "sample_size": self.sample_size,
            "first_observed": self.first_observed.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "active": self.active,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Pattern":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            pattern_type=data["pattern_type"],
            description=data.get("description", ""),
            conditions=data.get("conditions", {}),
            observations=data.get("observations", []),
            confidence=data.get("confidence", 0.0),
            sample_size=data.get("sample_size", 0),
            first_observed=datetime.fromisoformat(data["first_observed"]),
            last_updated=datetime.fromisoformat(data["last_updated"]),
            active=data.get("active", True),
        )


@dataclass
class Memory:
    """Long-term memory item - preferences, decisions, context."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    memory_type: str = ""  # preference, decision, fact, context

    # Content
    key: str = ""  # Lookup key
    value: Any = None  # The memory content
    context: str = ""  # Why/how this was learned

    # Source
    source: str = ""  # How it was captured
    confidence: float = 1.0  # How certain

    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0

    # Relationships
    related_memories: list[str] = field(default_factory=list)  # Memory IDs
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "memory_type": self.memory_type,
            "key": self.key,
            "value": self.value,
            "context": self.context,
            "source": self.source,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "access_count": self.access_count,
            "related_memories": self.related_memories,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Memory":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            memory_type=data["memory_type"],
            key=data["key"],
            value=data["value"],
            context=data.get("context", ""),
            source=data.get("source", ""),
            confidence=data.get("confidence", 1.0),
            created_at=datetime.fromisoformat(data["created_at"]),
            last_accessed=datetime.fromisoformat(data["last_accessed"]),
            access_count=data.get("access_count", 0),
            related_memories=data.get("related_memories", []),
            tags=data.get("tags", []),
        )


@dataclass
class Context:
    """Current context snapshot - energy, location, time blocks."""

    timestamp: datetime = field(default_factory=datetime.now)

    # Energy state
    energy_level: EnergyLevel = EnergyLevel.GOOD
    energy_note: str = ""

    # Time context
    day_of_week: int = field(default_factory=lambda: datetime.now().weekday())
    time_of_day: str = ""  # morning, afternoon, evening, night
    available_minutes: int | None = None  # Until next commitment

    # Location/situation
    location: str | None = None  # home, office, mobile
    focus_mode: bool = False  # In deep work mode

    # Recent activity
    last_task_completed: str | None = None
    last_break: datetime | None = None
    tasks_completed_today: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "energy_level": self.energy_level.value,
            "energy_note": self.energy_note,
            "day_of_week": self.day_of_week,
            "time_of_day": self.time_of_day,
            "available_minutes": self.available_minutes,
            "location": self.location,
            "focus_mode": self.focus_mode,
            "last_task_completed": self.last_task_completed,
            "last_break": self.last_break.isoformat() if self.last_break else None,
            "tasks_completed_today": self.tasks_completed_today,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Context":
        """Create from dictionary."""
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            energy_level=EnergyLevel(data["energy_level"]),
            energy_note=data.get("energy_note", ""),
            day_of_week=data.get("day_of_week", 0),
            time_of_day=data.get("time_of_day", ""),
            available_minutes=data.get("available_minutes"),
            location=data.get("location"),
            focus_mode=data.get("focus_mode", False),
            last_task_completed=data.get("last_task_completed"),
            last_break=datetime.fromisoformat(data["last_break"]) if data.get("last_break") else None,
            tasks_completed_today=data.get("tasks_completed_today", 0),
        )
