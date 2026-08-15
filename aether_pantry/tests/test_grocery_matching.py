"""Tests for grocery-list-to-product matching: resolved at add time,
case-insensitive exact match only, and the linked/free-text check-off split."""

import pytest

from pantry.core.database import init_db
from pantry.core.models import ProductCreate, ProductStatus
from pantry.core.services.grocery_list_service import GroceryListService
from pantry.core.services.product_service import ProductService


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("AETHER_PANTRY_DB_PATH", str(tmp_path / "test.db"))
    init_db()
    yield


class TestMatching:
    def test_exact_match_links(self, db):
        ProductService.create(ProductCreate(name="Milk"))
        item = GroceryListService.add_item("Milk")
        assert item.is_linked

    def test_case_insensitive_match_links(self, db):
        ProductService.create(ProductCreate(name="Milk"))
        item = GroceryListService.add_item("milk")
        assert item.is_linked

    def test_whitespace_trimmed_before_match(self, db):
        ProductService.create(ProductCreate(name="Milk"))
        item = GroceryListService.add_item("  Milk  ")
        assert item.is_linked
        assert item.raw_text == "Milk"

    def test_no_match_is_free_text(self, db):
        ProductService.create(ProductCreate(name="Milk"))
        item = GroceryListService.add_item("Dinner ingredients")
        assert not item.is_linked

    def test_substring_does_not_match(self, db):
        ProductService.create(ProductCreate(name="Milk"))
        item = GroceryListService.add_item("Milk chocolate")
        assert not item.is_linked

    def test_match_resolved_at_add_time_not_retroactive(self, db):
        """A free-text line stays free text even if a matching product is
        created afterward - matching is resolved once, at add time."""
        item = GroceryListService.add_item("Yogurt")
        assert not item.is_linked

        ProductService.create(ProductCreate(name="Yogurt"))

        refetched = GroceryListService.get_by_id(item.id)
        assert not refetched.is_linked


class TestCheckOff:
    def test_check_off_linked_resets_product_and_removes_line(self, db):
        product = ProductService.create(ProductCreate(name="Milk", interval_days=3))
        ProductService.set_status(product.id, ProductStatus.OUT)

        item = GroceryListService.add_item("Milk")
        assert GroceryListService.check_off(item.id) is True

        updated = ProductService.get_by_id(product.id)
        assert updated.status == ProductStatus.IN_STOCK
        assert GroceryListService.get_by_id(item.id) is None

    def test_check_off_free_text_just_removes_line(self, db):
        item = GroceryListService.add_item("Paper towels (one-off)")
        assert GroceryListService.check_off(item.id) is True
        assert GroceryListService.get_by_id(item.id) is None

    def test_delete_item_does_not_touch_linked_product(self, db):
        product = ProductService.create(ProductCreate(name="Milk"))
        ProductService.set_status(product.id, ProductStatus.OUT)

        item = GroceryListService.add_item("Milk")
        assert GroceryListService.delete_item(item.id) is True

        updated = ProductService.get_by_id(product.id)
        assert updated.status == ProductStatus.OUT  # untouched
