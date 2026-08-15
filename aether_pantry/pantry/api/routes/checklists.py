"""Checklist API routes."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from pantry.core import (
    Checklist,
    ChecklistCreate,
    ChecklistUpdate,
    ChecklistWithProducts,
    ChecklistService,
)

router = APIRouter(prefix="/checklists", tags=["checklists"])


class BulkAddProductsRequest(BaseModel):
    """Request body for adding multiple products to a checklist at once."""
    product_ids: list[str]


@router.get("", response_model=list[Checklist])
def list_checklists():
    """Get all checklists with status counts."""
    return ChecklistService.get_all()


@router.get("/{checklist_id}", response_model=ChecklistWithProducts)
def get_checklist(checklist_id: str):
    """Get a checklist with live product status, pre-sorted for walking:
    out -> low -> in_stock, then staleness within each tier."""
    checklist = ChecklistService.get_with_products(checklist_id)
    if not checklist:
        raise HTTPException(status_code=404, detail="Checklist not found")
    return checklist


@router.post("", response_model=Checklist, status_code=201)
def create_checklist(checklist: ChecklistCreate):
    """Create a new checklist."""
    return ChecklistService.create(checklist)


@router.put("/{checklist_id}", response_model=Checklist)
def update_checklist(checklist_id: str, update: ChecklistUpdate):
    """Update a checklist."""
    checklist = ChecklistService.update(checklist_id, update)
    if not checklist:
        raise HTTPException(status_code=404, detail="Checklist not found")
    return checklist


@router.post("/{checklist_id}/products/bulk", status_code=204)
def bulk_add_products_to_checklist(checklist_id: str, request: BulkAddProductsRequest):
    """Add multiple products to a checklist at once.

    Registered before the single-product POST route below - both match
    POST /{checklist_id}/products/<something>, and FastAPI/Starlette matches
    routes in registration order, so this specific path must come first or
    a request to .../products/bulk would be swallowed by {product_id}="bulk".
    """
    checklist = ChecklistService.get_by_id(checklist_id)
    if not checklist:
        raise HTTPException(status_code=404, detail="Checklist not found")

    ChecklistService.add_products(checklist_id, request.product_ids)


@router.post("/{checklist_id}/products/{product_id}", status_code=204)
def add_product_to_checklist(checklist_id: str, product_id: str):
    """Add a product to a checklist."""
    checklist = ChecklistService.get_by_id(checklist_id)
    if not checklist:
        raise HTTPException(status_code=404, detail="Checklist not found")

    if not ChecklistService.add_product(checklist_id, product_id):
        raise HTTPException(status_code=400, detail="Could not add product to checklist")


@router.delete("/{checklist_id}/products/{product_id}", status_code=204)
def remove_product_from_checklist(checklist_id: str, product_id: str):
    """Remove a product from a checklist."""
    if not ChecklistService.remove_product(checklist_id, product_id):
        raise HTTPException(status_code=404, detail="Product not found in checklist")


@router.delete("/{checklist_id}", status_code=204)
def delete_checklist(checklist_id: str):
    """Delete a checklist."""
    if not ChecklistService.delete(checklist_id):
        raise HTTPException(status_code=404, detail="Checklist not found")
