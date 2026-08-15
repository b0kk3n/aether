"""Vacation service - pauses every product's interval clock while away.

Unlike the chores app's vacation mode, there's no per-item eligibility
layer here - the spec calls for freezing every interval clock
unconditionally, so every product carrying an interval_days is eligible,
no exceptions/overrides.
"""

from datetime import datetime

from pantry.core.models import (
    ProductEligibility,
    VacationEndResult,
    VacationLogEntry,
    VacationStatus,
    generate_id,
)
from pantry.core.database import get_db


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
        """Start vacation mode. Every product's interval clock freezes immediately."""
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
        product carrying an interval, so their next_due shifts forward by
        exactly the length of the trip - clocks freeze, they don't reset.
        """
        status = VacationService.get_status()
        if not status.is_active or not status.started_at:
            raise ValueError("Vacation mode is not active")

        elapsed_days = (datetime.now() - status.started_at).total_seconds() / 86400

        with get_db() as conn:
            eligible_ids = [
                row["id"]
                for row in conn.execute(
                    "SELECT id FROM products WHERE interval_days IS NOT NULL"
                ).fetchall()
            ]

            if eligible_ids:
                placeholders = ", ".join("?" for _ in eligible_ids)
                conn.execute(
                    f"UPDATE products SET vacation_offset_days = vacation_offset_days + ? "
                    f"WHERE id IN ({placeholders})",
                    (elapsed_days, *eligible_ids),
                )

            conn.execute(
                "UPDATE vacation_state SET is_active = 0, started_at = NULL WHERE id = 1"
            )

            conn.execute(
                """
                INSERT INTO vacation_log (id, started_at, ended_at, days_elapsed, products_affected)
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

        return VacationEndResult(days_elapsed=elapsed_days, products_affected=len(eligible_ids))

    @staticmethod
    def get_eligible_preview() -> list[ProductEligibility]:
        """Non-mutating preview of which products would pause right now."""
        with get_db() as conn:
            rows = conn.execute(
                "SELECT id, name, interval_days FROM products ORDER BY name"
            ).fetchall()

        return [
            ProductEligibility(
                id=row["id"],
                name=row["name"],
                interval_days=row["interval_days"],
                vacation_eligible=row["interval_days"] is not None,
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
                products_affected=row["products_affected"],
            )
            for row in rows
        ]
