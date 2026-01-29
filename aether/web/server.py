"""FastAPI web server for Aether House Manager."""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ..core.engine import Aether
from ..data.models import EnergyLevel, TaskStatus, TaskPriority
from ..chores.manager import HouseManager
from ..chores.models import (
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
    Urgency,
)


# Request/Response models
class TaskCreate(BaseModel):
    text: str


class TaskUpdate(BaseModel):
    status: str | None = None
    priority: str | None = None
    due_date: str | None = None


class EnergyUpdate(BaseModel):
    level: str
    note: str = ""


class TimeAvailable(BaseModel):
    minutes: int


class ChoreTypeCreate(BaseModel):
    name: str
    icon: str = "🧹"
    description: str = ""
    default_interval_days: int = 7
    default_duration_minutes: int = 15
    color: str = "#6B7280"


class ChoreTypeUpdate(BaseModel):
    name: str | None = None
    icon: str | None = None
    description: str | None = None
    default_interval_days: int | None = None
    default_duration_minutes: int | None = None
    color: str | None = None
    active: bool | None = None


class RoomCreate(BaseModel):
    name: str
    icon: str = "🏠"
    zone: str = "indoor"
    color: str = "#6B7280"
    sort_order: int = 0


class RoomUpdate(BaseModel):
    name: str | None = None
    icon: str | None = None
    zone: str | None = None
    color: str | None = None
    sort_order: int | None = None


class ChoreInstanceCreate(BaseModel):
    chore_type_id: str
    room_id: str
    interval_days: int | None = None
    duration_minutes: int | None = None
    urgency: str = "normal"


class ChoreInstanceUpdate(BaseModel):
    interval_days: int | None = None
    duration_minutes: int | None = None
    urgency: str | None = None
    enabled: bool | None = None
    notes: str | None = None


class MaintenanceCreate(BaseModel):
    name: str
    description: str = ""
    icon: str = "🔧"
    interval_days: int = 365
    provider: str = ""
    estimated_cost: float | None = None
    notes: str = ""


class MaintenanceUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    icon: str | None = None
    interval_days: int | None = None
    provider: str | None = None
    estimated_cost: float | None = None
    notes: str | None = None
    enabled: bool | None = None


class ProjectCreate(BaseModel):
    name: str
    description: str = ""
    icon: str = "🏗️"
    budget: float | None = None
    target_date: str | None = None
    notes: str = ""


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    icon: str | None = None
    status: str | None = None
    budget: float | None = None
    spent: float | None = None
    target_date: str | None = None
    notes: str | None = None


class ProjectStepCreate(BaseModel):
    name: str
    notes: str = ""


class ChecklistCreate(BaseModel):
    name: str
    description: str = ""
    icon: str = "📋"
    color: str = "#6B7280"


class ChecklistItemCreate(BaseModel):
    chore_instance_id: str
    importance: str = "must"


class VoiceCommand(BaseModel):
    text: str


