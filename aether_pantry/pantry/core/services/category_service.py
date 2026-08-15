"""Category service - business logic for pantry categories."""

from datetime import datetime
from typing import Optional

from pantry.core.models import (
    Category,
    CategoryCreate,
    CategoryUpdate,
    generate_id,
)
from pantry.core.database import get_db


class CategoryService:
    """Service for category operations."""

    @staticmethod
    def _row_to_category(row) -> Category:
        return Category(
            id=row["id"],
            name=row["name"],
            icon=row["icon"],
            sort_order=row["sort_order"],
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
                INSERT INTO categories (id, name, icon, sort_order, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (category_id, category.name, category.icon, category.sort_order, now),
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

        if updates:
            params.append(category_id)
            with get_db() as conn:
                conn.execute(
                    f"UPDATE categories SET {', '.join(updates)} WHERE id = ?",
                    params,
                )

        return CategoryService.get_by_id(category_id)

    @staticmethod
    def delete(category_id: str) -> tuple[bool, Optional[str]]:
        """Delete a category. Blocked while any product references it.

        Products can be uncategorized (unlike chores' rooms, there's no
        distinction that would break) - but deleting a category that's
        still in use would silently uncategorize products the user may not
        expect, so we require reassigning first. Returns (success, error).
        """
        with get_db() as conn:
            in_use = conn.execute(
                "SELECT COUNT(*) FROM products WHERE category_id = ?", (category_id,)
            ).fetchone()[0]
            if in_use > 0:
                return False, f"{in_use} product(s) use this category; reassign or delete them first."

            cursor = conn.execute("DELETE FROM categories WHERE id = ?", (category_id,))
            return cursor.rowcount > 0, None
