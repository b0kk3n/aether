"""Checklist API routes."""

from fastapi import APIRouter, HTTPException

from aether.core import (
    Checklist,
    ChecklistCreate,
    ChecklistUpdate,
    ChecklistWithChores,
    ChecklistService,
)

router = APIRouter(prefix="/checklists", tags=["checklists"])


@router.get("", response_model=list[Checklist])
def list_checklists():
    """Get all checklists."""
    return ChecklistService.get_all()


@router.get("/{checklist_id}", response_model=ChecklistWithChores)
def get_checklist(checklist_id: str):
    """Get a checklist with live chore status.

    This shows the actual current status of each chore in the checklist,
    including whether they are overdue, their freshness, etc.
    """
    checklist = ChecklistService.get_with_chores(checklist_id)
    if not checklist:
        raise HTTPException(status_code=404, detail="Checklist not found")
    return checklist


@router.post("", response_model=Checklist, status_code=201)
def create_checklist(checklist: ChecklistCreate):
    """Create a new checklist."""
    return ChecklistService.create(checklist)


@router.put("/{checklist_id}", response_model=Checklist)
def update_checklist(checklist_id: str, update: ChecklistUpdate):
    """Update a checklist."""
    checklist = ChecklistService.update(checklist_id, update)
    if not checklist:
        raise HTTPException(status_code=404, detail="Checklist not found")
    return checklist


@router.post("/{checklist_id}/chores/{chore_id}", status_code=204)
def add_chore_to_checklist(checklist_id: str, chore_id: str):
    """Add a chore to a checklist."""
    checklist = ChecklistService.get_by_id(checklist_id)
    if not checklist:
        raise HTTPException(status_code=404, detail="Checklist not found")

    if not ChecklistService.add_chore(checklist_id, chore_id):
        raise HTTPException(status_code=400, detail="Could not add chore to checklist")


@router.delete("/{checklist_id}/chores/{chore_id}", status_code=204)
def remove_chore_from_checklist(checklist_id: str, chore_id: str):
    """Remove a chore from a checklist."""
    if not ChecklistService.remove_chore(checklist_id, chore_id):
        raise HTTPException(status_code=404, detail="Chore not found in checklist")


@router.delete("/{checklist_id}", status_code=204)
def delete_checklist(checklist_id: str):
    """Delete a checklist."""
    if not ChecklistService.delete(checklist_id):
        raise HTTPException(status_code=404, detail="Checklist not found")
