"""Todoist integration for syncing tasks."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any
import logging

from todoist_api_python.api_async import TodoistAPIAsync
from todoist_api_python.api import TodoistAPI

from ..data.models import Task, TaskStatus, TaskPriority, TaskType
from ..data.store import Store

logger = logging.getLogger(__name__)


class TodoistSync:
    """Bidirectional sync with Todoist."""

    # Todoist priority mapping (Todoist: 1=normal, 4=urgent)
    PRIORITY_MAP = {
        1: TaskPriority.LOW,
        2: TaskPriority.MEDIUM,
        3: TaskPriority.HIGH,
        4: TaskPriority.CRITICAL,
    }

    REVERSE_PRIORITY_MAP = {
        TaskPriority.SOMEDAY: 1,
        TaskPriority.LOW: 1,
        TaskPriority.MEDIUM: 2,
        TaskPriority.HIGH: 3,
        TaskPriority.CRITICAL: 4,
    }

    def __init__(self, api_token: str, store: Store):
        """Initialize with Todoist API token."""
        self.api_token = api_token
        self.store = store
        self.api = TodoistAPI(api_token)
        self.async_api = TodoistAPIAsync(api_token)
        self._project_cache: dict[str, str] = {}  # id -> name
        self._label_cache: dict[str, str] = {}  # id -> name

    async def sync(self) -> dict[str, Any]:
        """Perform full sync with Todoist."""
        logger.info("Starting Todoist sync")

        # Refresh caches
        await self._refresh_caches()

        # Get all active tasks from Todoist
        todoist_tasks = []
        async for task in self.async_api.get_tasks():
            todoist_tasks.append(task)

        synced = 0
        created = 0
        updated = 0

        for todoist_task in todoist_tasks:
            # Check if we have this task locally
            local_task = self._find_local_task(todoist_task.id)

            if local_task:
                # Update local task if Todoist version is newer
                if self._needs_update(local_task, todoist_task):
                    self._update_local_task(local_task, todoist_task)
                    updated += 1
            else:
                # Create new local task
                self._create_local_task(todoist_task)
                created += 1

            synced += 1

        # Handle completed tasks (mark local tasks as done if not in Todoist)
        self._sync_completed_tasks(todoist_tasks)

        logger.info(f"Sync complete: {synced} synced, {created} created, {updated} updated")

        return {
            "synced": synced,
            "created": created,
            "updated": updated,
            "timestamp": datetime.now().isoformat(),
        }

    async def _refresh_caches(self) -> None:
        """Refresh project and label caches."""
        try:
            projects = []
            async for p in self.async_api.get_projects():
                projects.append(p)
            self._project_cache = {p.id: p.name for p in projects}

            labels = []
            async for l in self.async_api.get_labels():
                labels.append(l)
            self._label_cache = {l.id: l.name for l in labels}
        except Exception as e:
            logger.warning(f"Failed to refresh caches: {e}")

    def _find_local_task(self, todoist_id: str) -> Task | None:
        """Find local task by Todoist ID."""
        tasks = self.store.get_tasks(include_done=True)
        for task in tasks:
            if task.metadata.get("todoist_id") == todoist_id:
                return task
        return None

    def _needs_update(self, local: Task, todoist: Any) -> bool:
        """Check if local task needs update from Todoist."""
        # Compare key fields
        if local.title != todoist.content:
            return True

        # Check due date
        todoist_due = self._parse_todoist_due(todoist.due)
        if local.due_date != todoist_due:
            return True

        # Check priority
        todoist_priority = self.PRIORITY_MAP.get(todoist.priority, TaskPriority.MEDIUM)
        if local.priority != todoist_priority:
            return True

        return False

    def _update_local_task(self, local: Task, todoist: Any) -> None:
        """Update local task with Todoist data."""
        local.title = todoist.content
        local.description = todoist.description or ""
        local.due_date = self._parse_todoist_due(todoist.due)
        local.priority = self.PRIORITY_MAP.get(todoist.priority, TaskPriority.MEDIUM)

        # Update project/area mapping
        if todoist.project_id and todoist.project_id in self._project_cache:
            project_name = self._project_cache[todoist.project_id]
            local.area = self._map_project_to_area(project_name)
            local.project = project_name

        # Update labels/tags
        if todoist.labels:
            local.tags = todoist.labels

        local.metadata["todoist_id"] = todoist.id
        local.metadata["todoist_updated"] = datetime.now().isoformat()

        self.store.save_task(local)

    def _create_local_task(self, todoist: Any) -> Task:
        """Create local task from Todoist task."""
        # Determine area from project
        area = None
        project = None
        if todoist.project_id and todoist.project_id in self._project_cache:
            project_name = self._project_cache[todoist.project_id]
            area = self._map_project_to_area(project_name)
            project = project_name

        # Infer task type from labels or content
        task_type = self._infer_task_type(todoist)

        task = Task(
            title=todoist.content,
            description=todoist.description or "",
            status=TaskStatus.TODO,
            priority=self.PRIORITY_MAP.get(todoist.priority, TaskPriority.MEDIUM),
            task_type=task_type,
            due_date=self._parse_todoist_due(todoist.due),
            area=area,
            project=project,
            tags=todoist.labels if todoist.labels else [],
            metadata={
                "todoist_id": todoist.id,
                "todoist_project_id": todoist.project_id,
                "todoist_created": todoist.created_at if isinstance(todoist.created_at, str) else (todoist.created_at.isoformat() if hasattr(todoist.created_at, 'isoformat') else str(todoist.created_at)),
                "todoist_synced": datetime.now().isoformat(),
            },
        )

        self.store.save_task(task)
        return task

    def _sync_completed_tasks(self, todoist_tasks: list[Any]) -> None:
        """Mark local tasks as done if completed in Todoist."""
        todoist_ids = {t.id for t in todoist_tasks}

        local_tasks = self.store.get_tasks(include_done=False)
        for task in local_tasks:
            todoist_id = task.metadata.get("todoist_id")
            if todoist_id and todoist_id not in todoist_ids:
                # Task is no longer in Todoist active list - might be completed
                task.status = TaskStatus.DONE
                task.completed_at = datetime.now()
                self.store.save_task(task)
                logger.info(f"Marked task as done (completed in Todoist): {task.title}")

    def _parse_todoist_due(self, due: Any) -> datetime | None:
        """Parse Todoist due date object."""
        if not due:
            return None

        try:
            # Check if due is a string (direct date)
            if isinstance(due, str):
                return datetime.fromisoformat(due.replace("Z", "+00:00"))

            # Check for datetime attribute (with time)
            if hasattr(due, 'datetime') and due.datetime:
                return datetime.fromisoformat(due.datetime.replace("Z", "+00:00"))

            # Check for date attribute (date only)
            if hasattr(due, 'date') and due.date:
                if isinstance(due.date, str):
                    return datetime.strptime(due.date, "%Y-%m-%d").replace(
                        hour=23, minute=59, second=59
                    )
                else:
                    # due.date is already a datetime.date object
                    return datetime.combine(due.date, datetime.max.time()).replace(
                        hour=23, minute=59, second=59
                    )

            # Try accessing as dict
            if isinstance(due, dict):
                if 'datetime' in due and due['datetime']:
                    return datetime.fromisoformat(due['datetime'].replace("Z", "+00:00"))
                elif 'date' in due and due['date']:
                    return datetime.strptime(due['date'], "%Y-%m-%d").replace(
                        hour=23, minute=59, second=59
                    )

        except (ValueError, AttributeError, TypeError) as e:
            logger.warning(f"Failed to parse due date {due}: {e}")

        return None

    def _map_project_to_area(self, project_name: str) -> str:
        """Map Todoist project name to Aether area."""
        # Common mappings - user can customize
        area_keywords = {
            "work": ["work", "job", "office", "career"],
            "home": ["home", "house", "chores", "cleaning"],
            "personal": ["personal", "self", "health", "fitness"],
            "shopping": ["shopping", "groceries", "buy"],
            "social": ["social", "friends", "family", "birthdays"],
            "projects": ["project", "diy", "improvement"],
        }

        project_lower = project_name.lower()
        for area, keywords in area_keywords.items():
            if any(kw in project_lower for kw in keywords):
                return area

        return project_name.lower()

    def _infer_task_type(self, todoist: Any) -> TaskType:
        """Infer task type from Todoist task."""
        content_lower = todoist.content.lower()
        labels = [l.lower() for l in (todoist.labels or [])]

        # Check labels first
        if "quick" in labels or "5min" in labels:
            return TaskType.QUICK_WIN
        if "deep" in labels or "focus" in labels:
            return TaskType.DEEP_WORK
        if "creative" in labels or "design" in labels:
            return TaskType.CREATIVE
        if "errand" in labels:
            return TaskType.ERRAND

        # Check content
        if any(word in content_lower for word in ["call", "email", "text", "message", "reply"]):
            return TaskType.COMMUNICATION
        if any(word in content_lower for word in ["buy", "pick up", "get", "shop"]):
            return TaskType.ERRAND
        if any(word in content_lower for word in ["clean", "wash", "organize", "tidy"]):
            return TaskType.ROUTINE

        return TaskType.ROUTINE

    # Sync back to Todoist

    async def push_task(self, task: Task) -> str | None:
        """Push a new task to Todoist."""
        try:
            # Find or create project
            project_id = await self._get_or_create_project(task.area or "Inbox")

            todoist_task = await self.async_api.add_task(
                content=task.title,
                description=task.description,
                project_id=project_id,
                priority=self.REVERSE_PRIORITY_MAP.get(task.priority, 1),
                due_string=self._format_due_date(task.due_date),
                labels=task.tags if task.tags else None,
            )

            # Update local task with Todoist ID
            task.metadata["todoist_id"] = todoist_task.id
            task.metadata["todoist_synced"] = datetime.now().isoformat()
            self.store.save_task(task)

            return todoist_task.id
        except Exception as e:
            logger.error(f"Failed to push task to Todoist: {e}")
            return None

    async def complete_task(self, task: Task) -> bool:
        """Mark task as complete in Todoist."""
        todoist_id = task.metadata.get("todoist_id")
        if not todoist_id:
            return False

        try:
            await self.async_api.close_task(todoist_id)
            return True
        except Exception as e:
            logger.error(f"Failed to complete task in Todoist: {e}")
            return False

    async def _get_or_create_project(self, name: str) -> str | None:
        """Get existing project or create new one."""
        # Check cache
        for project_id, project_name in self._project_cache.items():
            if project_name.lower() == name.lower():
                return project_id

        # Create new project
        try:
            project = await self.async_api.add_project(name=name)
            self._project_cache[project.id] = project.name
            return project.id
        except Exception as e:
            logger.error(f"Failed to create project: {e}")
            return None

    def _format_due_date(self, due_date: datetime | None) -> str | None:
        """Format due date for Todoist."""
        if not due_date:
            return None
        return due_date.strftime("%Y-%m-%d")

    # Convenience methods

    def sync_blocking(self) -> dict[str, Any]:
        """Synchronous sync wrapper."""
        logger.info("Starting Todoist sync")

        # Refresh caches
        try:
            # The paginator yields pages (lists), so we need to flatten them
            projects = []
            for page in self.api.get_projects():
                projects.extend(page if isinstance(page, list) else [page])
            self._project_cache = {p.id: p.name for p in projects}

            labels = []
            for page in self.api.get_labels():
                labels.extend(page if isinstance(page, list) else [page])
            self._label_cache = {l.id: l.name for l in labels}

            logger.info("Cache refresh successful")
        except Exception as e:
            logger.warning(f"Failed to refresh caches: {e}")
            import traceback
            traceback.print_exc()

        # Get all active tasks from Todoist (returns a paginator that yields pages)
        synced = 0
        created = 0
        updated = 0
        todoist_tasks = []

        for page in self.api.get_tasks():
            page_tasks = page if isinstance(page, list) else [page]
            for todoist_task in page_tasks:
                todoist_tasks.append(todoist_task)

                # Check if we have this task locally
                local_task = self._find_local_task(todoist_task.id)

                if local_task:
                    # Update local task if Todoist version is newer
                    if self._needs_update(local_task, todoist_task):
                        self._update_local_task(local_task, todoist_task)
                        updated += 1
                else:
                    # Create new local task
                    self._create_local_task(todoist_task)
                    created += 1

                synced += 1

        logger.info(f"Synced {synced} tasks")

        # Handle completed tasks (mark local tasks as done if not in Todoist)
        self._sync_completed_tasks(todoist_tasks)

        logger.info(f"Sync complete: {synced} synced, {created} created, {updated} updated")

        return {
            "synced": synced,
            "created": created,
            "updated": updated,
            "timestamp": datetime.now().isoformat(),
        }

    async def get_todoist_projects(self) -> list[dict[str, str]]:
        """Get all Todoist projects."""
        projects = await self.async_api.get_projects()
        return [{"id": p.id, "name": p.name} for p in projects]

    async def get_todoist_labels(self) -> list[dict[str, str]]:
        """Get all Todoist labels."""
        labels = await self.async_api.get_labels()
        return [{"id": l.id, "name": l.name} for l in labels]
