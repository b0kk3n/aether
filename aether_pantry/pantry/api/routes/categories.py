"""Category API routes."""

from fastapi import APIRouter, HTTPException

from pantry.core import (
    Category,
    CategoryCreate,
    CategoryUpdate,
    CategoryService,
)

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[Category])
def list_categories():
    """Get all categories."""
    return CategoryService.get_all()


@router.post("", response_model=Category, status_code=201)
def create_category(category: CategoryCreate):
    """Create a new category."""
    return CategoryService.create(category)


@router.put("/{category_id}", response_model=Category)
def update_category(category_id: str, update: CategoryUpdate):
    """Update a category."""
    category = CategoryService.update(category_id, update)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.delete("/{category_id}", status_code=204)
def delete_category(category_id: str):
    """Delete a category. Blocked if any product still uses it."""
    success, error = CategoryService.delete(category_id)
    if not success:
        if error:
            raise HTTPException(status_code=409, detail=error)
        raise HTTPException(status_code=404, detail="Category not found")
