"""Tests for vacation mode: eligibility rule, start/end lifecycle, offset math."""

import pytest

from aether.core.database import get_db, init_db
from aether.core.models import (
    Category,
    ChoreCreate,
    ChoreUpdate,
    RoomCreate,
    VacationOverride,
    is_vacation_eligible,
)
from aether.core.services.chore_service import ChoreService
from aether.core.services.room_service import RoomService
from aether.core.services.vacation_service import VacationService


@pytest.fixture
def db(tmp_path, monkeypatch):
    """Point AETHER_DB_PATH at a scratch file for each test."""
    monkeypatch.setenv("AETHER_DB_PATH", str(tmp_path / "test.db"))
    init_db()
    yield


def _make_chore(category=Category.VACUUM, interval_days=7, vacation_override=None):
    room = RoomService.create(RoomCreate(name="Test Room"))
    return ChoreService.create(ChoreCreate(
        name="Test chore",
        room_id=room.id,
        interval_days=interval_days,
        category=category,
        vacation_override=vacation_override,
    ))


def _backdate_vacation_start(days: int):
    with get_db() as conn:
        conn.execute(
            "UPDATE vacation_state SET started_at = datetime('now', ?) WHERE id = 1",
            (f"-{days} days",),
        )


class TestIsVacationEligible:
    def test_default_pausable_categories(self):
        for category in [
            Category.VACUUM, Category.MOP, Category.DUST, Category.DECLUTTER,
            Category.CLEAN, Category.WASH, Category.WIPE,
        ]:
            assert is_vacation_eligible(category, None) is True

    def test_maintain_not_pausable_by_default(self):
        assert is_vacation_eligible(Category.MAINTAIN, None) is False

    def test_override_force_pause_wins_over_category(self):
        assert is_vacation_eligible(Category.MAINTAIN, VacationOverride.FORCE_PAUSE) is True

    def test_override_force_exclude_wins_over_category(self):
        assert is_vacation_eligible(Category.VACUUM, VacationOverride.FORCE_EXCLUDE) is False


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

    def test_end_shifts_eligible_chore_due_date(self, db):
        chore = _make_chore(category=Category.VACUUM, interval_days=7)
        baseline_due = chore.due_date

        VacationService.start()
        _backdate_vacation_start(3)

        result = VacationService.end()
        assert result.chores_affected == 1
        assert result.days_elapsed == pytest.approx(3, abs=0.1)

        updated = ChoreService.get_by_id(chore.id)
        shift_days = (updated.due_date - baseline_due).total_seconds() / 86400
        assert shift_days == pytest.approx(3, abs=0.1)

    def test_end_does_not_shift_maintain_chore(self, db):
        chore = _make_chore(category=Category.MAINTAIN, interval_days=7)
        baseline_due = chore.due_date

        VacationService.start()
        _backdate_vacation_start(3)
        result = VacationService.end()
        assert result.chores_affected == 0

        updated = ChoreService.get_by_id(chore.id)
        assert updated.due_date == baseline_due

    def test_maintain_chore_with_force_pause_override_shifts(self, db):
        chore = _make_chore(
            category=Category.MAINTAIN,
            interval_days=7,
            vacation_override=VacationOverride.FORCE_PAUSE,
        )
        baseline_due = chore.due_date

        VacationService.start()
        _backdate_vacation_start(3)
        result = VacationService.end()
        assert result.chores_affected == 1

        updated = ChoreService.get_by_id(chore.id)
        shift_days = (updated.due_date - baseline_due).total_seconds() / 86400
        assert shift_days == pytest.approx(3, abs=0.1)

    def test_vacuum_chore_with_force_exclude_override_does_not_shift(self, db):
        chore = _make_chore(
            category=Category.VACUUM,
            interval_days=7,
            vacation_override=VacationOverride.FORCE_EXCLUDE,
        )
        baseline_due = chore.due_date

        VacationService.start()
        _backdate_vacation_start(3)
        result = VacationService.end()
        assert result.chores_affected == 0

        updated = ChoreService.get_by_id(chore.id)
        assert updated.due_date == baseline_due

    def test_live_read_during_active_vacation_freezes_due_date(self, db):
        """The countdown should already be frozen while vacation is active,
        not just corrected retroactively when it ends."""
        chore = _make_chore(category=Category.VACUUM, interval_days=7)
        baseline_due = chore.due_date

        VacationService.start()
        _backdate_vacation_start(3)

        live = ChoreService.get_by_id(chore.id)
        shift_days = (live.due_date - baseline_due).total_seconds() / 86400
        assert shift_days == pytest.approx(3, abs=0.1)


class TestChoreUpdateOverride:
    def test_override_persists_and_clears(self, db):
        chore = _make_chore(category=Category.MAINTAIN)
        assert chore.vacation_override is None

        updated = ChoreService.update(
            chore.id, ChoreUpdate(vacation_override=VacationOverride.FORCE_EXCLUDE)
        )
        assert updated.vacation_override == VacationOverride.FORCE_EXCLUDE

        # Omitting the field on a later update must not clear it.
        updated2 = ChoreService.update(chore.id, ChoreUpdate(name=chore.name))
        assert updated2.vacation_override == VacationOverride.FORCE_EXCLUDE

        # Explicitly setting it back to None clears it (inherit category default).
        updated3 = ChoreService.update(chore.id, ChoreUpdate(vacation_override=None))
        assert updated3.vacation_override is None
