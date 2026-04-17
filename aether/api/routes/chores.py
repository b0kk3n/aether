"""Chore API routes."""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from aether.core import (
    Chore,
    ChoreCreate,
    ChoreUpdate,
    ChoreStatus,
    ChoreWithRoom,
    CompletionLog,
    Category,
    ChoreService,
)

router = APIRouter(prefix="/chores", tags=["chores"])


class CompleteRequest(BaseModel):
    """Request body for completing a chore."""
    actual_minutes: Optional[int] = None
    notes: str = ""
    duration_was_accurate: Optional[bool] = None


class DurationFeedbackRequest(BaseModel):
    """Request body for duration feedback."""
    accurate: bool
    actual_minutes: Optional[int] = None


class IntervalFeedbackRequest(BaseModel):
    """Request body for interval feedback."""
    accurate: bool
    actual_days: Optional[int] = None


class CompleteResponse(BaseModel):
    """Response for chore completion."""
    chore: Chore
    ask_about_duration: bool
    ask_about_interval: bool
    message: str


@router.get("", response_model=list[ChoreWithRoom])
def list_chores(
    room_id: Optional[str] = Query(None, description="Filter by room ID"),
    category: Optional[Category] = Query(None, description="Filter by category"),
    active_only: bool = Query(True, description="Only show active chores"),
):
    """Get all chores with optional filters."""
    if room_id or category:
        chores = ChoreService.get_all(
            room_id=room_id,
            category=category,
            active_only=active_only,
        )
        # Convert to ChoreWithRoom (basic version without room details)
        return [ChoreWithRoom(**c.model_dump(), room=None) for c in chores]
    return ChoreService.get_all_with_room()


@router.get("/overdue", response_model=list[ChoreStatus])
def get_overdue_chores():
    """Get all overdue chores."""
    return ChoreService.get_overdue()


@router.get("/due-soon", response_model=list[ChoreStatus])
def get_due_soon(days: int = Query(3, ge=1, le=14)):
    """Get chores due within specified days."""
    return ChoreService.get_due_soon(days=days)


@router.get("/house-wide", response_model=list[ChoreStatus])
def get_house_wide_chores():
    """Get all house-wide chores (not assigned to a room)."""
    return ChoreService.get_house_wide()


@router.get("/category/{category}", response_model=list[ChoreStatus])
def get_chores_by_category(category: Category):
    """Get all chores of a specific category."""
    from aether.core import Prioritizer
    return Prioritizer.get_by_category(category)


@router.get("/{chore_id}", response_model=Chore)
def get_chore(chore_id: str):
    """Get a chore by ID."""
    chore = ChoreService.get_by_id(chore_id)
    if not chore:
        raise HTTPException(status_code=404, detail="Chore not found")
    return chore


@router.get("/{chore_id}/history", response_model=list[CompletionLog])
def get_chore_history(chore_id: str, limit: int = Query(10, ge=1, le=100)):
    """Get completion history for a chore."""
    chore = ChoreService.get_by_id(chore_id)
    if not chore:
        raise HTTPException(status_code=404, detail="Chore not found")
    return ChoreService.get_completion_history(chore_id, limit=limit)


@router.post("", response_model=Chore, status_code=201)
def create_chore(chore: ChoreCreate):
    """Create a new chore."""
    return ChoreService.create(chore)


@router.put("/{chore_id}", response_model=Chore)
def update_chore(chore_id: str, update: ChoreUpdate):
    """Update a chore."""
    chore = ChoreService.update(chore_id, update)
    if not chore:
        raise HTTPException(status_code=404, detail="Chore not found")
    return chore


@router.post("/{chore_id}/complete", response_model=CompleteResponse)
def complete_chore(chore_id: str, request: CompleteRequest = CompleteRequest()):
    """Mark a chore as complete.

    Optionally provide actual duration and feedback on estimate accuracy.
    If duration feedback is given twice as accurate, the estimate is confirmed.
    """
    from datetime import datetime

    chore = ChoreService.get_by_id(chore_id)
    if not chore:
        raise HTTPException(status_code=404, detail="Chore not found")

    # Check if we should ask about duration/interval before completing
    ask_about_duration = ChoreService.should_ask_duration(chore_id)
    ask_about_interval = ChoreService.should_ask_interval(chore_id)

    # Calculate interval deviation BEFORE completing
    ask_about_interval = False
    suggested_interval = None
    interval_context = None

    if chore.last_completed_at:
        days_since = (datetime.now() - chore.last_completed_at).days
        deviation = days_since - chore.interval_days

        # Only ask if deviation is significant:
        # - More than 2 days off (not just minor life variance)
        # - More than 25% of the interval (proportionally significant)
        min_deviation = max(3, int(chore.interval_days * 0.25))

        if abs(deviation) >= min_deviation:
            ask_about_interval = True
            suggested_interval = days_since

            if deviation < 0:
                interval_context = f"{abs(deviation)} days early"
            else:
                interval_context = f"{deviation} days late"

    # Complete the chore
    updated_chore = ChoreService.complete(
        chore_id,
        actual_minutes=request.actual_minutes,
        notes=request.notes,
        duration_was_accurate=request.duration_was_accurate,
    )

    # Generate response message
    if updated_chore.streak > 1:
        message = f"Done! {updated_chore.streak} in a row"
    else:
        message = "Done!"

    return CompleteResponse(
        chore=updated_chore,
        ask_about_duration=ask_about_duration and request.duration_was_accurate is None,
        ask_about_interval=ask_about_interval,
        message=message,
    )


@router.post("/{chore_id}/interval-feedback", status_code=204)
def record_interval_feedback(chore_id: str, request: IntervalFeedbackRequest):
    """Record user feedback on whether the interval schedule was accurate."""
    chore = ChoreService.get_by_id(chore_id)
    if not chore:
        raise HTTPException(status_code=404, detail="Chore not found")
    ChoreService.record_interval_feedback(chore_id, request.accurate, request.actual_days)


@router.post("/{chore_id}/duration-feedback", status_code=204)
def record_duration_feedback(chore_id: str, request: DurationFeedbackRequest):
    """Record user feedback on whether the duration estimate was accurate."""
    chore = ChoreService.get_by_id(chore_id)
    if not chore:
        raise HTTPException(status_code=404, detail="Chore not found")
    ChoreService.record_duration_feedback(chore_id, request.accurate, request.actual_minutes)


@router.delete("/{chore_id}", status_code=204)
def delete_chore(chore_id: str):
    """Delete a chore and its history."""
    if not ChoreService.delete(chore_id):
        raise HTTPException(status_code=404, detail="Chore not found")
