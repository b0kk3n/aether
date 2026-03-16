"""Initial seed data for Aether.

Contains:
- 10 rooms
- chores (room-specific + house-wide + maintenance)
- 2 checklists (Visitors, Sleepover)

Duration estimates are initial guesses - users can adjust via the
duration confirmation flow when completing chores.

Chore tuple format: (name, interval_days, estimated_minutes, category[, notes])
The notes field is optional.
"""

from aether.core.models import Category

# =============================================================================
# Rooms
# =============================================================================

ROOMS = [
    {"name": "Entry", "icon": "🚪", "sort_order": 0},
    {"name": "Hallway", "icon": "🚶", "sort_order": 1},
    {"name": "Living room", "icon": "🛋️", "sort_order": 2},
    {"name": "Office & Dining room", "icon": "🍽️", "sort_order": 3},
    {"name": "Bedroom", "icon": "🛏️", "sort_order": 4},
    {"name": "Bathroom", "icon": "🚿", "sort_order": 5},
    {"name": "Toilet", "icon": "🚽", "sort_order": 6},
    {"name": "Kitchen", "icon": "🍳", "sort_order": 7},
    {"name": "Storage", "icon": "📦", "sort_order": 8},
    {"name": "Balcony", "icon": "🌿", "sort_order": 9},
]


# =============================================================================
# Chores by Room
# =============================================================================

# Format: (name, interval_days, estimated_minutes, category[, notes])

CHORES_BY_ROOM = {
    "Entry": [
        ("Vacuum entryway", 10, 5, Category.VACUUM),
        ("Mop entryway", 30, 8, Category.MOP, "Do after vacuuming"),
        ("Declutter entryway", 60, 10, Category.DECLUTTER),
    ],
    "Hallway": [
        ("Vacuum hallway", 5, 5, Category.VACUUM),
        ("Mop hallway", 10, 8, Category.MOP, "Do after vacuuming"),
    ],
    "Living room": [
        ("Declutter living room", 5, 10, Category.DECLUTTER),
        ("Vacuum living room", 7, 10, Category.VACUUM),
        ("Dust living room surfaces", 10, 5, Category.DUST),
        ("Mop living room", 30, 15, Category.MOP, "Do after vacuuming"),
        ("Clean living room furniture", 30, 15, Category.CLEAN),
        ("Clean living room surfaces", 30, 15, Category.CLEAN),
        ("Wash living room blankets", 120, 5, Category.WASH),
        ("Wash living room pillow cases", 160, 10, Category.WASH),
        ("Deep clean living room rug", 160, 45, Category.CLEAN),
        ("Wash living room windows", 160, 60, Category.WASH),
        ("Wash living room curtains", 365, 15, Category.WASH),
    ],
    "Office & Dining room": [
        ("Wipe down dining room table", 3, 5, Category.WIPE),
        ("Declutter dining room", 5, 10, Category.DECLUTTER),
        ("Vacuum dining room", 7, 10, Category.VACUUM),
        ("Dust dining room surfaces", 10, 10, Category.DUST),
        ("Mop dining room", 30, 15, Category.MOP, "Do after vacuuming"),
        ("Clean dining room surfaces", 30, 15, Category.CLEAN),
        ("Wash office & dining room windows", 160, 60, Category.WASH),
        ("Wash dining room curtains", 365, 15, Category.WASH),
    ],
    "Bedroom": [
        ("Declutter bedroom", 7, 5, Category.DECLUTTER),
        ("Dust bedroom surfaces", 10, 5, Category.DUST),
        ("Vacuum bedroom", 14, 10, Category.VACUUM),
        ("Change bedsheets", 14, 10, Category.WASH),
        ("Vacuum matras", 28, 15, Category.VACUUM),
        ("Clean bedroom surfaces", 30, 10, Category.CLEAN),
        ("Mop bedroom", 60, 15, Category.MOP, "Do after vacuuming"),
        ("Wash sleeping pillow", 120, 5, Category.WASH),
        ("Wash matras cover", 120, 5, Category.WASH),
        ("Wash bedroom windows", 160, 60, Category.WASH),
        ("Wash bedroom curtains", 365, 15, Category.WASH),
    ],
    "Bathroom": [
        ("Wipe countertops", 5, 5, Category.WIPE),
        ("Vacuum bathroom floor", 7, 5, Category.VACUUM),
        ("Mop bathroom floor", 14, 10, Category.MOP, "Do after vacuuming"),
        ("Clean bathroom sink", 14, 10, Category.CLEAN),
        ("Clean bathroom mirror", 21, 5, Category.CLEAN),
        ("Wash bathroom rug", 21, 2, Category.WASH),
        ("Clean shower", 30, 20, Category.CLEAN),
        ("Clean outside bathroom cabinets", 60, 10, Category.CLEAN),
        ("Disinfect trashcan", 120, 5, Category.CLEAN),
        ("Clean inside bathroom cabinets", 160, 20, Category.CLEAN),
        ("Clean bathroom walls", 160, 30, Category.CLEAN),
        ("Wash bathroom windows", 160, 60, Category.WASH),
    ],
    "Toilet": [
        ("Clean toilet", 7, 10, Category.CLEAN),
        ("Vacuum toilet", 7, 5, Category.VACUUM),
        ("Mop toilet", 14, 8, Category.MOP, "Do after vacuuming"),
        ("Clean air ventilation toilet", 60, 5, Category.CLEAN),
    ],
    "Kitchen": [
        ("Wipe kitchen countertops", 3, 5, Category.WIPE),
        ("Vacuum kitchen floor", 5, 8, Category.VACUUM),
        ("Clean kitchen sink", 7, 5, Category.CLEAN),
        ("Clean stovetop", 7, 5, Category.CLEAN),
        ("Mop kitchen floor", 10, 12, Category.MOP, "Do after vacuuming"),
        ("Descale kettle", 45, 10, Category.CLEAN),
        ("Clean outside kitchen cabinets", 60, 15, Category.CLEAN),
        ("Clean fridge", 60, 20, Category.CLEAN),
        ("Disinfect trashcan", 60, 5, Category.CLEAN),
        ("Clean oven", 90, 30, Category.CLEAN),
        ("Clean freezer", 160, 30, Category.CLEAN),
        ("Clean inside kitchen cabinets", 160, 45, Category.CLEAN),
        ("Wash kitchen windows", 160, 60, Category.WASH),
    ],
    "Storage": [
        ("Vacuum storage", 14, 8, Category.VACUUM),
        ("Dust storage surfaces", 28, 10, Category.DUST),
        ("Mop storage", 42, 10, Category.MOP, "Do after vacuuming"),
        ("Declutter storage", 45, 30, Category.DECLUTTER),
        ("Clean storage surfaces", 60, 15, Category.CLEAN),
        ("Wash storage windows", 160, 60, Category.WASH),
        ("Wash storage curtains", 365, 15, Category.WASH),
    ],
    "Balcony": [
        ("Clean balcony floor", 180, 30, Category.CLEAN),
        ("Clean balcony gutter", 180, 15, Category.CLEAN),
        ("Clean balcony furniture", 180, 20, Category.CLEAN),
    ],
}


