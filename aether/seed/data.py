"""Initial seed data for Aether.

Contains:
- 10 rooms
- chores (room-specific + house-wide + maintenance)
- 2 checklists (Visitors, Sleepover)

Duration estimates are initial guesses - users can adjust via the
duration confirmation flow when completing chores.

Chore tuple format: (name, interval_days, estimated_minutes, category_id[, notes])
The notes field is optional. category_id values must match the seeded
category ids in aether/core/database.py's CATEGORIES_TABLE_SQL (vacuum, mop,
dust, declutter, clean, wash, wipe, maintain).
"""

# =============================================================================
# Rooms
# =============================================================================

ROOMS = [
    {"name": "Entry", "icon": "door", "sort_order": 0},
    {"name": "Hallway", "icon": "walk", "sort_order": 1},
    {"name": "Living room", "icon": "sofa", "sort_order": 2},
    {"name": "Office & Dining room", "icon": "dining", "sort_order": 3},
    {"name": "Bedroom", "icon": "bed", "sort_order": 4},
    {"name": "Bathroom", "icon": "shower", "sort_order": 5},
    {"name": "Toilet", "icon": "toilet", "sort_order": 6},
    {"name": "Kitchen", "icon": "pan", "sort_order": 7},
    {"name": "Storage", "icon": "box", "sort_order": 8},
    {"name": "Balcony", "icon": "leaf", "sort_order": 9},
]


# =============================================================================
# Chores by Room
# =============================================================================

# Format: (name, interval_days, estimated_minutes, category_id[, notes])

