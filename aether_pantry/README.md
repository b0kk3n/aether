# Aether Pantry

> Part of the Aether umbrella, alongside the chore manager — its own tab, its own data, no shared logic.

A place where "what's low or out at home" lives, so it doesn't have to live in your head.

## Philosophy

- **The grocery list is the hero** — add anything, anytime, no mode-switching
- **Nothing is mandatory** — a product can be bare: just a name and a status. Categories, intervals, and checklists are optional helpers
- **Buffer, not panic** — an elapsed interval means "low," not "out"; you buy with buffer

## Features

- **Grocery list** — add a line; if it matches a product by name, checking it off resets that product's status and restarts its interval. If it doesn't match, it's just a line — check it off and it's gone
- **Products** — status (in stock / low / out), optional category, optional interval
- **Categories** — structural groupings tied to physical storage, fully editable
- **Checklists** — cross-cutting groupings (Market, Sale, Breakfast, Cupboard, ...) for batch-walking several products' status at once, sorted out → low → in stock, staleness within each tier
- **Vacation mode** — freezes every interval clock while you're away; unpausing shifts due dates out by however long you were gone, it doesn't reset them

## Home Assistant Add-on

Aether Pantry runs as its own Home Assistant add-on, alongside (not merged
into) the Aether chore manager add-on — a separate sidebar tab, separate
container, separate database.
