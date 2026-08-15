"""Tests for pantry vacation mode: start/end lifecycle, unconditional
eligibility (no override layer, unlike chores), and offset accumulation."""

import pytest

from pantry.core.database import get_db, init_db
from pantry.core.models import ProductCreate
from pantry.core.services.product_service import ProductService
from pantry.core.services.vacation_service import VacationService


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("AETHER_PANTRY_DB_PATH", str(tmp_path / "test.db"))
    init_db()
    yield


def _backdate_vacation_start(days: int):
    with get_db() as conn:
        conn.execute(
            "UPDATE vacation_state SET started_at = datetime('now', ?) WHERE id = 1",
            (f"-{days} days",),
        )


class TestVacationLifecycle:
    def test_start_sets_active_state(self, db):
        status = VacationService.start()
        assert status.is_active is True
        assert status.started_at is not None

    def test_start_twice_raises(self, db):
        VacationService.start()
        with pytest.raises(ValueError):
            VacationService.start()

    def test_end_without_active_raises(self, db):
        with pytest.raises(ValueError):
            VacationService.end()

    def test_end_shifts_next_due_for_product_with_interval(self, db):
        product = ProductService.create(ProductCreate(name="Yogurt", interval_days=3))
        baseline_due = product.next_due

        VacationService.start()
        _backdate_vacation_start(3)

        result = VacationService.end()
        assert result.products_affected == 1
        assert result.days_elapsed == pytest.approx(3, abs=0.1)

        updated = ProductService.get_by_id(product.id)
        shift_days = (updated.next_due - baseline_due).total_seconds() / 86400
        assert shift_days == pytest.approx(3, abs=0.1)

    def test_end_does_not_affect_product_without_interval(self, db):
        product = ProductService.create(ProductCreate(name="Salt"))
        assert product.next_due is None

        VacationService.start()
        _backdate_vacation_start(3)
        result = VacationService.end()
        assert result.products_affected == 0

        updated = ProductService.get_by_id(product.id)
        assert updated.next_due is None

    def test_live_read_during_active_vacation_freezes_next_due(self, db):
        """The countdown should already be frozen while vacation is active,
        not just corrected retroactively when it ends."""
        product = ProductService.create(ProductCreate(name="Yogurt", interval_days=3))
        baseline_due = product.next_due

        VacationService.start()
        _backdate_vacation_start(3)

        live = ProductService.get_by_id(product.id)
        shift_days = (live.next_due - baseline_due).total_seconds() / 86400
        assert shift_days == pytest.approx(3, abs=0.1)

    def test_unpausing_shifts_rather_than_resets(self, db):
        """Clocks freeze, they don't reset: last_checked stays put, only
        the effective due date moves out by the trip length."""
        product = ProductService.create(ProductCreate(name="Yogurt", interval_days=3))
        original_last_checked = product.last_checked

        VacationService.start()
        _backdate_vacation_start(5)
        VacationService.end()

        updated = ProductService.get_by_id(product.id)
        assert updated.last_checked == original_last_checked


class TestEligibilityPreview:
    def test_product_with_interval_is_eligible(self, db):
        ProductService.create(ProductCreate(name="Yogurt", interval_days=3))
        preview = VacationService.get_eligible_preview()
        assert len(preview) == 1
        assert preview[0].vacation_eligible is True

    def test_product_without_interval_is_not_eligible(self, db):
        ProductService.create(ProductCreate(name="Salt"))
        preview = VacationService.get_eligible_preview()
        assert len(preview) == 1
        assert preview[0].vacation_eligible is False
