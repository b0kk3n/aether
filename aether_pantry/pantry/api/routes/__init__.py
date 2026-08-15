"""API routes for Aether Pantry."""

from .categories import router as categories_router
from .products import router as products_router
from .grocery_list import router as grocery_list_router
from .checklists import router as checklists_router
from .vacation import router as vacation_router

__all__ = [
    "categories_router",
    "products_router",
    "grocery_list_router",
    "checklists_router",
    "vacation_router",
]
