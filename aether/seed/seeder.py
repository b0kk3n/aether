"""Database seeder for Aether.

Populates the database with initial rooms, chores, and checklists.
"""

from aether.core.database import init_db, reset_db, get_db
from aether.core.models import RoomCreate, ChoreCreate, ChecklistCreate, Category
from aether.core.services.room_service import RoomService
from aether.core.services.chore_service import ChoreService
from aether.core.services.checklist_service import ChecklistService
from aether.seed.data import ROOMS, CHORES_BY_ROOM, HOUSE_WIDE_CHORES, MAINTENANCE_CHORES, CHECKLISTS


def seed_rooms() -> dict[str, str]:
    """Seed all rooms and return mapping of name -> id."""
    room_ids = {}
    for room_data in ROOMS:
        room = RoomService.create(RoomCreate(**room_data))
        room_ids[room.name] = room.id
        print(f"  Created room: {room.icon} {room.name}")
    return room_ids


def seed_chores(room_ids: dict[str, str]) -> dict[tuple[str, str], str]:
    """Seed all chores and return mapping of (room_name, chore_name) -> id."""
    chore_ids = {}

    # Room-specific chores
    for room_name, chores in CHORES_BY_ROOM.items():
        room_id = room_ids.get(room_name)
        for chore_data in chores:
            name, interval, minutes, category = chore_data[:4]
            notes = chore_data[4] if len(chore_data) > 4 else ""
            chore = ChoreService.create(ChoreCreate(
                name=name,
                room_id=room_id,
                interval_days=interval,
                estimated_minutes=minutes,
                category=category,
                notes=notes,
            ))
            chore_ids[(room_name, name)] = chore.id
        print(f"  Created {len(chores)} chores for {room_name}")

    # House-wide chores
    for chore_data in HOUSE_WIDE_CHORES:
        name, interval, minutes, category = chore_data[:4]
        notes = chore_data[4] if len(chore_data) > 4 else ""
        chore = ChoreService.create(ChoreCreate(
            name=name,
            room_id=None,
            interval_days=interval,
            estimated_minutes=minutes,
            category=category,
            notes=notes,
        ))
        chore_ids[(None, name)] = chore.id
    print(f"  Created {len(HOUSE_WIDE_CHORES)} house-wide chores")

    # Maintenance chores
    for chore_data in MAINTENANCE_CHORES:
        name, interval, minutes, category = chore_data[:4]
        notes = chore_data[4] if len(chore_data) > 4 else ""
        chore = ChoreService.create(ChoreCreate(
            name=name,
            room_id=None,
            interval_days=interval,
            estimated_minutes=minutes,
            category=category,
            notes=notes,
        ))
        chore_ids[(None, name)] = chore.id
    print(f"  Created {len(MAINTENANCE_CHORES)} maintenance chores")

    return chore_ids


def seed_checklists(room_ids: dict[str, str], chore_ids: dict[tuple[str, str], str]):
    """Seed all checklists."""
    for checklist_data in CHECKLISTS:
        # Resolve chore references to IDs
        resolved_chore_ids = []
        for room_name, chore_name in checklist_data["chores"]:
            key = (room_name, chore_name)
            if key in chore_ids:
                resolved_chore_ids.append(chore_ids[key])
            else:
                print(f"  Warning: Chore not found: {chore_name} in {room_name}")

        checklist = ChecklistService.create(ChecklistCreate(
            name=checklist_data["name"],
            description=checklist_data["description"],
            icon=checklist_data["icon"],
            chore_ids=resolved_chore_ids,
        ))
        print(f"  Created checklist: {checklist.icon} {checklist.name} ({len(resolved_chore_ids)} chores)")


def seed_database(reset: bool = False):
    """Seed the database with initial data.

    Args:
        reset: If True, drop all tables and recreate. WARNING: Deletes all data!
    """
    if reset:
        print("Resetting database...")
        reset_db()
    else:
        print("Initializing database...")
        init_db()

    print("\nSeeding rooms...")
    room_ids = seed_rooms()

    print("\nSeeding chores...")
    chore_ids = seed_chores(room_ids)

    print("\nSeeding checklists...")
    seed_checklists(room_ids, chore_ids)

    # Print summary
    print("\n" + "=" * 50)
    print("Seeding complete!")
    print(f"  Rooms: {len(room_ids)}")
    print(f"  Chores: {len(chore_ids)}")
    print(f"  Checklists: {len(CHECKLISTS)}")


if __name__ == "__main__":
    import sys
    reset = "--reset" in sys.argv
    seed_database(reset=reset)