# Global instances (initialized on startup)
aether: Aether | None = None
house: HouseManager | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize on startup, cleanup on shutdown."""
    global aether, house
    aether = Aether()
    house = HouseManager(aether.store)
    yield


def create_app() -> FastAPI:
    """Create FastAPI application."""
    app = FastAPI(
        title="Aether",
        description="House Manager - Keep your home running smoothly",
        version="0.3.0",
        lifespan=lifespan,
    )

    # CORS for mobile access
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Static files
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    # Routes

    @app.get("/", response_class=HTMLResponse)
    async def root():
        """Serve main app page."""
        template_path = Path(__file__).parent / "templates" / "index.html"
        if template_path.exists():
            return template_path.read_text()
        return "<html><body><h1>Aether</h1><p>Template not found</p></body></html>"

    @app.get("/manifest.json")
    async def manifest():
        """PWA manifest."""
        return {
            "name": "Aether",
            "short_name": "Aether",
            "description": "House Manager",
            "start_url": "/",
            "display": "standalone",
            "background_color": "#FDF6E3",
            "theme_color": "#C2410C",
            "icons": [
                {"src": "/static/icon-192.png", "sizes": "192x192", "type": "image/png"},
                {"src": "/static/icon-512.png", "sizes": "512x512", "type": "image/png"},
            ],
        }

    # ==================== Status & Overview ====================

    @app.get("/api/status")
    async def get_status():
        """Get quick status overview."""
        if not aether or not house:
            raise HTTPException(status_code=503, detail="Not initialized")

        stats = house.get_stats()
        ctx = aether.context.get_current()

        return {
            "energy": ctx.energy.value,
            "chores_due": stats["due_now"],
            "overdue_count": stats["overdue"],
            "maintenance_due": stats["maintenance_due"],
            "active_projects": stats["active_projects"],
            "average_freshness": stats["average_freshness"],
        }

    @app.get("/api/briefing")
    async def get_briefing():
        """Get morning briefing."""
        if not aether or not house:
            raise HTTPException(status_code=503, detail="Not initialized")

        stats = house.get_stats()
        due_chores = house.get_due_chores(limit=5)
        overdue = house.get_overdue_chores()
        maintenance = house.get_due_maintenance()[:3]
        rooms = house.get_all_rooms_status()[:3]  # Rooms needing attention

        return {
            "summary": {
                "chores_due": stats["due_now"],
                "overdue": stats["overdue"],
                "maintenance_due": stats["maintenance_due"],
                "average_freshness": stats["average_freshness"],
            },
            "priority_chores": [
                {
                    "id": c["instance"].id,
                    "name": f"{c['chore_type'].name} - {c['room'].name}",
                    "icon": c["chore_type"].icon,
                    "room_icon": c["room"].icon,
                    "urgency": c["urgency_score"],
                    "is_overdue": c["is_overdue"],
                }
                for c in due_chores
            ],
            "rooms_needing_attention": [
                {
                    "name": r["room"].name,
                    "icon": r["room"].icon,
                    "freshness": r["freshness"],
                    "due_count": r["due_count"],
                }
                for r in rooms
            ],
            "upcoming_maintenance": [
                {
                    "id": m.id,
                    "name": m.name,
                    "icon": m.icon,
                    "days_until_due": m.days_until_due,
                }
                for m in maintenance
            ],
        }

    # ==================== Chore Types ====================

    @app.get("/api/chore-types")
    async def get_chore_types(active_only: bool = True):
        """Get all chore types."""
        if not house:
            raise HTTPException(status_code=503, detail="Not initialized")
        types = house.get_chore_types(active_only=active_only)
        return [t.to_dict() for t in types]

    @app.get("/api/chore-types/{type_id}")
    async def get_chore_type(type_id: str):
        """Get a specific chore type."""
        if not house:
            raise HTTPException(status_code=503, detail="Not initialized")
        ct = house.get_chore_type(type_id)
        if not ct:
            raise HTTPException(status_code=404, detail="Chore type not found")
        return ct.to_dict()

    @app.post("/api/chore-types")
    async def create_chore_type(data: ChoreTypeCreate):
        """Create a new chore type."""
        if not house:
            raise HTTPException(status_code=503, detail="Not initialized")
        ct = ChoreType(
            name=data.name,
            icon=data.icon,
            description=data.description,
            default_interval_days=data.default_interval_days,
            default_duration_minutes=data.default_duration_minutes,
            color=data.color,
        )
        house.add_chore_type(ct)
        return ct.to_dict()

    @app.patch("/api/chore-types/{type_id}")
    async def update_chore_type(type_id: str, data: ChoreTypeUpdate):
        """Update a chore type."""
        if not house:
            raise HTTPException(status_code=503, detail="Not initialized")
        updates = {k: v for k, v in data.dict().items() if v is not None}
        ct = house.update_chore_type(type_id, **updates)
        if not ct:
            raise HTTPException(status_code=404, detail="Chore type not found")
        return ct.to_dict()

    # ==================== Rooms ====================

    @app.get("/api/rooms")
    async def get_rooms(zone: str | None = None):
        """Get all rooms."""
        if not house:
            raise HTTPException(status_code=503, detail="Not initialized")
        rooms = house.get_rooms(zone=zone)
        return [r.to_dict() for r in rooms]

    @app.get("/api/rooms/{room_id}")
    async def get_room(room_id: str):
        """Get a specific room with its status."""
        if not house:
            raise HTTPException(status_code=503, detail="Not initialized")
        room = house.get_room(room_id)
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")

        freshness = house.get_room_freshness(room_id)
        chores = house.get_chores_by_room(room_id)

        return {
            **room.to_dict(),
            "freshness": freshness,
            "chore_count": len(chores),
            "due_count": sum(1 for c in chores if c["is_due"]),
            "overdue_count": sum(1 for c in chores if c["is_overdue"]),
        }

    @app.post("/api/rooms")
    async def create_room(data: RoomCreate):
        """Create a new room."""
        if not house:
            raise HTTPException(status_code=503, detail="Not initialized")
        room = Room(
            name=data.name,
            icon=data.icon,
            zone=data.zone,
            color=data.color,
            sort_order=data.sort_order,
        )
        house.add_room(room)
        return room.to_dict()

    @app.patch("/api/rooms/{room_id}")
    async def update_room(room_id: str, data: RoomUpdate):
        """Update a room."""
        if not house:
            raise HTTPException(status_code=503, detail="Not initialized")
        updates = {k: v for k, v in data.dict().items() if v is not None}
        room = house.update_room(room_id, **updates)
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")
        return room.to_dict()

    @app.get("/api/rooms/status")
    async def get_rooms_status():
        """Get status of all rooms (freshness, due chores)."""
        if not house:
            raise HTTPException(status_code=503, detail="Not initialized")
        status = house.get_all_rooms_status()
        return [
            {
                "room": s["room"].to_dict(),
                "freshness": s["freshness"],
                "total_chores": s["total_chores"],
                "due_count": s["due_count"],
                "overdue_count": s["overdue_count"],
            }
            for s in status
        ]

    # ==================== Chore Instances ====================

    @app.get("/api/chores")
    async def get_chores(
        room_id: str | None = None,
        chore_type_id: str | None = None,
        due_only: bool = False,
    ):
        """Get chores, optionally filtered."""
        if not house:
            raise HTTPException(status_code=503, detail="Not initialized")

        if due_only:
            chores = house.get_due_chores()
        elif room_id:
            chores = house.get_chores_by_room(room_id)
        elif chore_type_id:
            chores = house.get_chores_by_type(chore_type_id)
        else:
            # Get all chore instances
            instances = house.get_chore_instances()
            chores = []
            for inst in instances:
                ct = house.get_chore_type(inst.chore_type_id)
                room = house.get_room(inst.room_id)
                if ct and room:
                    chores.append({
                        "instance": inst,
                        "chore_type": ct,
                        "room": room,
                        "is_due": inst.is_due(ct),
                        "is_overdue": inst.is_overdue(ct),
                        "freshness": inst.freshness_percent(ct),
                    })

        return [
            {
                "id": c["instance"].id,
                "chore_type": c["chore_type"].to_dict(),
                "room": c["room"].to_dict(),
                "interval": c["instance"].get_interval(c["chore_type"]),
                "duration": c["instance"].get_duration(c["chore_type"]),
                "last_completed": c["instance"].last_completed.isoformat() if c["instance"].last_completed else None,
                "streak": c["instance"].streak,
                "is_due": c["is_due"],
                "is_overdue": c.get("is_overdue", False),
                "freshness": c["freshness"],
                "urgency": c["instance"].urgency.value,
                "notes": c["instance"].notes,
            }
            for c in chores
        ]

    @app.get("/api/chores/{chore_id}")
    async def get_chore(chore_id: str):
        """Get a specific chore instance."""
        if not house:
            raise HTTPException(status_code=503, detail="Not initialized")

        inst = house.get_chore_instance(chore_id)
        if not inst:
            raise HTTPException(status_code=404, detail="Chore not found")

        ct = house.get_chore_type(inst.chore_type_id)
        room = house.get_room(inst.room_id)
        if not ct or not room:
            raise HTTPException(status_code=404, detail="Related data not found")

        return {
            "id": inst.id,
            "chore_type": ct.to_dict(),
            "room": room.to_dict(),
            "interval": inst.get_interval(ct),
            "duration": inst.get_duration(ct),
            "last_completed": inst.last_completed.isoformat() if inst.last_completed else None,
            "streak": inst.streak,
            "completion_count": inst.completion_count,
            "is_due": inst.is_due(ct),
            "is_overdue": inst.is_overdue(ct),
            "freshness": inst.freshness_percent(ct),
            "days_until_due": inst.days_until_due(ct),
            "urgency": inst.urgency.value,
            "notes": inst.notes,
        }

    @app.post("/api/chores")
    async def create_chore(data: ChoreInstanceCreate):
        """Create a new chore instance (chore + room combination)."""
        if not house:
            raise HTTPException(status_code=503, detail="Not initialized")

        urgency_map = {"critical": Urgency.CRITICAL, "normal": Urgency.NORMAL, "low": Urgency.LOW}

        inst = ChoreInstance(
            chore_type_id=data.chore_type_id,
            room_id=data.room_id,
            interval_days=data.interval_days,
            duration_minutes=data.duration_minutes,
            urgency=urgency_map.get(data.urgency.lower(), Urgency.NORMAL),
        )
        house.add_chore_instance(inst)
        return {"id": inst.id, "status": "created"}

    @app.patch("/api/chores/{chore_id}")
    async def update_chore(chore_id: str, data: ChoreInstanceUpdate):
        """Update a chore instance."""
        if not house:
            raise HTTPException(status_code=503, detail="Not initialized")

        updates = {}
        if data.interval_days is not None:
            updates["interval_days"] = data.interval_days
        if data.duration_minutes is not None:
            updates["duration_minutes"] = data.duration_minutes
        if data.urgency is not None:
            urgency_map = {"critical": Urgency.CRITICAL, "normal": Urgency.NORMAL, "low": Urgency.LOW}
            updates["urgency"] = urgency_map.get(data.urgency.lower(), Urgency.NORMAL)
        if data.enabled is not None:
            updates["enabled"] = data.enabled
        if data.notes is not None:
            updates["notes"] = data.notes

        inst = house.update_chore_instance(chore_id, **updates)
        if not inst:
            raise HTTPException(status_code=404, detail="Chore not found")
        return {"id": inst.id, "status": "updated"}

    @app.post("/api/chores/{chore_id}/done")
    async def complete_chore(chore_id: str):
        """Mark chore as done."""
        if not house:
            raise HTTPException(status_code=503, detail="Not initialized")

        inst = house.complete_chore(chore_id)
        if not inst:
            raise HTTPException(status_code=404, detail="Chore not found")

        ct = house.get_chore_type(inst.chore_type_id)
        return {
            "id": inst.id,
            "streak": inst.streak,
            "completion_count": inst.completion_count,
            "freshness": inst.freshness_percent(ct) if ct else 100,
        }

    @app.post("/api/chores/{chore_id}/skip")
    async def skip_chore(chore_id: str, reason: str = ""):
        """Skip a chore."""
        if not house:
            raise HTTPException(status_code=503, detail="Not initialized")

        inst = house.skip_chore(chore_id, reason)
        if not inst:
            raise HTTPException(status_code=404, detail="Chore not found")
        return {"id": inst.id, "status": "skipped"}

    @app.delete("/api/chores/{chore_id}")
    async def delete_chore(chore_id: str):
        """Delete a chore instance."""
        if not house:
            raise HTTPException(status_code=503, detail="Not initialized")

        if house.delete_chore_instance(chore_id):
            return {"status": "deleted"}
        raise HTTPException(status_code=404, detail="Chore not found")

    @app.get("/api/chores/stats")
    async def chore_stats():
        """Get chore statistics."""
        if not house:
            raise HTTPException(status_code=503, detail="Not initialized")
        return house.get_stats()

    # ==================== Maintenance Tasks ====================

    @app.get("/api/maintenance")
    async def get_maintenance(due_only: bool = False):
        """Get maintenance tasks."""
        if not house:
            raise HTTPException(status_code=503, detail="Not initialized")

        if due_only:
            tasks = house.get_due_maintenance()
        else:
            tasks = house.get_maintenance_tasks()

        return [
            {
                **t.to_dict(),
                "days_until_due": t.days_until_due,
                "is_overdue": t.is_overdue,
            }
            for t in tasks
        ]

    @app.get("/api/maintenance/{task_id}")
    async def get_maintenance_task(task_id: str):
        """Get a specific maintenance task."""
        if not house:
            raise HTTPException(status_code=503, detail="Not initialized")

        task = house.get_maintenance_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        return {
            **task.to_dict(),
            "days_until_due": task.days_until_due,
            "is_overdue": task.is_overdue,
        }

    @app.post("/api/maintenance")
    async def create_maintenance(data: MaintenanceCreate):
        """Create a maintenance task."""
        if not house:
            raise HTTPException(status_code=503, detail="Not initialized")

        task = MaintenanceTask(
            name=data.name,
            description=data.description,
            icon=data.icon,
            interval_days=data.interval_days,
            provider=data.provider,
            estimated_cost=data.estimated_cost,
            notes=data.notes,
        )
        house.add_maintenance_task(task)
        return task.to_dict()

    @app.patch("/api/maintenance/{task_id}")
    async def update_maintenance(task_id: str, data: MaintenanceUpdate):
        """Update a maintenance task."""
        if not house:
            raise HTTPException(status_code=503, detail="Not initialized")

        updates = {k: v for k, v in data.dict().items() if v is not None}
        task = house.update_maintenance_task(task_id, **updates)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return task.to_dict()

    @app.post("/api/maintenance/{task_id}/done")
    async def complete_maintenance(task_id: str):
        """Mark maintenance task as done."""
        if not house:
            raise HTTPException(status_code=503, detail="Not initialized")

        task = house.complete_maintenance_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return task.to_dict()

    @app.delete("/api/maintenance/{task_id}")
    async def delete_maintenance(task_id: str):
        """Delete a maintenance task."""
        if not house:
            raise HTTPException(status_code=503, detail="Not initialized")

        if house.delete_maintenance_task(task_id):
            return {"status": "deleted"}
        raise HTTPException(status_code=404, detail="Task not found")

    # ==================== Home Projects ====================

    @app.get("/api/projects")
    async def get_projects(status: str | None = None):
        """Get home projects."""
        if not house:
            raise HTTPException(status_code=503, detail="Not initialized")

        project_status = None
        if status:
            project_status = ProjectStatus(status)

        projects = house.get_projects(status=project_status)
        return [
            {
                **p.to_dict(),
                "progress_percent": p.progress_percent,
            }
            for p in projects
        ]

    @app.get("/api/projects/{project_id}")
    async def get_project(project_id: str):
        """Get a specific project."""
        if not house:
            raise HTTPException(status_code=503, detail="Not initialized")

        project = house.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        return {
            **project.to_dict(),
            "progress_percent": project.progress_percent,
        }

    @app.post("/api/projects")
    async def create_project(data: ProjectCreate):
        """Create a home project."""
        if not house:
            raise HTTPException(status_code=503, detail="Not initialized")

        target_date = None
        if data.target_date:
            target_date = datetime.fromisoformat(data.target_date)

        project = HomeProject(
            name=data.name,
            description=data.description,
            icon=data.icon,
            budget=data.budget,
            target_date=target_date,
            notes=data.notes,
        )
        house.add_project(project)
        return project.to_dict()

    @app.patch("/api/projects/{project_id}")
    async def update_project(project_id: str, data: ProjectUpdate):
        """Update a project."""
        if not house:
            raise HTTPException(status_code=503, detail="Not initialized")

        updates = {}
        for k, v in data.dict().items():
            if v is not None:
                if k == "status":
                    updates[k] = ProjectStatus(v)
                elif k == "target_date":
                    updates[k] = datetime.fromisoformat(v) if v else None
                else:
                    updates[k] = v

        project = house.update_project(project_id, **updates)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return project.to_dict()

    @app.post("/api/projects/{project_id}/steps")
    async def add_project_step(project_id: str, data: ProjectStepCreate):
        """Add a step to a project."""
        if not house:
            raise HTTPException(status_code=503, detail="Not initialized")

        step = ProjectStep(name=data.name, notes=data.notes)
        project = house.add_project_step(project_id, step)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return project.to_dict()

    @app.post("/api/projects/{project_id}/steps/{step_index}/toggle")
    async def toggle_project_step(project_id: str, step_index: int):
        """Toggle a project step completion."""
        if not house:
            raise HTTPException(status_code=503, detail="Not initialized")

        project = house.toggle_project_step(project_id, step_index)
        if not project:
            raise HTTPException(status_code=404, detail="Project or step not found")
        return project.to_dict()

    @app.delete("/api/projects/{project_id}")
    async def delete_project(project_id: str):
        """Delete a project."""
        if not house:
            raise HTTPException(status_code=503, detail="Not initialized")

        if house.delete_project(project_id):
            return {"status": "deleted"}
        raise HTTPException(status_code=404, detail="Project not found")

    # ==================== Checklists ====================

    @app.get("/api/checklists")
    async def get_checklists():
        """Get all checklists."""
        if not house:
            raise HTTPException(status_code=503, detail="Not initialized")

        checklists = house.get_checklists()
        return [c.to_dict() for c in checklists]

    @app.get("/api/checklists/{checklist_id}")
    async def get_checklist(checklist_id: str):
        """Get a checklist with its chores."""
        if not house:
            raise HTTPException(status_code=503, detail="Not initialized")

        checklist = house.get_checklist(checklist_id)
        if not checklist:
            raise HTTPException(status_code=404, detail="Checklist not found")

        chores = house.get_checklist_chores(checklist_id)

        return {
            **checklist.to_dict(),
            "chores": [
                {
                    "id": c["instance"].id,
                    "chore_name": c["chore_type"].name,
                    "room_name": c["room"].name,
                    "icon": c["chore_type"].icon,
                    "importance": c["importance"].value,
                    "freshness": c["freshness"],
                    "is_due": c["is_due"],
                }
                for c in chores
            ],
        }

    @app.post("/api/checklists")
    async def create_checklist(data: ChecklistCreate):
        """Create a checklist."""
        if not house:
            raise HTTPException(status_code=503, detail="Not initialized")

        checklist = Checklist(
            name=data.name,
            description=data.description,
            icon=data.icon,
            color=data.color,
        )
        house.add_checklist(checklist)
        return checklist.to_dict()

    @app.post("/api/checklists/{checklist_id}/items")
    async def add_checklist_item(checklist_id: str, data: ChecklistItemCreate):
        """Add an item to a checklist."""
        if not house:
            raise HTTPException(status_code=503, detail="Not initialized")

        checklist = house.get_checklist(checklist_id)
        if not checklist:
            raise HTTPException(status_code=404, detail="Checklist not found")

        importance_map = {
            "must": ChecklistItemImportance.MUST,
            "nice": ChecklistItemImportance.NICE,
            "optional": ChecklistItemImportance.OPTIONAL,
        }

        item = ChecklistItem(
            chore_instance_id=data.chore_instance_id,
            importance=importance_map.get(data.importance.lower(), ChecklistItemImportance.MUST),
        )
        checklist.items.append(item)
        house.update_checklist(checklist_id, items=checklist.items)

        return checklist.to_dict()

    @app.delete("/api/checklists/{checklist_id}")
    async def delete_checklist(checklist_id: str):
        """Delete a checklist."""
        if not house:
            raise HTTPException(status_code=503, detail="Not initialized")

        if house.delete_checklist(checklist_id):
            return {"status": "deleted"}
        raise HTTPException(status_code=404, detail="Checklist not found")

    # ==================== What Now? ====================

    @app.post("/api/whatnow")
    async def what_now(time: TimeAvailable):
        """Get recommendations for available time."""
        if not aether or not house:
            raise HTTPException(status_code=503, detail="Not initialized")

        # Get fitting chores
        fitting = house.get_chores_for_time(time.minutes)

        # Get tasks from Aether too
        recommendations = aether.next(10)
        tasks = []
        for task, score, reasoning in recommendations:
            if task.estimated_minutes and task.estimated_minutes <= time.minutes:
                tasks.append({
                    "task": task.to_dict(),
                    "score": score,
                })
            elif not task.estimated_minutes:
                tasks.append({
                    "task": task.to_dict(),
                    "score": score,
                    "note": "Duration unknown",
                })

        # Generate suggestion
        if time.minutes < 15:
            suggestion = "Quick wins - pick a fast chore or small task"
        elif time.minutes < 30:
            suggestion = "Good for a single room or focused task"
        elif time.minutes < 60:
            suggestion = "Solid cleaning session or tackle a project"
        else:
            suggestion = "Deep clean time - tackle a whole zone"

        return {
            "available_minutes": time.minutes,
            "chores": [
                {
                    "id": c["instance"].id,
                    "name": f"{c['chore_type'].name} - {c['room'].name}",
                    "icon": c["chore_type"].icon,
                    "duration": c["duration"],
                    "urgency": c["urgency_score"],
                }
                for c in fitting[:5]
            ],
            "tasks": tasks[:5],
            "suggestion": suggestion,
        }

    # ==================== Tasks (from Aether core) ====================

    @app.get("/api/tasks")
    async def get_tasks(
        status: str | None = None,
        area: str | None = None,
        limit: int = 50,
    ):
        """Get tasks."""
        if not aether:
            raise HTTPException(status_code=503, detail="Not initialized")

        task_status = None
        if status:
            task_status = TaskStatus(status)

        tasks = aether.tasks.list(status=task_status, area=area)[:limit]
        return [t.to_dict() for t in tasks]

    @app.post("/api/tasks")
    async def create_task(task: TaskCreate):
        """Quick add a task."""
        if not aether:
            raise HTTPException(status_code=503, detail="Not initialized")

        new_task = aether.add(task.text)
        return new_task.to_dict()

    @app.post("/api/tasks/{task_id}/done")
    async def complete_task(task_id: str, actual_minutes: int | None = None):
        """Mark task as done."""
        if not aether:
            raise HTTPException(status_code=503, detail="Not initialized")

        task = aether.done(task_id, actual_minutes)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return task.to_dict()

    # ==================== Context/Energy ====================

    @app.get("/api/context")
    async def get_context():
        """Get current context."""
        if not aether:
            raise HTTPException(status_code=503, detail="Not initialized")

        ctx = aether.context.get_current()
        return ctx.to_dict()

    @app.post("/api/energy")
    async def set_energy(update: EnergyUpdate):
        """Set energy level."""
        if not aether:
            raise HTTPException(status_code=503, detail="Not initialized")

        ctx = aether.energy(update.level, update.note)
        return ctx.to_dict()

    # ==================== Home Assistant webhook ====================

    @app.post("/api/ha/webhook")
    async def ha_webhook(data: dict[str, Any]):
        """Receive webhooks from Home Assistant."""
        event_type = data.get("event_type")
        event_data = data.get("event_data", {})

        if event_type == "time_available":
            minutes = event_data.get("minutes", 0)
            return await what_now(TimeAvailable(minutes=minutes))

        return {"status": "ok"}

    return app


# Run server directly
if __name__ == "__main__":
    import uvicorn

    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8080)
