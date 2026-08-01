"""Tests for room pause ("remodeling"): freeze/unfreeze lifecycle, offset math."""

import pytest

from aether.core.database import get_db, init_db
from aether.core.models import ChoreCreate, RoomCreate
from aether.core.services.chore_service import ChoreService
from aether.core.services.room_service import RoomService
from aether.core.services.vacation_service import VacationService

MAINTAIN = "maintain"


@pytest.fixture
def db(tmp_path, monkeypatch):
    """Point AETHER_DB_PATH at a scratch file for each test."""
    monkeypatch.setenv("AETHER_DB_PATH", str(tmp_path / "test.db"))
    init_db()
    yield


def _make_room_chore(category_id=MAINTAIN, interval_days=7):
    room = RoomService.create(RoomCreate(name="Test Room"))
    chore = ChoreService.create(ChoreCreate(
        name="Test chore",
        room_id=room.id,
        interval_days=interval_days,
        category_id=category_id,
    ))
    return room, chore


def _backdate_room_pause(room_id: str, days: int):
    with get_db() as conn:
        conn.execute(
            "UPDATE rooms SET paused_at = datetime('now', ?) WHERE id = ?",
            (f"-{days} days", room_id),
        )


class TestRoomPauseLifecycle:
    def test_pause_sets_state(self, db):
        room, _ = _make_room_chore()
        paused = RoomService.pause(room.id)
        assert paused.is_paused is True
        assert paused.paused_at is not None

    def test_pause_twice_raises(self, db):
        room, _ = _make_room_chore()
        RoomService.pause(room.id)
        with pytest.raises(ValueError):
            RoomService.pause(room.id)

    def test_unpause_without_pause_raises(self, db):
        room, _ = _make_room_chore()
        with pytest.raises(ValueError):
            RoomService.unpause(room.id)

    def test_pause_freezes_maintain_chore_regardless_of_category(self, db):
        """Unlike vacation mode's category-based eligibility, room pause is
        unconditional - a remodel blocks all work in the room."""
        room, chore = _make_room_chore(category_id=MAINTAIN, interval_days=7)
        baseline_due = chore.due_date

        RoomService.pause(room.id)
        _backdate_room_pause(room.id, 3)

        live = ChoreService.get_by_id(chore.id)
        shift_days = (live.due_date - baseline_due).total_seconds() / 86400
        assert shift_days == pytest.approx(3, abs=0.1)

    def test_unpause_shifts_due_date_forward(self, db):
        room, chore = _make_room_chore(interval_days=7)
        baseline_due = chore.due_date

        RoomService.pause(room.id)
        _backdate_room_pause(room.id, 4)
        unpaused = RoomService.unpause(room.id)

        assert unpaused.is_paused is False
        assert unpaused.paused_at is None

        updated = ChoreService.get_by_id(chore.id)
        shift_days = (updated.due_date - baseline_due).total_seconds() / 86400
        assert shift_days == pytest.approx(4, abs=0.1)

    def test_delete_blocked_while_paused(self, db):
        room, _ = _make_room_chore()
        RoomService.pause(room.id)

        success, error = RoomService.delete(room.id)
        assert success is False
        assert error is not None

    def test_delete_allowed_after_unpause(self, db):
        room, _ = _make_room_chore()
        RoomService.pause(room.id)
        RoomService.unpause(room.id)

        success, error = RoomService.delete(room.id)
        assert success is True
        assert error is None


class TestRoomPauseAndVacationCombined:
    def test_independent_offsets_accrue_and_unwind_separately(self, db):
        """A chore that is both vacation-paused and room-paused should
        accrue both offsets, and ending one must not disturb the other."""
        room, chore = _make_room_chore(category_id="vacuum", interval_days=10)
        baseline_due = chore.due_date

        VacationService.start()
        RoomService.pause(room.id)

        with get_db() as conn:
            conn.execute(
                "UPDATE vacation_state SET started_at = datetime('now', '-2 days') WHERE id = 1"
            )
        _backdate_room_pause(room.id, 5)

        live = ChoreService.get_by_id(chore.id)
        shift_days = (live.due_date - baseline_due).total_seconds() / 86400
        assert shift_days == pytest.approx(2 + 5, abs=0.2)

        # Unpausing the room should only bake in the room-pause component,
        # leaving the still-active vacation freeze untouched.
        RoomService.unpause(room.id)
        after_unpause = ChoreService.get_by_id(chore.id)
        shift_days_after = (after_unpause.due_date - baseline_due).total_seconds() / 86400
        assert shift_days_after == pytest.approx(2 + 5, abs=0.2)

        result = VacationService.end()
        assert result.chores_affected == 1

        after_vacation = ChoreService.get_by_id(chore.id)
        final_shift = (after_vacation.due_date - baseline_due).total_seconds() / 86400
        assert final_shift == pytest.approx(2 + 5, abs=0.2)
