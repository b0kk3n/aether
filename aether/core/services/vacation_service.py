"""Vacation service - pauses recurrence countdowns for eligible chores while away."""

from datetime import datetime

from aether.core.models import (
    ChoreEligibility,
    VacationEndResult,
    VacationLogEntry,
    VacationStatus,
    is_vacation_eligible,
    generate_id,
)
from aether.core.database import get_db


class VacationService:
    """Service for the global vacation-mode toggle."""

    @staticmethod
    def get_status() -> VacationStatus:
        """Get current vacation mode state, including live elapsed days."""
        with get_db() as conn:
            row = conn.execute(
                "SELECT is_active, started_at FROM vacation_state WHERE id = 1"
            ).fetchone()

        is_active = bool(row["is_active"]) if row else False
        started_at = (
            datetime.fromisoformat(row["started_at"])
            if row and row["started_at"]
            else None
        )
        days_elapsed = (
            (datetime.now() - started_at).total_seconds() / 86400
            if is_active and started_at
            else 0.0
        )

        return VacationStatus(is_active=is_active, started_at=started_at, days_elapsed=days_elapsed)

    @staticmethod
    def start() -> VacationStatus:
        """Start vacation mode. Eligible chores' countdowns freeze immediately."""
        if VacationService.get_status().is_active:
            raise ValueError("Vacation mode is already active")

        now = datetime.now().isoformat()
        with get_db() as conn:
            conn.execute(
                "UPDATE vacation_state SET is_active = 1, started_at = ? WHERE id = 1",
                (now,),
            )

        return VacationService.get_status()

    @staticmethod
    def end() -> VacationEndResult:
        """End vacation mode.

        Bakes the elapsed vacation days into vacation_offset_days for every
        currently-eligible active chore, so their due dates shift forward by
        exactly the length of the trip.
        """
        status = VacationService.get_status()
        if not status.is_active or not status.started_at:
            raise ValueError("Vacation mode is not active")

        elapsed_days = (datetime.now() - status.started_at).total_seconds() / 86400

        with get_db() as conn:
            chore_rows = conn.execute(
                """
                SELECT c.id, c.vacation_override, cat.is_vacation_pausable_default
                FROM chores c
                LEFT JOIN categories cat ON c.category_id = cat.id
                WHERE c.is_active = 1
                """
            ).fetchall()

            eligible_ids = [
                row["id"]
                for row in chore_rows
                if is_vacation_eligible(
                    bool(row["is_vacation_pausable_default"]) if row["is_vacation_pausable_default"] is not None else False,
                    row["vacation_override"] or None,
                )
            ]

            if eligible_ids:
                placeholders = ", ".join("?" for _ in eligible_ids)
                conn.execute(
                    f"UPDATE chores SET vacation_offset_days = vacation_offset_days + ? "
                    f"WHERE id IN ({placeholders})",
                    (elapsed_days, *eligible_ids),
                )

            conn.execute(
                "UPDATE vacation_state SET is_active = 0, started_at = NULL WHERE id = 1"
            )

            conn.execute(
                """
                INSERT INTO vacation_log (id, started_at, ended_at, days_elapsed, chores_affected)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    generate_id(),
                    status.started_at.isoformat(),
                    datetime.now().isoformat(),
                    elapsed_days,
                    len(eligible_ids),
                ),
            )

        return VacationEndResult(days_elapsed=elapsed_days, chores_affected=len(eligible_ids))

    @staticmethod
    def get_eligible_preview() -> list[ChoreEligibility]:
        """Non-mutating preview of which active chores would pause right now."""
        with get_db() as conn:
            rows = conn.execute(
                """
                SELECT c.id, c.name, c.vacation_override,
                       cat.name AS cat_name, cat.is_vacation_pausable_default
                FROM chores c
                LEFT JOIN categories cat ON c.category_id = cat.id
                WHERE c.is_active = 1
                ORDER BY c.name
                """
            ).fetchall()

        return [
            ChoreEligibility(
                id=row["id"],
                name=row["name"],
                category_name=row["cat_name"] or "",
                vacation_override=row["vacation_override"] or None,
                vacation_eligible=is_vacation_eligible(
                    bool(row["is_vacation_pausable_default"]) if row["is_vacation_pausable_default"] is not None else False,
                    row["vacation_override"] or None,
                ),
            )
            for row in rows
        ]

    @staticmethod
    def get_history(limit: int = 20) -> list[VacationLogEntry]:
        """Past vacation records, most recent first."""
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM vacation_log ORDER BY ended_at DESC LIMIT ?", (limit,)
            ).fetchall()

        return [
            VacationLogEntry(
                id=row["id"],
                started_at=datetime.fromisoformat(row["started_at"]),
                ended_at=datetime.fromisoformat(row["ended_at"]),
                days_elapsed=row["days_elapsed"],
                chores_affected=row["chores_affected"],
            )
            for row in rows
        ]
