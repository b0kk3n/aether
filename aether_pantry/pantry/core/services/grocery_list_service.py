"""Grocery list service - the hero feature: add anything, anytime.

Each line is either linked (matches an existing product by name) or free
text. Matching is resolved once, at add time, via a case-insensitive exact
match - never fuzzy/substring, and never re-resolved later even if a
matching product is created afterward.
"""

from datetime import datetime
from typing import Optional

from pantry.core.models import (
    GroceryListItem,
    ProductStatus,
    generate_id,
)
from pantry.core.database import get_db
from pantry.core.services.product_service import ProductService


class GroceryListService:
    """Service for the live grocery/to-buy list."""

    @staticmethod
    def _row_to_item(row) -> GroceryListItem:
        linked_name = None
        linked_status = None
        linked_effective_status = None
        if row["product_id"]:
            product = ProductService.get_by_id(row["product_id"])
            if product:
                linked_name = product.name
                linked_status = product.status
                linked_effective_status = product.effective_status

        return GroceryListItem(
            id=row["id"],
            raw_text=row["raw_text"],
            product_id=row["product_id"],
            linked_product_name=linked_name,
            linked_product_status=linked_status,
            linked_product_effective_status=linked_effective_status,
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    @staticmethod
    def add_item(raw_text: str) -> GroceryListItem:
        """Add a line to the grocery list, resolving a product match now."""
        raw_text = raw_text.strip()
        item_id = generate_id()
        now = datetime.now().isoformat()

        matched = ProductService.find_by_name(raw_text)
        product_id = matched.id if matched else None

        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO grocery_list_items (id, raw_text, product_id, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (item_id, raw_text, product_id, now),
            )

        return GroceryListService.get_by_id(item_id)

    @staticmethod
    def get_by_id(item_id: str) -> Optional[GroceryListItem]:
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM grocery_list_items WHERE id = ?", (item_id,)
            ).fetchone()

        return GroceryListService._row_to_item(row) if row else None

    @staticmethod
    def get_all() -> list[GroceryListItem]:
        """All current lines, oldest first."""
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM grocery_list_items ORDER BY created_at"
            ).fetchall()

        return [GroceryListService._row_to_item(row) for row in rows]

    @staticmethod
    def check_off(item_id: str) -> bool:
        """Check off a line.

        Linked: resets the product to in_stock (restarting its interval,
        via ProductService.set_status's unified restock rule), then removes
        the line. Free text: just removes the line. Either way the row is
        deleted - the grocery list is a live queue, not a purchase log.
        """
        item = GroceryListService.get_by_id(item_id)
        if not item:
            return False

        if item.product_id:
            ProductService.set_status(item.product_id, ProductStatus.IN_STOCK)

        with get_db() as conn:
            conn.execute("DELETE FROM grocery_list_items WHERE id = ?", (item_id,))

        return True

    @staticmethod
    def delete_item(item_id: str) -> bool:
        """Remove a line without triggering the linked-product effect (typo/changed mind)."""
        with get_db() as conn:
            cursor = conn.execute("DELETE FROM grocery_list_items WHERE id = ?", (item_id,))
            return cursor.rowcount > 0

    @staticmethod
    def add_from_product(product_id: str) -> Optional[GroceryListItem]:
        """One-tap 'add to list' for a needing-attention product."""
        product = ProductService.get_by_id(product_id)
        if not product:
            return None
        return GroceryListService.add_item(product.name)
