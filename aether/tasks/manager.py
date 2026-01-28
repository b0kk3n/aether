"""Task management operations."""

from datetime import datetime, timedelta
from typing import Any

from croniter import croniter

from ..data.models import Task, TaskStatus, TaskPriority, TaskType, EnergyLevel
from ..data.store import Store


class TaskManager:
    """Manages task operations and smart task handling."""

    def __init__(self, store: Store):
        """Initialize with data store."""
        self.store = store

    def add(
        self,
        title: str,
        description: str = "",
        due_date: datetime | None = None,
        priority: TaskPriority = TaskPriority.MEDIUM,
        task_type: TaskType = TaskType.ROUTINE,
        energy_required: EnergyLevel = EnergyLevel.GOOD,
        project: str | None = None,
        area: str | None = None,
        tags: list[str] | None = None,
        estimated_minutes: int | None = None,
        recurrence: str | None = None,
        status: TaskStatus = TaskStatus.INBOX,
    ) -> Task:
        """Add a new task."""
        task = Task(
            title=title,
            description=description,
            due_date=due_date,
            priority=priority,
            task_type=task_type,
            energy_required=energy_required,
            project=project,
            area=area,
            tags=tags or [],
            estimated_minutes=estimated_minutes,
            recurrence=recurrence,
            status=status,
        )
        self.store.save_task(task)
        self.store.log_activity("task_created", "task", task.id, {"title": title})
        return task

    def quick_add(self, text: str) -> Task:
        """Quick add task with natural language parsing.

        Supports shortcuts like:
        - "Buy milk #shopping @errands"
        - "Call mom !high due:tomorrow"
        - "Review PR est:30m @work"
        """
        title = text
        tags: list[str] = []
        area: str | None = None
        project: str | None = None
        priority = TaskPriority.MEDIUM
        due_date: datetime | None = None
        estimated_minutes: int | None = None
        task_type = TaskType.ROUTINE

        # Parse tokens
        tokens = text.split()
        clean_tokens = []

        for token in tokens:
            if token.startswith("#"):
                tags.append(token[1:])
            elif token.startswith("@"):
                area = token[1:]
            elif token.startswith("+"):
                project = token[1:]
            elif token.startswith("!"):
                priority_map = {
                    "!critical": TaskPriority.CRITICAL,
                    "!high": TaskPriority.HIGH,
                    "!med": TaskPriority.MEDIUM,
                    "!low": TaskPriority.LOW,
                    "!someday": TaskPriority.SOMEDAY,
                }
                priority = priority_map.get(token.lower(), TaskPriority.MEDIUM)
            elif token.startswith("due:"):
                due_str = token[4:].lower()
                due_date = self._parse_due_date(due_str)
            elif token.startswith("est:"):
                est_str = token[4:].lower()
                estimated_minutes = self._parse_duration(est_str)
            elif token.startswith("type:"):
                type_str = token[5:].lower()
                type_map = {
                    "creative": TaskType.CREATIVE,
                    "admin": TaskType.ADMIN,
                    "routine": TaskType.ROUTINE,
                    "deep": TaskType.DEEP_WORK,
                    "quick": TaskType.QUICK_WIN,
                    "errand": TaskType.ERRAND,
                    "comm": TaskType.COMMUNICATION,
                }
                task_type = type_map.get(type_str, TaskType.ROUTINE)
            else:
                clean_tokens.append(token)

        title = " ".join(clean_tokens)

        return self.add(
            title=title,
            tags=tags,
            area=area,
            project=project,
            priority=priority,
            due_date=due_date,
            estimated_minutes=estimated_minutes,
            task_type=task_type,
        )

    def _parse_due_date(self, due_str: str) -> datetime | None:
        """Parse due date string."""
        now = datetime.now()
        today = now.replace(hour=23, minute=59, second=59, microsecond=0)

        shortcuts = {
            "today": today,
            "tomorrow": today + timedelta(days=1),
            "tom": today + timedelta(days=1),
            "nextweek": today + timedelta(weeks=1),
            "mon": self._next_weekday(0),
            "tue": self._next_weekday(1),
            "wed": self._next_weekday(2),
            "thu": self._next_weekday(3),
            "fri": self._next_weekday(4),
            "sat": self._next_weekday(5),
            "sun": self._next_weekday(6),
        }

        if due_str in shortcuts:
            return shortcuts[due_str]

        # Try to parse as date
        try:
            return datetime.fromisoformat(due_str)
        except ValueError:
            pass

        # Try relative days (e.g., "3d" for 3 days)
        if due_str.endswith("d") and due_str[:-1].isdigit():
            days = int(due_str[:-1])
            return today + timedelta(days=days)

        return None

    def _next_weekday(self, weekday: int) -> datetime:
        """Get next occurrence of weekday (0=Monday)."""
        now = datetime.now()
        days_ahead = weekday - now.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        return now.replace(hour=23, minute=59, second=59, microsecond=0) + timedelta(days=days_ahead)

    def _parse_duration(self, duration_str: str) -> int | None:
        """Parse duration string to minutes."""
        if duration_str.endswith("m") and duration_str[:-1].isdigit():
            return int(duration_str[:-1])
        if duration_str.endswith("h") and duration_str[:-1].isdigit():
            return int(duration_str[:-1]) * 60
        if duration_str.isdigit():
            return int(duration_str)
        return None

    def get(self, task_id: str) -> Task | None:
        """Get a task by ID."""
        return self.store.get_task(task_id)

    def list(
        self,
        status: TaskStatus | list[TaskStatus] | None = None,
        area: str | None = None,
        project: str | None = None,
        include_done: bool = False,
    ) -> list[Task]:
        """List tasks with optional filters."""
        return self.store.get_tasks(
            status=status,
            area=area,
            project=project,
            include_done=include_done,
        )

    def update(self, task_id: str, **updates: Any) -> Task | None:
        """Update a task."""
        task = self.store.get_task(task_id)
        if not task:
            return None

        for key, value in updates.items():
            if hasattr(task, key):
                setattr(task, key, value)

        self.store.save_task(task)
        self.store.log_activity("task_updated", "task", task_id, updates)
        return task

    def complete(self, task_id: str, actual_minutes: int | None = None) -> Task | None:
        """Mark a task as complete."""
        task = self.store.get_task(task_id)
        if not task:
            return None

        task.status = TaskStatus.DONE
        task.completed_at = datetime.now()
        if actual_minutes:
            task.actual_minutes = actual_minutes

        self.store.save_task(task)
        self.store.log_activity(
            "task_completed",
            "task",
            task_id,
            {
                "estimated": task.estimated_minutes,
                "actual": actual_minutes,
                "energy_required": task.energy_required.value,
            },
        )

        # Handle recurring tasks
        if task.recurrence:
            self._create_next_occurrence(task)

        return task

    def _create_next_occurrence(self, task: Task) -> Task | None:
        """Create next occurrence of a recurring task."""
        if not task.recurrence:
            return None

        try:
            cron = croniter(task.recurrence, datetime.now())
            next_due = cron.get_next(datetime)

            new_task = Task(
                title=task.title,
                description=task.description,
                priority=task.priority,
                task_type=task.task_type,
                energy_required=task.energy_required,
                project=task.project,
                area=task.area,
                tags=task.tags.copy(),
                estimated_minutes=task.estimated_minutes,
                recurrence=task.recurrence,
                recurrence_parent=task.recurrence_parent or task.id,
                due_date=next_due,
                status=TaskStatus.TODO,
            )

            self.store.save_task(new_task)
            return new_task
        except (KeyError, ValueError):
            return None

    def start(self, task_id: str) -> Task | None:
        """Start working on a task."""
        task = self.store.get_task(task_id)
        if not task:
            return None

        task.status = TaskStatus.IN_PROGRESS
        self.store.save_task(task)
        self.store.log_activity("task_started", "task", task_id)
        return task

    def block(self, task_id: str, blocked_by: str | None = None, reason: str = "") -> Task | None:
        """Mark a task as blocked/waiting."""
        task = self.store.get_task(task_id)
        if not task:
            return None

        task.status = TaskStatus.WAITING
        if blocked_by:
            task.blocked_by.append(blocked_by)
        if reason:
            task.notes += f"\nBlocked: {reason}"

        self.store.save_task(task)
        self.store.log_activity("task_blocked", "task", task_id, {"blocked_by": blocked_by})
        return task

    def unblock(self, task_id: str) -> Task | None:
        """Unblock a task."""
        task = self.store.get_task(task_id)
        if not task:
            return None

        task.status = TaskStatus.TODO
        task.blocked_by = []
        self.store.save_task(task)
        self.store.log_activity("task_unblocked", "task", task_id)
        return task

    def delete(self, task_id: str) -> bool:
        """Delete a task."""
        return self.store.delete_task(task_id)

    def get_inbox(self) -> list[Task]:
        """Get all inbox items."""
        return self.store.get_tasks(status=TaskStatus.INBOX)

    def process_to_todo(self, task_id: str) -> Task | None:
        """Move task from inbox to todo."""
        return self.update(task_id, status=TaskStatus.TODO)

    def get_overdue(self) -> list[Task]:
        """Get all overdue tasks."""
        tasks = self.store.get_tasks()
        return [t for t in tasks if t.is_overdue]

    def get_due_soon(self, days: int = 3) -> list[Task]:
        """Get tasks due within N days."""
        tasks = self.store.get_tasks()
        cutoff = datetime.now() + timedelta(days=days)
        return [
            t
            for t in tasks
            if t.due_date and t.due_date <= cutoff and not t.is_overdue
        ]

    def get_blocked(self) -> list[Task]:
        """Get all blocked tasks."""
        return self.store.get_tasks(status=TaskStatus.WAITING)

    def get_in_progress(self) -> list[Task]:
        """Get tasks currently in progress."""
        return self.store.get_tasks(status=TaskStatus.IN_PROGRESS)

    def get_by_project(self, project: str) -> list[Task]:
        """Get all tasks for a project."""
        return self.store.get_tasks(project=project)

    def get_by_area(self, area: str) -> list[Task]:
        """Get all tasks for an area."""
        return self.store.get_tasks(area=area)

    def get_quick_wins(self, max_minutes: int = 15) -> list[Task]:
        """Get quick win tasks (under N minutes)."""
        tasks = self.store.get_tasks()
        return [
            t
            for t in tasks
            if t.estimated_minutes and t.estimated_minutes <= max_minutes
            or t.task_type == TaskType.QUICK_WIN
        ]

    def get_areas(self) -> list[str]:
        """Get all unique areas."""
        tasks = self.store.get_tasks(include_done=True)
        areas = set(t.area for t in tasks if t.area)
        return sorted(areas)

    def get_projects(self) -> list[str]:
        """Get all unique projects."""
        tasks = self.store.get_tasks(include_done=True)
        projects = set(t.project for t in tasks if t.project)
        return sorted(projects)
