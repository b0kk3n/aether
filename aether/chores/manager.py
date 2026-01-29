"""Chore scheduling system - Kaji-style interval-based tasks."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any
import uuid
import json

from ..data.store import Store


@dataclass
class Chore:
    """A recurring chore with interval-based scheduling."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""

    # Scheduling
    interval_days: int = 7  # How often it should be done
    duration_minutes: int = 15  # How long it takes
    flexibility_days: int = 2  # How many days early/late is OK

    # Location/Room
    room: str | None = None  # living_room, bathroom, kitchen, etc.
    zone: str | None = None  # indoor, outdoor, garage, etc.

    # Tracking
    last_completed: datetime | None = None
    completion_count: int = 0
    streak: int = 0  # Consecutive on-time completions

    # Preferences
    preferred_day: int | None = None  # 0=Monday, 6=Sunday
    preferred_time: str | None = None  # morning, afternoon, evening

    # State
    active: bool = True

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def due_date(self) -> datetime | None:
        """Calculate when this chore is due."""
        if not self.last_completed:
            return datetime.now()  # Never done, due now
        return self.last_completed + timedelta(days=self.interval_days)

    @property
    def is_due(self) -> bool:
        """Check if chore is due (within flexibility window)."""
        if not self.due_date:
            return True
        window_start = self.due_date - timedelta(days=self.flexibility_days)
        return datetime.now() >= window_start

    @property
    def is_overdue(self) -> bool:
        """Check if chore is overdue (past due date + flexibility)."""
        if not self.due_date:
            return True  # Never done
        window_end = self.due_date + timedelta(days=self.flexibility_days)
        return datetime.now() > window_end

    @property
    def days_until_due(self) -> int:
        """Days until due (negative if overdue)."""
        if not self.due_date:
            return -999
        return (self.due_date - datetime.now()).days

    @property
    def urgency_score(self) -> float:
        """Calculate urgency score (higher = more urgent)."""
        if not self.due_date:
            return 1.0  # Never done

        days = self.days_until_due

        if days < -self.flexibility_days:
            return 1.0  # Very overdue
        elif days < 0:
            return 0.8 + (abs(days) / self.flexibility_days) * 0.2
        elif days < self.flexibility_days:
            return 0.5 + ((self.flexibility_days - days) / self.flexibility_days) * 0.3
        else:
            return max(0.1, 0.5 - (days / self.interval_days) * 0.4)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "interval_days": self.interval_days,
            "duration_minutes": self.duration_minutes,
            "flexibility_days": self.flexibility_days,
            "room": self.room,
            "zone": self.zone,
            "last_completed": self.last_completed.isoformat() if self.last_completed else None,
            "completion_count": self.completion_count,
            "streak": self.streak,
            "preferred_day": self.preferred_day,
            "preferred_time": self.preferred_time,
            "active": self.active,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Chore":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            interval_days=data.get("interval_days", 7),
            duration_minutes=data.get("duration_minutes", 15),
            flexibility_days=data.get("flexibility_days", 2),
            room=data.get("room"),
            zone=data.get("zone"),
            last_completed=datetime.fromisoformat(data["last_completed"]) if data.get("last_completed") else None,
            completion_count=data.get("completion_count", 0),
            streak=data.get("streak", 0),
            preferred_day=data.get("preferred_day"),
            preferred_time=data.get("preferred_time"),
            active=data.get("active", True),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            metadata=data.get("metadata", {}),
        )


