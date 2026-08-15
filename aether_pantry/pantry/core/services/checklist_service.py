"""Checklist service - business logic for cross-cutting product checklists."""

from datetime import datetime
from typing import Optional

from pantry.core.models import (
    Checklist,
    ChecklistCreate,
    ChecklistUpdate,
    ChecklistWithProducts,
    ProductStatus,
    ProductSummary,
    generate_id,
)
from pantry.core.database import get_db
from pantry.core.services.product_service import ProductService


class ChecklistService:
    """Service for checklist operations."""

    @staticmethod
    def create(checklist: ChecklistCreate) -> Checklist:
        """Create a new checklist with products."""
        checklist_id = generate_id()
        now = datetime.now().isoformat()

        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO checklists (id, name, description, icon, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (checklist_id, checklist.name, checklist.description, checklist.icon, now),
            )

            for product_id in checklist.product_ids:
                conn.execute(
                    "INSERT OR IGNORE INTO checklist_products (checklist_id, product_id) VALUES (?, ?)",
                    (checklist_id, product_id),
                )

        return ChecklistService.get_by_id(checklist_id)

    @staticmethod
    def get_by_id(checklist_id: str) -> Optional[Checklist]:
        """Get a checklist by ID (without products), including status counts."""
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM checklists WHERE id = ?", (checklist_id,)
            ).fetchone()
            if not row:
                return None

            counts = conn.execute(
                """
                SELECT
                    SUM(CASE WHEN p.status = 'out' THEN 1 ELSE 0 END) as out_count,
                    SUM(CASE WHEN p.status = 'low' THEN 1 ELSE 0 END) as low_count,
                    SUM(CASE WHEN p.status = 'in_stock' THEN 1 ELSE 0 END) as in_stock_count
                FROM checklist_products cp
                JOIN products p ON cp.product_id = p.id
                WHERE cp.checklist_id = ?
                """,
                (checklist_id,),
            ).fetchone()

        return Checklist(
            id=row["id"],
            name=row["name"],
            description=row["description"] or "",
            icon=row["icon"],
            created_at=datetime.fromisoformat(row["created_at"]),
            out_count=counts["out_count"] or 0,
            low_count=counts["low_count"] or 0,
            in_stock_count=counts["in_stock_count"] or 0,
        )

    @staticmethod
    def get_all() -> list[Checklist]:
        """Get all checklists with summary status counts, ordered by name."""
        with get_db() as conn:
            rows = conn.execute("SELECT id FROM checklists ORDER BY name").fetchall()

        return [ChecklistService.get_by_id(row["id"]) for row in rows]

    @staticmethod
    def get_with_products(checklist_id: str) -> Optional[ChecklistWithProducts]:
        """Get a checklist with live product status.

        Sort order: out -> low -> in_stock, then by staleness (oldest
        last_checked first) within each tier - same walk order whether
        standing at a market stall or in your own cupboard.
        """
        checklist = ChecklistService.get_by_id(checklist_id)
        if not checklist:
            return None

        with get_db() as conn:
            rows = conn.execute(
                "SELECT product_id FROM checklist_products WHERE checklist_id = ?",
                (checklist_id,),
            ).fetchall()

        products = [ProductService.get_by_id(row["product_id"]) for row in rows]
        products = [p for p in products if p is not None]

        tier_order = {ProductStatus.OUT: 0, ProductStatus.LOW: 1, ProductStatus.IN_STOCK: 2}
        products.sort(key=lambda p: (tier_order[p.effective_status], p.last_checked))

        summaries = [
            ProductSummary(
                id=p.id,
                name=p.name,
                category_id=p.category_id,
                category_name=p.category_name,
                category_icon=p.category_icon,
                status=p.status,
                effective_status=p.effective_status,
                last_checked=p.last_checked,
                interval_days=p.interval_days,
            )
            for p in products
        ]

        return ChecklistWithProducts(
            id=checklist.id,
            name=checklist.name,
            description=checklist.description,
            icon=checklist.icon,
            created_at=checklist.created_at,
            out_count=checklist.out_count,
            low_count=checklist.low_count,
            in_stock_count=checklist.in_stock_count,
            products=summaries,
        )

    @staticmethod
    def get_product_ids(checklist_id: str) -> list[str]:
        """Get list of product IDs in a checklist."""
        with get_db() as conn:
            rows = conn.execute(
                "SELECT product_id FROM checklist_products WHERE checklist_id = ?",
                (checklist_id,),
            ).fetchall()

        return [row["product_id"] for row in rows]

    @staticmethod
    def update(checklist_id: str, update: ChecklistUpdate) -> Optional[Checklist]:
        """Update a checklist."""
        checklist = ChecklistService.get_by_id(checklist_id)
        if not checklist:
            return None

        with get_db() as conn:
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

            if update.product_ids is not None:
                conn.execute(
                    "DELETE FROM checklist_products WHERE checklist_id = ?",
                    (checklist_id,),
                )
                for product_id in update.product_ids:
                    conn.execute(
                        "INSERT OR IGNORE INTO checklist_products (checklist_id, product_id) VALUES (?, ?)",
                        (checklist_id, product_id),
                    )

        return ChecklistService.get_by_id(checklist_id)

    @staticmethod
    def add_products(checklist_id: str, product_ids: list[str]) -> int:
        """Add multiple products to a checklist at once. Returns count actually added."""
        if not product_ids:
            return 0

        added = 0
        with get_db() as conn:
            for product_id in product_ids:
                cursor = conn.execute(
                    "INSERT OR IGNORE INTO checklist_products (checklist_id, product_id) VALUES (?, ?)",
                    (checklist_id, product_id),
                )
                added += cursor.rowcount

        return added

    @staticmethod
    def add_product(checklist_id: str, product_id: str) -> bool:
        """Add a single product to a checklist."""
        return ChecklistService.add_products(checklist_id, [product_id]) == 1

    @staticmethod
    def remove_product(checklist_id: str, product_id: str) -> bool:
        """Remove a product from a checklist."""
        with get_db() as conn:
            cursor = conn.execute(
                "DELETE FROM checklist_products WHERE checklist_id = ? AND product_id = ?",
                (checklist_id, product_id),
            )
            return cursor.rowcount > 0

    @staticmethod
    def delete(checklist_id: str) -> bool:
        """Delete a checklist."""
        with get_db() as conn:
            cursor = conn.execute("DELETE FROM checklists WHERE id = ?", (checklist_id,))
            return cursor.rowcount > 0
