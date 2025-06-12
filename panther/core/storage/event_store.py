import sqlite3
import json
import threading
import logging
from datetime import datetime, timedelta
from typing import Any

from panther.core.events import BaseEvent as Event


class EventStore:
    """
    Stores events for historical analysis and debugging.

    This class provides persistent storage of events using SQLite,
    allowing for historical analysis, debugging, and audit trails.
    """

    def __init__(self, db_path: str = None, retention_days: int = 7, max_batch_size: int = 100):
        """
        Initialize a new EventStore.

        Args:
            db_path: Path to SQLite database file, or ":memory:" for in-memory
            retention_days: Number of days to keep events before automatic cleanup
            max_batch_size: Maximum number of events to store in a batch
        """
        self.db_path = db_path or ":memory:"
        self.retention_days = retention_days
        self.max_batch_size = max_batch_size
        self.logger = logging.getLogger("EventStore")

        # For batch operations
        self.batch = []
        self._lock = threading.RLock()

        # Connect to database
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        self._setup_db()

    def _setup_db(self):
        """Set up the database schema."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            event_type TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            data TEXT
        )
        """
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_event_type ON events(event_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON events(timestamp)")
        self.conn.commit()
        self.logger.info(f"Initialized EventStore with database {self.db_path}")

    def store_event(self, event: Event) -> bool:
        """
        Store a single event in the database.

        Args:
            event: The event to store

        Returns:
            bool: True if the event was stored successfully
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO events VALUES (?, ?, ?, ?)",
                (
                    str(event.id),
                    event.get_type(),
                    event.timestamp.isoformat(),
                    json.dumps(event.data),
                ),
            )
            self.conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"Failed to store event {event.get_type()}: {e}")
            return False

    def add_to_batch(self, event: Event) -> bool:
        """
        Add an event to the batch for later storage.

        Args:
            event: The event to add to batch

        Returns:
            bool: True if batch was stored (because it reached max size)
        """
        with self._lock:
            self.batch.append(
                (
                    str(event.id),
                    event.get_type(),
                    event.timestamp.isoformat(),
                    json.dumps(event.data),
                )
            )

            if len(self.batch) >= self.max_batch_size:
                return self.store_batch()
            return False

    def store_batch(self) -> bool:
        """
        Store all batched events to the database.

        Returns:
            bool: True if the batch was stored successfully
        """
        with self._lock:
            if not self.batch:
                return True

            try:
                cursor = self.conn.cursor()
                cursor.executemany("INSERT INTO events VALUES (?, ?, ?, ?)", self.batch)
                self.conn.commit()
                self.batch.clear()
                return True
            except Exception as e:
                self.logger.error(f"Failed to store batch of {len(self.batch)} events: {e}")
                return False

    def get_events(
        self,
        event_type: str = None,
        start_time: datetime = None,
        end_time: datetime = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Query events with filters.
        # TODO use transaction for better consistency and performance

        Args:
            event_type: Type of events to retrieve, or None for all types
            start_time: Earliest timestamp to include, or None for no lower bound
            end_time: Latest timestamp to include, or None for no upper bound
            limit: Maximum number of events to return

        Returns:
            list: List of event dictionaries
        """
        query = "SELECT * FROM events WHERE 1=1"
        params = []

        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)

        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time.isoformat())

        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time.isoformat())

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        try:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()

            # Convert rows to dictionaries
            events = []
            for row in rows:
                event_dict = dict(row)
                # Parse JSON data
                if event_dict["data"]:
                    event_dict["data"] = json.loads(event_dict["data"])
                events.append(event_dict)

            return events
        except Exception as e:
            self.logger.error(f"Failed to query events: {e}")
            return []

    def get_event_types(self) -> list[str]:
        """
        Get all unique event types in the store.

        Returns:
            list: List of unique event types
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT DISTINCT event_type FROM events ORDER BY event_type")
            return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"Failed to get event types: {e}")
            return []

    def get_event_counts_by_type(self) -> dict[str, int]:
        """
        Get count of events by type.

        Returns:
            dict: Mapping of event type to count
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT event_type, COUNT(*) as count FROM events GROUP BY event_type")
            return {row[0]: row[1] for row in cursor.fetchall()}
        except Exception as e:
            self.logger.error(f"Failed to get event counts: {e}")
            return {}

    def cleanup_old_events(self) -> int:
        """
        Remove events older than retention period.

        Returns:
            int: Number of events removed
        """
        cutoff = (datetime.now() - timedelta(days=self.retention_days)).isoformat()
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM events WHERE timestamp < ?", (cutoff,))
            self.conn.commit()
            deleted = cursor.rowcount
            self.logger.info(f"Cleaned up {deleted} old events")
            return deleted
        except Exception as e:
            self.logger.error(f"Failed to cleanup old events: {e}")
            return 0

    def close(self):
        """Close the database connection."""
        self.store_batch()  # Ensure any pending batch is stored
        self.conn.close()
        self.logger.info("EventStore closed")
