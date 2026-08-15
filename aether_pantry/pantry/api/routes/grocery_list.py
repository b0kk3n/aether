"""Grocery list API routes - the hero feature."""

from fastapi import APIRouter, HTTPException

from pantry.core import (
    GroceryListItem,
    GroceryListItemCreate,
    GroceryListService,
)

router = APIRouter(prefix="/grocery-list", tags=["grocery-list"])


@router.get("", response_model=list[GroceryListItem])
def list_grocery_items():
    """Get all current grocery list lines."""
    return GroceryListService.get_all()


@router.post("", response_model=GroceryListItem, status_code=201)
def add_grocery_item(item: GroceryListItemCreate):
    """Add a line. Resolves a product match now (linked vs free text)."""
    return GroceryListService.add_item(item.raw_text)


@router.post("/from-product/{product_id}", response_model=GroceryListItem, status_code=201)
def add_grocery_item_from_product(product_id: str):
    """One-tap 'add to list' for a needing-attention product."""
    item = GroceryListService.add_from_product(product_id)
    if not item:
        raise HTTPException(status_code=404, detail="Product not found")
    return item


@router.post("/{item_id}/check-off", status_code=204)
def check_off_grocery_item(item_id: str):
    """Check off a line - resets the linked product (if any) and removes the line."""
    if not GroceryListService.check_off(item_id):
        raise HTTPException(status_code=404, detail="Grocery list item not found")


@router.delete("/{item_id}", status_code=204)
def delete_grocery_item(item_id: str):
    """Remove a line without checking it off (typo/changed mind)."""
    if not GroceryListService.delete_item(item_id):
        raise HTTPException(status_code=404, detail="Grocery list item not found")
