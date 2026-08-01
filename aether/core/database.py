"""Database setup and connection management for Aether.

Uses SQLite for simple, portable, single-user storage.
Default location: ~/.aether/aether.db
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator
import os

# Default database path
DEFAULT_DB_PATH = Path.home() / ".aether" / "aether.db"


def get_db_path() -> Path:
    """Get database path from environment or use default."""
    env_path = os.environ.get("AETHER_DB_PATH")
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
-- Rooms table
CREATE TABLE IF NOT EXISTS rooms (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    icon TEXT DEFAULT 'home',
    sort_order INTEGER DEFAULT 0,
    is_paused INTEGER DEFAULT 0,
    paused_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Categories table
CREATE TABLE IF NOT EXISTS categories (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    icon TEXT DEFAULT 'tag',
    sort_order INTEGER DEFAULT 0,
    is_vacation_pausable_default INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
INSERT OR IGNORE INTO categories (id, name, icon, sort_order, is_vacation_pausable_default) VALUES
    ('vacuum', 'Vacuum', 'vacuum', 0, 1),
    ('mop', 'Mop', 'mop', 1, 1),
    ('dust', 'Dust', 'dust', 2, 1),
    ('declutter', 'Declutter', 'declutter', 3, 1),
    ('clean', 'Clean', 'clean', 4, 1),
    ('wash', 'Wash', 'wash', 5, 1),
    ('wipe', 'Wipe', 'wipe', 6, 1),
    ('maintain', 'Maintain', 'maintain', 7, 0);

-- Chores table
CREATE TABLE IF NOT EXISTS chores (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    room_id TEXT,
    interval_days INTEGER NOT NULL,
    estimated_minutes INTEGER DEFAULT 15,
    category TEXT DEFAULT 'clean',
    category_id TEXT REFERENCES categories(id),
    notes TEXT DEFAULT '',
    is_active INTEGER DEFAULT 1,
    last_completed_at TEXT,
    streak INTEGER DEFAULT 0,
    completion_count INTEGER DEFAULT 0,
    duration_confirmed INTEGER DEFAULT 0,
    duration_confirmations INTEGER DEFAULT 0,
    interval_confirmed INTEGER DEFAULT 0,
    interval_confirmations INTEGER DEFAULT 0,
    vacation_offset_days REAL NOT NULL DEFAULT 0,
    vacation_override TEXT,
    room_pause_offset_days REAL NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE SET NULL
);

-- Completion log table
CREATE TABLE IF NOT EXISTS completion_logs (
    id TEXT PRIMARY KEY,
    chore_id TEXT NOT NULL,
    completed_at TEXT NOT NULL DEFAULT (datetime('now')),
    actual_minutes INTEGER,
    notes TEXT DEFAULT '',
    FOREIGN KEY (chore_id) REFERENCES chores(id) ON DELETE CASCADE
);

-- Checklists table
CREATE TABLE IF NOT EXISTS checklists (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    icon TEXT DEFAULT 'clipboard',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Checklist chores junction table
CREATE TABLE IF NOT EXISTS checklist_chores (
    checklist_id TEXT NOT NULL,
    chore_id TEXT NOT NULL,
    sort_order INTEGER DEFAULT 0,
    PRIMARY KEY (checklist_id, chore_id),
    FOREIGN KEY (checklist_id) REFERENCES checklists(id) ON DELETE CASCADE,
    FOREIGN KEY (chore_id) REFERENCES chores(id) ON DELETE CASCADE
);

-- Vacation state (singleton global on/off switch)
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
    chores_affected INTEGER NOT NULL DEFAULT 0
);

-- App-wide settings (singleton row, same pattern as vacation_state)
CREATE TABLE IF NOT EXISTS app_settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    household_name TEXT
);
INSERT OR IGNORE INTO app_settings (id, household_name) VALUES (1, NULL);

-- Indexes for common queries
-- NOTE: idx_chores_category_id is intentionally NOT created here. On a
-- fresh install the chores table (with category_id) is created above in
-- this same script, so it would be safe - but on an EXISTING database
-- being upgraded, `CREATE TABLE IF NOT EXISTS chores` above is a no-op
-- (the table already exists without category_id), and init_db() always
-- runs before migrate_db() adds that column via ALTER TABLE. Indexing a
-- column that doesn't exist yet crashes executescript() and takes down
-- the whole app before migrate_db() gets a chance to fix the schema. It's
-- created instead in migrate_db()'s v4 block, right after the column is
-- guaranteed to exist, for both fresh installs and upgrades alike.
CREATE INDEX IF NOT EXISTS idx_chores_room_id ON chores(room_id);
CREATE INDEX IF NOT EXISTS idx_chores_category ON chores(category);
CREATE INDEX IF NOT EXISTS idx_chores_is_active ON chores(is_active);
CREATE INDEX IF NOT EXISTS idx_completion_logs_chore_id ON completion_logs(chore_id);
CREATE INDEX IF NOT EXISTS idx_completion_logs_completed_at ON completion_logs(completed_at);
"""

