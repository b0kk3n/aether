"""Context and energy tracking."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from ..data.models import Context, EnergyLevel, Pattern, Memory
from ..data.store import Store


class ContextTracker:
    """Tracks and manages user context including energy levels."""

    def __init__(self, store: Store):
        """Initialize with data store."""
        self.store = store

    def get_current(self) -> Context:
        """Get current context, inferring values where possible."""
        # Start with latest saved context or new one
        context = self.store.get_latest_context()
        if not context:
            context = Context()

        # Update time-based fields
        now = datetime.now()
        context.timestamp = now
        context.day_of_week = now.weekday()
        context.time_of_day = self._get_time_of_day(now.hour)

        # Infer energy if not recently set
        if context.timestamp < now - timedelta(hours=2):
            inferred_energy = self._infer_energy(context)
            if inferred_energy:
                context.energy_level = inferred_energy

        # Calculate tasks completed today
        context.tasks_completed_today = self._count_tasks_today()

        return context

    def _get_time_of_day(self, hour: int) -> str:
        """Get time of day category."""
        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 21:
            return "evening"
        else:
            return "night"

    def _infer_energy(self, context: Context) -> EnergyLevel | None:
        """Infer energy level from patterns and time."""
        # Check for energy patterns
        patterns = self.store.get_patterns(
            pattern_type="energy",
            min_confidence=0.6,
        )

        for pattern in patterns:
            conditions = pattern.conditions
            if conditions.get("time_of_day") == context.time_of_day:
                if conditions.get("day_of_week") == context.day_of_week:
                    # Strong match
                    energy_value = conditions.get("typical_energy")
                    if energy_value:
                        return EnergyLevel(energy_value)

        # Default patterns if no learned patterns
        hour = context.timestamp.hour
        if 9 <= hour <= 11:  # Late morning typically good
            return EnergyLevel.GOOD
        elif 14 <= hour <= 15:  # Post-lunch dip
            return EnergyLevel.LOW
        elif 20 <= hour or hour < 6:  # Late evening/night
            return EnergyLevel.DEPLETED

        return None

    def _count_tasks_today(self) -> int:
        """Count tasks completed today."""
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        activities = self.store.get_activity_log(
            event_type="task_completed",
            since=today_start,
        )
        return len(activities)

    def set_energy(
        self,
        level: EnergyLevel,
        note: str = "",
    ) -> Context:
        """Set current energy level."""
        context = self.get_current()
        context.energy_level = level
        context.energy_note = note
        context.timestamp = datetime.now()

        self.store.save_context(context)
        self.store.log_activity(
            "energy_set",
            "context",
            None,
            {
                "level": level.value,
                "time_of_day": context.time_of_day,
                "day_of_week": context.day_of_week,
            },
        )

        # Update energy pattern
        self._update_energy_pattern(context)

        return context

    def _update_energy_pattern(self, context: Context) -> None:
        """Update energy patterns based on new data point."""
        # Find or create pattern for this time slot
        patterns = self.store.get_patterns(pattern_type="energy")

        pattern_key = f"{context.day_of_week}_{context.time_of_day}"
        matching_pattern = None

        for p in patterns:
            if (
                p.conditions.get("day_of_week") == context.day_of_week
                and p.conditions.get("time_of_day") == context.time_of_day
            ):
                matching_pattern = p
                break

        if matching_pattern:
            # Update existing pattern
            matching_pattern.observations.append({
                "energy": context.energy_level.value,
                "timestamp": context.timestamp.isoformat(),
            })
            matching_pattern.sample_size = len(matching_pattern.observations)
            matching_pattern.last_updated = datetime.now()

            # Recalculate typical energy
            energy_counts: dict[str, int] = {}
            for obs in matching_pattern.observations[-20:]:  # Last 20 observations
                e = obs["energy"]
                energy_counts[e] = energy_counts.get(e, 0) + 1

            if energy_counts:
                typical = max(energy_counts.items(), key=lambda x: x[1])[0]
                matching_pattern.conditions["typical_energy"] = typical
                matching_pattern.confidence = max(energy_counts.values()) / sum(energy_counts.values())

            self.store.save_pattern(matching_pattern)
        else:
            # Create new pattern
            new_pattern = Pattern(
                pattern_type="energy",
                description=f"Energy pattern for {context.time_of_day} on day {context.day_of_week}",
                conditions={
                    "day_of_week": context.day_of_week,
                    "time_of_day": context.time_of_day,
                    "typical_energy": context.energy_level.value,
                },
                observations=[{
                    "energy": context.energy_level.value,
                    "timestamp": context.timestamp.isoformat(),
                }],
                confidence=0.5,  # Low confidence for new pattern
                sample_size=1,
            )
            self.store.save_pattern(new_pattern)

    def set_location(self, location: str) -> Context:
        """Set current location."""
        context = self.get_current()
        context.location = location
        context.timestamp = datetime.now()
        self.store.save_context(context)
        return context

    def set_focus_mode(self, enabled: bool) -> Context:
        """Set focus mode on/off."""
        context = self.get_current()
        context.focus_mode = enabled
        context.timestamp = datetime.now()
        self.store.save_context(context)
        self.store.log_activity(
            "focus_mode_changed",
            "context",
            None,
            {"enabled": enabled},
        )
        return context

    def record_task_completed(self, task_id: str) -> Context:
        """Record that a task was completed."""
        context = self.get_current()
        context.last_task_completed = task_id
        context.tasks_completed_today += 1
        context.timestamp = datetime.now()
        self.store.save_context(context)
        return context

    def record_break(self) -> Context:
        """Record that user is taking a break."""
        context = self.get_current()
        context.last_break = datetime.now()
        context.timestamp = datetime.now()
        self.store.save_context(context)
        self.store.log_activity("break_taken", "context", None)
        return context

    def set_available_time(self, minutes: int) -> Context:
        """Set available time until next commitment."""
        context = self.get_current()
        context.available_minutes = minutes
        context.timestamp = datetime.now()
        self.store.save_context(context)
        return context

    def get_energy_history(
        self,
        days: int = 7,
    ) -> list[dict[str, Any]]:
        """Get energy history for analysis."""
        since = datetime.now() - timedelta(days=days)
        activities = self.store.get_activity_log(
            event_type="energy_set",
            since=since,
        )
        return activities

    def get_energy_summary(self) -> dict[str, Any]:
        """Get summary of energy patterns."""
        patterns = self.store.get_patterns(pattern_type="energy", min_confidence=0.5)

        summary = {
            "patterns_found": len(patterns),
            "by_time_of_day": {},
            "best_times": [],
            "low_energy_times": [],
        }

        for pattern in patterns:
            tod = pattern.conditions.get("time_of_day", "unknown")
            energy = pattern.conditions.get("typical_energy", "unknown")
            confidence = pattern.confidence

            if tod not in summary["by_time_of_day"]:
                summary["by_time_of_day"][tod] = []

            summary["by_time_of_day"][tod].append({
                "day": pattern.conditions.get("day_of_week"),
                "energy": energy,
                "confidence": confidence,
            })

            if energy in ("peak", "good") and confidence > 0.6:
                summary["best_times"].append({
                    "time_of_day": tod,
                    "day_of_week": pattern.conditions.get("day_of_week"),
                    "energy": energy,
                })
            elif energy in ("low", "depleted") and confidence > 0.6:
                summary["low_energy_times"].append({
                    "time_of_day": tod,
                    "day_of_week": pattern.conditions.get("day_of_week"),
                    "energy": energy,
                })

        return summary

    def should_suggest_break(self) -> tuple[bool, str]:
        """Check if a break should be suggested."""
        context = self.get_current()

        # Check time since last break
        if context.last_break:
            minutes_since_break = (datetime.now() - context.last_break).total_seconds() / 60
            if minutes_since_break > 90:
                return True, "It's been over 90 minutes since your last break"

        # Check tasks completed
        if context.tasks_completed_today >= 5:
            # Check if break was taken recently
            if not context.last_break or (datetime.now() - context.last_break).total_seconds() / 60 > 60:
                return True, f"You've completed {context.tasks_completed_today} tasks - consider a break"

        # Check energy level
        if context.energy_level == EnergyLevel.DEPLETED:
            return True, "Your energy is depleted - take a break"

        return False, ""

    def get_productivity_score(self) -> dict[str, Any]:
        """Calculate productivity score for today."""
        context = self.get_current()
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        # Get today's activities
        task_completions = self.store.get_activity_log(
            event_type="task_completed",
            since=today_start,
        )

        # Calculate metrics
        tasks_done = len(task_completions)
        estimated_time = 0
        actual_time = 0

        for activity in task_completions:
            if activity["data"]:
                est = activity["data"].get("estimated")
                act = activity["data"].get("actual")
                if est:
                    estimated_time += est
                if act:
                    actual_time += act

        # Simple scoring
        score = min(100, tasks_done * 15)  # Base points for tasks

        # Bonus for estimation accuracy
        if estimated_time > 0 and actual_time > 0:
            accuracy = min(estimated_time, actual_time) / max(estimated_time, actual_time)
            score += int(accuracy * 20)

        return {
            "score": score,
            "tasks_completed": tasks_done,
            "estimated_minutes": estimated_time,
            "actual_minutes": actual_time,
            "current_energy": context.energy_level.value,
            "breaks_taken": self._count_breaks_today(),
        }

    def _count_breaks_today(self) -> int:
        """Count breaks taken today."""
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        activities = self.store.get_activity_log(
            event_type="break_taken",
            since=today_start,
        )
        return len(activities)
