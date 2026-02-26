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


class Category(str, Enum):
    """Chore category for filtering and grouping."""
    VACUUM = "vacuum"
    MOP = "mop"
    DUST = "dust"
    DECLUTTER = "declutter"
    CLEAN = "clean"
    WASH = "wash"
    WIPE = "wipe"
    MAINTAIN = "maintain"


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
    icon: str = "🏠"
    sort_order: int = 0


class RoomCreate(RoomBase):
    """Model for creating a room."""
    pass


class Room(RoomBase):
    """A room in the home."""
    id: str = Field(default_factory=generate_id)
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        from_attributes = True


class RoomWithFreshness(Room):
    """Room with calculated freshness score."""
    freshness_percent: int = 100
    chore_count: int = 0
    overdue_count: int = 0


# =============================================================================
# Chore
# =============================================================================

class ChoreBase(BaseModel):
    """Base chore model for creation/updates."""
    name: str
    room_id: Optional[str] = None  # None = house-wide
    interval_days: int
    estimated_minutes: int = 15
    category: Category = Category.CLEAN
    notes: str = ""
    is_active: bool = True


class ChoreCreate(ChoreBase):
    """Model for creating a chore."""
    pass


class ChoreUpdate(BaseModel):
    """Model for updating a chore."""
    name: Optional[str] = None
    interval_days: Optional[int] = None
    estimated_minutes: Optional[int] = None
    category: Optional[Category] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


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

    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        from_attributes = True

    @property
    def priority(self) -> Priority:
        """Auto-calculate priority from interval."""
        return priority_from_interval(self.interval_days)

    @property
    def due_date(self) -> datetime:
        """When this chore is due."""
        if not self.last_completed_at:
            return datetime.now()  # Never done = due now
        return self.last_completed_at + timedelta(days=self.interval_days)

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
        """How fresh is this chore (100 = just done, 0 = due/overdue).

        Calculated as percentage of interval remaining.
        Overdue chores score 0%. Chores due within 3 days score at least 50%
        to avoid an overly negative view when nothing urgent needs doing.
        """
        if not self.last_completed_at:
            return 0

        days_since = (datetime.now() - self.last_completed_at).days

        if days_since <= 0:
            return 100
        elif days_since >= self.interval_days:
            return 0
        else:
            actual = int(100 - (days_since / self.interval_days * 100))
            days_until = self.interval_days - days_since
            if days_until <= 3:
                return max(actual, 50)
            return actual

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
    category: Category
    days_until_due: int
    freshness_percent: int
    is_overdue: bool
    last_completed_at: Optional[datetime]
    estimated_minutes: int
    streak: int


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
    icon: str = "📋"


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
    total_minutes: int = 0  # Estimated time to complete all
    overdue_count: int = 0


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
    rooms_needing_attention: list[str]


class QuickCleanList(BaseModel):
    """Prioritized list for "I have X minutes" mode."""
    available_minutes: int
    chores: list[ChoreStatus]
    total_minutes: int
    impact_summary: str  # e.g., "This will freshen up 3 rooms"
