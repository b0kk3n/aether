"""Smart task prioritization based on context and patterns."""

from datetime import datetime, timedelta
from typing import Any

from ..data.models import (
    Task,
    TaskStatus,
    TaskPriority,
    TaskType,
    EnergyLevel,
    Context,
    Pattern,
)
from ..data.store import Store


class Prioritizer:
    """Prioritizes and recommends tasks based on context."""

    # Weights for scoring factors
    WEIGHTS = {
        "urgency": 3.0,  # Due date pressure
        "importance": 2.5,  # Priority level
        "energy_match": 2.0,  # Energy level alignment
        "momentum": 1.5,  # Continuation of work
        "quick_win": 1.0,  # Easy wins for motivation
        "blocked_tasks": 1.5,  # Unblocks other work
        "pattern_match": 1.0,  # Historical success patterns
    }

    def __init__(self, store: Store):
        """Initialize with data store."""
        self.store = store

    def get_recommended(
        self,
        context: Context | None = None,
        limit: int = 5,
        area: str | None = None,
        exclude_ids: list[str] | None = None,
    ) -> list[tuple[Task, float, dict[str, Any]]]:
        """Get recommended tasks for current context.

        Returns list of (task, score, reasoning) tuples.
        """
        # Get active tasks
        tasks = self.store.get_tasks(
            status=[TaskStatus.TODO, TaskStatus.IN_PROGRESS],
            area=area,
        )

        if exclude_ids:
            tasks = [t for t in tasks if t.id not in exclude_ids]

        if not tasks:
            return []

        # Use provided context or get latest
        if context is None:
            context = self.store.get_latest_context()
        if context is None:
            context = Context()

        # Get patterns for context-aware scoring
        patterns = self.store.get_patterns(active_only=True, min_confidence=0.5)

        # Score each task
        scored_tasks: list[tuple[Task, float, dict[str, Any]]] = []
        for task in tasks:
            if task.is_blocked:
                continue

            score, reasoning = self._score_task(task, context, patterns)
            scored_tasks.append((task, score, reasoning))

        # Sort by score descending
        scored_tasks.sort(key=lambda x: x[1], reverse=True)

        return scored_tasks[:limit]

    def _score_task(
        self,
        task: Task,
        context: Context,
        patterns: list[Pattern],
    ) -> tuple[float, dict[str, Any]]:
        """Score a task based on current context."""
        score = 0.0
        reasoning: dict[str, Any] = {}

        # Urgency score based on due date
        urgency = self._calc_urgency(task)
        score += urgency * self.WEIGHTS["urgency"]
        reasoning["urgency"] = urgency

        # Importance score based on priority
        importance = self._calc_importance(task)
        score += importance * self.WEIGHTS["importance"]
        reasoning["importance"] = importance

        # Energy match score
        energy_match = self._calc_energy_match(task, context)
        score += energy_match * self.WEIGHTS["energy_match"]
        reasoning["energy_match"] = energy_match

        # Momentum score (continuing similar work)
        momentum = self._calc_momentum(task, context)
        score += momentum * self.WEIGHTS["momentum"]
        reasoning["momentum"] = momentum

        # Quick win bonus when energy is low
        quick_win = self._calc_quick_win(task, context)
        score += quick_win * self.WEIGHTS["quick_win"]
        reasoning["quick_win"] = quick_win

        # Blocking other tasks bonus
        blocking = self._calc_blocking_value(task)
        score += blocking * self.WEIGHTS["blocked_tasks"]
        reasoning["blocking"] = blocking

        # Pattern-based adjustments
        pattern_score = self._calc_pattern_score(task, context, patterns)
        score += pattern_score * self.WEIGHTS["pattern_match"]
        reasoning["pattern"] = pattern_score

        reasoning["total"] = score
        return score, reasoning

    def _calc_urgency(self, task: Task) -> float:
        """Calculate urgency score (0-1) based on due date."""
        if not task.due_date:
            return 0.3  # Some urgency for undated tasks

        days = task.days_until_due
        if days is None:
            return 0.3

        if days < 0:  # Overdue
            return 1.0
        if days == 0:  # Due today
            return 0.95
        if days == 1:  # Due tomorrow
            return 0.8
        if days <= 3:  # Due within 3 days
            return 0.6
        if days <= 7:  # Due within a week
            return 0.4
        return 0.2

    def _calc_importance(self, task: Task) -> float:
        """Calculate importance score (0-1) based on priority."""
        priority_scores = {
            TaskPriority.CRITICAL: 1.0,
            TaskPriority.HIGH: 0.8,
            TaskPriority.MEDIUM: 0.5,
            TaskPriority.LOW: 0.3,
            TaskPriority.SOMEDAY: 0.1,
        }
        return priority_scores.get(task.priority, 0.5)

    def _calc_energy_match(self, task: Task, context: Context) -> float:
        """Calculate how well task matches current energy level."""
        # Energy compatibility matrix
        compatibility = {
            EnergyLevel.PEAK: {
                EnergyLevel.PEAK: 1.0,
                EnergyLevel.GOOD: 0.7,
                EnergyLevel.LOW: 0.3,
                EnergyLevel.DEPLETED: 0.1,
            },
            EnergyLevel.GOOD: {
                EnergyLevel.PEAK: 0.5,  # Waste of peak energy
                EnergyLevel.GOOD: 1.0,
                EnergyLevel.LOW: 0.6,
                EnergyLevel.DEPLETED: 0.2,
            },
            EnergyLevel.LOW: {
                EnergyLevel.PEAK: 0.2,  # Poor match
                EnergyLevel.GOOD: 0.5,
                EnergyLevel.LOW: 1.0,
                EnergyLevel.DEPLETED: 0.7,
            },
            EnergyLevel.DEPLETED: {
                EnergyLevel.PEAK: 0.0,  # Don't attempt
                EnergyLevel.GOOD: 0.2,
                EnergyLevel.LOW: 0.7,
                EnergyLevel.DEPLETED: 1.0,
            },
        }

        # Task type to energy requirement mapping
        type_energy = {
            TaskType.CREATIVE: EnergyLevel.PEAK,
            TaskType.DEEP_WORK: EnergyLevel.PEAK,
            TaskType.ADMIN: EnergyLevel.LOW,
            TaskType.ROUTINE: EnergyLevel.LOW,
            TaskType.QUICK_WIN: EnergyLevel.DEPLETED,
            TaskType.ERRAND: EnergyLevel.GOOD,
            TaskType.COMMUNICATION: EnergyLevel.GOOD,
        }

        # Use task's explicit energy requirement or infer from type
        task_energy = task.energy_required
        if task_energy == EnergyLevel.GOOD and task.task_type in type_energy:
            task_energy = type_energy[task.task_type]

        return compatibility.get(context.energy_level, {}).get(task_energy, 0.5)

    def _calc_momentum(self, task: Task, context: Context) -> float:
        """Calculate momentum bonus for continuing similar work."""
        if not context.last_task_completed:
            return 0.0

        last_task = self.store.get_task(context.last_task_completed)
        if not last_task:
            return 0.0

        score = 0.0

        # Same project bonus
        if task.project and task.project == last_task.project:
            score += 0.4

        # Same area bonus
        if task.area and task.area == last_task.area:
            score += 0.3

        # Same type bonus
        if task.task_type == last_task.task_type:
            score += 0.2

        # Shared tags bonus
        if task.tags and last_task.tags:
            shared = set(task.tags) & set(last_task.tags)
            if shared:
                score += 0.1 * len(shared)

        return min(score, 1.0)

    def _calc_quick_win(self, task: Task, context: Context) -> float:
        """Calculate quick win bonus when energy is low."""
        is_quick = (
            task.task_type == TaskType.QUICK_WIN
            or (task.estimated_minutes and task.estimated_minutes <= 15)
        )

        if not is_quick:
            return 0.0

        # Quick wins are more valuable when energy is low
        energy_bonus = {
            EnergyLevel.PEAK: 0.2,
            EnergyLevel.GOOD: 0.4,
            EnergyLevel.LOW: 0.8,
            EnergyLevel.DEPLETED: 1.0,
        }

        return energy_bonus.get(context.energy_level, 0.4)

    def _calc_blocking_value(self, task: Task) -> float:
        """Calculate value of completing task that unblocks others."""
        if not task.blocks:
            return 0.0

        # More blocked tasks = higher value
        blocked_count = len(task.blocks)
        return min(blocked_count * 0.3, 1.0)

    def _calc_pattern_score(
        self,
        task: Task,
        context: Context,
        patterns: list[Pattern],
    ) -> float:
        """Calculate score based on learned patterns."""
        score = 0.0

        for pattern in patterns:
            if pattern.pattern_type == "task_completion":
                # Check if pattern conditions match current context
                conditions = pattern.conditions

                # Time of day match
                if "time_of_day" in conditions:
                    if conditions["time_of_day"] == context.time_of_day:
                        score += 0.2 * pattern.confidence

                # Day of week match
                if "day_of_week" in conditions:
                    if conditions["day_of_week"] == context.day_of_week:
                        score += 0.2 * pattern.confidence

                # Task type match
                if "task_type" in conditions:
                    if conditions["task_type"] == task.task_type.value:
                        score += 0.3 * pattern.confidence

                # Area match
                if "area" in conditions:
                    if conditions["area"] == task.area:
                        score += 0.2 * pattern.confidence

        return min(score, 1.0)

    def get_for_energy(
        self,
        energy: EnergyLevel,
        limit: int = 5,
    ) -> list[Task]:
        """Get tasks suitable for specific energy level."""
        context = Context(energy_level=energy)
        recommendations = self.get_recommended(context=context, limit=limit)
        return [task for task, _, _ in recommendations]

    def get_quick_wins(self, limit: int = 3) -> list[Task]:
        """Get quick win tasks for momentum building."""
        tasks = self.store.get_tasks(status=[TaskStatus.TODO])

        quick_tasks = [
            t
            for t in tasks
            if not t.is_blocked
            and (
                t.task_type == TaskType.QUICK_WIN
                or (t.estimated_minutes and t.estimated_minutes <= 15)
            )
        ]

        # Sort by priority
        quick_tasks.sort(key=lambda t: t.priority.value)
        return quick_tasks[:limit]

    def get_deep_work(self, available_minutes: int = 60) -> list[Task]:
        """Get deep work tasks for focused sessions."""
        tasks = self.store.get_tasks(status=[TaskStatus.TODO])

        deep_tasks = [
            t
            for t in tasks
            if not t.is_blocked
            and t.task_type in (TaskType.CREATIVE, TaskType.DEEP_WORK)
            and (not t.estimated_minutes or t.estimated_minutes <= available_minutes)
        ]

        # Sort by priority then due date
        deep_tasks.sort(key=lambda t: (t.priority.value, t.due_date or datetime.max))
        return deep_tasks

    def analyze_workload(self) -> dict[str, Any]:
        """Analyze current workload and provide insights."""
        tasks = self.store.get_tasks()

        analysis = {
            "total_active": len(tasks),
            "overdue": 0,
            "due_today": 0,
            "due_this_week": 0,
            "blocked": 0,
            "in_progress": 0,
            "inbox": 0,
            "by_area": {},
            "by_priority": {},
            "estimated_hours": 0,
            "insights": [],
        }

        now = datetime.now()
        week_end = now + timedelta(days=7)

        for task in tasks:
            # Status counts
            if task.status == TaskStatus.INBOX:
                analysis["inbox"] += 1
            elif task.status == TaskStatus.IN_PROGRESS:
                analysis["in_progress"] += 1
            elif task.status == TaskStatus.WAITING:
                analysis["blocked"] += 1

            # Due date analysis
            if task.is_overdue:
                analysis["overdue"] += 1
            elif task.due_date:
                if task.due_date.date() == now.date():
                    analysis["due_today"] += 1
                elif task.due_date <= week_end:
                    analysis["due_this_week"] += 1

            # Area breakdown
            area = task.area or "uncategorized"
            analysis["by_area"][area] = analysis["by_area"].get(area, 0) + 1

            # Priority breakdown
            priority = task.priority.name
            analysis["by_priority"][priority] = analysis["by_priority"].get(priority, 0) + 1

            # Time estimation
            if task.estimated_minutes:
                analysis["estimated_hours"] += task.estimated_minutes / 60

        # Generate insights
        if analysis["overdue"] > 0:
            analysis["insights"].append(
                f"⚠️ {analysis['overdue']} overdue task(s) need attention"
            )

        if analysis["inbox"] > 5:
            analysis["insights"].append(
                f"📥 {analysis['inbox']} items in inbox - consider processing"
            )

        if analysis["blocked"] > 3:
            analysis["insights"].append(
                f"🚧 {analysis['blocked']} blocked tasks - check dependencies"
            )

        if analysis["in_progress"] > 3:
            analysis["insights"].append(
                f"🔄 {analysis['in_progress']} tasks in progress - consider focusing"
            )

        return analysis
