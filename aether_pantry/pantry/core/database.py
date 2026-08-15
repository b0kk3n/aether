"""Database setup and connection management for Aether Pantry.

Uses SQLite for simple, portable, single-user storage.
Default location: ~/.aether_pantry/pantry.db

Mirrors the pattern in the sibling chores app's aether/core/database.py
(raw SQL, PRAGMA user_version migrations) but is its own independent
module/database - no import or data ties to that app.
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator
import os

# Default database path
DEFAULT_DB_PATH = Path.home() / ".aether_pantry" / "pantry.db"


def get_db_path() -> Path:
    """Get database path from environment or use default."""
    env_path = os.environ.get("AETHER_PANTRY_DB_PATH")
    if env_path:
        return Path(env_path)
    return DEFAULT_DB_PATH


def ensure_db_directory():
    """Ensure the database directory exists."""
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)


def get_connection() -> sqlite3.Connection:
    """Get a database connection with row factory."""
    ensure_db_directory()
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Context manager for database connections."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# =============================================================================
# Schema Definition
# =============================================================================

SCHEMA = """
-- Categories table: structural, tied to physical storage. User-creatable.
CREATE TABLE IF NOT EXISTS categories (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    icon TEXT DEFAULT 'tag',
    sort_order INTEGER DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
INSERT OR IGNORE INTO categories (id, name, icon, sort_order) VALUES
    ('produce', 'Produce', 'produce', 0),
    ('dairy', 'Dairy', 'dairy', 1),
    ('meat_seafood', 'Meat & Seafood', 'meat', 2),
    ('pantry_staples', 'Pantry Staples', 'jar', 3),
    ('spices_condiments', 'Spices & Condiments', 'spice', 4),
    ('cleaning_supplies', 'Cleaning Supplies', 'spray', 5),
    ('household', 'Household', 'household', 6),
    ('frozen_beverages', 'Frozen & Beverages', 'snowflake', 7);

-- Products table: every tracked item. A product can be bare - just a
-- name and a status - category/interval are optional helpers.
CREATE TABLE IF NOT EXISTS products (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category_id TEXT REFERENCES categories(id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'in_stock' CHECK (status IN ('in_stock', 'low', 'out')),
    last_checked TEXT NOT NULL DEFAULT (datetime('now')),
    interval_days INTEGER,
    vacation_offset_days REAL NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_products_category_id ON products(category_id);
CREATE INDEX IF NOT EXISTS idx_products_status ON products(status);
CREATE INDEX IF NOT EXISTS idx_products_name ON products(name COLLATE NOCASE);

-- Grocery list: a live to-buy queue, not a log. Each line is either
-- linked to a product (matched by name at add time) or free text.
CREATE TABLE IF NOT EXISTS grocery_list_items (
    id TEXT PRIMARY KEY,
    raw_text TEXT NOT NULL,
    product_id TEXT REFERENCES products(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_grocery_items_product_id ON grocery_list_items(product_id);

-- Checklists: contextual, cross-cutting groupings of products (Market,
-- Sale, Breakfast, Cupboard, ...).
CREATE TABLE IF NOT EXISTS checklists (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    icon TEXT DEFAULT 'clipboard',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Checklist membership. No sort_order - walk order is always computed
-- live (status tier, then staleness), never a stored ordering.
CREATE TABLE IF NOT EXISTS checklist_products (
    checklist_id TEXT NOT NULL,
    product_id TEXT NOT NULL,
    PRIMARY KEY (checklist_id, product_id),
    FOREIGN KEY (checklist_id) REFERENCES checklists(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

-- Vacation state (singleton global on/off switch) - freezes every
-- product's interval clock while active.
CREATE TABLE IF NOT EXISTS vacation_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    is_active INTEGER NOT NULL DEFAULT 0,
    started_at TEXT
);
INSERT OR IGNORE INTO vacation_state (id, is_active, started_at) VALUES (1, 0, NULL);

-- Vacation history log
CREATE TABLE IF NOT EXISTS vacation_log (
    id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    ended_at TEXT NOT NULL,
    days_elapsed REAL NOT NULL,
    products_affected INTEGER NOT NULL DEFAULT 0
);
"""

# View joining category display fields and computing the live vacation-pause
# arithmetic. The "has the interval actually elapsed" decision itself is a
# Product.effective_status Python property (see core/models.py), not SQL -
# this view only supplies the effective_paused_days a Python property can't
# derive without a second round trip against vacation_state.
PRODUCTS_EFFECTIVE_VIEW_SQL = """
CREATE VIEW IF NOT EXISTS products_effective AS
SELECT
    p.*,
    cat.name AS cat_name,
    cat.icon AS cat_icon,
    CASE
        WHEN (SELECT is_active FROM vacation_state WHERE id = 1) = 1
        THEN p.vacation_offset_days
             + (julianday('now') - julianday((SELECT started_at FROM vacation_state WHERE id = 1)))
        ELSE p.vacation_offset_days
    END AS effective_paused_days
FROM products p
LEFT JOIN categories cat ON p.category_id = cat.id;
"""


def init_db():
    """Initialize the database with schema."""
    with get_db() as conn:
        conn.executescript(SCHEMA)
        conn.executescript(PRODUCTS_EFFECTIVE_VIEW_SQL)


def reset_db():
    """Reset the database (drop all tables and recreate).

    WARNING: This will delete all data!
    """
    with get_db() as conn:
        conn.executescript("""
            DROP VIEW IF EXISTS products_effective;
            DROP TABLE IF EXISTS checklist_products;
            DROP TABLE IF EXISTS checklists;
            DROP TABLE IF EXISTS grocery_list_items;
            DROP TABLE IF EXISTS vacation_log;
            DROP TABLE IF EXISTS vacation_state;
            DROP TABLE IF EXISTS products;
            DROP TABLE IF EXISTS categories;
        """)
        conn.executescript(SCHEMA)
        conn.executescript(PRODUCTS_EFFECTIVE_VIEW_SQL)


def db_exists() -> bool:
    """Check if database file exists."""
    return get_db_path().exists()


# =============================================================================
# Migration Support (for future schema changes)
# =============================================================================

def get_schema_version(conn: sqlite3.Connection) -> int:
    """Get current schema version."""
    try:
        cursor = conn.execute("PRAGMA user_version")
        return cursor.fetchone()[0]
    except Exception:
        return 0


def set_schema_version(conn: sqlite3.Connection, version: int):
    """Set schema version."""
    conn.execute(f"PRAGMA user_version = {version}")


# Current schema version
CURRENT_SCHEMA_VERSION = 1


def migrate_db():
    """Run any pending migrations.

    No migrations yet - schema starts at v1. Future schema changes get
    their own numbered `if current_version < N` block here, same pattern
    as the chores app's migrate_db().
    """
    with get_db() as conn:
        current_version = get_schema_version(conn)

        if current_version < 1:
            conn.executescript(SCHEMA)
            conn.executescript(PRODUCTS_EFFECTIVE_VIEW_SQL)
            set_schema_version(conn, 1)
