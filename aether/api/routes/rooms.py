"""Room API routes."""

from typing import Optional
from fastapi import APIRouter, HTTPException

from aether.core import (
    Room,
    RoomCreate,
    RoomWithFreshness,
    ChoreStatus,
    RoomService,
    ChoreService,
)

router = APIRouter(prefix="/rooms", tags=["rooms"])


@router.get("", response_model=list[RoomWithFreshness])
def list_rooms():
    """Get all rooms with freshness scores."""
    return RoomService.get_all_with_freshness()


@router.get("/{room_id}", response_model=RoomWithFreshness)
def get_room(room_id: str):
    """Get a room by ID with freshness score."""
    rooms = RoomService.get_all_with_freshness()
    for room in rooms:
        if room.id == room_id:
            return room
    raise HTTPException(status_code=404, detail="Room not found")


@router.get("/{room_id}/chores", response_model=list[ChoreStatus])
def get_room_chores(room_id: str):
    """Get all chores for a room with status."""
    room = RoomService.get_by_id(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return ChoreService.get_for_room(room_id)


@router.post("", response_model=Room, status_code=201)
def create_room(room: RoomCreate):
    """Create a new room."""
    return RoomService.create(room)


@router.put("/{room_id}", response_model=Room)
def update_room(
    room_id: str,
    name: Optional[str] = None,
    icon: Optional[str] = None,
    sort_order: Optional[int] = None,
):
    """Update a room."""
    room = RoomService.update(room_id, name=name, icon=icon, sort_order=sort_order)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return room


@router.post("/reorder", response_model=list[Room])
def reorder_rooms(room_ids: list[str]):
    """Reorder rooms by providing list of IDs in desired order."""
    return RoomService.reorder(room_ids)


@router.delete("/{room_id}", status_code=204)
def delete_room(room_id: str):
    """Delete a room. Associated chores will become house-wide."""
    success, error = RoomService.delete(room_id)
    if not success:
        if error:
            raise HTTPException(status_code=409, detail=error)
        raise HTTPException(status_code=404, detail="Room not found")


@router.post("/{room_id}/pause", response_model=RoomWithFreshness)
def pause_room(room_id: str):
    """Pause a room (e.g. mid-remodel), freezing all of its chores."""
    try:
        room = RoomService.pause(room_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return get_room(room_id)


@router.post("/{room_id}/unpause", response_model=RoomWithFreshness)
def unpause_room(room_id: str):
    """Unpause a room, shifting its chores' due dates forward by the pause length."""
    try:
        room = RoomService.unpause(room_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return get_room(room_id)
