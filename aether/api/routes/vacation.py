"""Vacation mode API routes."""

from fastapi import APIRouter, HTTPException

from aether.core import (
    ChoreEligibility,
    VacationEndResult,
    VacationService,
    VacationStatus,
)

router = APIRouter(prefix="/vacation", tags=["vacation"])


@router.get("", response_model=VacationStatus)
def get_vacation_status():
    """Get current vacation mode status."""
    return VacationService.get_status()


@router.post("/start", response_model=VacationStatus, status_code=201)
def start_vacation():
    """Start vacation mode, pausing eligible chores' countdowns."""
    try:
        return VacationService.start()
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/end", response_model=VacationEndResult)
def end_vacation():
    """End vacation mode, shifting eligible chores' due dates forward."""
    try:
        return VacationService.end()
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/eligibility", response_model=list[ChoreEligibility])
def get_vacation_eligibility():
    """Preview which active chores would pause if vacation started now."""
    return VacationService.get_eligible_preview()
