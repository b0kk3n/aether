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
        # Check if room already exists
        existing = RoomService.get_by_name(room_data["name"])
        if existing:
            room_ids[existing.name] = existing.id
            print(f"  Room exists: {room_data['icon']} {existing.name}")
        else:
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
        created = 0
        existed = 0
        for name, interval, minutes, category in chores:
            existing = ChoreService.get_by_name_and_room(name, room_id)
            if existing:
                chore_ids[(room_name, name)] = existing.id
                existed += 1
            else:
                chore = ChoreService.create(ChoreCreate(
                    name=name,
                    room_id=room_id,
                    interval_days=interval,
                    estimated_minutes=minutes,
                    category=category,
                ))
                chore_ids[(room_name, name)] = chore.id
                created += 1
        if existed:
            print(f"  {room_name}: {created} created, {existed} already existed")
        else:
            print(f"  Created {len(chores)} chores for {room_name}")

    # House-wide chores
    created = 0
    for name, interval, minutes, category in HOUSE_WIDE_CHORES:
        existing = ChoreService.get_by_name_and_room(name, None)
        if existing:
            chore_ids[(None, name)] = existing.id
        else:
            chore = ChoreService.create(ChoreCreate(
                name=name,
                room_id=None,
                interval_days=interval,
                estimated_minutes=minutes,
                category=category,
            ))
            chore_ids[(None, name)] = chore.id
            created += 1
    print(f"  Created {created} house-wide chores ({len(HOUSE_WIDE_CHORES) - created} existed)")

    # Maintenance chores
    created = 0
    for name, interval, minutes, category in MAINTENANCE_CHORES:
        existing = ChoreService.get_by_name_and_room(name, None)
        if existing:
            chore_ids[(None, name)] = existing.id
        else:
            chore = ChoreService.create(ChoreCreate(
                name=name,
                room_id=None,
                interval_days=interval,
                estimated_minutes=minutes,
                category=category,
            ))
            chore_ids[(None, name)] = chore.id
            created += 1
    print(f"  Created {created} maintenance chores ({len(MAINTENANCE_CHORES) - created} existed)")

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
