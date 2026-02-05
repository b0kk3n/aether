"""Checklist service - business logic for checklists."""

from datetime import datetime
from typing import Optional

from aether.core.models import (
    Checklist,
    ChecklistCreate,
    ChecklistUpdate,
    ChecklistWithChores,
    ChoreStatus,
    generate_id,
)
from aether.core.database import get_db
from aether.core.services.chore_service import ChoreService


class ChecklistService:
    """Service for checklist operations."""

    @staticmethod
    def create(checklist: ChecklistCreate) -> Checklist:
        """Create a new checklist with chores."""
        checklist_id = generate_id()
        now = datetime.now().isoformat()

        with get_db() as conn:
            # Create checklist
            conn.execute(
                """
                INSERT INTO checklists (id, name, description, icon, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (checklist_id, checklist.name, checklist.description, checklist.icon, now),
            )

            # Add chores to checklist
            for i, chore_id in enumerate(checklist.chore_ids):
                conn.execute(
                    """
                    INSERT INTO checklist_chores (checklist_id, chore_id, sort_order)
                    VALUES (?, ?, ?)
                    """,
                    (checklist_id, chore_id, i),
                )

        return Checklist(
            id=checklist_id,
            name=checklist.name,
            description=checklist.description,
            icon=checklist.icon,
            created_at=datetime.fromisoformat(now),
        )

    @staticmethod
    def get_by_id(checklist_id: str) -> Optional[Checklist]:
        """Get a checklist by ID (without chores)."""
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM checklists WHERE id = ?", (checklist_id,)
            ).fetchone()

        if not row:
            return None

        return Checklist(
            id=row["id"],
            name=row["name"],
            description=row["description"] or "",
            icon=row["icon"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    @staticmethod
    def get_by_name(name: str) -> Optional[Checklist]:
        """Get a checklist by name."""
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM checklists WHERE name = ?", (name,)
            ).fetchone()

        if not row:
            return None

        return Checklist(
            id=row["id"],
            name=row["name"],
            description=row["description"] or "",
            icon=row["icon"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    @staticmethod
    def get_all() -> list[Checklist]:
        """Get all checklists."""
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM checklists ORDER BY name"
            ).fetchall()

        return [
            Checklist(
                id=row["id"],
                name=row["name"],
                description=row["description"] or "",
                icon=row["icon"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]

    @staticmethod
    def get_with_chores(checklist_id: str) -> Optional[ChecklistWithChores]:
        """Get a checklist with live chore status.

        This is the main way to view a checklist - it shows the actual
        current status of each chore referenced in the checklist.
        """
        checklist = ChecklistService.get_by_id(checklist_id)
        if not checklist:
            return None

        with get_db() as conn:
            # Get chores in this checklist with their room names
            rows = conn.execute(
                """
                SELECT c.*, r.name as room_name, cc.sort_order
                FROM checklist_chores cc
                JOIN chores c ON cc.chore_id = c.id
                LEFT JOIN rooms r ON c.room_id = r.id
                WHERE cc.checklist_id = ?
                ORDER BY cc.sort_order
                """,
                (checklist_id,),
            ).fetchall()

        chores = []
        total_minutes = 0
        overdue_count = 0

        for row in rows:
            chore = ChoreService._row_to_chore_status(row, row["room_name"])
            chores.append(chore)
            total_minutes += chore.estimated_minutes
            if chore.is_overdue:
                overdue_count += 1

        return ChecklistWithChores(
            id=checklist.id,
            name=checklist.name,
            description=checklist.description,
            icon=checklist.icon,
            created_at=checklist.created_at,
            chores=chores,
            total_minutes=total_minutes,
            overdue_count=overdue_count,
        )

    @staticmethod
    def get_chore_ids(checklist_id: str) -> list[str]:
        """Get list of chore IDs in a checklist."""
        with get_db() as conn:
            rows = conn.execute(
                """
                SELECT chore_id FROM checklist_chores
                WHERE checklist_id = ?
                ORDER BY sort_order
                """,
                (checklist_id,),
            ).fetchall()

        return [row["chore_id"] for row in rows]

    @staticmethod
    def update(checklist_id: str, update: ChecklistUpdate) -> Optional[Checklist]:
        """Update a checklist."""
        checklist = ChecklistService.get_by_id(checklist_id)
        if not checklist:
            return None

        with get_db() as conn:
            # Update basic fields
            updates = []
            params = []

            if update.name is not None:
                updates.append("name = ?")
                params.append(update.name)
            if update.description is not None:
                updates.append("description = ?")
                params.append(update.description)
            if update.icon is not None:
                updates.append("icon = ?")
                params.append(update.icon)

            if updates:
                params.append(checklist_id)
                conn.execute(
                    f"UPDATE checklists SET {', '.join(updates)} WHERE id = ?",
                    params,
                )

            # Update chores if provided
            if update.chore_ids is not None:
                # Remove existing chores
                conn.execute(
                    "DELETE FROM checklist_chores WHERE checklist_id = ?",
                    (checklist_id,),
                )

                # Add new chores
                for i, chore_id in enumerate(update.chore_ids):
                    conn.execute(
                        """
                        INSERT INTO checklist_chores (checklist_id, chore_id, sort_order)
                        VALUES (?, ?, ?)
                        """,
                        (checklist_id, chore_id, i),
                    )

        return ChecklistService.get_by_id(checklist_id)

    @staticmethod
    def add_chore(checklist_id: str, chore_id: str) -> bool:
        """Add a chore to a checklist."""
        with get_db() as conn:
            # Get max sort order
            max_order = conn.execute(
                "SELECT MAX(sort_order) FROM checklist_chores WHERE checklist_id = ?",
                (checklist_id,),
            ).fetchone()[0] or -1

            try:
                conn.execute(
                    """
                    INSERT INTO checklist_chores (checklist_id, chore_id, sort_order)
                    VALUES (?, ?, ?)
                    """,
                    (checklist_id, chore_id, max_order + 1),
                )
                return True
            except Exception:
                return False

    @staticmethod
    def remove_chore(checklist_id: str, chore_id: str) -> bool:
        """Remove a chore from a checklist."""
        with get_db() as conn:
            cursor = conn.execute(
                "DELETE FROM checklist_chores WHERE checklist_id = ? AND chore_id = ?",
                (checklist_id, chore_id),
            )
            return cursor.rowcount > 0

    @staticmethod
    def delete(checklist_id: str) -> bool:
        """Delete a checklist."""
        with get_db() as conn:
            cursor = conn.execute(
                "DELETE FROM checklists WHERE id = ?", (checklist_id,)
            )
            return cursor.rowcount > 0
