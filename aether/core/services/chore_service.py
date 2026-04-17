"""Chore service - business logic for chores."""

from datetime import datetime
from typing import Optional
import sqlite3

from aether.core.models import (
    Chore,
    ChoreCreate,
    ChoreUpdate,
    ChoreWithRoom,
    ChoreStatus,
    CompletionLog,
    CompletionLogCreate,
    Room,
    Category,
    Priority,
    priority_from_interval,
    generate_id,
)
from aether.core.database import get_db


class ChoreService:
    """Service for chore operations."""

    @staticmethod
    def _row_to_chore(row: sqlite3.Row) -> Chore:
        """Convert database row to Chore model."""
        return Chore(
            id=row["id"],
            name=row["name"],
            room_id=row["room_id"],
            interval_days=row["interval_days"],
            estimated_minutes=row["estimated_minutes"],
            category=Category(row["category"]),
            notes=row["notes"] or "",
            is_active=bool(row["is_active"]),
            last_completed_at=datetime.fromisoformat(row["last_completed_at"]) if row["last_completed_at"] else None,
            streak=row["streak"],
            completion_count=row["completion_count"],
            duration_confirmed=bool(row["duration_confirmed"]),
            duration_confirmations=row["duration_confirmations"],
            interval_confirmed=bool(row["interval_confirmed"]) if row["interval_confirmed"] is not None else False,
            interval_confirmations=row["interval_confirmations"] if row["interval_confirmations"] is not None else 0,
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    @staticmethod
    def _row_to_chore_status(row: sqlite3.Row, room_name: Optional[str] = None) -> ChoreStatus:
        """Convert database row to ChoreStatus model."""
        chore = ChoreService._row_to_chore(row)
        return ChoreStatus(
            id=chore.id,
            name=chore.name,
            room_name=room_name,
            priority=chore.priority,
            category=chore.category,
            days_until_due=chore.days_until_due,
            freshness_percent=chore.freshness_percent,
            is_overdue=chore.is_overdue,
            last_completed_at=chore.last_completed_at,
            estimated_minutes=chore.estimated_minutes,
            streak=chore.streak,
        )

    @staticmethod
    def create(chore: ChoreCreate) -> Chore:
        """Create a new chore."""
        chore_id = generate_id()
        now = datetime.now().isoformat()

        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO chores (
                    id, name, room_id, interval_days, estimated_minutes,
                    category, notes, is_active, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chore_id,
                    chore.name,
                    chore.room_id,
                    chore.interval_days,
                    chore.estimated_minutes,
                    chore.category.value,
                    chore.notes,
                    1 if chore.is_active else 0,
                    now,
                ),
            )

        return ChoreService.get_by_id(chore_id)

    @staticmethod
    def get_by_id(chore_id: str) -> Optional[Chore]:
        """Get a chore by ID."""
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM chores WHERE id = ?", (chore_id,)
            ).fetchone()

        if not row:
            return None

        return ChoreService._row_to_chore(row)

    @staticmethod
    def get_by_name_and_room(name: str, room_id: Optional[str]) -> Optional[Chore]:
        """Get a chore by name and room."""
        with get_db() as conn:
            if room_id:
                row = conn.execute(
                    "SELECT * FROM chores WHERE name = ? AND room_id = ?",
                    (name, room_id),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT * FROM chores WHERE name = ? AND room_id IS NULL",
                    (name,),
                ).fetchone()

        if not row:
            return None

        return ChoreService._row_to_chore(row)

    @staticmethod
    def get_all(
        room_id: Optional[str] = None,
        category: Optional[Category] = None,
        active_only: bool = True,
        include_house_wide: bool = True,
    ) -> list[Chore]:
        """Get chores with optional filters."""
        conditions = []
        params = []

        if active_only:
            conditions.append("is_active = 1")

        if room_id is not None:
            if include_house_wide:
                conditions.append("(room_id = ? OR room_id IS NULL)")
            else:
                conditions.append("room_id = ?")
            params.append(room_id)

        if category is not None:
            conditions.append("category = ?")
            params.append(category.value)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        with get_db() as conn:
            rows = conn.execute(
                f"SELECT * FROM chores WHERE {where_clause} ORDER BY interval_days, name",
                params,
            ).fetchall()

        return [ChoreService._row_to_chore(row) for row in rows]

    @staticmethod
    def get_all_with_room() -> list[ChoreWithRoom]:
        """Get all chores with room details."""
        with get_db() as conn:
            rows = conn.execute(
                """
                SELECT c.*, r.id as r_id, r.name as r_name, r.icon as r_icon,
                       r.sort_order as r_sort_order, r.created_at as r_created_at
                FROM chores c
                LEFT JOIN rooms r ON c.room_id = r.id
                WHERE c.is_active = 1
                ORDER BY c.interval_days, c.name
                """
            ).fetchall()

        result = []
        for row in rows:
            chore = ChoreService._row_to_chore(row)
            room = None
            if row["r_id"]:
                room = Room(
                    id=row["r_id"],
                    name=row["r_name"],
                    icon=row["r_icon"],
                    sort_order=row["r_sort_order"],
                    created_at=datetime.fromisoformat(row["r_created_at"]),
                )
            result.append(ChoreWithRoom(**chore.model_dump(), room=room))

        return result

    @staticmethod
    def get_for_room(room_id: str) -> list[ChoreStatus]:
        """Get all chores for a specific room with status."""
        with get_db() as conn:
            # Get room name
            room_row = conn.execute(
                "SELECT name FROM rooms WHERE id = ?", (room_id,)
            ).fetchone()
            room_name = room_row["name"] if room_row else None

            rows = conn.execute(
                """
                SELECT * FROM chores
                WHERE room_id = ? AND is_active = 1
                ORDER BY
                    CASE WHEN last_completed_at IS NULL THEN 0
                         ELSE julianday(last_completed_at) + interval_days - julianday('now')
                    END,
                    interval_days
                """,
                (room_id,),
            ).fetchall()

        return [ChoreService._row_to_chore_status(row, room_name) for row in rows]

    @staticmethod
    def get_house_wide() -> list[ChoreStatus]:
        """Get all house-wide chores (no room assigned)."""
        with get_db() as conn:
            rows = conn.execute(
                """
                SELECT * FROM chores
                WHERE room_id IS NULL AND is_active = 1
                ORDER BY
                    CASE WHEN last_completed_at IS NULL THEN 0
                         ELSE julianday(last_completed_at) + interval_days - julianday('now')
                    END,
                    interval_days
                """
            ).fetchall()

        return [ChoreService._row_to_chore_status(row, None) for row in rows]

    @staticmethod
    def get_overdue() -> list[ChoreStatus]:
        """Get all overdue chores."""
        with get_db() as conn:
            rows = conn.execute(
                """
                SELECT c.*, r.name as room_name
                FROM chores c
                LEFT JOIN rooms r ON c.room_id = r.id
                WHERE c.is_active = 1
                AND (
                    c.last_completed_at IS NULL
                    OR julianday('now') - julianday(c.last_completed_at) > c.interval_days
                )
                ORDER BY
                    CASE WHEN c.last_completed_at IS NULL THEN 999
                         ELSE julianday('now') - julianday(c.last_completed_at) - c.interval_days
                    END DESC
                """
            ).fetchall()

        return [ChoreService._row_to_chore_status(row, row["room_name"]) for row in rows]

    @staticmethod
    def get_due_soon(days: int = 3) -> list[ChoreStatus]:
        """Get chores due within specified days."""
        with get_db() as conn:
            rows = conn.execute(
                """
                SELECT c.*, r.name as room_name
                FROM chores c
                LEFT JOIN rooms r ON c.room_id = r.id
                WHERE c.is_active = 1
                AND c.last_completed_at IS NOT NULL
                AND julianday(c.last_completed_at) + c.interval_days - julianday('now') <= ?
                AND julianday(c.last_completed_at) + c.interval_days - julianday('now') > 0
                ORDER BY julianday(c.last_completed_at) + c.interval_days
                """,
                (days,),
            ).fetchall()

        return [ChoreService._row_to_chore_status(row, row["room_name"]) for row in rows]

    @staticmethod
    def update(chore_id: str, update: ChoreUpdate) -> Optional[Chore]:
        """Update a chore."""
        chore = ChoreService.get_by_id(chore_id)
        if not chore:
            return None

        updates = []
        params = []

        if update.name is not None:
            updates.append("name = ?")
            params.append(update.name)
        if "room_id" in update.model_fields_set:
            updates.append("room_id = ?")
            params.append(update.room_id)
        if update.interval_days is not None:
            updates.append("interval_days = ?")
            params.append(update.interval_days)
            # Reset interval confirmation when schedule changes
            updates.append("interval_confirmed = 0")
            updates.append("interval_confirmations = 0")
        if update.estimated_minutes is not None:
            updates.append("estimated_minutes = ?")
            params.append(update.estimated_minutes)
            # Reset duration confirmation when estimate changes
            updates.append("duration_confirmed = 0")
            updates.append("duration_confirmations = 0")
        if update.category is not None:
            updates.append("category = ?")
            params.append(update.category.value)
        if update.notes is not None:
            updates.append("notes = ?")
            params.append(update.notes)
        if update.is_active is not None:
            updates.append("is_active = ?")
            params.append(1 if update.is_active else 0)

        if updates:
            params.append(chore_id)
            with get_db() as conn:
                conn.execute(
                    f"UPDATE chores SET {', '.join(updates)} WHERE id = ?",
                    params,
                )

        return ChoreService.get_by_id(chore_id)

    @staticmethod
    def complete(
        chore_id: str,
        actual_minutes: Optional[int] = None,
        notes: str = "",
        duration_was_accurate: Optional[bool] = None,
    ) -> Optional[Chore]:
        """Mark a chore as complete.

        Args:
            chore_id: The chore to complete
            actual_minutes: How long it actually took (optional)
            notes: Any notes about this completion
            duration_was_accurate: User feedback on duration estimate.
                If True twice, duration is confirmed.
                If False, could prompt for actual time.
        """
        chore = ChoreService.get_by_id(chore_id)
        if not chore:
            return None

        now = datetime.now()
        log_id = generate_id()

        with get_db() as conn:
            # Log the completion
            conn.execute(
                """
                INSERT INTO completion_logs (id, chore_id, completed_at, actual_minutes, notes)
                VALUES (?, ?, ?, ?, ?)
                """,
                (log_id, chore_id, now.isoformat(), actual_minutes, notes),
            )

            # Calculate new streak
            new_streak = chore.streak
            if chore.last_completed_at:
                days_since = (now - chore.last_completed_at).days
                if days_since <= chore.interval_days + 2:  # 2 day grace period
                    new_streak += 1
                else:
                    new_streak = 1  # Reset streak if too late
            else:
                new_streak = 1

            # Handle duration confirmation
            duration_confirmed = chore.duration_confirmed
            duration_confirmations = chore.duration_confirmations

            if duration_was_accurate is True and not duration_confirmed:
                duration_confirmations += 1
                if duration_confirmations >= 2:
                    duration_confirmed = True

            # Update chore
            conn.execute(
                """
                UPDATE chores SET
                    last_completed_at = ?,
                    streak = ?,
                    completion_count = completion_count + 1,
                    duration_confirmed = ?,
                    duration_confirmations = ?
                WHERE id = ?
                """,
                (
                    now.isoformat(),
                    new_streak,
                    1 if duration_confirmed else 0,
                    duration_confirmations,
                    chore_id,
                ),
            )

        return ChoreService.get_by_id(chore_id)

    @staticmethod
    def get_completion_history(chore_id: str, limit: int = 10) -> list[CompletionLog]:
        """Get completion history for a chore."""
        with get_db() as conn:
            rows = conn.execute(
                """
                SELECT * FROM completion_logs
                WHERE chore_id = ?
                ORDER BY completed_at DESC
                LIMIT ?
                """,
                (chore_id, limit),
            ).fetchall()

        return [
            CompletionLog(
                id=row["id"],
                chore_id=row["chore_id"],
                completed_at=datetime.fromisoformat(row["completed_at"]),
                actual_minutes=row["actual_minutes"],
                notes=row["notes"] or "",
            )
            for row in rows
        ]

    @staticmethod
    def delete(chore_id: str) -> bool:
        """Delete a chore and its completion history."""
        with get_db() as conn:
            cursor = conn.execute("DELETE FROM chores WHERE id = ?", (chore_id,))
            return cursor.rowcount > 0

    @staticmethod
    def should_ask_duration(chore_id: str) -> bool:
        """Check if we should ask about duration accuracy.

        Returns True if:
        - Duration is not yet confirmed
        - This will be an odd-numbered completion (1st, 3rd, 5th, etc.)

        Note: Called BEFORE completion, so we check if current count is even
        (0, 2, 4...) which becomes odd (1, 3, 5...) after completing.
        """
        chore = ChoreService.get_by_id(chore_id)
        if not chore:
            return False

        if chore.duration_confirmed:
            return False

        # Ask every other time until confirmed
        return chore.completion_count % 2 == 1

    @staticmethod
    def should_ask_interval(chore_id: str) -> bool:
        """Check if we should ask about interval accuracy.

        Asks every 4th completion (offset from duration checks which ask every 2nd)
        so the two prompts never appear on the same completion.
        """
        chore = ChoreService.get_by_id(chore_id)
        if not chore:
            return False

        if chore.interval_confirmed:
            return False

        return chore.completion_count % 4 == 2

    @staticmethod
    def record_interval_feedback(
        chore_id: str,
        was_accurate: bool,
        actual_days: Optional[int] = None,
    ) -> Optional[Chore]:
        """Record user feedback on interval accuracy.

        If actual_days is provided and was_accurate is False, updates the
        interval and resets confirmation counters.
        """
        chore = ChoreService.get_by_id(chore_id)
        if not chore or chore.interval_confirmed:
            return chore

        interval_confirmations = chore.interval_confirmations
        interval_confirmed = chore.interval_confirmed

        if was_accurate:
            interval_confirmations += 1
            if interval_confirmations >= 2:
                interval_confirmed = True

        with get_db() as conn:
            if not was_accurate and actual_days and actual_days > 0:
                conn.execute(
                    """UPDATE chores SET interval_days = ?,
                       interval_confirmed = 0, interval_confirmations = 0
                       WHERE id = ?""",
                    (actual_days, chore_id),
                )
            else:
                conn.execute(
                    "UPDATE chores SET interval_confirmed = ?, interval_confirmations = ? WHERE id = ?",
                    (1 if interval_confirmed else 0, interval_confirmations, chore_id),
                )

        return ChoreService.get_by_id(chore_id)

    @staticmethod
    def record_duration_feedback(
        chore_id: str,
        was_accurate: bool,
        actual_minutes: Optional[int] = None,
    ) -> Optional[Chore]:
        """Record user feedback on duration estimate accuracy.

        If actual_minutes is provided and was_accurate is False, updates the
        estimate and resets confirmation counters.
        """
        chore = ChoreService.get_by_id(chore_id)
        if not chore or chore.duration_confirmed:
            return chore

        duration_confirmations = chore.duration_confirmations
        duration_confirmed = chore.duration_confirmed

        if was_accurate:
            duration_confirmations += 1
            if duration_confirmations >= 2:
                duration_confirmed = True

        with get_db() as conn:
            if not was_accurate and actual_minutes and actual_minutes > 0:
                # Update estimate and reset counters so the new estimate gets confirmed
                conn.execute(
                    """UPDATE chores SET estimated_minutes = ?,
                       duration_confirmed = 0, duration_confirmations = 0
                       WHERE id = ?""",
                    (actual_minutes, chore_id),
                )
            else:
                conn.execute(
                    "UPDATE chores SET duration_confirmed = ?, duration_confirmations = ? WHERE id = ?",
                    (1 if duration_confirmed else 0, duration_confirmations, chore_id),
                )

        return ChoreService.get_by_id(chore_id)
