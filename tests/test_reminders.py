"""Tests for reminder system."""

import pytest
from datetime import datetime, timedelta
import tempfile
import os

from aether.data.store import Store
from aether.data.models import Reminder, ReminderType, EnergyLevel, Context
from aether.reminders.manager import ReminderManager


@pytest.fixture
def store():
    """Create a temporary store for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        yield Store(db_path)


@pytest.fixture
def reminder_manager(store):
    """Create reminder manager with test store."""
    return ReminderManager(store)


class TestReminderManager:
    """Tests for ReminderManager."""

    def test_add_reminder(self, reminder_manager):
        """Test adding a basic reminder."""
        trigger = datetime.now() + timedelta(hours=1)
        reminder = reminder_manager.add("Test reminder", trigger)

        assert reminder.title == "Test reminder"
        assert reminder.trigger_at == trigger
        assert reminder.active is True

    def test_add_medication_reminder(self, reminder_manager):
        """Test adding a medication reminder."""
        trigger = datetime.now() + timedelta(hours=1)
        reminder = reminder_manager.add_medication("Adderall", trigger, window_hours=2)

        assert "Adderall" in reminder.title
        assert reminder.reminder_type == ReminderType.MEDICATION
        assert reminder.adaptive is True
        assert reminder.window_start is not None
        assert reminder.window_end is not None

    def test_add_meeting_prep(self, reminder_manager):
        """Test adding meeting prep reminder."""
        meeting_start = datetime.now() + timedelta(hours=2)
        reminder = reminder_manager.add_meeting_prep(
            "Team standup",
            meeting_start,
            prep_minutes=15,
        )

        assert "Team standup" in reminder.title
        assert reminder.reminder_type == ReminderType.MEETING_PREP
        # Should trigger 15 min before meeting
        expected_trigger = meeting_start - timedelta(minutes=15)
        assert reminder.trigger_at == expected_trigger

    def test_snooze_reminder(self, reminder_manager):
        """Test snoozing a reminder."""
        trigger = datetime.now()
        reminder = reminder_manager.add("Test", trigger)

        snoozed = reminder_manager.snooze(reminder.id, minutes=10)
        assert snoozed.snooze_count == 1
        assert snoozed.trigger_at > trigger

    def test_max_snoozes(self, reminder_manager):
        """Test max snooze limit."""
        trigger = datetime.now()
        reminder = reminder_manager.add("Test", trigger)

        # Snooze up to max
        for _ in range(reminder.max_snoozes):
            reminder_manager.snooze(reminder.id, minutes=5)

        # Next snooze should not increase count
        result = reminder_manager.snooze(reminder.id, minutes=5)
        assert result.snooze_count == reminder.max_snoozes

    def test_complete_reminder(self, reminder_manager):
        """Test completing a reminder."""
        trigger = datetime.now()
        reminder = reminder_manager.add("Test", trigger)

        completed = reminder_manager.complete(reminder.id)
        assert completed.completed is True
        assert completed.last_triggered is not None

    def test_get_due_reminders(self, reminder_manager, store):
        """Test getting due reminders."""
        now = datetime.now()

        # Add due reminder
        due = reminder_manager.add(
            "Due now",
            now - timedelta(minutes=5),
            window_minutes=60,
        )

        # Add future reminder
        future = reminder_manager.add(
            "Future",
            now + timedelta(hours=2),
        )

        due_list = reminder_manager.get_due()
        due_ids = [r.id for r in due_list]

        assert due.id in due_ids
        assert future.id not in due_ids

    def test_adaptive_timing_energy(self, reminder_manager, store):
        """Test adaptive timing based on energy."""
        now = datetime.now()

        # Add adaptive reminder that prefers good energy
        reminder = reminder_manager.add(
            "Take medication",
            now,
            reminder_type=ReminderType.MEDICATION,
            adaptive=True,
        )
        reminder.preferred_energy = EnergyLevel.GOOD
        reminder.window_start = now - timedelta(hours=1)
        reminder.window_end = now + timedelta(hours=1)
        store.save_reminder(reminder)

        # With good energy, should be due
        good_context = Context(energy_level=EnergyLevel.GOOD)
        due_good = reminder_manager.get_due(good_context)
        assert any(r.id == reminder.id for r in due_good)

    def test_get_upcoming(self, reminder_manager):
        """Test getting upcoming reminders."""
        now = datetime.now()

        # Add reminders at various times
        reminder_manager.add("Soon", now + timedelta(hours=1))
        reminder_manager.add("Later", now + timedelta(hours=12))
        reminder_manager.add("Tomorrow", now + timedelta(hours=30))

        upcoming = reminder_manager.get_upcoming(hours=24)
        assert len(upcoming) == 2

    def test_dismiss_recurring(self, reminder_manager):
        """Test dismissing a recurring reminder schedules next."""
        trigger = datetime.now()
        reminder = reminder_manager.add(
            "Daily task",
            trigger,
            recurrence="0 9 * * *",  # Daily at 9am
        )

        dismissed = reminder_manager.dismiss(reminder.id)
        # Should have new trigger time
        assert dismissed.trigger_at > trigger
