"""Briefing generator for daily/weekly summaries."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from ..data.models import (
    Task,
    TaskStatus,
    EnergyLevel,
    Context,
)
from ..data.store import Store
from ..tasks.prioritizer import Prioritizer
from ..reminders.manager import ReminderManager
from ..context.tracker import ContextTracker


class BriefingGenerator:
    """Generates context-aware briefings."""

    def __init__(
        self,
        store: Store,
        prioritizer: Prioritizer,
        reminders: ReminderManager,
        context_tracker: ContextTracker,
    ):
        """Initialize with dependencies."""
        self.store = store
        self.prioritizer = prioritizer
        self.reminders = reminders
        self.context_tracker = context_tracker

    def daily(self) -> dict[str, Any]:
        """Generate daily briefing."""
        context = self.context_tracker.get_current()
        now = datetime.now()
        today_end = now.replace(hour=23, minute=59, second=59)

        briefing: dict[str, Any] = {
            "generated_at": now.isoformat(),
            "type": "daily",
            "greeting": self._get_greeting(context),
            "summary": {},
            "priorities": [],
            "warnings": [],
            "reminders": [],
            "events": [],
            "suggestions": [],
        }

        # Get task summary
        tasks = self.store.get_tasks()
        overdue = [t for t in tasks if t.is_overdue]
        due_today = [t for t in tasks if t.due_date and t.due_date.date() == now.date() and not t.is_overdue]
        in_progress = [t for t in tasks if t.status == TaskStatus.IN_PROGRESS]
        inbox_count = len([t for t in tasks if t.status == TaskStatus.INBOX])

        briefing["summary"] = {
            "total_active": len([t for t in tasks if t.status not in (TaskStatus.DONE, TaskStatus.CANCELLED)]),
            "overdue": len(overdue),
            "due_today": len(due_today),
            "in_progress": len(in_progress),
            "inbox": inbox_count,
            "energy": context.energy_level.value,
        }

        # Priorities - top recommended tasks
        recommendations = self.prioritizer.get_recommended(context=context, limit=5)
        briefing["priorities"] = [
            {
                "id": task.id,
                "title": task.title,
                "score": round(score, 2),
                "due": task.due_date.strftime("%Y-%m-%d") if task.due_date else None,
                "reason": self._explain_priority(task, reasoning),
            }
            for task, score, reasoning in recommendations
        ]

        # Warnings
        if overdue:
            briefing["warnings"].append({
                "type": "overdue",
                "message": f"{len(overdue)} overdue task(s)",
                "tasks": [{"id": t.id, "title": t.title, "due": t.due_date.strftime("%Y-%m-%d") if t.due_date else None} for t in overdue[:3]],
            })

        if inbox_count > 5:
            briefing["warnings"].append({
                "type": "inbox_overflow",
                "message": f"{inbox_count} items in inbox need processing",
            })

        # Check for blocked tasks that might be unblocked
        blocked = [t for t in tasks if t.status == TaskStatus.WAITING]
        if blocked:
            briefing["warnings"].append({
                "type": "blocked",
                "message": f"{len(blocked)} task(s) are blocked",
                "tasks": [{"id": t.id, "title": t.title} for t in blocked[:3]],
            })

        # Upcoming reminders
        upcoming_reminders = self.reminders.get_upcoming(hours=12)
        briefing["reminders"] = [
            {
                "id": r.id,
                "title": r.title,
                "time": r.trigger_at.strftime("%H:%M") if r.trigger_at else None,
                "type": r.reminder_type.value,
            }
            for r in upcoming_reminders[:5]
        ]

        # Today's events
        events = self.store.get_events(
            start_after=now,
            start_before=today_end,
        )
        briefing["events"] = [
            {
                "id": e.id,
                "title": e.title,
                "start": e.start.strftime("%H:%M"),
                "duration": e.duration_minutes,
                "prep_needed": e.prep_time_minutes > 0,
            }
            for e in events[:5]
        ]

        # Context-aware suggestions
        briefing["suggestions"] = self._generate_suggestions(context, tasks)

        return briefing

    def weekly(self) -> dict[str, Any]:
        """Generate weekly review briefing."""
        now = datetime.now()
        week_start = now - timedelta(days=now.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = week_start + timedelta(days=7)

        briefing: dict[str, Any] = {
            "generated_at": now.isoformat(),
            "type": "weekly",
            "period": {
                "start": week_start.strftime("%Y-%m-%d"),
                "end": week_end.strftime("%Y-%m-%d"),
            },
            "accomplishments": [],
            "patterns": {},
            "upcoming": {},
            "areas": {},
            "insights": [],
        }

        # Get completed tasks this week
        completions = self.store.get_activity_log(
            event_type="task_completed",
            since=week_start,
        )

        completed_tasks = []
        for activity in completions:
            task_id = activity.get("entity_id")
            if task_id:
                task = self.store.get_task(task_id)
                if task:
                    completed_tasks.append(task)

        briefing["accomplishments"] = {
            "count": len(completed_tasks),
            "by_area": {},
            "by_priority": {},
            "highlights": [],
        }

        # Analyze completions
        for task in completed_tasks:
            area = task.area or "uncategorized"
            briefing["accomplishments"]["by_area"][area] = (
                briefing["accomplishments"]["by_area"].get(area, 0) + 1
            )

            priority = task.priority.name
            briefing["accomplishments"]["by_priority"][priority] = (
                briefing["accomplishments"]["by_priority"].get(priority, 0) + 1
            )

        # Highlight significant completions (high priority or long estimated)
        highlights = [
            t for t in completed_tasks
            if t.priority.value <= 2 or (t.estimated_minutes and t.estimated_minutes >= 60)
        ]
        briefing["accomplishments"]["highlights"] = [
            {"title": t.title, "area": t.area}
            for t in highlights[:5]
        ]

        # Energy patterns
        energy_summary = self.context_tracker.get_energy_summary()
        briefing["patterns"]["energy"] = energy_summary

        # Upcoming week
        next_week_end = now + timedelta(days=7)
        upcoming_tasks = self.store.get_tasks()
        upcoming_due = [
            t for t in upcoming_tasks
            if t.due_date and now <= t.due_date <= next_week_end
        ]

        briefing["upcoming"] = {
            "tasks_due": len(upcoming_due),
            "by_day": {},
        }

        for task in upcoming_due:
            if task.due_date:
                day = task.due_date.strftime("%A")
                if day not in briefing["upcoming"]["by_day"]:
                    briefing["upcoming"]["by_day"][day] = []
                briefing["upcoming"]["by_day"][day].append({
                    "id": task.id,
                    "title": task.title,
                })

        # Area breakdown
        all_tasks = self.store.get_tasks()
        for task in all_tasks:
            area = task.area or "uncategorized"
            if area not in briefing["areas"]:
                briefing["areas"][area] = {"active": 0, "completed_this_week": 0}

            if task.status not in (TaskStatus.DONE, TaskStatus.CANCELLED):
                briefing["areas"][area]["active"] += 1

        for task in completed_tasks:
            area = task.area or "uncategorized"
            if area in briefing["areas"]:
                briefing["areas"][area]["completed_this_week"] += 1

        # Generate insights
        briefing["insights"] = self._generate_weekly_insights(
            completed_tasks,
            upcoming_due,
            energy_summary,
        )

        return briefing

    def _get_greeting(self, context: Context) -> str:
        """Generate context-appropriate greeting."""
        hour = datetime.now().hour

        if hour < 12:
            time_greeting = "Good morning"
        elif hour < 17:
            time_greeting = "Good afternoon"
        else:
            time_greeting = "Good evening"

        energy_note = ""
        if context.energy_level == EnergyLevel.PEAK:
            energy_note = "You're at peak energy - great time for challenging work."
        elif context.energy_level == EnergyLevel.LOW:
            energy_note = "Energy is low - consider admin tasks or quick wins."
        elif context.energy_level == EnergyLevel.DEPLETED:
            energy_note = "Energy is depleted - focus on essentials only."

        return f"{time_greeting}. {energy_note}".strip()

    def _explain_priority(self, task: Task, reasoning: dict[str, Any]) -> str:
        """Generate human-readable explanation for task priority."""
        reasons = []

        if reasoning.get("urgency", 0) > 0.7:
            if task.is_overdue:
                reasons.append("overdue")
            elif task.days_until_due == 0:
                reasons.append("due today")
            elif task.days_until_due and task.days_until_due <= 2:
                reasons.append("due soon")

        if reasoning.get("importance", 0) > 0.7:
            reasons.append("high priority")

        if reasoning.get("energy_match", 0) > 0.8:
            reasons.append("matches current energy")

        if reasoning.get("momentum", 0) > 0.3:
            reasons.append("continues current work")

        if reasoning.get("quick_win", 0) > 0.5:
            reasons.append("quick win")

        if reasoning.get("blocking", 0) > 0.3:
            reasons.append("unblocks other tasks")

        if not reasons:
            reasons.append("good fit for now")

        return ", ".join(reasons)

    def _generate_suggestions(
        self,
        context: Context,
        tasks: list[Task],
    ) -> list[dict[str, str]]:
        """Generate context-aware suggestions."""
        suggestions = []

        # Energy-based suggestions
        if context.energy_level == EnergyLevel.PEAK:
            deep_work = [
                t for t in tasks
                if t.task_type.value in ("creative", "deep_work")
                and t.status == TaskStatus.TODO
            ]
            if deep_work:
                suggestions.append({
                    "type": "energy",
                    "message": f"Peak energy: tackle creative/deep work ({len(deep_work)} available)",
                })

        elif context.energy_level in (EnergyLevel.LOW, EnergyLevel.DEPLETED):
            quick_wins = [
                t for t in tasks
                if (t.estimated_minutes and t.estimated_minutes <= 15)
                or t.task_type.value == "quick_win"
            ]
            if quick_wins:
                suggestions.append({
                    "type": "energy",
                    "message": f"Low energy: {len(quick_wins)} quick wins available",
                })

        # Break suggestion
        should_break, reason = self.context_tracker.should_suggest_break()
        if should_break:
            suggestions.append({
                "type": "break",
                "message": reason,
            })

        # Inbox processing
        inbox_tasks = [t for t in tasks if t.status == TaskStatus.INBOX]
        if len(inbox_tasks) > 3:
            suggestions.append({
                "type": "process",
                "message": f"Process inbox: {len(inbox_tasks)} items waiting",
            })

        # Time-based suggestions
        if context.time_of_day == "morning" and context.day_of_week < 5:
            suggestions.append({
                "type": "planning",
                "message": "Morning: good time to review priorities",
            })

        if context.time_of_day == "evening":
            suggestions.append({
                "type": "review",
                "message": "Evening: consider reviewing tomorrow's tasks",
            })

        return suggestions[:4]  # Limit suggestions

    def _generate_weekly_insights(
        self,
        completed: list[Task],
        upcoming: list[Task],
        energy_patterns: dict[str, Any],
    ) -> list[str]:
        """Generate weekly review insights."""
        insights = []

        # Completion insights
        if len(completed) > 10:
            insights.append(f"Productive week: completed {len(completed)} tasks")
        elif len(completed) < 3:
            insights.append("Light completion week - check if tasks are sized appropriately")

        # Area balance
        if completed:
            areas = {}
            for t in completed:
                area = t.area or "uncategorized"
                areas[area] = areas.get(area, 0) + 1

            dominant_area = max(areas.items(), key=lambda x: x[1])
            if dominant_area[1] > len(completed) * 0.6:
                insights.append(f"Heavy focus on {dominant_area[0]} this week")

        # Upcoming workload
        if len(upcoming) > 15:
            insights.append(f"Heavy week ahead: {len(upcoming)} tasks due")
        elif len(upcoming) < 5:
            insights.append("Light week ahead - opportunity for proactive work")

        # Energy patterns
        if energy_patterns.get("best_times"):
            best = energy_patterns["best_times"][0]
            insights.append(
                f"Best energy: {best['time_of_day']}s (day {best['day_of_week']})"
            )

        return insights

    def quick_status(self) -> dict[str, Any]:
        """Generate quick status check."""
        context = self.context_tracker.get_current()
        tasks = self.store.get_tasks()

        in_progress = [t for t in tasks if t.status == TaskStatus.IN_PROGRESS]
        overdue = [t for t in tasks if t.is_overdue]

        due_reminders = self.reminders.get_due(context)

        return {
            "energy": context.energy_level.value,
            "in_progress": [{"id": t.id, "title": t.title} for t in in_progress],
            "overdue_count": len(overdue),
            "due_reminders": [{"id": r.id, "title": r.title} for r in due_reminders],
            "tasks_today": context.tasks_completed_today,
        }
