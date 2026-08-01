"""Core data models for Aether Home Concierge.

Simplified model focused purely on home management:
- Room: A physical space in the home
- Chore: A recurring task (room-specific or house-wide)
- CompletionLog: History of completed chores
- Checklist: A scenario-based view of chores
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
import uuid


def generate_id() -> str:
    """Generate a short unique ID."""
    return str(uuid.uuid4())[:8]


class Priority(str, Enum):
    """Chore priority level.

    Auto-calculated based on interval:
    - HIGH: interval <= 10 days
    - NORMAL: interval 11-59 days
    - LOW: interval >= 60 days
    """
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class VacationOverride(str, Enum):
    """Per-chore override of the category-level vacation-pause default."""
    FORCE_PAUSE = "force_pause"
    FORCE_EXCLUDE = "force_exclude"


def is_vacation_eligible(category_pausable_default: bool, override) -> bool:
    """Whether a chore's countdown pauses during vacation mode.

    A per-chore override always wins over the category's own
    is_vacation_pausable_default setting.
    """
    if override == VacationOverride.FORCE_EXCLUDE:
        return False
    if override == VacationOverride.FORCE_PAUSE:
        return True
    return bool(category_pausable_default)


def priority_from_interval(interval_days: int) -> Priority:
    """Calculate priority based on interval.

    - HIGH: <= 10 days (frequent, important to keep up)
    - NORMAL: 11-59 days (regular maintenance)
    - LOW: >= 60 days (rare, can wait)
    """
    if interval_days <= 10:
        return Priority.HIGH
    elif interval_days >= 60:
        return Priority.LOW
    return Priority.NORMAL


# =============================================================================
# Room
# =============================================================================

class RoomBase(BaseModel):
    """Base room model for creation/updates."""
    name: str
    icon: str = "home"
    sort_order: int = 0


class RoomCreate(RoomBase):
    """Model for creating a room."""
    pass


class Room(RoomBase):
    """A room in the home."""
    id: str = Field(default_factory=generate_id)
    is_paused: bool = False
    paused_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        from_attributes = True


class RoomWithFreshness(Room):
    """Room with calculated freshness score."""
    freshness_percent: int = 100
    chore_count: int = 0
    overdue_count: int = 0


# =============================================================================
# Category
# =============================================================================

class CategoryBase(BaseModel):
    """Base category model for creation/updates."""
    name: str
    icon: str = "tag"
    sort_order: int = 0
    is_vacation_pausable_default: bool = True


class CategoryCreate(CategoryBase):
    """Model for creating a category."""
    pass


class CategoryUpdate(BaseModel):
    """Model for updating a category."""
    name: Optional[str] = None
    icon: Optional[str] = None
    sort_order: Optional[int] = None
    is_vacation_pausable_default: Optional[bool] = None


class Category(CategoryBase):
    """A user-editable chore category."""
    id: str = Field(default_factory=generate_id)
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        from_attributes = True


# =============================================================================
# Chore
# =============================================================================

class ChoreBase(BaseModel):
    """Base chore model for creation/updates."""
    name: str
    room_id: Optional[str] = None  # None = house-wide
    interval_days: int
    estimated_minutes: int = 15
    category_id: str
    notes: str = ""
    is_active: bool = True
    vacation_override: Optional[VacationOverride] = None


class ChoreCreate(ChoreBase):
    """Model for creating a chore."""
    pass


class ChoreUpdate(BaseModel):
    """Model for updating a chore."""
    name: Optional[str] = None
    room_id: Optional[str] = None
    interval_days: Optional[int] = None
    estimated_minutes: Optional[int] = None
    category_id: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None
    vacation_override: Optional[VacationOverride] = None


class Chore(ChoreBase):
    """A recurring chore.

    Can be room-specific (room_id set) or house-wide (room_id is None).
    Priority is auto-calculated from interval_days.
    """
    id: str = Field(default_factory=generate_id)
    last_completed_at: Optional[datetime] = None
    streak: int = 0
    completion_count: int = 0

    # Duration estimation tracking
    duration_confirmed: bool = False
    duration_confirmations: int = 0

    # Interval tracking
    interval_confirmed: bool = False
    interval_confirmations: int = 0

    # Accumulated + in-progress paused days from vacation mode AND room pause
    # combined (from chores_effective view's effective_paused_days column).
    vacation_paused_days: float = 0.0

    # Category display info, populated from the chores_effective view's join.
    category_pausable_default: bool = True
    category_name: Optional[str] = None
    category_icon: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        from_attributes = True

    @property
    def priority(self) -> Priority:
        """Auto-calculate priority from interval."""
        return priority_from_interval(self.interval_days)

    @property
    def vacation_eligible(self) -> bool:
        """Whether this chore's countdown pauses during vacation mode."""
        return is_vacation_eligible(self.category_pausable_default, self.vacation_override)

    @property
    def effective_interval_days(self) -> float:
        """interval_days adjusted for accumulated + in-progress vacation pause."""
        return self.interval_days + self.vacation_paused_days

    @property
    def due_date(self) -> datetime:
        """When this chore is due."""
        reference = self.last_completed_at or self.created_at
        return reference + timedelta(days=self.effective_interval_days)

    @property
    def days_until_due(self) -> int:
        """Days until due (negative if overdue)."""
        return (self.due_date - datetime.now()).days

    @property
    def is_overdue(self) -> bool:
        """Check if chore is past due date."""
        return datetime.now() > self.due_date

    @property
    def freshness_percent(self) -> int:
        """How fresh is this chore (100 = just done/new, 0 = overdue).

        Stays at 100% for the first 50% of the interval, then decays linearly
        to 0% over the final 50%. Uses created_at as the reference point for
        chores that have never been completed.
        """
        reference = self.last_completed_at or self.created_at
        days_since = (datetime.now() - reference).days
        interval_days = self.effective_interval_days

        if days_since <= 0:
            return 100
        if days_since >= interval_days:
            return 0

        days_until = interval_days - days_since
        decay_window = interval_days * 0.5

        if days_until > decay_window:
            return 100

        return int((days_until / decay_window) * 100)

    @property
    def urgency_score(self) -> float:
        """Calculate urgency score (0-1, higher = more urgent).

        Used for prioritizing "I have X minutes" lists.
        Combines overdue status with priority weighting.
        """
        priority_weight = {
            Priority.HIGH: 1.2,
            Priority.NORMAL: 1.0,
            Priority.LOW: 0.8,
        }[self.priority]

        days = self.days_until_due

        if days < -7:
            # Very overdue
            base = 1.0
        elif days < 0:
            # Overdue
            base = 0.7 + (min(abs(days), 7) / 7) * 0.3
        elif days < 3:
            # Due soon
            base = 0.4 + ((3 - days) / 3) * 0.3
        else:
            # Not due yet
            base = max(0.1, 0.4 - (min(days, 14) / 14) * 0.3)

        return min(1.0, base * priority_weight)