class ChoreManager:
    """Manages chores with smart scheduling."""

    # Default chore templates
    TEMPLATES = {
        "vacuum_living": Chore(name="Vacuum living room", interval_days=7, duration_minutes=15, room="living_room"),
        "vacuum_bedroom": Chore(name="Vacuum bedroom", interval_days=7, duration_minutes=10, room="bedroom"),
        "clean_bathroom": Chore(name="Clean bathroom", interval_days=14, duration_minutes=30, room="bathroom"),
        "clean_toilet": Chore(name="Clean toilet", interval_days=7, duration_minutes=10, room="bathroom"),
        "mop_floors": Chore(name="Mop floors", interval_days=14, duration_minutes=30, zone="indoor"),
        "dust_surfaces": Chore(name="Dust surfaces", interval_days=14, duration_minutes=20, zone="indoor"),
        "clean_kitchen": Chore(name="Deep clean kitchen", interval_days=7, duration_minutes=45, room="kitchen"),
        "change_sheets": Chore(name="Change bed sheets", interval_days=14, duration_minutes=15, room="bedroom"),
        "laundry": Chore(name="Do laundry", interval_days=7, duration_minutes=20),
        "trash_out": Chore(name="Take out trash", interval_days=3, duration_minutes=5),
        "water_plants": Chore(name="Water plants", interval_days=7, duration_minutes=10),
        "clean_fridge": Chore(name="Clean out fridge", interval_days=14, duration_minutes=20, room="kitchen"),
        "wipe_appliances": Chore(name="Wipe kitchen appliances", interval_days=7, duration_minutes=15, room="kitchen"),
    }

    def __init__(self, store: Store):
        """Initialize with data store."""
        self.store = store

    def add(self, chore: Chore) -> Chore:
        """Add a new chore."""
        self._save_chore(chore)
        self.store.log_activity("chore_created", "chore", chore.id, {"name": chore.name})
        return chore

    def add_from_template(self, template_key: str) -> Chore | None:
        """Add a chore from a template."""
        if template_key not in self.TEMPLATES:
            return None

        template = self.TEMPLATES[template_key]
        chore = Chore(
            name=template.name,
            description=template.description,
            interval_days=template.interval_days,
            duration_minutes=template.duration_minutes,
            flexibility_days=template.flexibility_days,
            room=template.room,
            zone=template.zone,
        )
        return self.add(chore)

    def get(self, chore_id: str) -> Chore | None:
        """Get chore by ID."""
        chores = self._load_chores()
        for chore in chores:
            if chore.id == chore_id:
                return chore
        return None

    def list(
        self,
        active_only: bool = True,
        room: str | None = None,
        zone: str | None = None,
    ) -> list[Chore]:
        """List chores with optional filters."""
        chores = self._load_chores()

        if active_only:
            chores = [c for c in chores if c.active]

        if room:
            chores = [c for c in chores if c.room == room]

        if zone:
            chores = [c for c in chores if c.zone == zone]

        return chores

    def get_due(self, limit: int | None = None) -> list[Chore]:
        """Get chores that are due."""
        chores = self.list(active_only=True)
        due = [c for c in chores if c.is_due]

        # Sort by urgency
        due.sort(key=lambda c: c.urgency_score, reverse=True)

        if limit:
            due = due[:limit]

        return due

    def get_overdue(self) -> list[Chore]:
        """Get overdue chores."""
        chores = self.list(active_only=True)
        return [c for c in chores if c.is_overdue]

    def complete(self, chore_id: str) -> Chore | None:
        """Mark a chore as complete."""
        chore = self.get(chore_id)
        if not chore:
            return None

        now = datetime.now()

        # Update streak
        if chore.due_date and not chore.is_overdue:
            chore.streak += 1
        else:
            chore.streak = 1  # Reset streak if overdue

        chore.last_completed = now
        chore.completion_count += 1

        self._save_chore(chore)
        self.store.log_activity(
            "chore_completed",
            "chore",
            chore.id,
            {
                "name": chore.name,
                "streak": chore.streak,
                "on_time": not chore.is_overdue,
            },
        )

        return chore

    def skip(self, chore_id: str, reason: str = "") -> Chore | None:
        """Skip a chore (resets due date without completion)."""
        chore = self.get(chore_id)
        if not chore:
            return None

        # Reset due date to now (so it's due again in interval_days)
        chore.last_completed = datetime.now()
        chore.streak = 0  # Break streak

        self._save_chore(chore)
        self.store.log_activity(
            "chore_skipped",
            "chore",
            chore.id,
            {"name": chore.name, "reason": reason},
        )

        return chore

    def update(self, chore_id: str, **updates: Any) -> Chore | None:
        """Update a chore."""
        chore = self.get(chore_id)
        if not chore:
            return None

        for key, value in updates.items():
            if hasattr(chore, key):
                setattr(chore, key, value)

        self._save_chore(chore)
        return chore

    def delete(self, chore_id: str) -> bool:
        """Delete a chore."""
        chores = self._load_chores()
        original_len = len(chores)
        chores = [c for c in chores if c.id != chore_id]

        if len(chores) < original_len:
            self._save_all_chores(chores)
            return True
        return False

    def get_for_time(
        self,
        available_minutes: int,
        room: str | None = None,
    ) -> list[Chore]:
        """Get chores that fit within available time."""
        due_chores = self.get_due()

        if room:
            due_chores = [c for c in due_chores if c.room == room or c.room is None]

        # Find chores that fit in available time
        fitting = [c for c in due_chores if c.duration_minutes <= available_minutes]

        return fitting

    def get_room_status(self) -> dict[str, dict[str, Any]]:
        """Get cleaning status by room."""
        chores = self.list(active_only=True)
        rooms: dict[str, dict[str, Any]] = {}

        for chore in chores:
            room = chore.room or "general"
            if room not in rooms:
                rooms[room] = {
                    "total": 0,
                    "due": 0,
                    "overdue": 0,
                    "chores": [],
                }

            rooms[room]["total"] += 1
            rooms[room]["chores"].append(chore.name)

            if chore.is_overdue:
                rooms[room]["overdue"] += 1
            elif chore.is_due:
                rooms[room]["due"] += 1

        return rooms

    def get_stats(self) -> dict[str, Any]:
        """Get chore statistics."""
        chores = self.list(active_only=True)
        completed_this_week = 0
        total_streak = 0
        longest_streak = 0

        week_ago = datetime.now() - timedelta(days=7)

        for chore in chores:
            total_streak += chore.streak
            longest_streak = max(longest_streak, chore.streak)
            if chore.last_completed and chore.last_completed > week_ago:
                completed_this_week += 1

        return {
            "total_chores": len(chores),
            "due_now": len(self.get_due()),
            "overdue": len(self.get_overdue()),
            "completed_this_week": completed_this_week,
            "average_streak": total_streak / len(chores) if chores else 0,
            "longest_streak": longest_streak,
        }

    def get_templates(self) -> list[dict[str, Any]]:
        """Get available chore templates."""
        return [
            {
                "key": key,
                "name": chore.name,
                "interval_days": chore.interval_days,
                "duration_minutes": chore.duration_minutes,
                "room": chore.room,
            }
            for key, chore in self.TEMPLATES.items()
        ]

    # Storage helpers

    def _load_chores(self) -> list[Chore]:
        """Load chores from memory storage."""
        memory = self.store.get_memory("chores_data")
        if memory and memory.value:
            try:
                data = json.loads(memory.value) if isinstance(memory.value, str) else memory.value
                return [Chore.from_dict(c) for c in data]
            except (json.JSONDecodeError, TypeError):
                pass
        return []

    def _save_chore(self, chore: Chore) -> None:
        """Save a single chore (updates or adds)."""
        chores = self._load_chores()

        # Find and update existing or add new
        found = False
        for i, c in enumerate(chores):
            if c.id == chore.id:
                chores[i] = chore
                found = True
                break

        if not found:
            chores.append(chore)

        self._save_all_chores(chores)

    def _save_all_chores(self, chores: list[Chore]) -> None:
        """Save all chores to memory storage."""
        from ..data.models import Memory

        data = json.dumps([c.to_dict() for c in chores])
        memory = Memory(
            key="chores_data",
            value=data,
            memory_type="data",
            context="Chore scheduling data",
        )
        self.store.save_memory(memory)
