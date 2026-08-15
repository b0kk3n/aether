"""Vacation mode API routes."""

from fastapi import APIRouter, HTTPException, Query

from pantry.core import (
    ProductEligibility,
    VacationEndResult,
    VacationLogEntry,
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
    """Start vacation mode, freezing every product's interval clock."""
    try:
        return VacationService.start()
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/end", response_model=VacationEndResult)
def end_vacation():
    """End vacation mode, shifting every eligible product's next_due forward."""
    try:
        return VacationService.end()
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/eligibility", response_model=list[ProductEligibility])
def get_vacation_eligibility():
    """Preview which products would pause if vacation started now."""
    return VacationService.get_eligible_preview()


@router.get("/history", response_model=list[VacationLogEntry])
def get_vacation_history(limit: int = Query(20, ge=1, le=100)):
    """Past vacations, most recent first."""
    return VacationService.get_history(limit=limit)
