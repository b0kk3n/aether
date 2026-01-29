#!/usr/bin/env python3
"""Quick script to set up chores in Aether."""

from aether.core.engine import Aether
from aether.chores import Chore

# Initialize Aether
aether = Aether()

# Add your custom chores here
chores = [
    # Example chores - customize these!
    Chore(
        name="Vacuum living room",
        interval_days=7,
        duration_minutes=15,
        room="living_room"
    ),
    Chore(
        name="Clean bathroom",
        interval_days=14,
        duration_minutes=30,
        room="bathroom"
    ),
    Chore(
        name="Take out trash",
        interval_days=3,
        duration_minutes=5,
    ),
    # Add more chores here...
]

# Or use templates
template_chores = [
    "vacuum_living",
    "clean_bathroom",
    "trash_out",
    "water_plants",
    # Add template names here
]

print("Adding chores...")

# Add custom chores
for chore in chores:
    aether.chores.add(chore)
    print(f"✓ Added: {chore.name} (every {chore.interval_days} days)")

# Add from templates
for template in template_chores:
    chore = aether.chores.add_from_template(template)
    if chore:
        print(f"✓ Added from template: {chore.name}")

print(f"\n✓ Setup complete! Added {len(chores) + len(template_chores)} chores")
print("\nView them at: http://192.168.2.4:8080 (Chores tab)")
print("Or run: aether chores")
