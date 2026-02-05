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
    icon TEXT DEFAULT '🏠',
    sort_order INTEGER DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Chores table
CREATE TABLE IF NOT EXISTS chores (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    room_id TEXT,
    interval_days INTEGER NOT NULL,
    estimated_minutes INTEGER DEFAULT 15,
    category TEXT DEFAULT 'clean',
    notes TEXT DEFAULT '',
    is_active INTEGER DEFAULT 1,
    last_completed_at TEXT,
    streak INTEGER DEFAULT 0,
    completion_count INTEGER DEFAULT 0,
    duration_confirmed INTEGER DEFAULT 0,
    duration_confirmations INTEGER DEFAULT 0,
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
    icon TEXT DEFAULT '📋',
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

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_chores_room_id ON chores(room_id);
CREATE INDEX IF NOT EXISTS idx_chores_category ON chores(category);
CREATE INDEX IF NOT EXISTS idx_chores_is_active ON chores(is_active);
CREATE INDEX IF NOT EXISTS idx_completion_logs_chore_id ON completion_logs(chore_id);
CREATE INDEX IF NOT EXISTS idx_completion_logs_completed_at ON completion_logs(completed_at);
"""


def init_db():
    """Initialize the database with schema."""
    with get_db() as conn:
        conn.executescript(SCHEMA)


def reset_db():
    """Reset the database (drop all tables and recreate).

    WARNING: This will delete all data!
    """
    with get_db() as conn:
        conn.executescript("""
            DROP TABLE IF EXISTS checklist_chores;
            DROP TABLE IF EXISTS checklists;
            DROP TABLE IF EXISTS completion_logs;
            DROP TABLE IF EXISTS chores;
            DROP TABLE IF EXISTS rooms;
        """)
        conn.executescript(SCHEMA)


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
    """Run any pending migrations."""
    with get_db() as conn:
        current_version = get_schema_version(conn)

        if current_version < 1:
            # Initial schema (v1)
            conn.executescript(SCHEMA)
            set_schema_version(conn, 1)

        # Future migrations would go here:
        # if current_version < 2:
        #     conn.execute("ALTER TABLE ...")
        #     set_schema_version(conn, 2)
