"""API routes for Aether."""

from .rooms import router as rooms_router
from .chores import router as chores_router
from .checklists import router as checklists_router
from .dashboard import router as dashboard_router

__all__ = ["rooms_router", "chores_router", "checklists_router", "dashboard_router"]