CHORES_BY_ROOM = {
    "Entry": [
        ("Vacuum entryway", 10, 5, 'vacuum'),
        ("Mop entryway", 30, 8, 'mop', "Do after vacuuming"),
        ("Declutter entryway", 60, 10, 'declutter'),
    ],
    "Hallway": [
        ("Vacuum hallway", 5, 5, 'vacuum'),
        ("Mop hallway", 10, 8, 'mop', "Do after vacuuming"),
    ],
    "Living room": [
        ("Declutter living room", 5, 10, 'declutter'),
        ("Vacuum living room", 7, 10, 'vacuum'),
        ("Dust living room surfaces", 10, 5, 'dust'),
        ("Mop living room", 30, 15, 'mop', "Do after vacuuming"),
        ("Clean living room furniture", 30, 15, 'clean'),
        ("Clean living room surfaces", 30, 15, 'clean'),
        ("Wash living room blankets", 120, 5, 'wash'),
        ("Wash living room pillow cases", 160, 10, 'wash'),
        ("Deep clean living room rug", 160, 45, 'clean'),
        ("Wash living room windows", 160, 60, 'wash'),
        ("Wash living room curtains", 365, 15, 'wash'),
    ],
    "Office & Dining room": [
        ("Wipe down dining room table", 3, 5, 'wipe'),
        ("Declutter dining room", 5, 10, 'declutter'),
        ("Vacuum dining room", 7, 10, 'vacuum'),
        ("Dust dining room surfaces", 10, 10, 'dust'),
        ("Mop dining room", 30, 15, 'mop', "Do after vacuuming"),
        ("Clean dining room surfaces", 30, 15, 'clean'),
        ("Wash office & dining room windows", 160, 60, 'wash'),
        ("Wash dining room curtains", 365, 15, 'wash'),
    ],
    "Bedroom": [
        ("Declutter bedroom", 7, 5, 'declutter'),
        ("Dust bedroom surfaces", 10, 5, 'dust'),
        ("Vacuum bedroom", 14, 10, 'vacuum'),
        ("Change bedsheets", 14, 10, 'wash'),
        ("Vacuum matras", 28, 15, 'vacuum'),
        ("Clean bedroom surfaces", 30, 10, 'clean'),
        ("Mop bedroom", 60, 15, 'mop', "Do after vacuuming"),
        ("Wash sleeping pillow", 120, 5, 'wash'),
        ("Wash matras cover", 120, 5, 'wash'),
        ("Wash bedroom windows", 160, 60, 'wash'),
        ("Wash bedroom curtains", 365, 15, 'wash'),
    ],
    "Bathroom": [
        ("Wipe countertops", 5, 5, 'wipe'),
        ("Vacuum bathroom floor", 7, 5, 'vacuum'),
        ("Mop bathroom floor", 14, 10, 'mop', "Do after vacuuming"),
        ("Clean bathroom sink", 14, 10, 'clean'),
        ("Clean bathroom mirror", 21, 5, 'clean'),
        ("Wash bathroom rug", 21, 2, 'wash'),
        ("Clean shower", 30, 20, 'clean'),
        ("Clean outside bathroom cabinets", 60, 10, 'clean'),
        ("Disinfect trashcan", 120, 5, 'clean'),
        ("Clean inside bathroom cabinets", 160, 20, 'clean'),
        ("Clean bathroom walls", 160, 30, 'clean'),
        ("Wash bathroom windows", 160, 60, 'wash'),
    ],
    "Toilet": [
        ("Clean toilet", 7, 10, 'clean'),
        ("Vacuum toilet", 7, 5, 'vacuum'),
        ("Mop toilet", 14, 8, 'mop', "Do after vacuuming"),
        ("Clean air ventilation toilet", 60, 5, 'clean'),
    ],
    "Kitchen": [
        ("Wipe kitchen countertops", 3, 5, 'wipe'),
        ("Vacuum kitchen floor", 5, 8, 'vacuum'),
        ("Clean kitchen sink", 7, 5, 'clean'),
        ("Clean stovetop", 7, 5, 'clean'),
        ("Mop kitchen floor", 10, 12, 'mop', "Do after vacuuming"),
        ("Descale kettle", 45, 10, 'clean'),
        ("Clean outside kitchen cabinets", 60, 15, 'clean'),
        ("Clean fridge", 60, 20, 'clean'),
        ("Disinfect trashcan", 60, 5, 'clean'),
        ("Clean oven", 90, 30, 'clean'),
        ("Clean freezer", 160, 30, 'clean'),
        ("Clean inside kitchen cabinets", 160, 45, 'clean'),
        ("Wash kitchen windows", 160, 60, 'wash'),
    ],
    "Storage": [
        ("Vacuum storage", 14, 8, 'vacuum'),
        ("Dust storage surfaces", 28, 10, 'dust'),
        ("Mop storage", 42, 10, 'mop', "Do after vacuuming"),
        ("Declutter storage", 45, 30, 'declutter'),
        ("Clean storage surfaces", 60, 15, 'clean'),
        ("Wash storage windows", 160, 60, 'wash'),
        ("Wash storage curtains", 365, 15, 'wash'),
    ],
    "Balcony": [
        ("Clean balcony floor", 180, 30, 'clean'),
        ("Clean balcony gutter", 180, 15, 'clean'),
        ("Clean balcony furniture", 180, 20, 'clean'),
    ],
}


# =============================================================================
# House-wide Chores (no specific room)
# =============================================================================

HOUSE_WIDE_CHORES = [
    ("Clean doorhandles", 45, 15, 'clean'),
    ("Clean light switches", 45, 15, 'clean'),
    ("Clean doors", 160, 60, 'clean'),
    ("Clean radiators", 200, 60, 'clean'),
]


# =============================================================================
# Maintenance Tasks (longer intervals, house-wide)
# =============================================================================

MAINTENANCE_CHORES = [
    ("Smoke detector batteries", 365, 15, 'maintain'),
    ("Oil wooden floors", 365, 120, 'maintain'),
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
        "icon": "party",
        "chores": [
            # Declutter
            ("Living room", "Declutter living room"),
            ("Office & Dining room", "Declutter dining room"),
            # Vacuum
            ("Living room", "Vacuum living room"),
            ("Office & Dining room", "Vacuum dining room"),
            ("Hallway", "Vacuum hallway"),
            ("Kitchen", "Vacuum kitchen floor"),
            ("Toilet", "Vacuum toilet"),
            # Mop
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
        "icon": "moon",
        "chores": [
            # Bedsheets
            ("Bedroom", "Change bedsheets"),
            # Declutter
            ("Bedroom", "Declutter bedroom"),
            ("Bathroom", "Wipe countertops"),
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