# =============================================================================
# House-wide Chores (no specific room)
# =============================================================================

HOUSE_WIDE_CHORES = [
    ("Clean doorhandles", 45, 15, Category.CLEAN),
    ("Clean light switches", 45, 15, Category.CLEAN),
    ("Clean doors", 160, 60, Category.CLEAN),
    ("Clean radiators", 200, 60, Category.CLEAN),
]


# =============================================================================
# Maintenance Tasks (longer intervals, house-wide)
# =============================================================================

MAINTENANCE_CHORES = [
    ("Smoke detector batteries", 365, 15, Category.MAINTAIN),
    ("Oil wooden floors", 365, 120, Category.MAINTAIN),
]


# =============================================================================
# Checklists
# =============================================================================

# Checklists reference chores by name (will be resolved to IDs during seeding)
# Format: list of (room_name or None for house-wide, chore_name)

CHECKLISTS = [
    {
        "name": "Visitors",
        "description": "Quick prep for when visitors are coming over",
        "icon": "👋",
        "chores": [
            # Declutter
            ("Living room", "Declutter living room"),
            ("Office & Dining room", "Declutter dining room"),
            # Dust
            ("Living room", "Dust living room surfaces"),
            ("Office & Dining room", "Dust dining room surfaces"),
            # Vacuum
            ("Living room", "Vacuum living room"),
            ("Office & Dining room", "Vacuum dining room"),
            ("Hallway", "Vacuum hallway"),
            ("Kitchen", "Vacuum kitchen floor"),
            ("Toilet", "Vacuum toilet"),
            # Mop
            ("Toilet", "Mop toilet"),
            ("Hallway", "Mop hallway"),
            ("Kitchen", "Mop kitchen floor"),
            # Clean
            ("Toilet", "Clean toilet"),
            ("Office & Dining room", "Wipe down dining room table"),
            ("Kitchen", "Wipe kitchen countertops"),
            ("Kitchen", "Clean kitchen sink"),
        ],
    },
    {
        "name": "Sleepover",
        "description": "Prep for overnight guests",
        "icon": "🌙",
        "chores": [
            # Bedsheets
            ("Bedroom", "Change bedsheets"),
            # Declutter
            ("Bedroom", "Declutter bedroom"),
            ("Bathroom", "Wipe countertops"),
            # Dust
            ("Living room", "Dust living room surfaces"),
            ("Office & Dining room", "Dust dining room surfaces"),
            ("Bedroom", "Dust bedroom surfaces"),
            # Vacuum
            ("Living room", "Vacuum living room"),
            ("Office & Dining room", "Vacuum dining room"),
            ("Bedroom", "Vacuum bedroom"),
            ("Hallway", "Vacuum hallway"),
            ("Kitchen", "Vacuum kitchen floor"),
            # Clean
            ("Toilet", "Clean toilet"),
            ("Bathroom", "Clean bathroom mirror"),
            ("Office & Dining room", "Wipe down dining room table"),
        ],
    },
]


def get_all_chores():
    """Get all chores as a flat list with room info.

    Returns list of tuples: (room_name or None, chore_name, interval, minutes, category)
    """
    all_chores = []

    # Room-specific chores
    for room_name, chores in CHORES_BY_ROOM.items():
        for chore_data in chores:
            all_chores.append((room_name, *chore_data))

    # House-wide chores
    for chore_data in HOUSE_WIDE_CHORES:
        all_chores.append((None, *chore_data))

    # Maintenance chores
    for chore_data in MAINTENANCE_CHORES:
        all_chores.append((None, *chore_data))

    return all_chores


def count_chores():
    """Count total chores."""
    room_chores = sum(len(chores) for chores in CHORES_BY_ROOM.values())
    house_wide = len(HOUSE_WIDE_CHORES)
    maintenance = len(MAINTENANCE_CHORES)
    return {
        "room_specific": room_chores,
        "house_wide": house_wide,
        "maintenance": maintenance,
        "total": room_chores + house_wide + maintenance,
    }