class ChoreWithRoom(Chore):
    """Chore with room details included."""
    room: Optional[Room] = None


class ChoreStatus(BaseModel):
    """Chore status for display."""
    id: str
    name: str
    room_name: Optional[str]
    priority: Priority
    category: str  # category display name
    category_id: str
    category_icon: Optional[str] = None
    days_until_due: int
    freshness_percent: int
    is_overdue: bool
    last_completed_at: Optional[datetime]
    estimated_minutes: int
    streak: int
    vacation_eligible: bool = True


# =============================================================================
# Completion Log
# =============================================================================

class CompletionLogCreate(BaseModel):
    """Model for logging a completion."""
    chore_id: str
    actual_minutes: Optional[int] = None
    notes: str = ""
    duration_was_accurate: Optional[bool] = None  # User feedback on estimate


class CompletionLog(BaseModel):
    """A record of a chore completion."""
    id: str = Field(default_factory=generate_id)
    chore_id: str
    completed_at: datetime = Field(default_factory=datetime.now)
    actual_minutes: Optional[int] = None
    notes: str = ""

    class Config:
        from_attributes = True


# =============================================================================
# Checklist
# =============================================================================

class ChecklistBase(BaseModel):
    """Base checklist model."""
    name: str
    description: str = ""
    icon: str = "clipboard"
    overdue_count: int = 0
    total_minutes: int = 0
    remaining_minutes: int = 0


class ChecklistCreate(ChecklistBase):
    """Model for creating a checklist."""
    chore_ids: list[str] = []


class ChecklistUpdate(BaseModel):
    """Model for updating a checklist."""
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    chore_ids: Optional[list[str]] = None


class Checklist(ChecklistBase):
    """A scenario-based checklist.

    References actual chores and shows their real status.
    Examples: "Parents visiting", "Sleepover", "Spring cleaning"
    """
    id: str = Field(default_factory=generate_id)
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        from_attributes = True


class ChecklistWithChores(Checklist):
    """Checklist with live chore status."""
    chores: list[ChoreStatus] = []


# =============================================================================
# Dashboard / Briefing Models
# =============================================================================

class DashboardRoom(BaseModel):
    """Room summary for dashboard."""
    id: str
    name: str
    icon: str
    freshness_percent: int
    overdue_count: int
    chore_count: int


class Dashboard(BaseModel):
    """Home dashboard overview."""
    rooms: list[DashboardRoom]
    house_wide_chores: list[ChoreStatus]
    overall_freshness: int
    total_overdue: int
    chores_due_soon: int  # Due in next 3 days


class Briefing(BaseModel):
    """Morning briefing with suggested tasks."""
    greeting: str
    suggested_chores: list[ChoreStatus]
    total_minutes: int


class QuickCleanList(BaseModel):
    """Prioritized list for "I have X minutes" mode."""
    available_minutes: int
    chores: list[ChoreStatus]
    total_minutes: int
    impact_summary: str  # e.g., "This will freshen up 3 rooms"


# =============================================================================
# Vacation Mode
# =============================================================================

class VacationStatus(BaseModel):
    """Current global vacation-mode state."""
    is_active: bool
    started_at: Optional[datetime] = None
    days_elapsed: float = 0.0  # live, only meaningful while is_active


class VacationEndResult(BaseModel):
    """Result of ending a vacation."""
    days_elapsed: float
    chores_affected: int


class VacationLogEntry(BaseModel):
    """A past vacation's record from vacation_log."""
    id: str
    started_at: datetime
    ended_at: datetime
    days_elapsed: float
    chores_affected: int


class ChoreEligibility(BaseModel):
    """Preview of whether a chore would pause under vacation mode."""
    id: str
    name: str
    category_name: str
    vacation_override: Optional[VacationOverride] = None
    vacation_eligible: bool
