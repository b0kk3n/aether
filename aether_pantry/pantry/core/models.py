"""Core data models for Aether Pantry.

Simplified model focused purely on "what's low or out at home":
- Category: a physical storage grouping (structural, one per product)
- Product: a tracked item with a status, optionally a category/interval
- GroceryListItem: a line on the live to-buy list, linked or free text
- Checklist: a cross-cutting, contextual grouping of products
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
import uuid


def generate_id() -> str:
    """Generate a short unique ID."""
    return str(uuid.uuid4())[:8]


class ProductStatus(str, Enum):
    """A product's stock status."""
    IN_STOCK = "in_stock"
    LOW = "low"
    OUT = "out"


# =============================================================================
# Category
# =============================================================================

class CategoryBase(BaseModel):
    """Base category model for creation/updates."""
    name: str
    icon: str = "tag"
    sort_order: int = 0


class CategoryCreate(CategoryBase):
    """Model for creating a category."""
    pass


class CategoryUpdate(BaseModel):
    """Model for updating a category."""
    name: Optional[str] = None
    icon: Optional[str] = None
    sort_order: Optional[int] = None


class Category(CategoryBase):
    """A user-editable, storage-oriented product category."""
    id: str = Field(default_factory=generate_id)
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        from_attributes = True


# =============================================================================
# Product
# =============================================================================

class ProductBase(BaseModel):
    """Base product model for creation/updates."""
    name: str
    category_id: Optional[str] = None
    interval_days: Optional[int] = None


class ProductCreate(ProductBase):
    """Model for creating a product."""
    pass


class ProductUpdate(BaseModel):
    """Model for updating a product (rename/recategorize/interval).

    Never touches status/last_checked - those change only through
    ProductService.set_status().
    """
    name: Optional[str] = None
    category_id: Optional[str] = None
    interval_days: Optional[int] = None


class ProductStatusUpdate(BaseModel):
    """Request body for a quick status flip."""
    status: ProductStatus


class Product(ProductBase):
    """A tracked pantry item.

    Can be bare - just a name and a status - or carry a category and/or
    an interval. `status` is the last explicitly-set value; `effective_status`
    is what should actually be shown/sorted on, escalating to `low` once an
    interval has silently elapsed.
    """
    id: str = Field(default_factory=generate_id)
    status: ProductStatus = ProductStatus.IN_STOCK
    last_checked: datetime = Field(default_factory=datetime.now)

    # Accumulated + in-progress paused days from vacation mode, from the
    # products_effective view's effective_paused_days column.
    vacation_paused_days: float = 0.0

    # Category display info, populated from the products_effective view's join.
    category_name: Optional[str] = None
    category_icon: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        from_attributes = True

    @property
    def effective_interval_days(self) -> Optional[float]:
        """interval_days adjusted for accumulated + in-progress vacation pause."""
        if self.interval_days is None:
            return None
        return self.interval_days + self.vacation_paused_days

    @property
    def days_since_checked(self) -> float:
        """Days elapsed since last_checked."""
        return (datetime.now() - self.last_checked).total_seconds() / 86400

    @property
    def next_due(self) -> Optional[datetime]:
        """When this product's interval next elapses, if it has one."""
        if self.effective_interval_days is None:
            return None
        return self.last_checked + timedelta(days=self.effective_interval_days)

    @property
    def effective_status(self) -> ProductStatus:
        """The status to actually display/sort on.

        Only ever escalates in_stock -> low once the interval has elapsed
        without being checked - never touches an already-low/out product,
        so it can't clobber a stronger manual signal. Never written back to
        the stored `status` column; computed fresh on every read.
        """
        if self.status != ProductStatus.IN_STOCK or self.effective_interval_days is None:
            return self.status
        if self.days_since_checked > self.effective_interval_days:
            return ProductStatus.LOW
        return self.status


class ProductSummary(BaseModel):
    """Compact product view for checklist/grouped-list display."""
    id: str
    name: str
    category_id: Optional[str] = None
    category_name: Optional[str] = None
    category_icon: Optional[str] = None
    status: ProductStatus
    effective_status: ProductStatus
    last_checked: datetime
    interval_days: Optional[int] = None


# =============================================================================
# Grocery List
# =============================================================================

class GroceryListItemCreate(BaseModel):
    """Model for adding a line to the grocery list."""
    raw_text: str


class GroceryListItem(BaseModel):
    """A line on the live to-buy list.

    Linked (product_id set) if it matched an existing product by name at
    add time; free text (product_id None) otherwise, forever.
    """
    id: str = Field(default_factory=generate_id)
    raw_text: str
    product_id: Optional[str] = None

    # Display-only convenience fields, populated when linked.
    linked_product_name: Optional[str] = None
    linked_product_status: Optional[ProductStatus] = None
    linked_product_effective_status: Optional[ProductStatus] = None

    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        from_attributes = True

    @property
    def is_linked(self) -> bool:
        return self.product_id is not None


# =============================================================================
# Checklist
# =============================================================================

class ChecklistBase(BaseModel):
    """Base checklist model."""
    name: str
    description: str = ""
    icon: str = "clipboard"


class ChecklistCreate(ChecklistBase):
    """Model for creating a checklist."""
    product_ids: list[str] = []


class ChecklistUpdate(BaseModel):
    """Model for updating a checklist."""
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    product_ids: Optional[list[str]] = None


class Checklist(ChecklistBase):
    """A scenario-based, cross-cutting checklist.

    References actual products and shows their real status. Examples:
    "Market", "Sale", "Breakfast", "Cupboard".
    """
    id: str = Field(default_factory=generate_id)
    created_at: datetime = Field(default_factory=datetime.now)

    out_count: int = 0
    low_count: int = 0
    in_stock_count: int = 0

    class Config:
        from_attributes = True


class ChecklistWithProducts(Checklist):
    """Checklist with live product status, sorted out -> low -> in_stock,
    then by staleness (oldest last_checked first) within each tier."""
    products: list[ProductSummary] = []


# =============================================================================
# Vacation Mode
# =============================================================================

class VacationStatus(BaseModel):
    """Current global vacation-mode state."""
    is_active: bool
    started_at: Optional[datetime] = None
    days_elapsed: float = 0.0  # live, only meaningful while is_active


class VacationEndResult(BaseModel):
    """Result of ending a vacation."""
    days_elapsed: float
    products_affected: int


class VacationLogEntry(BaseModel):
    """A past vacation's record from vacation_log."""
    id: str
    started_at: datetime
    ended_at: datetime
    days_elapsed: float
    products_affected: int


class ProductEligibility(BaseModel):
    """Preview of whether a product would pause under vacation mode."""
    id: str
    name: str
    interval_days: Optional[int] = None
    vacation_eligible: bool
