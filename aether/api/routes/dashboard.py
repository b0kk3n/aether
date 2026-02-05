"""Dashboard API routes."""

from fastapi import APIRouter, Query

from aether.core import (
    Dashboard,
    Briefing,
    QuickCleanList,
    Prioritizer,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=Dashboard)
def get_dashboard():
    """Get the home dashboard overview.

    Shows all rooms with freshness scores, house-wide chores,
    and summary statistics.
    """
    return Prioritizer.get_dashboard()


@router.get("/briefing", response_model=Briefing)
def get_briefing():
    """Get the morning briefing.

    Returns ~15 minutes of suggested high-priority tasks
    with a friendly greeting.
    """
    return Prioritizer.get_morning_briefing()


@router.get("/quick-clean", response_model=QuickCleanList)
def get_quick_clean(minutes: int = Query(30, ge=5, le=180)):
    """Get prioritized chores for available time.

    The "I have X minutes" feature. Returns highest-impact chores
    that fit within your time budget.
    """
    return Prioritizer.get_quick_clean(minutes)
