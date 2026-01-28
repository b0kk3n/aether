"""Data persistence layer using SQLite."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import (
    Task,
    TaskStatus,
    Reminder,
    Event,
    Pattern,
    Memory,
    Context,
)


class Store:
    """SQLite-based data store for Aether."""

    def __init__(self, db_path: str | Path | None = None):
        """Initialize store with database path."""
        if db_path is None:
            data_dir = Path.home() / ".aether"
            data_dir.mkdir(parents=True, exist_ok=True)
            db_path = data_dir / "aether.db"

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Initialize database schema."""
        conn = self._get_conn()
        try:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    status TEXT NOT NULL,
                    priority INTEGER NOT NULL,
                    area TEXT,
                    project TEXT,
                    due_date TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS reminders (
                    id TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    reminder_type TEXT NOT NULL,
                    trigger_at TEXT,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    start TEXT NOT NULL,
                    end TEXT,
                    event_type TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS patterns (
                    id TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    pattern_type TEXT NOT NULL,
                    confidence REAL NOT NULL DEFAULT 0,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    key TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS context_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS activity_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    entity_type TEXT,
                    entity_id TEXT,
                    data TEXT,
                    timestamp TEXT NOT NULL
                );

                -- Indexes for common queries
                CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
                CREATE INDEX IF NOT EXISTS idx_tasks_due ON tasks(due_date);
                CREATE INDEX IF NOT EXISTS idx_tasks_area ON tasks(area);
                CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project);
                CREATE INDEX IF NOT EXISTS idx_reminders_trigger ON reminders(trigger_at);
                CREATE INDEX IF NOT EXISTS idx_reminders_active ON reminders(active);
                CREATE INDEX IF NOT EXISTS idx_events_start ON events(start);
                CREATE INDEX IF NOT EXISTS idx_memories_key ON memories(key);
                CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type);
                CREATE INDEX IF NOT EXISTS idx_activity_timestamp ON activity_log(timestamp);
            """
            )
            conn.commit()
        finally:
            conn.close()

    # Task operations
    def save_task(self, task: Task) -> None:
        """Save or update a task."""
        conn = self._get_conn()
        try:
            now = datetime.now().isoformat()
            conn.execute(
                """
                INSERT OR REPLACE INTO tasks
                (id, data, status, priority, area, project, due_date, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    task.id,
                    json.dumps(task.to_dict()),
                    task.status.value,
                    task.priority.value,
                    task.area,
                    task.project,
                    task.due_date.isoformat() if task.due_date else None,
                    task.created_at.isoformat(),
                    now,
                ),
            )
            conn.commit()
            self._log_activity(conn, "task_saved", "task", task.id, {"status": task.status.value})
        finally:
            conn.close()

    def get_task(self, task_id: str) -> Task | None:
        """Get task by ID."""
        conn = self._get_conn()
        try:
            row = conn.execute("SELECT data FROM tasks WHERE id = ?", (task_id,)).fetchone()
            if row:
                return Task.from_dict(json.loads(row["data"]))
            return None
        finally:
            conn.close()

    def get_tasks(
        self,
        status: TaskStatus | list[TaskStatus] | None = None,
        area: str | None = None,
        project: str | None = None,
        include_done: bool = False,
        limit: int | None = None,
    ) -> list[Task]:
        """Get tasks with optional filters."""
        conn = self._get_conn()
        try:
            query = "SELECT data FROM tasks WHERE 1=1"
            params: list[Any] = []

            if status:
                if isinstance(status, list):
                    placeholders = ",".join("?" * len(status))
                    query += f" AND status IN ({placeholders})"
                    params.extend(s.value for s in status)
                else:
                    query += " AND status = ?"
                    params.append(status.value)
            elif not include_done:
                query += " AND status NOT IN ('done', 'cancelled')"

            if area:
                query += " AND area = ?"
                params.append(area)

            if project:
                query += " AND project = ?"
                params.append(project)

            query += " ORDER BY priority ASC, due_date ASC NULLS LAST, created_at ASC"

            if limit:
                query += " LIMIT ?"
                params.append(limit)

            rows = conn.execute(query, params).fetchall()
            return [Task.from_dict(json.loads(row["data"])) for row in rows]
        finally:
            conn.close()

    def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        conn = self._get_conn()
        try:
            result = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            conn.commit()
            if result.rowcount > 0:
                self._log_activity(conn, "task_deleted", "task", task_id)
                return True
            return False
        finally:
            conn.close()

    # Reminder operations
    def save_reminder(self, reminder: Reminder) -> None:
        """Save or update a reminder."""
        conn = self._get_conn()
        try:
            now = datetime.now().isoformat()
            conn.execute(
                """
                INSERT OR REPLACE INTO reminders
                (id, data, reminder_type, trigger_at, active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    reminder.id,
                    json.dumps(reminder.to_dict()),
                    reminder.reminder_type.value,
                    reminder.trigger_at.isoformat() if reminder.trigger_at else None,
                    1 if reminder.active else 0,
                    reminder.created_at.isoformat(),
                    now,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get_reminder(self, reminder_id: str) -> Reminder | None:
        """Get reminder by ID."""
        conn = self._get_conn()
        try:
            row = conn.execute("SELECT data FROM reminders WHERE id = ?", (reminder_id,)).fetchone()
            if row:
                return Reminder.from_dict(json.loads(row["data"]))
            return None
        finally:
            conn.close()

    def get_reminders(
        self,
        active_only: bool = True,
        due_before: datetime | None = None,
    ) -> list[Reminder]:
        """Get reminders with optional filters."""
        conn = self._get_conn()
        try:
            query = "SELECT data FROM reminders WHERE 1=1"
            params: list[Any] = []

            if active_only:
                query += " AND active = 1"

            if due_before:
                query += " AND trigger_at <= ?"
                params.append(due_before.isoformat())

            query += " ORDER BY trigger_at ASC NULLS LAST"

            rows = conn.execute(query, params).fetchall()
            return [Reminder.from_dict(json.loads(row["data"])) for row in rows]
        finally:
            conn.close()

    def delete_reminder(self, reminder_id: str) -> bool:
        """Delete a reminder."""
        conn = self._get_conn()
        try:
            result = conn.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
            conn.commit()
            return result.rowcount > 0
        finally:
            conn.close()

    # Event operations
    def save_event(self, event: Event) -> None:
        """Save or update an event."""
        conn = self._get_conn()
        try:
            now = datetime.now().isoformat()
            conn.execute(
                """
                INSERT OR REPLACE INTO events
                (id, data, start, end, event_type, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    event.id,
                    json.dumps(event.to_dict()),
                    event.start.isoformat(),
                    event.end.isoformat() if event.end else None,
                    event.event_type,
                    now,
                    now,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get_event(self, event_id: str) -> Event | None:
        """Get event by ID."""
        conn = self._get_conn()
        try:
            row = conn.execute("SELECT data FROM events WHERE id = ?", (event_id,)).fetchone()
            if row:
                return Event.from_dict(json.loads(row["data"]))
            return None
        finally:
            conn.close()

    def get_events(
        self,
        start_after: datetime | None = None,
        start_before: datetime | None = None,
        event_type: str | None = None,
    ) -> list[Event]:
        """Get events with optional filters."""
        conn = self._get_conn()
        try:
            query = "SELECT data FROM events WHERE 1=1"
            params: list[Any] = []

            if start_after:
                query += " AND start >= ?"
                params.append(start_after.isoformat())

            if start_before:
                query += " AND start <= ?"
                params.append(start_before.isoformat())

            if event_type:
                query += " AND event_type = ?"
                params.append(event_type)

            query += " ORDER BY start ASC"

            rows = conn.execute(query, params).fetchall()
            return [Event.from_dict(json.loads(row["data"])) for row in rows]
        finally:
            conn.close()

    def delete_event(self, event_id: str) -> bool:
        """Delete an event."""
        conn = self._get_conn()
        try:
            result = conn.execute("DELETE FROM events WHERE id = ?", (event_id,))
            conn.commit()
            return result.rowcount > 0
        finally:
            conn.close()

    # Pattern operations
    def save_pattern(self, pattern: Pattern) -> None:
        """Save or update a pattern."""
        conn = self._get_conn()
        try:
            now = datetime.now().isoformat()
            conn.execute(
                """
                INSERT OR REPLACE INTO patterns
                (id, data, pattern_type, confidence, active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    pattern.id,
                    json.dumps(pattern.to_dict()),
                    pattern.pattern_type,
                    pattern.confidence,
                    1 if pattern.active else 0,
                    pattern.first_observed.isoformat(),
                    now,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get_patterns(
        self,
        pattern_type: str | None = None,
        active_only: bool = True,
        min_confidence: float = 0.0,
    ) -> list[Pattern]:
        """Get patterns with optional filters."""
        conn = self._get_conn()
        try:
            query = "SELECT data FROM patterns WHERE confidence >= ?"
            params: list[Any] = [min_confidence]

            if active_only:
                query += " AND active = 1"

            if pattern_type:
                query += " AND pattern_type = ?"
                params.append(pattern_type)

            query += " ORDER BY confidence DESC"

            rows = conn.execute(query, params).fetchall()
            return [Pattern.from_dict(json.loads(row["data"])) for row in rows]
        finally:
            conn.close()

    # Memory operations
    def save_memory(self, memory: Memory) -> None:
        """Save or update a memory."""
        conn = self._get_conn()
        try:
            now = datetime.now().isoformat()
            conn.execute(
                """
                INSERT OR REPLACE INTO memories
                (id, data, memory_type, key, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    memory.id,
                    json.dumps(memory.to_dict()),
                    memory.memory_type,
                    memory.key,
                    memory.created_at.isoformat(),
                    now,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get_memory(self, key: str) -> Memory | None:
        """Get memory by key."""
        conn = self._get_conn()
        try:
            row = conn.execute("SELECT data FROM memories WHERE key = ?", (key,)).fetchone()
            if row:
                memory = Memory.from_dict(json.loads(row["data"]))
                # Update access tracking
                memory.last_accessed = datetime.now()
                memory.access_count += 1
                self.save_memory(memory)
                return memory
            return None
        finally:
            conn.close()

    def get_memories(
        self,
        memory_type: str | None = None,
        tags: list[str] | None = None,
    ) -> list[Memory]:
        """Get memories with optional filters."""
        conn = self._get_conn()
        try:
            query = "SELECT data FROM memories WHERE 1=1"
            params: list[Any] = []

            if memory_type:
                query += " AND memory_type = ?"
                params.append(memory_type)

            rows = conn.execute(query, params).fetchall()
            memories = [Memory.from_dict(json.loads(row["data"])) for row in rows]

            # Filter by tags if specified
            if tags:
                memories = [m for m in memories if any(t in m.tags for t in tags)]

            return memories
        finally:
            conn.close()

    def search_memories(self, query: str) -> list[Memory]:
        """Search memories by key or value content."""
        conn = self._get_conn()
        try:
            # Simple LIKE search - could be enhanced with FTS5
            rows = conn.execute(
                "SELECT data FROM memories WHERE key LIKE ? OR data LIKE ?",
                (f"%{query}%", f"%{query}%"),
            ).fetchall()
            return [Memory.from_dict(json.loads(row["data"])) for row in rows]
        finally:
            conn.close()

    # Context operations
    def save_context(self, context: Context) -> None:
        """Save a context snapshot."""
        conn = self._get_conn()
        try:
            conn.execute(
                "INSERT INTO context_log (data, timestamp) VALUES (?, ?)",
                (json.dumps(context.to_dict()), context.timestamp.isoformat()),
            )
            conn.commit()
        finally:
            conn.close()

    def get_latest_context(self) -> Context | None:
        """Get the most recent context."""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT data FROM context_log ORDER BY timestamp DESC LIMIT 1"
            ).fetchone()
            if row:
                return Context.from_dict(json.loads(row["data"]))
            return None
        finally:
            conn.close()

    def get_context_history(
        self,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[Context]:
        """Get context history."""
        conn = self._get_conn()
        try:
            query = "SELECT data FROM context_log"
            params: list[Any] = []

            if since:
                query += " WHERE timestamp >= ?"
                params.append(since.isoformat())

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()
            return [Context.from_dict(json.loads(row["data"])) for row in rows]
        finally:
            conn.close()

    # Activity logging
    def _log_activity(
        self,
        conn: sqlite3.Connection,
        event_type: str,
        entity_type: str | None = None,
        entity_id: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> None:
        """Log an activity event."""
        conn.execute(
            """
            INSERT INTO activity_log (event_type, entity_type, entity_id, data, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                event_type,
                entity_type,
                entity_id,
                json.dumps(data) if data else None,
                datetime.now().isoformat(),
            ),
        )

    def log_activity(
        self,
        event_type: str,
        entity_type: str | None = None,
        entity_id: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> None:
        """Public method to log activity."""
        conn = self._get_conn()
        try:
            self._log_activity(conn, event_type, entity_type, entity_id, data)
            conn.commit()
        finally:
            conn.close()

    def get_activity_log(
        self,
        event_type: str | None = None,
        entity_type: str | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get activity log entries."""
        conn = self._get_conn()
        try:
            query = "SELECT * FROM activity_log WHERE 1=1"
            params: list[Any] = []

            if event_type:
                query += " AND event_type = ?"
                params.append(event_type)

            if entity_type:
                query += " AND entity_type = ?"
                params.append(entity_type)

            if since:
                query += " AND timestamp >= ?"
                params.append(since.isoformat())

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()
            return [
                {
                    "id": row["id"],
                    "event_type": row["event_type"],
                    "entity_type": row["entity_type"],
                    "entity_id": row["entity_id"],
                    "data": json.loads(row["data"]) if row["data"] else None,
                    "timestamp": row["timestamp"],
                }
                for row in rows
            ]
        finally:
            conn.close()

    # Statistics
    def get_stats(self) -> dict[str, Any]:
        """Get database statistics."""
        conn = self._get_conn()
        try:
            stats = {}

            # Task stats
            row = conn.execute(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END) as done,
                    SUM(CASE WHEN status IN ('inbox', 'todo') THEN 1 ELSE 0 END) as active,
                    SUM(CASE WHEN due_date < datetime('now') AND status NOT IN ('done', 'cancelled') THEN 1 ELSE 0 END) as overdue
                FROM tasks
            """
            ).fetchone()
            stats["tasks"] = dict(row)

            # Reminder stats
            row = conn.execute(
                "SELECT COUNT(*) as total, SUM(CASE WHEN active = 1 THEN 1 ELSE 0 END) as active FROM reminders"
            ).fetchone()
            stats["reminders"] = dict(row)

            # Event stats
            row = conn.execute(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN start >= datetime('now') THEN 1 ELSE 0 END) as upcoming
                FROM events
            """
            ).fetchone()
            stats["events"] = dict(row)

            # Memory stats
            row = conn.execute("SELECT COUNT(*) as total FROM memories").fetchone()
            stats["memories"] = dict(row)

            # Pattern stats
            row = conn.execute(
                "SELECT COUNT(*) as total, AVG(confidence) as avg_confidence FROM patterns WHERE active = 1"
            ).fetchone()
            stats["patterns"] = dict(row)

            return stats
        finally:
            conn.close()