# Categories table + seed rows, shared verbatim between SCHEMA (fresh installs
# already have this via SCHEMA above) and the v4 migration path (which adds it
# to pre-existing databases). Kept as one string so the two paths can't drift.
CATEGORIES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS categories (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    icon TEXT DEFAULT 'tag',
    sort_order INTEGER DEFAULT 0,
    is_vacation_pausable_default INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
INSERT OR IGNORE INTO categories (id, name, icon, sort_order, is_vacation_pausable_default) VALUES
    ('vacuum', 'Vacuum', 'vacuum', 0, 1),
    ('mop', 'Mop', 'mop', 1, 1),
    ('dust', 'Dust', 'dust', 2, 1),
    ('declutter', 'Declutter', 'declutter', 3, 1),
    ('clean', 'Clean', 'clean', 4, 1),
    ('wash', 'Wash', 'wash', 5, 1),
    ('wipe', 'Wipe', 'wipe', 6, 1),
    ('maintain', 'Maintain', 'maintain', 7, 0);
"""

# View used by every read path that computes due dates/freshness. Adds
# effective_paused_days = accumulated vacation_offset_days, plus (only while
# a vacation is active AND the chore's category is pausable-by-default or
# force-paused) the live elapsed time of the in-progress vacation, plus
# (only while the chore's room is paused) the live elapsed time of that
# room pause. Callers add this to interval_days wherever they currently do
# julianday(...) + interval_days arithmetic.
#
# Every joined column is explicitly aliased (cat_name, cat_icon, ...) since
# `c.*` already includes a `name` column (the chore's own name) - an
# unaliased `categories.name` would collide with it in sqlite3.Row's
# column-name lookup and silently corrupt chore names on every read.
CHORES_EFFECTIVE_VIEW_SQL = """
CREATE VIEW IF NOT EXISTS chores_effective AS
SELECT
    c.*,
    cat.name AS cat_name,
    cat.icon AS cat_icon,
    cat.is_vacation_pausable_default AS category_pausable_default,
    rm.is_paused AS room_is_paused,
    (
        CASE
            WHEN (SELECT is_active FROM vacation_state WHERE id = 1) = 1
                 AND (
                     c.vacation_override = 'force_pause'
                     OR (
                         (c.vacation_override IS NULL OR c.vacation_override = '')
                         AND cat.is_vacation_pausable_default = 1
                     )
                 )
            THEN c.vacation_offset_days
                 + (julianday('now') - julianday((SELECT started_at FROM vacation_state WHERE id = 1)))
            ELSE c.vacation_offset_days
        END
        +
        CASE
            WHEN c.room_id IS NOT NULL AND rm.is_paused = 1
                THEN c.room_pause_offset_days + (julianday('now') - julianday(rm.paused_at))
            ELSE c.room_pause_offset_days
        END
    ) AS effective_paused_days
FROM chores c
LEFT JOIN categories cat ON c.category_id = cat.id
LEFT JOIN rooms rm ON c.room_id = rm.id;
"""

# Intermediate view definition used only by the v4 migration step, for
# databases upgrading from v3 that don't have rooms.is_paused /
# chores.room_pause_offset_days yet (those are added in v5, later in the
# same migrate_db() run). Fresh installs and post-v5 databases always use
# the full CHORES_EFFECTIVE_VIEW_SQL above instead.
CHORES_EFFECTIVE_VIEW_SQL_V4 = """
CREATE VIEW IF NOT EXISTS chores_effective AS
SELECT
    c.*,
    cat.name AS cat_name,
    cat.icon AS cat_icon,
    cat.is_vacation_pausable_default AS category_pausable_default,
    CASE
        WHEN (SELECT is_active FROM vacation_state WHERE id = 1) = 1
             AND (
                 c.vacation_override = 'force_pause'
                 OR (
                     (c.vacation_override IS NULL OR c.vacation_override = '')
                     AND cat.is_vacation_pausable_default = 1
                 )
             )
        THEN c.vacation_offset_days
             + (julianday('now') - julianday((SELECT started_at FROM vacation_state WHERE id = 1)))
        ELSE c.vacation_offset_days
    END AS effective_paused_days
FROM chores c
LEFT JOIN categories cat ON c.category_id = cat.id;
"""


def init_db():
    """Initialize the database with schema."""
    with get_db() as conn:
        conn.executescript(SCHEMA)
        conn.executescript(CHORES_EFFECTIVE_VIEW_SQL)


def reset_db():
    """Reset the database (drop all tables and recreate).

    WARNING: This will delete all data!
    """
    with get_db() as conn:
        conn.executescript("""
            DROP VIEW IF EXISTS chores_effective;
            DROP TABLE IF EXISTS checklist_chores;
            DROP TABLE IF EXISTS checklists;
            DROP TABLE IF EXISTS completion_logs;
            DROP TABLE IF EXISTS vacation_log;
            DROP TABLE IF EXISTS vacation_state;
            DROP TABLE IF EXISTS chores;
            DROP TABLE IF EXISTS rooms;
        """)
        conn.executescript(SCHEMA)
        conn.executescript(CHORES_EFFECTIVE_VIEW_SQL)


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
CURRENT_SCHEMA_VERSION = 6


def migrate_db():
    """Run any pending migrations."""
    with get_db() as conn:
        current_version = get_schema_version(conn)

        if current_version < 1:
            # Initial schema (v1)
            conn.executescript(SCHEMA)
            conn.executescript(CHORES_EFFECTIVE_VIEW_SQL)
            set_schema_version(conn, 1)

        if current_version < 2:
            # v2: interval confirmation tracking
            try:
                conn.execute("ALTER TABLE chores ADD COLUMN interval_confirmed INTEGER DEFAULT 0")
            except Exception:
                pass  # Column may already exist on fresh DBs
            try:
                conn.execute("ALTER TABLE chores ADD COLUMN interval_confirmations INTEGER DEFAULT 0")
            except Exception:
                pass
            set_schema_version(conn, 2)

        if current_version < 3:
            # v3: vacation mode
            try:
                conn.execute("ALTER TABLE chores ADD COLUMN vacation_offset_days REAL NOT NULL DEFAULT 0")
            except Exception:
                pass  # Column may already exist on fresh DBs
            try:
                conn.execute("ALTER TABLE chores ADD COLUMN vacation_override TEXT")
            except Exception:
                pass
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS vacation_state (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    is_active INTEGER NOT NULL DEFAULT 0,
                    started_at TEXT
                );
                INSERT OR IGNORE INTO vacation_state (id, is_active, started_at) VALUES (1, 0, NULL);
                CREATE TABLE IF NOT EXISTS vacation_log (
                    id TEXT PRIMARY KEY,
                    started_at TEXT NOT NULL,
                    ended_at TEXT NOT NULL,
                    days_elapsed REAL NOT NULL,
                    chores_affected INTEGER NOT NULL DEFAULT 0
                );
                DROP VIEW IF EXISTS chores_effective;
            """)
            conn.executescript(CHORES_EFFECTIVE_VIEW_SQL)
            set_schema_version(conn, 3)

        if current_version < 4:
            # v4: user-editable categories (replaces the hardcoded enum)
            try:
                conn.execute("ALTER TABLE chores ADD COLUMN category_id TEXT")
            except Exception:
                pass  # Column may already exist on fresh DBs
            conn.executescript(CATEGORIES_TABLE_SQL)
            conn.execute("UPDATE chores SET category_id = category WHERE category_id IS NULL")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_chores_category_id ON chores(category_id)")
            conn.executescript("DROP VIEW IF EXISTS chores_effective;")
            conn.executescript(CHORES_EFFECTIVE_VIEW_SQL_V4)
            set_schema_version(conn, 4)

        if current_version < 5:
            # v5: room pause ("remodeling") - freezes all of a room's chores
            try:
                conn.execute("ALTER TABLE rooms ADD COLUMN is_paused INTEGER DEFAULT 0")
            except Exception:
                pass
            try:
                conn.execute("ALTER TABLE rooms ADD COLUMN paused_at TEXT")
            except Exception:
                pass
            try:
                conn.execute("ALTER TABLE chores ADD COLUMN room_pause_offset_days REAL NOT NULL DEFAULT 0")
            except Exception:
                pass
            conn.executescript("DROP VIEW IF EXISTS chores_effective;")
            conn.executescript(CHORES_EFFECTIVE_VIEW_SQL)
            set_schema_version(conn, 5)

        if current_version < 6:
            # v6: app-wide settings (currently just an optional household name)
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS app_settings (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    household_name TEXT
                );
                INSERT OR IGNORE INTO app_settings (id, household_name) VALUES (1, NULL);
            """)
            set_schema_version(conn, 6)
