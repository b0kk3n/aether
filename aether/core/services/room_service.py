"""Room service - business logic for rooms."""

from datetime import datetime
from typing import Optional
import sqlite3

from aether.core.models import (
    Room,
    RoomCreate,
    RoomWithFreshness,
    DashboardRoom,
    generate_id,
)
from aether.core.database import get_db


class RoomService:
    """Service for room operations."""

    @staticmethod
    def create(room: RoomCreate) -> Room:
        """Create a new room."""
        room_id = generate_id()
        now = datetime.now().isoformat()

        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO rooms (id, name, icon, sort_order, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (room_id, room.name, room.icon, room.sort_order, now),
            )

        return Room(
            id=room_id,
            name=room.name,
            icon=room.icon,
            sort_order=room.sort_order,
            created_at=datetime.fromisoformat(now),
        )

    @staticmethod
    def get_by_id(room_id: str) -> Optional[Room]:
        """Get a room by ID."""
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM rooms WHERE id = ?", (room_id,)
            ).fetchone()

        if not row:
            return None

        return Room(
            id=row["id"],
            name=row["name"],
            icon=row["icon"],
            sort_order=row["sort_order"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    @staticmethod
    def get_by_name(name: str) -> Optional[Room]:
        """Get a room by name."""
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM rooms WHERE name = ?", (name,)
            ).fetchone()

        if not row:
            return None

        return Room(
            id=row["id"],
            name=row["name"],
            icon=row["icon"],
            sort_order=row["sort_order"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    @staticmethod
    def get_all() -> list[Room]:
        """Get all rooms ordered by sort_order."""
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM rooms ORDER BY sort_order, name"
            ).fetchall()

        return [
            Room(
                id=row["id"],
                name=row["name"],
                icon=row["icon"],
                sort_order=row["sort_order"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]

    @staticmethod
    def get_all_with_freshness() -> list[RoomWithFreshness]:
        """Get all rooms with calculated freshness scores."""
        rooms = RoomService.get_all()
        result = []

        with get_db() as conn:
            for room in rooms:
                # Get chore stats for this room
                stats = conn.execute(
                    """
                    SELECT
                        COUNT(*) as chore_count,
                        AVG(
                            CASE
                                WHEN (interval_days + effective_paused_days) - (julianday('now') - julianday(COALESCE(last_completed_at, created_at))) <= 0
                                    THEN 0
                                WHEN (interval_days + effective_paused_days) - (julianday('now') - julianday(COALESCE(last_completed_at, created_at))) > 0.5 * (interval_days + effective_paused_days)
                                    THEN 100
                                ELSE CAST(
                                    (((interval_days + effective_paused_days) - (julianday('now') - julianday(COALESCE(last_completed_at, created_at)))) / (0.5 * (interval_days + effective_paused_days))) * 100
                                    AS INTEGER
                                )
                            END
                        ) as avg_freshness,
                        SUM(
                            CASE
                                WHEN julianday('now') - julianday(COALESCE(last_completed_at, created_at)) > (interval_days + effective_paused_days) THEN 1
                                ELSE 0
                            END
                        ) as overdue_count
                    FROM chores_effective
                    WHERE room_id = ? AND is_active = 1
                    """,
                    (room.id,),
                ).fetchone()

                # Handle None vs 0 for freshness (0 is valid, None means no chores)
                avg_fresh = stats["avg_freshness"]
                freshness = int(avg_fresh) if avg_fresh is not None else 100

                result.append(
                    RoomWithFreshness(
                        id=room.id,
                        name=room.name,
                        icon=room.icon,
                        sort_order=room.sort_order,
                        created_at=room.created_at,
                        freshness_percent=freshness,
                        chore_count=stats["chore_count"] or 0,
                        overdue_count=stats["overdue_count"] or 0,
                    )
                )

        return result

    @staticmethod
    def get_dashboard_rooms() -> list[DashboardRoom]:
        """Get room summaries for dashboard."""
        rooms_with_freshness = RoomService.get_all_with_freshness()
        return [
            DashboardRoom(
                id=r.id,
                name=r.name,
                icon=r.icon,
                freshness_percent=r.freshness_percent,
                overdue_count=r.overdue_count,
                chore_count=r.chore_count,
            )
            for r in rooms_with_freshness
        ]

    @staticmethod
    def update(room_id: str, name: Optional[str] = None, icon: Optional[str] = None, sort_order: Optional[int] = None) -> Optional[Room]:
        """Update a room."""
        room = RoomService.get_by_id(room_id)
        if not room:
            return None

        updates = []
        params = []

        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if icon is not None:
            updates.append("icon = ?")
            params.append(icon)
        if sort_order is not None:
            updates.append("sort_order = ?")
            params.append(sort_order)

        if updates:
            params.append(room_id)
            with get_db() as conn:
                conn.execute(
                    f"UPDATE rooms SET {', '.join(updates)} WHERE id = ?",
                    params,
                )

        return RoomService.get_by_id(room_id)

    @staticmethod
    def delete(room_id: str) -> bool:
        """Delete a room. Chores will have room_id set to NULL."""
        with get_db() as conn:
            cursor = conn.execute("DELETE FROM rooms WHERE id = ?", (room_id,))
            return cursor.rowcount > 0

    @staticmethod
    def reorder(room_ids: list[str]) -> list[Room]:
        """Reorder rooms by providing list of IDs in desired order."""
        with get_db() as conn:
            for i, room_id in enumerate(room_ids):
                conn.execute(
                    "UPDATE rooms SET sort_order = ? WHERE id = ?",
                    (i, room_id),
                )

        return RoomService.get_all()
