"""House management system - Chores, Maintenance, Projects."""

from datetime import datetime, timedelta
from typing import Any
import json

from ..data.store import Store
from .models import (
    Urgency,
    ChoreType,
    Room,
    ChoreInstance,
    MaintenanceTask,
    HomeProject,
    ProjectStatus,
    ProjectStep,
    Checklist,
    ChecklistItem,
    ChecklistItemImportance,
)


class HouseManager:
    """Manages house chores, maintenance, and projects.

    Core concept: ChoreType + Room = ChoreInstance
    Each room can have different settings for the same chore type.
    """

    # Default chore types
    DEFAULT_CHORE_TYPES = [
        ChoreType(id="vacuum", name="Vacuum", icon="🧹", description="Vacuum floors and carpets", default_interval_days=7, default_duration_minutes=15, color="#C2410C"),
        ChoreType(id="mop", name="Mop", icon="🪣", description="Mop hard floors", default_interval_days=14, default_duration_minutes=20, color="#0369A1"),
        ChoreType(id="dust", name="Dust", icon="✨", description="Dust surfaces and furniture", default_interval_days=14, default_duration_minutes=15, color="#CA8A04"),
        ChoreType(id="declutter", name="Declutter", icon="📦", description="Organize and declutter", default_interval_days=30, default_duration_minutes=30, color="#7C3AED"),
        ChoreType(id="clean_bathroom", name="Clean Bathroom", icon="🚿", description="Clean bathroom surfaces", default_interval_days=7, default_duration_minutes=25, color="#0891B2"),
        ChoreType(id="clean_toilet", name="Clean Toilet", icon="🚽", description="Clean and sanitize toilet", default_interval_days=7, default_duration_minutes=10, color="#0891B2"),
        ChoreType(id="change_sheets", name="Change Sheets", icon="🛏️", description="Change bed linens", default_interval_days=14, default_duration_minutes=15, color="#DB2777"),
        ChoreType(id="wipe_surfaces", name="Wipe Surfaces", icon="🧽", description="Wipe down counters and surfaces", default_interval_days=3, default_duration_minutes=10, color="#059669"),
        ChoreType(id="clean_windows", name="Clean Windows", icon="🪟", description="Clean windows and mirrors", default_interval_days=30, default_duration_minutes=20, color="#0EA5E9"),
        ChoreType(id="deep_clean", name="Deep Clean", icon="🧼", description="Deep clean the area", default_interval_days=90, default_duration_minutes=60, color="#DC2626"),
    ]

    # Default rooms
    DEFAULT_ROOMS = [
        Room(id="living", name="Living Room", icon="🛋️", zone="indoor", color="#B45309", sort_order=1),
        Room(id="bedroom", name="Bedroom", icon="🛏️", zone="indoor", color="#7C3AED", sort_order=2),
        Room(id="bathroom", name="Bathroom", icon="🚿", zone="indoor", color="#0891B2", sort_order=3),
        Room(id="kitchen", name="Kitchen", icon="🍳", zone="indoor", color="#059669", sort_order=4),
        Room(id="office", name="Office", icon="💻", zone="indoor", color="#4F46E5", sort_order=5),
        Room(id="hallway", name="Hallway", icon="🚪", zone="indoor", color="#78716C", sort_order=6),
        Room(id="garage", name="Garage", icon="🚗", zone="garage", color="#57534E", sort_order=7),
        Room(id="outdoor", name="Outdoor", icon="🌳", zone="outdoor", color="#15803D", sort_order=8),
    ]

    def __init__(self, store: Store):
        """Initialize with data store."""
        self.store = store
        self._ensure_defaults()

    def _ensure_defaults(self) -> None:
        """Ensure default chore types and rooms exist."""
        types = self._load_chore_types()
        if not types:
            for ct in self.DEFAULT_CHORE_TYPES:
                self._save_chore_type(ct)

        rooms = self._load_rooms()
        if not rooms:
            for room in self.DEFAULT_ROOMS:
                self._save_room(room)

    # ==================== Chore Types ====================

    def get_chore_types(self, active_only: bool = True) -> list[ChoreType]:
        """Get all chore types."""
        types = self._load_chore_types()
        if active_only:
            types = [t for t in types if t.active]
        return types

    def get_chore_type(self, type_id: str) -> ChoreType | None:
        """Get a chore type by ID."""
        types = self._load_chore_types()
        for t in types:
            if t.id == type_id:
                return t
        return None

    def add_chore_type(self, chore_type: ChoreType) -> ChoreType:
        """Add a new chore type."""
        self._save_chore_type(chore_type)
        self.store.log_activity("chore_type_created", "chore_type", chore_type.id, {"name": chore_type.name})
        return chore_type

    def update_chore_type(self, type_id: str, **updates: Any) -> ChoreType | None:
        """Update a chore type."""
        chore_type = self.get_chore_type(type_id)
        if not chore_type:
            return None
        for key, value in updates.items():
            if hasattr(chore_type, key):
                setattr(chore_type, key, value)
        self._save_chore_type(chore_type)
        return chore_type

    # ==================== Rooms ====================

    def get_rooms(self, zone: str | None = None) -> list[Room]:
        """Get all rooms, optionally filtered by zone."""
        rooms = self._load_rooms()
        if zone:
            rooms = [r for r in rooms if r.zone == zone]
        rooms.sort(key=lambda r: r.sort_order)
        return rooms

    def get_room(self, room_id: str) -> Room | None:
        """Get a room by ID."""
        rooms = self._load_rooms()
        for r in rooms:
            if r.id == room_id:
                return r
        return None

    def add_room(self, room: Room) -> Room:
        """Add a new room."""
        self._save_room(room)
        self.store.log_activity("room_created", "room", room.id, {"name": room.name})
        return room

    def update_room(self, room_id: str, **updates: Any) -> Room | None:
        """Update a room."""
        room = self.get_room(room_id)
        if not room:
            return None
        for key, value in updates.items():
            if hasattr(room, key):
                setattr(room, key, value)
        self._save_room(room)
        return room

    # ==================== Chore Instances ====================

    def get_chore_instances(
        self,
        room_id: str | None = None,
        chore_type_id: str | None = None,
        enabled_only: bool = True,
    ) -> list[ChoreInstance]:
        """Get chore instances with optional filters."""
        instances = self._load_chore_instances()

        if enabled_only:
            instances = [i for i in instances if i.enabled]
        if room_id:
            instances = [i for i in instances if i.room_id == room_id]
        if chore_type_id:
            instances = [i for i in instances if i.chore_type_id == chore_type_id]

        return instances

    def get_chore_instance(self, instance_id: str) -> ChoreInstance | None:
        """Get a chore instance by ID."""
        instances = self._load_chore_instances()
        for i in instances:
            if i.id == instance_id:
                return i
        return None

    def get_or_create_instance(self, chore_type_id: str, room_id: str) -> ChoreInstance:
        """Get existing instance or create a new one for chore+room combination."""
        instances = self.get_chore_instances(room_id=room_id, chore_type_id=chore_type_id, enabled_only=False)
        if instances:
            return instances[0]

        instance = ChoreInstance(chore_type_id=chore_type_id, room_id=room_id)
        self._save_chore_instance(instance)
        self.store.log_activity("chore_instance_created", "chore_instance", instance.id, {
            "chore_type_id": chore_type_id,
            "room_id": room_id,
        })
        return instance

    def add_chore_instance(self, instance: ChoreInstance) -> ChoreInstance:
        """Add a new chore instance."""
        self._save_chore_instance(instance)
        return instance

    def update_chore_instance(self, instance_id: str, **updates: Any) -> ChoreInstance | None:
        """Update a chore instance."""
        instance = self.get_chore_instance(instance_id)
        if not instance:
            return None
        for key, value in updates.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        self._save_chore_instance(instance)
        return instance

    def complete_chore(self, instance_id: str) -> ChoreInstance | None:
        """Mark a chore instance as complete."""
        instance = self.get_chore_instance(instance_id)
        if not instance:
            return None

        chore_type = self.get_chore_type(instance.chore_type_id)
        if not chore_type:
            return None

        now = datetime.now()

        # Update streak
        if not instance.is_overdue(chore_type):
            instance.streak += 1
        else:
            instance.streak = 1

        instance.last_completed = now
        instance.completion_count += 1

        self._save_chore_instance(instance)
        self.store.log_activity("chore_completed", "chore_instance", instance.id, {
            "chore_type_id": instance.chore_type_id,
            "room_id": instance.room_id,
            "streak": instance.streak,
        })

        return instance

    def skip_chore(self, instance_id: str, reason: str = "") -> ChoreInstance | None:
        """Skip a chore (resets due date without completion credit)."""
        instance = self.get_chore_instance(instance_id)
        if not instance:
            return None

        instance.last_completed = datetime.now()
        instance.streak = 0

        self._save_chore_instance(instance)
        self.store.log_activity("chore_skipped", "chore_instance", instance.id, {"reason": reason})

        return instance

    def delete_chore_instance(self, instance_id: str) -> bool:
        """Delete a chore instance."""
        instances = self._load_chore_instances()
        original_len = len(instances)
        instances = [i for i in instances if i.id != instance_id]
        if len(instances) < original_len:
            self._save_all_chore_instances(instances)
            return True
        return False

    # ==================== Filtering & Queries ====================

    def get_due_chores(self, limit: int | None = None) -> list[dict[str, Any]]:
        """Get chores that are due, enriched with type and room info."""
        instances = self.get_chore_instances(enabled_only=True)
        due = []

        for instance in instances:
            chore_type = self.get_chore_type(instance.chore_type_id)
            room = self.get_room(instance.room_id)
            if not chore_type or not room:
                continue

            if instance.is_due(chore_type):
                due.append({
                    "instance": instance,
                    "chore_type": chore_type,
                    "room": room,
                    "urgency_score": instance.urgency_score(chore_type),
                    "days_until_due": instance.days_until_due(chore_type),
                    "freshness": instance.freshness_percent(chore_type),
                    "is_overdue": instance.is_overdue(chore_type),
                })

        due.sort(key=lambda x: x["urgency_score"], reverse=True)

        if limit:
            due = due[:limit]

        return due

    def get_overdue_chores(self) -> list[dict[str, Any]]:
        """Get overdue chores."""
        instances = self.get_chore_instances(enabled_only=True)
        overdue = []

        for instance in instances:
            chore_type = self.get_chore_type(instance.chore_type_id)
            room = self.get_room(instance.room_id)
            if not chore_type or not room:
                continue

            if instance.is_overdue(chore_type):
                overdue.append({
                    "instance": instance,
                    "chore_type": chore_type,
                    "room": room,
                    "days_overdue": abs(instance.days_until_due(chore_type)),
                })

        overdue.sort(key=lambda x: x["days_overdue"], reverse=True)
        return overdue

    def get_chores_by_room(self, room_id: str) -> list[dict[str, Any]]:
        """Get all chores for a room with their status."""
        instances = self.get_chore_instances(room_id=room_id, enabled_only=True)
        room = self.get_room(room_id)
        if not room:
            return []

        chores = []
        for instance in instances:
            chore_type = self.get_chore_type(instance.chore_type_id)
            if not chore_type:
                continue

            chores.append({
                "instance": instance,
                "chore_type": chore_type,
                "room": room,
                "is_due": instance.is_due(chore_type),
                "is_overdue": instance.is_overdue(chore_type),
                "days_until_due": instance.days_until_due(chore_type),
                "freshness": instance.freshness_percent(chore_type),
                "duration": instance.get_duration(chore_type),
                "interval": instance.get_interval(chore_type),
            })

        chores.sort(key=lambda x: x["instance"].urgency_score(x["chore_type"]), reverse=True)
        return chores

    def get_chores_by_type(self, chore_type_id: str) -> list[dict[str, Any]]:
        """Get all rooms that have this chore type with their status."""
        instances = self.get_chore_instances(chore_type_id=chore_type_id, enabled_only=True)
        chore_type = self.get_chore_type(chore_type_id)
        if not chore_type:
            return []

        chores = []
        for instance in instances:
            room = self.get_room(instance.room_id)
            if not room:
                continue

            chores.append({
                "instance": instance,
                "chore_type": chore_type,
                "room": room,
                "is_due": instance.is_due(chore_type),
                "is_overdue": instance.is_overdue(chore_type),
                "days_until_due": instance.days_until_due(chore_type),
                "freshness": instance.freshness_percent(chore_type),
                "duration": instance.get_duration(chore_type),
                "interval": instance.get_interval(chore_type),
            })

        chores.sort(key=lambda x: x["instance"].urgency_score(x["chore_type"]), reverse=True)
        return chores

    def get_chores_for_time(self, available_minutes: int, room_id: str | None = None) -> list[dict[str, Any]]:
        """Get due chores that fit within available time."""
        due = self.get_due_chores()

        if room_id:
            due = [d for d in due if d["room"].id == room_id]

        fitting = []
        for d in due:
            duration = d["instance"].get_duration(d["chore_type"])
            if duration <= available_minutes:
                d["duration"] = duration
                fitting.append(d)

        return fitting

    def get_room_freshness(self, room_id: str) -> int:
        """Get overall freshness of a room (0-100)."""
        chores = self.get_chores_by_room(room_id)
        if not chores:
            return 100

        total_freshness = sum(c["freshness"] for c in chores)
        return int(total_freshness / len(chores))

    def get_all_rooms_status(self) -> list[dict[str, Any]]:
        """Get status of all rooms."""
        rooms = self.get_rooms()
        result = []

        for room in rooms:
            chores = self.get_chores_by_room(room.id)
            due_count = sum(1 for c in chores if c["is_due"])
            overdue_count = sum(1 for c in chores if c["is_overdue"])

            result.append({
                "room": room,
                "freshness": self.get_room_freshness(room.id),
                "total_chores": len(chores),
                "due_count": due_count,
                "overdue_count": overdue_count,
            })

        result.sort(key=lambda x: x["freshness"])
        return result

    # ==================== Maintenance Tasks ====================

    def get_maintenance_tasks(self, enabled_only: bool = True) -> list[MaintenanceTask]:
        """Get all maintenance tasks."""
        tasks = self._load_maintenance_tasks()
        if enabled_only:
            tasks = [t for t in tasks if t.enabled]
        return tasks

    def get_maintenance_task(self, task_id: str) -> MaintenanceTask | None:
        """Get a maintenance task by ID."""
        tasks = self._load_maintenance_tasks()
        for t in tasks:
            if t.id == task_id:
                return t
        return None

    def add_maintenance_task(self, task: MaintenanceTask) -> MaintenanceTask:
        """Add a new maintenance task."""
        self._save_maintenance_task(task)
        self.store.log_activity("maintenance_created", "maintenance", task.id, {"name": task.name})
        return task

    def update_maintenance_task(self, task_id: str, **updates: Any) -> MaintenanceTask | None:
        """Update a maintenance task."""
        task = self.get_maintenance_task(task_id)
        if not task:
            return None
        for key, value in updates.items():
            if hasattr(task, key):
                setattr(task, key, value)
        self._save_maintenance_task(task)
        return task

    def complete_maintenance_task(self, task_id: str) -> MaintenanceTask | None:
        """Mark a maintenance task as complete."""
        task = self.get_maintenance_task(task_id)
        if not task:
            return None

        task.last_completed = datetime.now()
        task.next_due = None  # Reset to calculated due

        self._save_maintenance_task(task)
        self.store.log_activity("maintenance_completed", "maintenance", task.id, {"name": task.name})
        return task

    def get_due_maintenance(self) -> list[MaintenanceTask]:
        """Get maintenance tasks that are due or coming up soon."""
        tasks = self.get_maintenance_tasks(enabled_only=True)
        due = [t for t in tasks if t.days_until_due <= 30]
        due.sort(key=lambda t: t.days_until_due)
        return due

    def delete_maintenance_task(self, task_id: str) -> bool:
        """Delete a maintenance task."""
        tasks = self._load_maintenance_tasks()
        original_len = len(tasks)
        tasks = [t for t in tasks if t.id != task_id]
        if len(tasks) < original_len:
            self._save_all_maintenance_tasks(tasks)
            return True
        return False

    # ==================== Home Projects ====================

    def get_projects(self, status: ProjectStatus | None = None) -> list[HomeProject]:
        """Get all projects, optionally filtered by status."""
        projects = self._load_projects()
        if status:
            projects = [p for p in projects if p.status == status]
        return projects

    def get_project(self, project_id: str) -> HomeProject | None:
        """Get a project by ID."""
        projects = self._load_projects()
        for p in projects:
            if p.id == project_id:
                return p
        return None

    def add_project(self, project: HomeProject) -> HomeProject:
        """Add a new project."""
        self._save_project(project)
        self.store.log_activity("project_created", "project", project.id, {"name": project.name})
        return project

    def update_project(self, project_id: str, **updates: Any) -> HomeProject | None:
        """Update a project."""
        project = self.get_project(project_id)
        if not project:
            return None
        for key, value in updates.items():
            if hasattr(project, key):
                setattr(project, key, value)
        self._save_project(project)
        return project

    def add_project_step(self, project_id: str, step: ProjectStep) -> HomeProject | None:
        """Add a step to a project."""
        project = self.get_project(project_id)
        if not project:
            return None
        project.steps.append(step)
        self._save_project(project)
        return project

    def toggle_project_step(self, project_id: str, step_index: int) -> HomeProject | None:
        """Toggle completion of a project step."""
        project = self.get_project(project_id)
        if not project or step_index >= len(project.steps):
            return None
        project.steps[step_index].done = not project.steps[step_index].done
        self._save_project(project)
        return project

    def delete_project(self, project_id: str) -> bool:
        """Delete a project."""
        projects = self._load_projects()
        original_len = len(projects)
        projects = [p for p in projects if p.id != project_id]
        if len(projects) < original_len:
            self._save_all_projects(projects)
            return True
        return False

    # ==================== Checklists ====================

    def get_checklists(self) -> list[Checklist]:
        """Get all checklists."""
        return self._load_checklists()

    def get_checklist(self, checklist_id: str) -> Checklist | None:
        """Get a checklist by ID."""
        checklists = self._load_checklists()
        for c in checklists:
            if c.id == checklist_id:
                return c
        return None

    def add_checklist(self, checklist: Checklist) -> Checklist:
        """Add a new checklist."""
        self._save_checklist(checklist)
        self.store.log_activity("checklist_created", "checklist", checklist.id, {"name": checklist.name})
        return checklist

    def update_checklist(self, checklist_id: str, **updates: Any) -> Checklist | None:
        """Update a checklist."""
        checklist = self.get_checklist(checklist_id)
        if not checklist:
            return None
        for key, value in updates.items():
            if hasattr(checklist, key):
                setattr(checklist, key, value)
        self._save_checklist(checklist)
        return checklist

    def get_checklist_chores(self, checklist_id: str) -> list[dict[str, Any]]:
        """Get the chores for a checklist with their current status."""
        checklist = self.get_checklist(checklist_id)
        if not checklist:
            return []

        result = []
        for item in checklist.items:
            instance = self.get_chore_instance(item.chore_instance_id)
            if not instance:
                continue
            chore_type = self.get_chore_type(instance.chore_type_id)
            room = self.get_room(instance.room_id)
            if not chore_type or not room:
                continue

            result.append({
                "instance": instance,
                "chore_type": chore_type,
                "room": room,
                "importance": item.importance,
                "freshness": instance.freshness_percent(chore_type),
                "is_due": instance.is_due(chore_type),
            })

        # Sort by importance
        importance_order = {
            ChecklistItemImportance.MUST: 0,
            ChecklistItemImportance.NICE: 1,
            ChecklistItemImportance.OPTIONAL: 2,
        }
        result.sort(key=lambda x: importance_order[x["importance"]])
        return result

    def delete_checklist(self, checklist_id: str) -> bool:
        """Delete a checklist."""
        checklists = self._load_checklists()
        original_len = len(checklists)
        checklists = [c for c in checklists if c.id != checklist_id]
        if len(checklists) < original_len:
            self._save_all_checklists(checklists)
            return True
        return False

    # ==================== Stats ====================

    def get_stats(self) -> dict[str, Any]:
        """Get overall house management statistics."""
        instances = self.get_chore_instances(enabled_only=True)
        due_chores = self.get_due_chores()
        overdue_chores = self.get_overdue_chores()
        maintenance_due = self.get_due_maintenance()
        projects = self.get_projects()
        active_projects = [p for p in projects if p.status == ProjectStatus.IN_PROGRESS]

        # Calculate streaks
        total_streak = sum(i.streak for i in instances)
        longest_streak = max((i.streak for i in instances), default=0)

        # Completed this week
        week_ago = datetime.now() - timedelta(days=7)
        completed_this_week = sum(
            1 for i in instances
            if i.last_completed and i.last_completed > week_ago
        )

        # Average room freshness
        rooms = self.get_rooms()
        avg_freshness = 0
        if rooms:
            avg_freshness = sum(self.get_room_freshness(r.id) for r in rooms) // len(rooms)

        return {
            "total_chores": len(instances),
            "due_now": len(due_chores),
            "overdue": len(overdue_chores),
            "completed_this_week": completed_this_week,
            "average_streak": total_streak / len(instances) if instances else 0,
            "longest_streak": longest_streak,
            "average_freshness": avg_freshness,
            "maintenance_due": len(maintenance_due),
            "active_projects": len(active_projects),
            "total_projects": len(projects),
        }

    # ==================== Storage Helpers ====================

    def _load_chore_types(self) -> list[ChoreType]:
        """Load chore types from storage."""
        memory = self.store.get_memory("house_chore_types")
        if memory and memory.value:
            try:
                data = json.loads(memory.value) if isinstance(memory.value, str) else memory.value
                return [ChoreType.from_dict(d) for d in data]
            except (json.JSONDecodeError, TypeError):
                pass
        return []

    def _save_chore_type(self, chore_type: ChoreType) -> None:
        """Save a chore type."""
        types = self._load_chore_types()
        found = False
        for i, t in enumerate(types):
            if t.id == chore_type.id:
                types[i] = chore_type
                found = True
                break
        if not found:
            types.append(chore_type)
        self._save_all_chore_types(types)

    def _save_all_chore_types(self, types: list[ChoreType]) -> None:
        """Save all chore types."""
        from ..data.models import Memory
        data = json.dumps([t.to_dict() for t in types])
        memory = Memory(key="house_chore_types", value=data, memory_type="data", context="Chore types")
        self.store.save_memory(memory)

    def _load_rooms(self) -> list[Room]:
        """Load rooms from storage."""
        memory = self.store.get_memory("house_rooms")
        if memory and memory.value:
            try:
                data = json.loads(memory.value) if isinstance(memory.value, str) else memory.value
                return [Room.from_dict(d) for d in data]
            except (json.JSONDecodeError, TypeError):
                pass
        return []

    def _save_room(self, room: Room) -> None:
        """Save a room."""
        rooms = self._load_rooms()
        found = False
        for i, r in enumerate(rooms):
            if r.id == room.id:
                rooms[i] = room
                found = True
                break
        if not found:
            rooms.append(room)
        self._save_all_rooms(rooms)

    def _save_all_rooms(self, rooms: list[Room]) -> None:
        """Save all rooms."""
        from ..data.models import Memory
        data = json.dumps([r.to_dict() for r in rooms])
        memory = Memory(key="house_rooms", value=data, memory_type="data", context="Rooms")
        self.store.save_memory(memory)

    def _load_chore_instances(self) -> list[ChoreInstance]:
        """Load chore instances from storage."""
        memory = self.store.get_memory("house_chore_instances")
        if memory and memory.value:
            try:
                data = json.loads(memory.value) if isinstance(memory.value, str) else memory.value
                return [ChoreInstance.from_dict(d) for d in data]
            except (json.JSONDecodeError, TypeError):
                pass
        return []

    def _save_chore_instance(self, instance: ChoreInstance) -> None:
        """Save a chore instance."""
        instances = self._load_chore_instances()
        found = False
        for i, inst in enumerate(instances):
            if inst.id == instance.id:
                instances[i] = instance
                found = True
                break
        if not found:
            instances.append(instance)
        self._save_all_chore_instances(instances)

    def _save_all_chore_instances(self, instances: list[ChoreInstance]) -> None:
        """Save all chore instances."""
        from ..data.models import Memory
        data = json.dumps([i.to_dict() for i in instances])
        memory = Memory(key="house_chore_instances", value=data, memory_type="data", context="Chore instances")
        self.store.save_memory(memory)

    def _load_maintenance_tasks(self) -> list[MaintenanceTask]:
        """Load maintenance tasks from storage."""
        memory = self.store.get_memory("house_maintenance")
        if memory and memory.value:
            try:
                data = json.loads(memory.value) if isinstance(memory.value, str) else memory.value
                return [MaintenanceTask.from_dict(d) for d in data]
            except (json.JSONDecodeError, TypeError):
                pass
        return []

    def _save_maintenance_task(self, task: MaintenanceTask) -> None:
        """Save a maintenance task."""
        tasks = self._load_maintenance_tasks()
        found = False
        for i, t in enumerate(tasks):
            if t.id == task.id:
                tasks[i] = task
                found = True
                break
        if not found:
            tasks.append(task)
        self._save_all_maintenance_tasks(tasks)

    def _save_all_maintenance_tasks(self, tasks: list[MaintenanceTask]) -> None:
        """Save all maintenance tasks."""
        from ..data.models import Memory
        data = json.dumps([t.to_dict() for t in tasks])
        memory = Memory(key="house_maintenance", value=data, memory_type="data", context="Maintenance tasks")
        self.store.save_memory(memory)

    def _load_projects(self) -> list[HomeProject]:
        """Load projects from storage."""
        memory = self.store.get_memory("house_projects")
        if memory and memory.value:
            try:
                data = json.loads(memory.value) if isinstance(memory.value, str) else memory.value
                return [HomeProject.from_dict(d) for d in data]
            except (json.JSONDecodeError, TypeError):
                pass
        return []

    def _save_project(self, project: HomeProject) -> None:
        """Save a project."""
        projects = self._load_projects()
        found = False
        for i, p in enumerate(projects):
            if p.id == project.id:
                projects[i] = project
                found = True
                break
        if not found:
            projects.append(project)
        self._save_all_projects(projects)

    def _save_all_projects(self, projects: list[HomeProject]) -> None:
        """Save all projects."""
        from ..data.models import Memory
        data = json.dumps([p.to_dict() for p in projects])
        memory = Memory(key="house_projects", value=data, memory_type="data", context="Home projects")
        self.store.save_memory(memory)

    def _load_checklists(self) -> list[Checklist]:
        """Load checklists from storage."""
        memory = self.store.get_memory("house_checklists")
        if memory and memory.value:
            try:
                data = json.loads(memory.value) if isinstance(memory.value, str) else memory.value
                return [Checklist.from_dict(d) for d in data]
            except (json.JSONDecodeError, TypeError):
                pass
        return []

    def _save_checklist(self, checklist: Checklist) -> None:
        """Save a checklist."""
        checklists = self._load_checklists()
        found = False
        for i, c in enumerate(checklists):
            if c.id == checklist.id:
                checklists[i] = checklist
                found = True
                break
        if not found:
            checklists.append(checklist)
        self._save_all_checklists(checklists)

    def _save_all_checklists(self, checklists: list[Checklist]) -> None:
        """Save all checklists."""
        from ..data.models import Memory
        data = json.dumps([c.to_dict() for c in checklists])
        memory = Memory(key="house_checklists", value=data, memory_type="data", context="Checklists")
        self.store.save_memory(memory)
