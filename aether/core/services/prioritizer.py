"""Prioritizer - smart task recommendation based on context.

Handles:
- "I have X minutes" mode
- Morning briefings
- Dashboard overviews
"""

import random
from datetime import datetime
from typing import Optional

from aether.core.models import (
    ChoreStatus,
    Briefing,
    QuickCleanList,
    Dashboard,
    DashboardRoom,
    Priority,
)
from aether.core.database import get_db
from aether.core.services.room_service import RoomService
from aether.core.services.chore_service import ChoreService
from aether.core.services.app_settings_service import AppSettingsService


def _build_greeting(hour: int, household_name: Optional[str], suggested_count: int, total_overdue: int) -> str:
    """Pick a greeting phrase based on time of day and how the home's doing.

    Busy days get the plain time-based greeting (no nagging about backlog);
    caught-up and light days get a bit of personality instead. A household
    name, if set, is appended to any variant.
    """
    if hour < 12:
        period = "morning"
    elif hour < 17:
        period = "afternoon"
    else:
        period = "evening"
    time_greeting = f"Good {period}"

    if suggested_count == 0:
        phrase = random.choice(["All caught up", "Nothing on the list", "Home's looking great"])
    elif suggested_count <= 2 and total_overdue == 0:
        phrase = random.choice([time_greeting, "Light day ahead", "Just a little something today"])
    else:
        phrase = time_greeting

    if household_name:
        phrase = f"{phrase}, {household_name}"

    return phrase


class Prioritizer:
    """Smart prioritization for chores."""

    @staticmethod
    def get_prioritized_chores(limit: Optional[int] = None) -> list[ChoreStatus]:
        """Get all chores sorted by urgency.

        Urgency is calculated based on:
        - How overdue the chore is
        - The chore's priority (based on interval)
        - Never-done chores are most urgent
        """
        with get_db() as conn:
            rows = conn.execute(
                """
                SELECT c.*, r.name as room_name
                FROM chores_effective c
                LEFT JOIN rooms r ON c.room_id = r.id
                WHERE c.is_active = 1
                AND (
                    -- Never done = always show
                    c.last_completed_at IS NULL
                    -- Overdue or due within 3 days
                    OR julianday('now') - julianday(c.last_completed_at) >= c.interval_days + c.effective_paused_days - 3
                )
                ORDER BY
                    -- Never done = highest priority
                    CASE WHEN c.last_completed_at IS NULL THEN 0 ELSE 1 END,
                    -- Then by how overdue (most overdue first)
                    CASE WHEN c.last_completed_at IS NULL THEN -999
                         ELSE julianday(c.last_completed_at) + c.interval_days + c.effective_paused_days - julianday('now')
                    END,
                    -- House-wide tasks before room-specific at same urgency
                    CASE WHEN c.room_id IS NULL THEN 0 ELSE 1 END,
                    -- Then by interval (shorter = higher priority)
                    c.interval_days
                """
            ).fetchall()

        chores = [ChoreService._row_to_chore_status(row, row["room_name"]) for row in rows]

        if limit:
            return chores[:limit]
        return chores

    @staticmethod
    def get_quick_clean(minutes: int) -> QuickCleanList:
        """Get prioritized chores that fit in available time.

        The "I have X minutes" feature. Returns highest-impact chores
        that can be completed within the time budget.
        """
        all_chores = Prioritizer.get_prioritized_chores()

        selected = []
        total_minutes = 0
        rooms_affected = set()

        for chore in all_chores:
            if total_minutes + chore.estimated_minutes <= minutes:
                selected.append(chore)
                total_minutes += chore.estimated_minutes
                if chore.room_name:
                    rooms_affected.add(chore.room_name)

        # Generate impact summary
        if len(rooms_affected) == 0:
            impact = "Focus on house-wide tasks"
        elif len(rooms_affected) == 1:
            impact = f"This will freshen up {list(rooms_affected)[0]}"
        else:
            impact = f"This will freshen up {len(rooms_affected)} rooms"

        return QuickCleanList(
            available_minutes=minutes,
            chores=selected,
            total_minutes=total_minutes,
            impact_summary=impact,
        )

    @staticmethod
    def get_morning_briefing() -> Briefing:
        """Generate morning briefing with the top 3 most urgent chores.

        Friendly tone, focused on highest-impact items - independent of the
        "I have..." time-budget feature, which is a separate way to browse.
        """
        top_urgent = Prioritizer.get_prioritized_chores(limit=3)
        total_minutes = sum(c.estimated_minutes for c in top_urgent)

        dashboard = Prioritizer.get_dashboard()
        settings = AppSettingsService.get()

        greeting = _build_greeting(
            datetime.now().hour,
            settings.household_name,
            len(top_urgent),
            dashboard.total_overdue,
        )

        return Briefing(
            greeting=greeting,
            suggested_chores=top_urgent,
            total_minutes=total_minutes,
            overall_freshness=dashboard.overall_freshness,
        )

    @staticmethod
    def get_dashboard() -> Dashboard:
        """Get full dashboard overview.

        Shows all rooms with freshness, house-wide chores, and summary stats.
        """
        # Get room summaries
        rooms = RoomService.get_dashboard_rooms()

        # Get house-wide chores
        house_wide = ChoreService.get_house_wide()

        # Calculate totals
        total_overdue = sum(r.overdue_count for r in rooms)
        total_overdue += sum(1 for c in house_wide if c.is_overdue)

        # Calculate overall freshness
        all_freshness = [r.freshness_percent for r in rooms if r.chore_count > 0]
        if house_wide:
            all_freshness.extend(c.freshness_percent for c in house_wide)

        overall_freshness = int(sum(all_freshness) / len(all_freshness)) if all_freshness else 100

        # Count chores due soon (next 3 days)
        due_soon = ChoreService.get_due_soon(days=3)

        return Dashboard(
            rooms=rooms,
            house_wide_chores=house_wide,
            overall_freshness=overall_freshness,
            total_overdue=total_overdue,
            chores_due_soon=len(due_soon),
        )

    @staticmethod
    def get_by_category(category_id: str) -> list[ChoreStatus]:
        """Get all chores of a specific category, sorted by urgency.

        Useful for "vacuum day" or "dusting session" type activities.
        """
        with get_db() as conn:
            rows = conn.execute(
                """
                SELECT c.*, r.name as room_name
                FROM chores_effective c
                LEFT JOIN rooms r ON c.room_id = r.id
                WHERE c.is_active = 1 AND c.category_id = ?
                ORDER BY
                    CASE WHEN c.last_completed_at IS NULL THEN 0 ELSE 1 END,
                    CASE WHEN c.last_completed_at IS NULL THEN -999
                         ELSE julianday(c.last_completed_at) + c.interval_days + c.effective_paused_days - julianday('now')
                    END
                """,
                (category_id,),
            ).fetchall()

        return [ChoreService._row_to_chore_status(row, row["room_name"]) for row in rows]
