"""Core module for Aether Pantry.

Contains:
- models: Data models (Category, Product, GroceryListItem, Checklist, ...)
- database: SQLite setup and connection
- services: Business logic (CategoryService, ProductService, ...)
"""

from .models import (
    Category,
    CategoryBase,
    CategoryCreate,
    CategoryUpdate,
    Product,
    ProductBase,
    ProductCreate,
    ProductUpdate,
    ProductStatus,
    ProductStatusUpdate,
    ProductSummary,
    GroceryListItem,
    GroceryListItemCreate,
    Checklist,
    ChecklistBase,
    ChecklistCreate,
    ChecklistUpdate,
    ChecklistWithProducts,
    VacationStatus,
    VacationEndResult,
    VacationLogEntry,
    ProductEligibility,
)

from .database import init_db, reset_db, get_db, migrate_db

from .services import (
    CategoryService,
    ProductService,
    GroceryListService,
    ChecklistService,
    VacationService,
)

__all__ = [
    # Models
    "Category",
    "CategoryBase",
    "CategoryCreate",
    "CategoryUpdate",
    "Product",
    "ProductBase",
    "ProductCreate",
    "ProductUpdate",
    "ProductStatus",
    "ProductStatusUpdate",
    "ProductSummary",
    "GroceryListItem",
    "GroceryListItemCreate",
    "Checklist",
    "ChecklistBase",
    "ChecklistCreate",
    "ChecklistUpdate",
    "ChecklistWithProducts",
    "VacationStatus",
    "VacationEndResult",
    "VacationLogEntry",
    "ProductEligibility",
    # Database
    "init_db",
    "reset_db",
    "get_db",
    "migrate_db",
    # Services
    "CategoryService",
    "ProductService",
    "GroceryListService",
    "ChecklistService",
    "VacationService",
]
