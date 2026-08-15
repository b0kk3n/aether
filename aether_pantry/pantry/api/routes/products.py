"""Product API routes."""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from pantry.core import (
    Product,
    ProductCreate,
    ProductUpdate,
    ProductStatus,
    ProductStatusUpdate,
    ProductService,
)

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=list[Product])
def list_products(
    category_id: Optional[str] = Query(None, description="Filter by category ID"),
    status: Optional[ProductStatus] = Query(None, description="Filter by status"),
):
    """Get all products with optional filters."""
    return ProductService.get_all(category_id=category_id, status=status)


@router.get("/needing-attention", response_model=list[Product])
def get_products_needing_attention():
    """Products whose effective status is low/out - for grocery-list surfacing.

    Registered before /{product_id} - both would otherwise match this path,
    and FastAPI/Starlette matches routes in registration order.
    """
    return ProductService.get_needing_attention()


@router.get("/{product_id}", response_model=Product)
def get_product(product_id: str):
    """Get a product by ID."""
    product = ProductService.get_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.post("", response_model=Product, status_code=201)
def create_product(product: ProductCreate):
    """Create a new product."""
    return ProductService.create(product)


@router.put("/{product_id}", response_model=Product)
def update_product(product_id: str, update: ProductUpdate):
    """Update a product's name/category/interval (edit mode)."""
    product = ProductService.update(product_id, update)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.patch("/{product_id}/status", response_model=Product)
def set_product_status(product_id: str, update: ProductStatusUpdate):
    """Quick status flip (tap in_stock / low / out). Also used for postpone."""
    product = ProductService.set_status(product_id, update.status)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.delete("/{product_id}", status_code=204)
def delete_product(product_id: str):
    """Delete a product."""
    if not ProductService.delete(product_id):
        raise HTTPException(status_code=404, detail="Product not found")
