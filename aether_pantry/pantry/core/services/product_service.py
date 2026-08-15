"""Product service - business logic for pantry products."""

from datetime import datetime
from typing import Optional
import sqlite3

from pantry.core.models import (
    Product,
    ProductCreate,
    ProductUpdate,
    ProductStatus,
    ProductSummary,
    generate_id,
)
from pantry.core.database import get_db


class ProductService:
    """Service for product operations."""

    @staticmethod
    def _row_to_product(row: sqlite3.Row) -> Product:
        """Convert a database row (from products_effective) to a Product model."""
        row_keys = row.keys()
        return Product(
            id=row["id"],
            name=row["name"],
            category_id=row["category_id"],
            interval_days=row["interval_days"],
            status=ProductStatus(row["status"]),
            last_checked=datetime.fromisoformat(row["last_checked"]),
            vacation_paused_days=row["effective_paused_days"] if "effective_paused_days" in row_keys and row["effective_paused_days"] is not None else 0.0,
            category_name=row["cat_name"] if "cat_name" in row_keys else None,
            category_icon=row["cat_icon"] if "cat_icon" in row_keys else None,
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    @staticmethod
    def _row_to_summary(row: sqlite3.Row) -> ProductSummary:
        product = ProductService._row_to_product(row)
        return ProductSummary(
            id=product.id,
            name=product.name,
            category_id=product.category_id,
            category_name=product.category_name,
            category_icon=product.category_icon,
            status=product.status,
            effective_status=product.effective_status,
            last_checked=product.last_checked,
            interval_days=product.interval_days,
        )

    @staticmethod
    def create(product: ProductCreate) -> Product:
        """Create a new product, starting in_stock as of now."""
        product_id = generate_id()
        now = datetime.now().isoformat()

        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO products (id, name, category_id, interval_days, status, last_checked, created_at)
                VALUES (?, ?, ?, ?, 'in_stock', ?, ?)
                """,
                (product_id, product.name, product.category_id, product.interval_days, now, now),
            )

        return ProductService.get_by_id(product_id)

    @staticmethod
    def get_by_id(product_id: str) -> Optional[Product]:
        """Get a product by ID."""
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM products_effective WHERE id = ?", (product_id,)
            ).fetchone()

        return ProductService._row_to_product(row) if row else None

    @staticmethod
    def find_by_name(name: str) -> Optional[Product]:
        """Case-insensitive, trimmed exact-match lookup by name.

        Used by grocery list matching - not fuzzy/substring, an exact name
        match only.
        """
        name = name.strip()
        if not name:
            return None

        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM products_effective WHERE name = ? COLLATE NOCASE",
                (name,),
            ).fetchone()

        return ProductService._row_to_product(row) if row else None

    @staticmethod
    def get_all(category_id: Optional[str] = None, status: Optional[ProductStatus] = None) -> list[Product]:
        """Get products with optional filters."""
        conditions = []
        params = []

        if category_id is not None:
            conditions.append("category_id = ?")
            params.append(category_id)
        if status is not None:
            conditions.append("status = ?")
            params.append(status.value)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        with get_db() as conn:
            rows = conn.execute(
                f"SELECT * FROM products_effective WHERE {where_clause} ORDER BY name",
                params,
            ).fetchall()

        return [ProductService._row_to_product(row) for row in rows]

    @staticmethod
    def set_status(product_id: str, status: ProductStatus) -> Optional[Product]:
        """Flip a product's status.

        Any transition to in_stock - whether from a grocery check-off, a
        checklist walk, or a manual "postpone" tap in All Products - resets
        last_checked to now and restarts the interval clock. Transitions to
        low/out never touch last_checked. This makes postpone and restocking
        the same action at the data layer: both mean "as of right now, this
        is fine."
        """
        product = ProductService.get_by_id(product_id)
        if not product:
            return None

        with get_db() as conn:
            if status == ProductStatus.IN_STOCK:
                conn.execute(
                    "UPDATE products SET status = ?, last_checked = ? WHERE id = ?",
                    (status.value, datetime.now().isoformat(), product_id),
                )
            else:
                conn.execute(
                    "UPDATE products SET status = ? WHERE id = ?",
                    (status.value, product_id),
                )

        return ProductService.get_by_id(product_id)

    @staticmethod
    def update(product_id: str, update: ProductUpdate) -> Optional[Product]:
        """Update a product's name/category/interval. Never touches status."""
        product = ProductService.get_by_id(product_id)
        if not product:
            return None

        updates = []
        params = []

        if update.name is not None:
            updates.append("name = ?")
            params.append(update.name)
        if "category_id" in update.model_fields_set:
            updates.append("category_id = ?")
            params.append(update.category_id)
        if "interval_days" in update.model_fields_set:
            updates.append("interval_days = ?")
            params.append(update.interval_days)

        if updates:
            params.append(product_id)
            with get_db() as conn:
                conn.execute(
                    f"UPDATE products SET {', '.join(updates)} WHERE id = ?",
                    params,
                )

        return ProductService.get_by_id(product_id)

    @staticmethod
    def delete(product_id: str) -> bool:
        """Delete a product. Any grocery list lines linked to it become free text."""
        with get_db() as conn:
            conn.execute(
                "UPDATE grocery_list_items SET product_id = NULL WHERE product_id = ?",
                (product_id,),
            )
            cursor = conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
            return cursor.rowcount > 0

    @staticmethod
    def get_needing_attention() -> list[Product]:
        """Products whose effective status is low/out - for grocery-list surfacing."""
        products = ProductService.get_all()
        return [p for p in products if p.effective_status != ProductStatus.IN_STOCK]
