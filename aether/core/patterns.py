"""Pattern learning and recognition system."""

from datetime import datetime, timedelta
from typing import Any
from collections import defaultdict

from ..data.models import Pattern, Task, TaskStatus, EnergyLevel
from ..data.store import Store


class PatternLearner:
    """Learns patterns from user behavior to improve recommendations."""

    # Minimum samples needed for a pattern to be considered reliable
    MIN_SAMPLES = 5
    # Confidence threshold for patterns to be used
    CONFIDENCE_THRESHOLD = 0.6

    def __init__(self, store: Store):
        """Initialize with data store."""
        self.store = store

    def learn_from_completion(self, task: Task) -> None:
        """Learn from a completed task."""
        if not task.completed_at:
            return

        # Record completion context
        context = {
            "task_type": task.task_type.value,
            "area": task.area,
            "priority": task.priority.value,
            "hour": task.completed_at.hour,
            "day_of_week": task.completed_at.weekday(),
            "time_of_day": self._get_time_of_day(task.completed_at.hour),
            "estimated": task.estimated_minutes,
            "actual": task.actual_minutes,
            "energy_required": task.energy_required.value,
        }

        # Update task completion patterns
        self._update_completion_pattern(context)

        # Update estimation accuracy if we have both values
        if task.estimated_minutes and task.actual_minutes:
            self._update_estimation_pattern(task)

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

    def _update_completion_pattern(self, context: dict[str, Any]) -> None:
        """Update task completion patterns."""
        # Pattern key: when do you complete tasks of this type?
        pattern_key = f"completion_{context['task_type']}_{context['time_of_day']}"

        patterns = self.store.get_patterns(pattern_type="task_completion")
        matching = None

        for p in patterns:
            if (
                p.conditions.get("task_type") == context["task_type"]
                and p.conditions.get("time_of_day") == context["time_of_day"]
            ):
                matching = p
                break

        if matching:
            # Update existing pattern
            matching.observations.append({
                "timestamp": datetime.now().isoformat(),
                **context,
            })
            matching.sample_size = len(matching.observations)
            matching.last_updated = datetime.now()

            # Recalculate confidence based on consistency
            matching.confidence = self._calculate_confidence(matching.observations)
            self.store.save_pattern(matching)
        else:
            # Create new pattern
            pattern = Pattern(
                pattern_type="task_completion",
                description=f"Complete {context['task_type']} tasks in {context['time_of_day']}",
                conditions={
                    "task_type": context["task_type"],
                    "time_of_day": context["time_of_day"],
                },
                observations=[{
                    "timestamp": datetime.now().isoformat(),
                    **context,
                }],
                confidence=0.3,  # Low initial confidence
                sample_size=1,
            )
            self.store.save_pattern(pattern)

    def _calculate_confidence(self, observations: list[dict[str, Any]]) -> float:
        """Calculate pattern confidence based on observations."""
        if len(observations) < self.MIN_SAMPLES:
            return 0.3 + (len(observations) / self.MIN_SAMPLES) * 0.2

        # Check recent vs older observations for trend
        recent = observations[-10:]
        if len(recent) < 3:
            return 0.5

        # Simple consistency check - same behavior recently
        return min(0.9, 0.5 + (len(recent) / 20))

    def _update_estimation_pattern(self, task: Task) -> None:
        """Update estimation accuracy patterns."""
        if not task.estimated_minutes or not task.actual_minutes:
            return

        ratio = task.actual_minutes / task.estimated_minutes
        pattern_key = f"estimation_{task.task_type.value}"

        patterns = self.store.get_patterns(pattern_type="estimation")
        matching = None

        for p in patterns:
            if p.conditions.get("task_type") == task.task_type.value:
                matching = p
                break

        observation = {
            "timestamp": datetime.now().isoformat(),
            "estimated": task.estimated_minutes,
            "actual": task.actual_minutes,
            "ratio": ratio,
        }

        if matching:
            matching.observations.append(observation)
            matching.sample_size = len(matching.observations)
            matching.last_updated = datetime.now()

            # Calculate average ratio
            ratios = [o["ratio"] for o in matching.observations[-20:]]
            avg_ratio = sum(ratios) / len(ratios)
            matching.conditions["avg_ratio"] = avg_ratio
            matching.confidence = self._calculate_confidence(matching.observations)
            self.store.save_pattern(matching)
        else:
            pattern = Pattern(
                pattern_type="estimation",
                description=f"Estimation accuracy for {task.task_type.value} tasks",
                conditions={
                    "task_type": task.task_type.value,
                    "avg_ratio": ratio,
                },
                observations=[observation],
                confidence=0.3,
                sample_size=1,
            )
            self.store.save_pattern(pattern)

    def get_estimation_factor(self, task_type: str) -> float:
        """Get estimation adjustment factor for a task type.

        Returns a multiplier to apply to estimates based on past accuracy.
        """
        patterns = self.store.get_patterns(
            pattern_type="estimation",
            min_confidence=self.CONFIDENCE_THRESHOLD,
        )

        for p in patterns:
            if p.conditions.get("task_type") == task_type:
                return p.conditions.get("avg_ratio", 1.0)

        return 1.0  # No adjustment

    def get_best_times(self, task_type: str | None = None) -> list[dict[str, Any]]:
        """Get best times for completing tasks."""
        patterns = self.store.get_patterns(
            pattern_type="task_completion",
            min_confidence=self.CONFIDENCE_THRESHOLD,
        )

        results = []
        for p in patterns:
            if task_type and p.conditions.get("task_type") != task_type:
                continue

            results.append({
                "task_type": p.conditions.get("task_type"),
                "time_of_day": p.conditions.get("time_of_day"),
                "confidence": p.confidence,
                "sample_size": p.sample_size,
            })

        # Sort by confidence
        results.sort(key=lambda x: x["confidence"], reverse=True)
        return results

    def analyze_productivity(self, days: int = 30) -> dict[str, Any]:
        """Analyze productivity patterns over time."""
        since = datetime.now() - timedelta(days=days)

        # Get completion activities
        activities = self.store.get_activity_log(
            event_type="task_completed",
            since=since,
        )

        analysis = {
            "total_completed": len(activities),
            "by_day_of_week": defaultdict(int),
            "by_time_of_day": defaultdict(int),
            "by_hour": defaultdict(int),
            "completion_streaks": [],
            "most_productive_day": None,
            "most_productive_time": None,
        }

        for activity in activities:
            ts = datetime.fromisoformat(activity["timestamp"])
            analysis["by_day_of_week"][ts.strftime("%A")] += 1
            analysis["by_time_of_day"][self._get_time_of_day(ts.hour)] += 1
            analysis["by_hour"][ts.hour] += 1

        # Find most productive periods
        if analysis["by_day_of_week"]:
            analysis["most_productive_day"] = max(
                analysis["by_day_of_week"].items(),
                key=lambda x: x[1],
            )[0]

        if analysis["by_time_of_day"]:
            analysis["most_productive_time"] = max(
                analysis["by_time_of_day"].items(),
                key=lambda x: x[1],
            )[0]

        # Convert defaultdicts to regular dicts
        analysis["by_day_of_week"] = dict(analysis["by_day_of_week"])
        analysis["by_time_of_day"] = dict(analysis["by_time_of_day"])
        analysis["by_hour"] = dict(analysis["by_hour"])

        return analysis

    def suggest_optimal_schedule(self) -> dict[str, list[str]]:
        """Suggest optimal task scheduling based on patterns."""
        patterns = self.store.get_patterns(
            pattern_type="task_completion",
            min_confidence=self.CONFIDENCE_THRESHOLD,
        )

        schedule: dict[str, list[str]] = {
            "morning": [],
            "afternoon": [],
            "evening": [],
            "night": [],
        }

        for p in patterns:
            time_of_day = p.conditions.get("time_of_day")
            task_type = p.conditions.get("task_type")

            if time_of_day and task_type:
                schedule[time_of_day].append(task_type)

        return schedule

    def detect_anomalies(self) -> list[dict[str, Any]]:
        """Detect anomalies or changes in patterns."""
        anomalies = []
        patterns = self.store.get_patterns(active_only=True)

        for pattern in patterns:
            if len(pattern.observations) < 10:
                continue

            # Check for recent deviation from pattern
            recent = pattern.observations[-5:]
            older = pattern.observations[-15:-5]

            if not older:
                continue

            # Simple anomaly detection: check if recent behavior differs
            # This is a placeholder for more sophisticated analysis
            if pattern.pattern_type == "energy":
                recent_energies = [o.get("energy") for o in recent if o.get("energy")]
                older_energies = [o.get("energy") for o in older if o.get("energy")]

                if recent_energies and older_energies:
                    # Check for shift in typical energy
                    recent_common = max(set(recent_energies), key=recent_energies.count)
                    older_common = max(set(older_energies), key=older_energies.count)

                    if recent_common != older_common:
                        anomalies.append({
                            "type": "energy_shift",
                            "description": f"Energy pattern shifted from {older_common} to {recent_common}",
                            "pattern_id": pattern.id,
                        })

        return anomalies
