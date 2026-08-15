"""Tests for the unified restock/postpone rule and the auto-flip-to-low
escalation logic (Product.effective_status)."""

import pytest

from pantry.core.database import get_db, init_db
from pantry.core.models import ProductCreate, ProductStatus
from pantry.core.services.product_service import ProductService


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("AETHER_PANTRY_DB_PATH", str(tmp_path / "test.db"))
    init_db()
    yield


def _backdate_last_checked(product_id: str, days: int):
    with get_db() as conn:
        conn.execute(
            "UPDATE products SET last_checked = datetime('now', ?) WHERE id = ?",
            (f"-{days} days", product_id),
        )


class TestUnifiedRestockRule:
    def test_transition_to_in_stock_resets_last_checked(self, db):
        product = ProductService.create(ProductCreate(name="Milk", interval_days=3))
        _backdate_last_checked(product.id, 10)

        updated = ProductService.set_status(product.id, ProductStatus.IN_STOCK)
        assert updated.days_since_checked == pytest.approx(0, abs=0.01)

    def test_transition_to_low_does_not_touch_last_checked(self, db):
        product = ProductService.create(ProductCreate(name="Milk", interval_days=3))
        _backdate_last_checked(product.id, 1)
        before = ProductService.get_by_id(product.id).last_checked

        updated = ProductService.set_status(product.id, ProductStatus.LOW)
        assert updated.last_checked == before

    def test_transition_to_out_does_not_touch_last_checked(self, db):
        product = ProductService.create(ProductCreate(name="Milk", interval_days=3))
        _backdate_last_checked(product.id, 1)
        before = ProductService.get_by_id(product.id).last_checked

        updated = ProductService.set_status(product.id, ProductStatus.OUT)
        assert updated.last_checked == before

    def test_postpone_after_elapsed_interval_does_not_immediately_reflip(self, db):
        """A product whose interval already elapsed shows effective_status
        'low'. Postponing (manually setting in_stock) must not immediately
        re-show as 'low' on the next read - this is the bug the unified
        restock rule exists to prevent."""
        product = ProductService.create(ProductCreate(name="Yogurt", interval_days=3))
        _backdate_last_checked(product.id, 10)

        elapsed = ProductService.get_by_id(product.id)
        assert elapsed.effective_status == ProductStatus.LOW

        postponed = ProductService.set_status(product.id, ProductStatus.IN_STOCK)
        assert postponed.effective_status == ProductStatus.IN_STOCK


class TestEffectiveStatusEscalation:
    def test_in_stock_within_interval_stays_in_stock(self, db):
        product = ProductService.create(ProductCreate(name="Milk", interval_days=7))
        _backdate_last_checked(product.id, 2)

        live = ProductService.get_by_id(product.id)
        assert live.effective_status == ProductStatus.IN_STOCK

    def test_in_stock_past_interval_escalates_to_low(self, db):
        product = ProductService.create(ProductCreate(name="Milk", interval_days=7))
        _backdate_last_checked(product.id, 10)

        live = ProductService.get_by_id(product.id)
        assert live.effective_status == ProductStatus.LOW

    def test_escalation_never_produces_out(self, db):
        """Elapsed interval means 'low', never 'out' - buffer-buying assumption."""
        product = ProductService.create(ProductCreate(name="Milk", interval_days=3))
        _backdate_last_checked(product.id, 90)

        live = ProductService.get_by_id(product.id)
        assert live.effective_status == ProductStatus.LOW

    def test_no_interval_never_escalates(self, db):
        product = ProductService.create(ProductCreate(name="Salt"))
        _backdate_last_checked(product.id, 365)

        live = ProductService.get_by_id(product.id)
        assert live.effective_status == ProductStatus.IN_STOCK

    def test_already_low_is_not_touched_by_escalation(self, db):
        product = ProductService.create(ProductCreate(name="Milk", interval_days=3))
        ProductService.set_status(product.id, ProductStatus.LOW)
        _backdate_last_checked(product.id, 90)

        live = ProductService.get_by_id(product.id)
        assert live.effective_status == ProductStatus.LOW

    def test_already_out_is_not_touched_by_escalation(self, db):
        product = ProductService.create(ProductCreate(name="Milk", interval_days=3))
        ProductService.set_status(product.id, ProductStatus.OUT)
        _backdate_last_checked(product.id, 90)

        live = ProductService.get_by_id(product.id)
        assert live.effective_status == ProductStatus.OUT
