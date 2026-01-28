"""Tests for context tracking."""

import pytest
from datetime import datetime
import tempfile
import os

from aether.data.store import Store
from aether.data.models import EnergyLevel, Context
from aether.context.tracker import ContextTracker


@pytest.fixture
def store():
    """Create a temporary store for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        yield Store(db_path)


@pytest.fixture
def tracker(store):
    """Create context tracker with test store."""
    return ContextTracker(store)


class TestContextTracker:
    """Tests for ContextTracker."""

    def test_get_current_creates_default(self, tracker):
        """Test that get_current creates default context."""
        context = tracker.get_current()
        assert context is not None
        assert context.energy_level is not None
        assert context.time_of_day is not None

    def test_set_energy(self, tracker):
        """Test setting energy level."""
        context = tracker.set_energy(EnergyLevel.PEAK, "Feeling great")
        assert context.energy_level == EnergyLevel.PEAK
        assert context.energy_note == "Feeling great"

    def test_set_location(self, tracker):
        """Test setting location."""
        context = tracker.set_location("home")
        assert context.location == "home"

    def test_set_focus_mode(self, tracker):
        """Test toggling focus mode."""
        context = tracker.set_focus_mode(True)
        assert context.focus_mode is True

        context = tracker.set_focus_mode(False)
        assert context.focus_mode is False

    def test_record_break(self, tracker):
        """Test recording a break."""
        context = tracker.record_break()
        assert context.last_break is not None

    def test_time_of_day(self, tracker):
        """Test time of day calculation."""
        # Test internal method
        assert tracker._get_time_of_day(8) == "morning"
        assert tracker._get_time_of_day(14) == "afternoon"
        assert tracker._get_time_of_day(19) == "evening"
        assert tracker._get_time_of_day(23) == "night"

    def test_energy_pattern_updates(self, tracker, store):
        """Test that setting energy updates patterns."""
        # Set energy multiple times
        for _ in range(3):
            tracker.set_energy(EnergyLevel.PEAK)

        # Check pattern was created
        patterns = store.get_patterns(pattern_type="energy")
        assert len(patterns) > 0

    def test_productivity_score(self, tracker, store):
        """Test productivity score calculation."""
        # Log some task completions
        store.log_activity("task_completed", "task", "t1", {"estimated": 30, "actual": 25})
        store.log_activity("task_completed", "task", "t2", {"estimated": 15, "actual": 20})

        score = tracker.get_productivity_score()
        assert "score" in score
        assert "tasks_completed" in score
        assert score["tasks_completed"] == 2

    def test_should_suggest_break(self, tracker, store):
        """Test break suggestions."""
        # Fresh context shouldn't suggest break
        should_break, _ = tracker.should_suggest_break()
        # Result depends on context state

        # Set depleted energy
        tracker.set_energy(EnergyLevel.DEPLETED)
        should_break, reason = tracker.should_suggest_break()
        assert should_break is True
        assert "depleted" in reason.lower()
