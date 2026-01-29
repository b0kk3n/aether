"""Main Aether engine - orchestrates all components."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from ..data.store import Store
from ..data.models import (
    Task,
    TaskStatus,
    TaskPriority,
    TaskType,
    EnergyLevel,
    Reminder,
    ReminderType,
    Event,
    Memory,
    Context,
)
from ..tasks.manager import TaskManager
from ..tasks.prioritizer import Prioritizer
from ..reminders.manager import ReminderManager
from ..context.tracker import ContextTracker
from .briefing import BriefingGenerator


class Aether:
    """Main Aether personal assistant engine.

    This is the primary interface for interacting with Aether.
    It coordinates all subsystems and provides a unified API.
    """

    def __init__(self, db_path: str | Path | None = None):
        """Initialize Aether with all components.

        Args:
            db_path: Optional path to database file. Defaults to ~/.aether/aether.db
        """
        self.store = Store(db_path)

        # Initialize managers
        self.tasks = TaskManager(self.store)
        self.prioritizer = Prioritizer(self.store)
        self.reminders = ReminderManager(self.store)
        self.context = ContextTracker(self.store)
        self.briefing = BriefingGenerator(
            self.store,
            self.prioritizer,
            self.reminders,
            self.context,
        )

    # Quick actions - most common operations

    def add(self, text: str) -> Task:
        """Quick add a task using natural language.

        Examples:
            ae.add("Buy milk #shopping @errands")
            ae.add("Call mom !high due:tomorrow")
            ae.add("Review PR est:30m @work")
        """
        return self.tasks.quick_add(text)

    def done(self, task_id: str, actual_minutes: int | None = None) -> Task | None:
        """Mark a task as done.

        Args:
            task_id: Task ID (or partial match)
            actual_minutes: Optional actual time spent
        """
        task = self._resolve_task_id(task_id)
        if task:
            result = self.tasks.complete(task.id, actual_minutes)
            if result:
                self.context.record_task_completed(task.id)
            return result
        return None

    def start(self, task_id: str) -> Task | None:
        """Start working on a task."""
        task = self._resolve_task_id(task_id)
        if task:
            return self.tasks.start(task.id)
        return None

    def _resolve_task_id(self, task_id: str) -> Task | None:
        """Resolve a task ID, supporting partial matches."""
        # Try exact match first
        task = self.tasks.get(task_id)
        if task:
            return task

        # Try partial match
        all_tasks = self.tasks.list(include_done=True)
        for t in all_tasks:
            if t.id.startswith(task_id):
                return t

        return None

    # Briefings and status

    def morning(self) -> dict[str, Any]:
        """Get morning briefing."""
        return self.briefing.daily()

    def status(self) -> dict[str, Any]:
        """Get quick status."""
        return self.briefing.quick_status()

    def weekly(self) -> dict[str, Any]:
        """Get weekly review."""
        return self.briefing.weekly()

    # Context and energy

    def energy(self, level: str, note: str = "") -> Context:
        """Set current energy level.

        Args:
            level: One of 'peak', 'good', 'low', 'depleted'
            note: Optional note about energy state
        """
        energy_level = EnergyLevel(level.lower())
        return self.context.set_energy(energy_level, note)

    def focus(self, enabled: bool = True) -> Context:
        """Toggle focus mode."""
        return self.context.set_focus_mode(enabled)

    def take_break(self) -> Context:
        """Record taking a break."""
        return self.context.record_break()

    # Task queries

    def next(self, count: int = 3) -> list[tuple[Task, float, dict[str, Any]]]:
        """Get next recommended tasks based on current context."""
        return self.prioritizer.get_recommended(limit=count)

    def inbox(self) -> list[Task]:
        """Get inbox items."""
        return self.tasks.get_inbox()

    def overdue(self) -> list[Task]:
        """Get overdue tasks."""
        return self.tasks.get_overdue()

    def today(self) -> list[Task]:
        """Get tasks due today."""
        return self.tasks.get_due_soon(days=0)

    def quick_wins(self, count: int = 5) -> list[Task]:
        """Get quick win tasks."""
        return self.prioritizer.get_quick_wins(limit=count)

    def blocked(self) -> list[Task]:
        """Get blocked tasks."""
        return self.tasks.get_blocked()

    # Reminders

    def remind(
        self,
        title: str,
        when: datetime,
        reminder_type: str = "recurring",
        adaptive: bool = False,
    ) -> Reminder:
        """Add a reminder.

        Args:
            title: Reminder title
            when: When to trigger
            reminder_type: Type of reminder
            adaptive: Whether to use adaptive timing
        """
        rtype = ReminderType(reminder_type)
        return self.reminders.add(
            title=title,
            trigger_at=when,
            reminder_type=rtype,
            adaptive=adaptive,
        )

    def medication(
        self,
        name: str,
        time: datetime,
        window_hours: float = 2.0,
        recurrence: str | None = None,
    ) -> Reminder:
        """Add a medication reminder with adaptive timing."""
        return self.reminders.add_medication(
            name=name,
            target_time=time,
            window_hours=window_hours,
            recurrence=recurrence,
        )

    def due_reminders(self) -> list[Reminder]:
        """Get reminders that are due now."""
        ctx = self.context.get_current()
        return self.reminders.get_due(ctx)

    def snooze(self, reminder_id: str, minutes: int = 15) -> Reminder | None:
        """Snooze a reminder."""
        return self.reminders.snooze(reminder_id, minutes)

    def ack(self, reminder_id: str) -> Reminder | None:
        """Acknowledge/complete a reminder."""
        return self.reminders.complete(reminder_id)

    # Events

    def event(
        self,
        title: str,
        start: datetime,
        end: datetime | None = None,
        event_type: str = "meeting",
        prep_minutes: int = 0,
    ) -> Event:
        """Add a calendar event."""
        evt = Event(
            title=title,
            start=start,
            end=end,
            event_type=event_type,
            prep_time_minutes=prep_minutes,
        )
        self.store.save_event(evt)

        # Auto-create prep reminder if needed
        if prep_minutes > 0:
            self.reminders.add_meeting_prep(
                meeting_title=title,
                meeting_start=start,
                prep_minutes=prep_minutes,
                event_id=evt.id,
            )

        return evt

    def upcoming_events(self, hours: int = 24) -> list[Event]:
        """Get upcoming events."""
        from datetime import timedelta
        now = datetime.now()
        return self.store.get_events(
            start_after=now,
            start_before=now + timedelta(hours=hours),
        )

    # Memory and preferences

    def remember(
        self,
        key: str,
        value: Any,
        memory_type: str = "preference",
        context: str = "",
    ) -> Memory:
        """Remember something for later.

        Args:
            key: Lookup key
            value: Value to remember
            memory_type: Type (preference, decision, fact, context)
            context: Why/how this was learned
        """
        memory = Memory(
            key=key,
            value=value,
            memory_type=memory_type,
            context=context,
            source="user_input",
        )
        self.store.save_memory(memory)
        return memory

    def recall(self, key: str) -> Any:
        """Recall a stored memory."""
        memory = self.store.get_memory(key)
        return memory.value if memory else None

    def search_memory(self, query: str) -> list[Memory]:
        """Search memories."""
        return self.store.search_memories(query)

    # Analytics

    def workload(self) -> dict[str, Any]:
        """Analyze current workload."""
        return self.prioritizer.analyze_workload()

    def productivity(self) -> dict[str, Any]:
        """Get productivity score for today."""
        return self.context.get_productivity_score()

    def stats(self) -> dict[str, Any]:
        """Get overall statistics."""
        return self.store.get_stats()

    # Batch operations

    def process_inbox(self) -> list[Task]:
        """Get inbox items for processing."""
        return self.inbox()

    def promote(self, task_id: str) -> Task | None:
        """Promote task from inbox to todo."""
        task = self._resolve_task_id(task_id)
        if task:
            return self.tasks.process_to_todo(task.id)
        return None

    def block(self, task_id: str, reason: str = "") -> Task | None:
        """Mark a task as blocked."""
        task = self._resolve_task_id(task_id)
        if task:
            return self.tasks.block(task.id, reason=reason)
        return None

    def unblock(self, task_id: str) -> Task | None:
        """Unblock a task."""
        task = self._resolve_task_id(task_id)
        if task:
            return self.tasks.unblock(task.id)
        return None

    # Areas and projects

    def areas(self) -> list[str]:
        """Get all areas."""
        return self.tasks.get_areas()

    def projects(self) -> list[str]:
        """Get all projects."""
        return self.tasks.get_projects()

    def by_area(self, area: str) -> list[Task]:
        """Get tasks by area."""
        return self.tasks.get_by_area(area)

    def by_project(self, project: str) -> list[Task]:
        """Get tasks by project."""
        return self.tasks.get_by_project(project)

    # Utilities

    def export(self) -> dict[str, Any]:
        """Export all data."""
        return {
            "tasks": [t.to_dict() for t in self.tasks.list(include_done=True)],
            "reminders": [r.to_dict() for r in self.reminders.list(active_only=False)],
            "events": [e.to_dict() for e in self.store.get_events()],
            "memories": [m.to_dict() for m in self.store.get_memories()],
            "patterns": [p.to_dict() for p in self.store.get_patterns(active_only=False)],
            "stats": self.stats(),
            "exported_at": datetime.now().isoformat(),
        }
