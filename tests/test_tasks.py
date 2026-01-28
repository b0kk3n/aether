"""Tests for task management."""

import pytest
from datetime import datetime, timedelta
import tempfile
import os

from aether.data.store import Store
from aether.data.models import Task, TaskStatus, TaskPriority, TaskType, EnergyLevel
from aether.tasks.manager import TaskManager
from aether.tasks.prioritizer import Prioritizer


@pytest.fixture
def store():
    """Create a temporary store for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        yield Store(db_path)


@pytest.fixture
def task_manager(store):
    """Create task manager with test store."""
    return TaskManager(store)


@pytest.fixture
def prioritizer(store):
    """Create prioritizer with test store."""
    return Prioritizer(store)


class TestTaskManager:
    """Tests for TaskManager."""

    def test_add_task(self, task_manager):
        """Test adding a basic task."""
        task = task_manager.add("Test task", area="work")
        assert task.title == "Test task"
        assert task.area == "work"
        assert task.status == TaskStatus.INBOX

    def test_quick_add_basic(self, task_manager):
        """Test quick add with basic text."""
        task = task_manager.quick_add("Buy milk")
        assert task.title == "Buy milk"

    def test_quick_add_with_tags(self, task_manager):
        """Test quick add with tags."""
        task = task_manager.quick_add("Buy milk #shopping #groceries")
        assert task.title == "Buy milk"
        assert "shopping" in task.tags
        assert "groceries" in task.tags

    def test_quick_add_with_area(self, task_manager):
        """Test quick add with area."""
        task = task_manager.quick_add("Review PR @work")
        assert task.title == "Review PR"
        assert task.area == "work"

    def test_quick_add_with_priority(self, task_manager):
        """Test quick add with priority."""
        task = task_manager.quick_add("Fix bug !high")
        assert task.title == "Fix bug"
        assert task.priority == TaskPriority.HIGH

    def test_quick_add_with_due_date(self, task_manager):
        """Test quick add with due date."""
        task = task_manager.quick_add("Submit report due:tomorrow")
        assert task.title == "Submit report"
        assert task.due_date is not None
        expected = (datetime.now() + timedelta(days=1)).date()
        assert task.due_date.date() == expected

    def test_quick_add_with_estimate(self, task_manager):
        """Test quick add with time estimate."""
        task = task_manager.quick_add("Quick fix est:15m")
        assert task.title == "Quick fix"
        assert task.estimated_minutes == 15

    def test_complete_task(self, task_manager):
        """Test completing a task."""
        task = task_manager.add("Test task")
        completed = task_manager.complete(task.id, actual_minutes=30)
        assert completed.status == TaskStatus.DONE
        assert completed.completed_at is not None
        assert completed.actual_minutes == 30

    def test_start_task(self, task_manager):
        """Test starting a task."""
        task = task_manager.add("Test task")
        started = task_manager.start(task.id)
        assert started.status == TaskStatus.IN_PROGRESS

    def test_block_task(self, task_manager):
        """Test blocking a task."""
        task = task_manager.add("Test task")
        blocked = task_manager.block(task.id, reason="Waiting for input")
        assert blocked.status == TaskStatus.WAITING
        assert "Waiting for input" in blocked.notes

    def test_unblock_task(self, task_manager):
        """Test unblocking a task."""
        task = task_manager.add("Test task")
        task_manager.block(task.id)
        unblocked = task_manager.unblock(task.id)
        assert unblocked.status == TaskStatus.TODO

    def test_get_overdue(self, task_manager):
        """Test getting overdue tasks."""
        # Add overdue task
        task = task_manager.add(
            "Overdue task",
            due_date=datetime.now() - timedelta(days=1),
            status=TaskStatus.TODO,
        )

        # Add future task
        task_manager.add(
            "Future task",
            due_date=datetime.now() + timedelta(days=1),
            status=TaskStatus.TODO,
        )

        overdue = task_manager.get_overdue()
        assert len(overdue) == 1
        assert overdue[0].id == task.id

    def test_get_inbox(self, task_manager):
        """Test getting inbox items."""
        task_manager.add("Inbox item 1")
        task_manager.add("Inbox item 2")
        task_manager.add("Todo item", status=TaskStatus.TODO)

        inbox = task_manager.get_inbox()
        assert len(inbox) == 2


class TestPrioritizer:
    """Tests for Prioritizer."""

    def test_urgency_scoring(self, store, prioritizer):
        """Test that overdue tasks score higher."""
        # Add overdue task
        overdue = Task(
            title="Overdue",
            status=TaskStatus.TODO,
            due_date=datetime.now() - timedelta(days=1),
        )
        store.save_task(overdue)

        # Add future task
        future = Task(
            title="Future",
            status=TaskStatus.TODO,
            due_date=datetime.now() + timedelta(days=7),
        )
        store.save_task(future)

        recommendations = prioritizer.get_recommended(limit=10)

        # Find scores
        overdue_score = next(s for t, s, _ in recommendations if t.id == overdue.id)
        future_score = next(s for t, s, _ in recommendations if t.id == future.id)

        assert overdue_score > future_score

    def test_priority_scoring(self, store, prioritizer):
        """Test that high priority tasks score higher."""
        high = Task(
            title="High priority",
            status=TaskStatus.TODO,
            priority=TaskPriority.HIGH,
        )
        store.save_task(high)

        low = Task(
            title="Low priority",
            status=TaskStatus.TODO,
            priority=TaskPriority.LOW,
        )
        store.save_task(low)

        recommendations = prioritizer.get_recommended(limit=10)

        high_score = next(s for t, s, _ in recommendations if t.id == high.id)
        low_score = next(s for t, s, _ in recommendations if t.id == low.id)

        assert high_score > low_score

    def test_quick_wins(self, store, prioritizer):
        """Test getting quick wins."""
        quick = Task(
            title="Quick task",
            status=TaskStatus.TODO,
            estimated_minutes=10,
        )
        store.save_task(quick)

        long_task = Task(
            title="Long task",
            status=TaskStatus.TODO,
            estimated_minutes=120,
        )
        store.save_task(long_task)

        quick_wins = prioritizer.get_quick_wins()
        assert len(quick_wins) == 1
        assert quick_wins[0].id == quick.id

    def test_workload_analysis(self, store, prioritizer):
        """Test workload analysis."""
        # Add various tasks
        Task(title="T1", status=TaskStatus.TODO)
        store.save_task(Task(title="T1", status=TaskStatus.TODO, area="work"))
        store.save_task(Task(title="T2", status=TaskStatus.IN_PROGRESS, area="work"))
        store.save_task(Task(title="T3", status=TaskStatus.INBOX, area="home"))
        store.save_task(Task(
            title="T4",
            status=TaskStatus.TODO,
            due_date=datetime.now() - timedelta(days=1),
        ))

        analysis = prioritizer.analyze_workload()

        assert analysis["total_active"] >= 3
        assert analysis["overdue"] >= 1
        assert analysis["in_progress"] >= 1
        assert analysis["inbox"] >= 1
        assert "work" in analysis["by_area"]
