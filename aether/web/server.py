"""FastAPI web server for Aether."""

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
from ..chores import ChoreManager


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


class ChoreCreate(BaseModel):
    name: str
    interval_days: int = 7
    duration_minutes: int = 15
    room: str | None = None


class VoiceCommand(BaseModel):
    text: str


# Global instances (initialized on startup)
aether: Aether | None = None
chores: ChoreManager | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize on startup, cleanup on shutdown."""
    global aether, chores
    aether = Aether()
    chores = ChoreManager(aether.store)
    yield
    # Cleanup if needed


def create_app() -> FastAPI:
    """Create FastAPI application."""
    app = FastAPI(
        title="Aether",
        description="Personal command center",
        version="0.2.0",
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
            "description": "Personal command center",
            "start_url": "/",
            "display": "standalone",
            "background_color": "#000000",
            "theme_color": "#1a1a2e",
            "icons": [
                {"src": "/static/icon-192.png", "sizes": "192x192", "type": "image/png"},
                {"src": "/static/icon-512.png", "sizes": "512x512", "type": "image/png"},
            ],
        }

    # API Routes

    @app.get("/api/status")
    async def get_status():
        """Get quick status."""
        if not aether:
            raise HTTPException(status_code=503, detail="Not initialized")
        return aether.status()

    @app.get("/api/briefing")
    async def get_briefing():
        """Get morning briefing."""
        if not aether:
            raise HTTPException(status_code=503, detail="Not initialized")
        return aether.morning()

    @app.get("/api/briefing/weekly")
    async def get_weekly():
        """Get weekly review."""
        if not aether:
            raise HTTPException(status_code=503, detail="Not initialized")
        return aether.weekly()

    # Tasks

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

    @app.get("/api/tasks/next")
    async def get_next_tasks(count: int = 5):
        """Get recommended next tasks."""
        if not aether:
            raise HTTPException(status_code=503, detail="Not initialized")

        recommendations = aether.next(count)
        return [
            {
                "task": task.to_dict(),
                "score": score,
                "reasoning": reasoning,
            }
            for task, score, reasoning in recommendations
        ]

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

    @app.post("/api/tasks/{task_id}/start")
    async def start_task(task_id: str):
        """Start working on task."""
        if not aether:
            raise HTTPException(status_code=503, detail="Not initialized")

        task = aether.start(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return task.to_dict()

    @app.get("/api/tasks/overdue")
    async def get_overdue():
        """Get overdue tasks."""
        if not aether:
            raise HTTPException(status_code=503, detail="Not initialized")

        tasks = aether.overdue()
        return [t.to_dict() for t in tasks]

    @app.get("/api/tasks/quick")
    async def get_quick_wins(count: int = 5):
        """Get quick win tasks."""
        if not aether:
            raise HTTPException(status_code=503, detail="Not initialized")

        tasks = aether.quick_wins(count)
        return [t.to_dict() for t in tasks]

    # Context/Energy

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

    @app.post("/api/break")
    async def take_break():
        """Record a break."""
        if not aether:
            raise HTTPException(status_code=503, detail="Not initialized")

        ctx = aether.take_break()
        return ctx.to_dict()

    # What Now? - Time-based recommendations

    @app.post("/api/whatnow")
    async def what_now(time: TimeAvailable):
        """Get recommendations for available time."""
        if not aether or not chores:
            raise HTTPException(status_code=503, detail="Not initialized")

        result = {
            "available_minutes": time.minutes,
            "tasks": [],
            "chores": [],
            "suggestion": "",
        }

        # Get recommended tasks
        recommendations = aether.next(10)
        for task, score, reasoning in recommendations:
            if task.estimated_minutes and task.estimated_minutes <= time.minutes:
                result["tasks"].append({
                    "task": task.to_dict(),
                    "score": score,
                })
            elif not task.estimated_minutes:
                # Unknown duration, include with note
                result["tasks"].append({
                    "task": task.to_dict(),
                    "score": score,
                    "note": "Duration unknown",
                })

        # Get fitting chores
        fitting_chores = chores.get_for_time(time.minutes)
        result["chores"] = [c.to_dict() for c in fitting_chores[:5]]

        # Generate suggestion
        if time.minutes < 15:
            result["suggestion"] = "Quick wins only - pick something fast"
        elif time.minutes < 30:
            result["suggestion"] = "Good for a small task or chore"
        elif time.minutes < 60:
            result["suggestion"] = "Solid work block - tackle something meaningful"
        else:
            result["suggestion"] = "Deep work time available"

        return result

    # Chores

    @app.get("/api/chores")
    async def get_chores(due_only: bool = False):
        """Get chores."""
        if not chores:
            raise HTTPException(status_code=503, detail="Not initialized")

        if due_only:
            chore_list = chores.get_due()
        else:
            chore_list = chores.list()

        return [c.to_dict() for c in chore_list]

    @app.post("/api/chores")
    async def create_chore(chore: ChoreCreate):
        """Create a new chore."""
        if not chores:
            raise HTTPException(status_code=503, detail="Not initialized")

        from ..chores import Chore

        new_chore = Chore(
            name=chore.name,
            interval_days=chore.interval_days,
            duration_minutes=chore.duration_minutes,
            room=chore.room,
        )
        chores.add(new_chore)
        return new_chore.to_dict()

    @app.post("/api/chores/{chore_id}/done")
    async def complete_chore(chore_id: str):
        """Mark chore as done."""
        if not chores:
            raise HTTPException(status_code=503, detail="Not initialized")

        chore = chores.complete(chore_id)
        if not chore:
            raise HTTPException(status_code=404, detail="Chore not found")
        return chore.to_dict()

    @app.get("/api/chores/stats")
    async def chore_stats():
        """Get chore statistics."""
        if not chores:
            raise HTTPException(status_code=503, detail="Not initialized")

        return chores.get_stats()

    @app.get("/api/chores/rooms")
    async def room_status():
        """Get cleaning status by room."""
        if not chores:
            raise HTTPException(status_code=503, detail="Not initialized")

        return chores.get_room_status()

    # Reminders

    @app.get("/api/reminders")
    async def get_reminders():
        """Get upcoming reminders."""
        if not aether:
            raise HTTPException(status_code=503, detail="Not initialized")

        reminders = aether.reminders.get_upcoming(hours=24)
        return [r.to_dict() for r in reminders]

    @app.get("/api/reminders/due")
    async def get_due_reminders():
        """Get reminders due now."""
        if not aether:
            raise HTTPException(status_code=503, detail="Not initialized")

        ctx = aether.context.get_current()
        reminders = aether.reminders.get_due(ctx)
        return [r.to_dict() for r in reminders]

    @app.post("/api/reminders/{reminder_id}/snooze")
    async def snooze_reminder(reminder_id: str, minutes: int = 15):
        """Snooze a reminder."""
        if not aether:
            raise HTTPException(status_code=503, detail="Not initialized")

        reminder = aether.snooze(reminder_id, minutes)
        if not reminder:
            raise HTTPException(status_code=404, detail="Reminder not found")
        return reminder.to_dict()

    @app.post("/api/reminders/{reminder_id}/ack")
    async def ack_reminder(reminder_id: str):
        """Acknowledge reminder."""
        if not aether:
            raise HTTPException(status_code=503, detail="Not initialized")

        reminder = aether.ack(reminder_id)
        if not reminder:
            raise HTTPException(status_code=404, detail="Reminder not found")
        return reminder.to_dict()

    # Voice

    @app.post("/api/voice")
    async def process_voice(file: UploadFile = File(...)):
        """Process voice input."""
        if not aether:
            raise HTTPException(status_code=503, detail="Not initialized")

        # Save temp file and transcribe
        # For now, return placeholder - full Whisper integration would go here
        return {
            "status": "received",
            "message": "Voice processing not yet implemented. Use text input.",
        }

    @app.post("/api/voice/text")
    async def process_voice_text(command: VoiceCommand):
        """Process voice command as text (transcribed externally)."""
        if not aether:
            raise HTTPException(status_code=503, detail="Not initialized")

        text = command.text.lower().strip()

        # Simple command parsing
        if text.startswith("add "):
            task = aether.add(text[4:])
            return {"action": "task_added", "task": task.to_dict()}

        elif "what" in text and ("do" in text or "should" in text):
            recommendations = aether.next(3)
            return {
                "action": "recommendations",
                "tasks": [
                    {"title": t.title, "id": t.id}
                    for t, _, _ in recommendations
                ],
            }

        elif "done" in text or "finished" in text or "completed" in text:
            # Try to find what they completed
            return {
                "action": "need_task_id",
                "message": "Which task did you complete?",
            }

        elif "briefing" in text or "morning" in text:
            briefing = aether.morning()
            return {"action": "briefing", "data": briefing}

        else:
            # Treat as task addition by default
            task = aether.add(text)
            return {"action": "task_added", "task": task.to_dict()}

    # Analytics

    @app.get("/api/stats")
    async def get_stats():
        """Get overall statistics."""
        if not aether:
            raise HTTPException(status_code=503, detail="Not initialized")

        return aether.stats()

    @app.get("/api/workload")
    async def get_workload():
        """Get workload analysis."""
        if not aether:
            raise HTTPException(status_code=503, detail="Not initialized")

        return aether.workload()

    @app.get("/api/productivity")
    async def get_productivity():
        """Get productivity score."""
        if not aether:
            raise HTTPException(status_code=503, detail="Not initialized")

        return aether.productivity()

    # Home Assistant webhook endpoint

    @app.post("/api/ha/webhook")
    async def ha_webhook(data: dict[str, Any]):
        """Receive webhooks from Home Assistant."""
        # Process HA events
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
