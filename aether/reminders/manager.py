"""Adaptive reminder management."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from croniter import croniter

from ..data.models import (
    Reminder,
    ReminderType,
    EnergyLevel,
    Context,
    Pattern,
)
from ..data.store import Store


class ReminderManager:
    """Manages reminders with adaptive timing."""

    # Default windows for different reminder types
    DEFAULT_WINDOWS = {
        ReminderType.MEDICATION: timedelta(hours=2),  # 2-hour window
        ReminderType.MEETING_PREP: timedelta(minutes=30),  # 30 min before
        ReminderType.DEADLINE: timedelta(hours=1),  # 1-hour window
        ReminderType.RECURRING: timedelta(hours=4),  # 4-hour window
        ReminderType.CONTEXTUAL: timedelta(hours=8),  # 8-hour window
        ReminderType.FOLLOW_UP: timedelta(hours=24),  # 24-hour window
    }

    def __init__(self, store: Store):
        """Initialize with data store."""
        self.store = store

    def add(
        self,
        title: str,
        trigger_at: datetime,
        reminder_type: ReminderType = ReminderType.RECURRING,
        description: str = "",
        window_minutes: int | None = None,
        adaptive: bool = False,
        preferred_energy: EnergyLevel | None = None,
        recurrence: str | None = None,
        linked_task: str | None = None,
        linked_event: str | None = None,
    ) -> Reminder:
        """Add a new reminder."""
        # Calculate window
        if window_minutes:
            window = timedelta(minutes=window_minutes)
        else:
            window = self.DEFAULT_WINDOWS.get(reminder_type, timedelta(hours=1))

        window_start = trigger_at - (window / 2)
        window_end = trigger_at + (window / 2)

        reminder = Reminder(
            title=title,
            description=description,
            reminder_type=reminder_type,
            trigger_at=trigger_at,
            window_start=window_start,
            window_end=window_end,
            adaptive=adaptive,
            preferred_energy=preferred_energy,
            recurrence=recurrence,
            linked_task=linked_task,
            linked_event=linked_event,
        )

        self.store.save_reminder(reminder)
        self.store.log_activity(
            "reminder_created",
            "reminder",
            reminder.id,
            {"title": title, "type": reminder_type.value},
        )
        return reminder

    def add_medication(
        self,
        name: str,
        target_time: datetime,
        window_hours: float = 2.0,
        recurrence: str | None = None,
    ) -> Reminder:
        """Add a medication reminder with adaptive timing."""
        return self.add(
            title=f"Take {name}",
            trigger_at=target_time,
            reminder_type=ReminderType.MEDICATION,
            window_minutes=int(window_hours * 60),
            adaptive=True,  # Always adaptive for medication
            preferred_energy=EnergyLevel.GOOD,  # Need to be alert enough
            recurrence=recurrence,
        )

    def add_meeting_prep(
        self,
        meeting_title: str,
        meeting_start: datetime,
        prep_minutes: int = 15,
        event_id: str | None = None,
    ) -> Reminder:
        """Add a meeting preparation reminder."""
        trigger_at = meeting_start - timedelta(minutes=prep_minutes)
        return self.add(
            title=f"Prepare for: {meeting_title}",
            trigger_at=trigger_at,
            reminder_type=ReminderType.MEETING_PREP,
            window_minutes=prep_minutes,
            linked_event=event_id,
        )

    def add_deadline(
        self,
        title: str,
        deadline: datetime,
        advance_hours: float = 24.0,
        task_id: str | None = None,
    ) -> Reminder:
        """Add a deadline reminder."""
        trigger_at = deadline - timedelta(hours=advance_hours)
        return self.add(
            title=f"Deadline approaching: {title}",
            trigger_at=trigger_at,
            reminder_type=ReminderType.DEADLINE,
            window_minutes=60,
            linked_task=task_id,
        )

    def get(self, reminder_id: str) -> Reminder | None:
        """Get reminder by ID."""
        return self.store.get_reminder(reminder_id)

    def list(
        self,
        active_only: bool = True,
        due_before: datetime | None = None,
    ) -> list[Reminder]:
        """List reminders."""
        return self.store.get_reminders(
            active_only=active_only,
            due_before=due_before,
        )

    def get_due(self, context: Context | None = None) -> list[Reminder]:
        """Get reminders that are due now, considering context."""
        now = datetime.now()
        reminders = self.store.get_reminders(active_only=True)

        due_reminders = []
        for reminder in reminders:
            if self._is_due(reminder, now, context):
                due_reminders.append(reminder)

        return due_reminders

    def _is_due(
        self,
        reminder: Reminder,
        now: datetime,
        context: Context | None = None,
    ) -> bool:
        """Check if a reminder is due, considering adaptive timing."""
        if not reminder.window_start or not reminder.window_end:
            return False

        # Check if we're within the window
        if not (reminder.window_start <= now <= reminder.window_end):
            return False

        # If not adaptive, just check if past trigger time
        if not reminder.adaptive:
            return reminder.trigger_at is not None and now >= reminder.trigger_at

        # Adaptive timing - consider energy level
        if context and reminder.preferred_energy:
            # If energy matches or is better, trigger now
            energy_order = [
                EnergyLevel.DEPLETED,
                EnergyLevel.LOW,
                EnergyLevel.GOOD,
                EnergyLevel.PEAK,
            ]

            current_idx = energy_order.index(context.energy_level)
            preferred_idx = energy_order.index(reminder.preferred_energy)

            # If current energy is at or above preferred, trigger
            if current_idx >= preferred_idx:
                return True

            # If we're past the trigger time and approaching window end, trigger anyway
            if reminder.trigger_at and now >= reminder.trigger_at:
                # Calculate how far through the remaining window we are
                remaining = (reminder.window_end - now).total_seconds()
                total_after = (reminder.window_end - reminder.trigger_at).total_seconds()
                if total_after > 0 and remaining / total_after < 0.3:
                    # Less than 30% of post-trigger window remaining
                    return True

            return False

        # Default: past trigger time
        return reminder.trigger_at is not None and now >= reminder.trigger_at

    def snooze(
        self,
        reminder_id: str,
        minutes: int = 15,
    ) -> Reminder | None:
        """Snooze a reminder."""
        reminder = self.store.get_reminder(reminder_id)
        if not reminder:
            return None

        if reminder.snooze_count >= reminder.max_snoozes:
            # Can't snooze anymore - log this for pattern learning
            self.store.log_activity(
                "reminder_snooze_maxed",
                "reminder",
                reminder_id,
            )
            return reminder

        # Update trigger time
        new_trigger = datetime.now() + timedelta(minutes=minutes)
        reminder.trigger_at = new_trigger
        reminder.snooze_count += 1

        # Extend window if needed
        if reminder.window_end and new_trigger > reminder.window_end:
            reminder.window_end = new_trigger + timedelta(minutes=30)

        self.store.save_reminder(reminder)
        self.store.log_activity(
            "reminder_snoozed",
            "reminder",
            reminder_id,
            {"minutes": minutes, "snooze_count": reminder.snooze_count},
        )
        return reminder

    def complete(self, reminder_id: str) -> Reminder | None:
        """Mark a reminder as completed."""
        reminder = self.store.get_reminder(reminder_id)
        if not reminder:
            return None

        reminder.completed = True
        reminder.last_triggered = datetime.now()

        # Handle recurrence
        if reminder.recurrence:
            self._schedule_next(reminder)
        else:
            reminder.active = False

        self.store.save_reminder(reminder)
        self.store.log_activity(
            "reminder_completed",
            "reminder",
            reminder_id,
            {"snooze_count": reminder.snooze_count},
        )
        return reminder

    def _schedule_next(self, reminder: Reminder) -> None:
        """Schedule the next occurrence of a recurring reminder."""
        if not reminder.recurrence:
            return

        try:
            cron = croniter(reminder.recurrence, datetime.now())
            next_trigger = cron.get_next(datetime)

            # Calculate new window
            window = self.DEFAULT_WINDOWS.get(
                reminder.reminder_type,
                timedelta(hours=1),
            )

            reminder.trigger_at = next_trigger
            reminder.window_start = next_trigger - (window / 2)
            reminder.window_end = next_trigger + (window / 2)
            reminder.completed = False
            reminder.snooze_count = 0

        except (KeyError, ValueError):
            # Invalid cron, deactivate
            reminder.active = False

    def dismiss(self, reminder_id: str) -> Reminder | None:
        """Dismiss a reminder without completing."""
        reminder = self.store.get_reminder(reminder_id)
        if not reminder:
            return None

        self.store.log_activity(
            "reminder_dismissed",
            "reminder",
            reminder_id,
        )

        # If recurring, schedule next
        if reminder.recurrence:
            self._schedule_next(reminder)
            self.store.save_reminder(reminder)
        else:
            reminder.active = False
            self.store.save_reminder(reminder)

        return reminder

    def delete(self, reminder_id: str) -> bool:
        """Delete a reminder."""
        return self.store.delete_reminder(reminder_id)

    def get_upcoming(
        self,
        hours: int = 24,
        include_recurring: bool = True,
    ) -> list[Reminder]:
        """Get upcoming reminders within N hours."""
        cutoff = datetime.now() + timedelta(hours=hours)
        reminders = self.store.get_reminders(
            active_only=True,
            due_before=cutoff,
        )

        if not include_recurring:
            reminders = [r for r in reminders if not r.recurrence]

        return sorted(reminders, key=lambda r: r.trigger_at or datetime.max)

    def get_missed(self) -> list[Reminder]:
        """Get reminders that were missed (past window)."""
        now = datetime.now()
        reminders = self.store.get_reminders(active_only=True)

        missed = []
        for reminder in reminders:
            if reminder.window_end and now > reminder.window_end:
                if not reminder.completed:
                    missed.append(reminder)

        return missed

    def analyze_patterns(self) -> dict[str, Any]:
        """Analyze reminder patterns for optimization."""
        # Get activity log for reminders
        activities = self.store.get_activity_log(
            entity_type="reminder",
            limit=500,
        )

        analysis = {
            "total_completed": 0,
            "total_snoozed": 0,
            "total_dismissed": 0,
            "avg_snoozes": 0,
            "best_completion_times": [],
            "problematic_reminders": [],
        }

        snooze_counts = []
        completion_hours = []

        for activity in activities:
            if activity["event_type"] == "reminder_completed":
                analysis["total_completed"] += 1
                if activity["data"]:
                    snooze_counts.append(activity["data"].get("snooze_count", 0))
                # Track completion time
                hour = datetime.fromisoformat(activity["timestamp"]).hour
                completion_hours.append(hour)

            elif activity["event_type"] == "reminder_snoozed":
                analysis["total_snoozed"] += 1

            elif activity["event_type"] == "reminder_dismissed":
                analysis["total_dismissed"] += 1

        if snooze_counts:
            analysis["avg_snoozes"] = sum(snooze_counts) / len(snooze_counts)

        if completion_hours:
            # Find most common completion hours
            hour_counts: dict[int, int] = {}
            for h in completion_hours:
                hour_counts[h] = hour_counts.get(h, 0) + 1

            sorted_hours = sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)
            analysis["best_completion_times"] = [h for h, _ in sorted_hours[:3]]

        return analysis
