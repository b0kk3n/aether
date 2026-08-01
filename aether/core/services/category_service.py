"""Category service - business logic for chore categories."""

from datetime import datetime
from typing import Optional

from aether.core.models import (
    Category,
    CategoryCreate,
    CategoryUpdate,
    generate_id,
)
from aether.core.database import get_db


class CategoryService:
    """Service for category operations."""

    @staticmethod
    def _row_to_category(row) -> Category:
        return Category(
            id=row["id"],
            name=row["name"],
            icon=row["icon"],
            sort_order=row["sort_order"],
            is_vacation_pausable_default=bool(row["is_vacation_pausable_default"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    @staticmethod
    def create(category: CategoryCreate) -> Category:
        """Create a new category."""
        category_id = generate_id()
        now = datetime.now().isoformat()

        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO categories (id, name, icon, sort_order, is_vacation_pausable_default, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    category_id,
                    category.name,
                    category.icon,
                    category.sort_order,
                    1 if category.is_vacation_pausable_default else 0,
                    now,
                ),
            )

        return CategoryService.get_by_id(category_id)

    @staticmethod
    def get_by_id(category_id: str) -> Optional[Category]:
        """Get a category by ID."""
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM categories WHERE id = ?", (category_id,)
            ).fetchone()

        return CategoryService._row_to_category(row) if row else None

    @staticmethod
    def get_all() -> list[Category]:
        """Get all categories ordered by sort_order."""
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM categories ORDER BY sort_order, name"
            ).fetchall()

        return [CategoryService._row_to_category(row) for row in rows]

    @staticmethod
    def update(category_id: str, update: CategoryUpdate) -> Optional[Category]:
        """Update a category."""
        category = CategoryService.get_by_id(category_id)
        if not category:
            return None

        updates = []
        params = []

        if update.name is not None:
            updates.append("name = ?")
            params.append(update.name)
        if update.icon is not None:
            updates.append("icon = ?")
            params.append(update.icon)
        if update.sort_order is not None:
            updates.append("sort_order = ?")
            params.append(update.sort_order)
        if update.is_vacation_pausable_default is not None:
            updates.append("is_vacation_pausable_default = ?")
            params.append(1 if update.is_vacation_pausable_default else 0)

        if updates:
            params.append(category_id)
            with get_db() as conn:
                conn.execute(
                    f"UPDATE categories SET {', '.join(updates)} WHERE id = ?",
                    params,
                )

        return CategoryService.get_by_id(category_id)

    @staticmethod
    def reorder(category_ids: list[str]) -> list[Category]:
        """Reorder categories by providing list of IDs in desired order."""
        with get_db() as conn:
            for i, category_id in enumerate(category_ids):
                conn.execute(
                    "UPDATE categories SET sort_order = ? WHERE id = ?",
                    (i, category_id),
                )

        return CategoryService.get_all()

    @staticmethod
    def delete(category_id: str) -> tuple[bool, Optional[str]]:
        """Delete a category. Blocked while any chore references it.

        A null category_id has no meaningful "uncategorized" fallback (unlike
        a room, where house-wide is a valid state) and would silently disable
        vacation-pause eligibility for those chores. Returns (success, error).
        """
        with get_db() as conn:
            in_use = conn.execute(
                "SELECT COUNT(*) FROM chores WHERE category_id = ?", (category_id,)
            ).fetchone()[0]
            if in_use > 0:
                return False, f"{in_use} chore(s) use this category; reassign or delete them first."

            cursor = conn.execute("DELETE FROM categories WHERE id = ?", (category_id,))
            return cursor.rowcount > 0, None
