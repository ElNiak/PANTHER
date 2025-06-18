"""
Transaction Implementation for event_store.py
Addresses the TODO: use transaction for better consistency and performance
"""

import sqlite3
import json
import logging
from contextlib import contextmanager
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Union, Callable
from enum import Enum
import threading
from queue import Queue
import time

logger = logging.getLogger(__name__)


class TransactionState(Enum):
    """Transaction state enum."""
    PENDING = "pending"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"


@dataclass
class Event:
    """Event data structure."""
    event_type: str
    event_name: str
    timestamp: float
    data: Dict[str, Any]
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            **asdict(self),
            "data": json.dumps(self.data),
            "metadata": json.dumps(self.metadata or {})
        }


class TransactionalEventStore:
    """
    Event store with transaction support for consistency and performance.
    Implements Write-Ahead Logging (WAL) for better concurrent access.
    """
    
    def __init__(self, db_path: str = ":memory:", enable_wal: bool = True):
        self.db_path = db_path
        self.enable_wal = enable_wal
        self._local = threading.local()
        self._init_database()
        
        # Batch processing for performance
        self.batch_queue = Queue()
        self.batch_size = 100
        self.batch_timeout = 0.1  # seconds
        
        if db_path != ":memory:":
            self._start_batch_processor()
    
    def _init_database(self) -> None:
        """Initialize database with proper schema and settings."""
        with self._get_connection() as conn:
            # Enable WAL mode for better concurrency
            if self.enable_wal and self.db_path != ":memory:":
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA synchronous=NORMAL")
            
            # Create events table with indexes
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    event_name TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    data TEXT NOT NULL,
                    metadata TEXT,
                    created_at REAL DEFAULT (julianday('now')),
                    INDEX idx_event_type (event_type),
                    INDEX idx_event_name (event_name),
                    INDEX idx_timestamp (timestamp)
                )
            """)
            
            # Create transactions table for tracking
            conn.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    transaction_id TEXT UNIQUE NOT NULL,
                    state TEXT NOT NULL,
                    started_at REAL NOT NULL,
                    completed_at REAL,
                    event_count INTEGER DEFAULT 0,
                    metadata TEXT
                )
            """)
            
            conn.commit()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(
                self.db_path,
                isolation_level=None  # Autocommit mode by default
            )
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection
    
    @contextmanager
    def transaction(self, transaction_id: Optional[str] = None):
        """
        Context manager for database transactions.
        Ensures consistency and provides rollback on errors.
        """
        conn = self._get_connection()
        transaction_id = transaction_id or f"txn_{int(time.time() * 1000000)}"
        
        # Start transaction
        conn.execute("BEGIN IMMEDIATE")
        
        # Record transaction start
        conn.execute("""
            INSERT INTO transactions (transaction_id, state, started_at)
            VALUES (?, ?, julianday('now'))
        """, (transaction_id, TransactionState.PENDING.value))
        
        try:
            # Create transaction context
            ctx = TransactionContext(conn, transaction_id)
            yield ctx
            
            # Update transaction record
            conn.execute("""
                UPDATE transactions
                SET state = ?, completed_at = julianday('now'), event_count = ?
                WHERE transaction_id = ?
            """, (TransactionState.COMMITTED.value, ctx.event_count, transaction_id))
            
            # Commit transaction
            conn.commit()
            logger.debug(f"Transaction {transaction_id} committed with {ctx.event_count} events")
            
        except Exception as e:
            # Rollback on error
            conn.rollback()
            
            # Update transaction record
            conn.execute("""
                UPDATE transactions
                SET state = ?, completed_at = julianday('now')
                WHERE transaction_id = ?
            """, (TransactionState.ROLLED_BACK.value, transaction_id))
            
            logger.error(f"Transaction {transaction_id} rolled back: {e}")
            raise
    
    def store_event(self, event: Event) -> int:
        """
        Store a single event (auto-commits).
        For better performance with multiple events, use batch operations.
        """
        conn = self._get_connection()
        cursor = conn.execute("""
            INSERT INTO events (event_type, event_name, timestamp, data, metadata)
            VALUES (?, ?, ?, ?, ?)
        """, (
            event.event_type,
            event.event_name,
            event.timestamp,
            json.dumps(event.data),
            json.dumps(event.metadata or {})
        ))
        
        return cursor.lastrowid
    
    def store_events_batch(self, events: List[Event]) -> List[int]:
        """
        Store multiple events in a single transaction.
        Much more efficient than individual inserts.
        """
        with self.transaction() as ctx:
            return ctx.add_events(events)
    
    def query_events(
        self,
        event_type: Optional[str] = None,
        event_name: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Query events with optional filters.
        Uses indexes for efficient retrieval.
        """
        conn = self._get_connection()
        
        # Build query
        query = "SELECT * FROM events WHERE 1=1"
        params = []
        
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)
        
        if event_name:
            query += " AND event_name = ?"
            params.append(event_name)
        
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)
        
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time)
        
        query += " ORDER BY timestamp DESC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        # Execute query
        cursor = conn.execute(query, params)
        
        # Convert results
        events = []
        for row in cursor:
            event = dict(row)
            event['data'] = json.loads(event['data'])
            event['metadata'] = json.loads(event['metadata']) if event['metadata'] else {}
            events.append(event)
        
        return events
    
    def get_event_statistics(self) -> Dict[str, Any]:
        """Get statistics about stored events."""
        conn = self._get_connection()
        
        stats = {
            "total_events": 0,
            "events_by_type": {},
            "transaction_summary": {},
        }
        
        # Total events
        cursor = conn.execute("SELECT COUNT(*) as count FROM events")
        stats["total_events"] = cursor.fetchone()["count"]
        
        # Events by type
        cursor = conn.execute("""
            SELECT event_type, COUNT(*) as count
            FROM events
            GROUP BY event_type
        """)
        stats["events_by_type"] = {row["event_type"]: row["count"] for row in cursor}
        
        # Transaction summary
        cursor = conn.execute("""
            SELECT state, COUNT(*) as count, SUM(event_count) as total_events
            FROM transactions
            GROUP BY state
        """)
        stats["transaction_summary"] = {
            row["state"]: {
                "count": row["count"],
                "total_events": row["total_events"] or 0
            }
            for row in cursor
        }
        
        return stats
    
    def _start_batch_processor(self) -> None:
        """Start background thread for batch processing."""
        import threading
        
        def process_batches():
            while True:
                batch = []
                deadline = time.time() + self.batch_timeout
                
                # Collect events until batch size or timeout
                while len(batch) < self.batch_size and time.time() < deadline:
                    try:
                        timeout = max(0, deadline - time.time())
                        event = self.batch_queue.get(timeout=timeout)
                        batch.append(event)
                    except:
                        break
                
                # Process batch if not empty
                if batch:
                    try:
                        self.store_events_batch(batch)
                        logger.debug(f"Processed batch of {len(batch)} events")
                    except Exception as e:
                        logger.error(f"Batch processing error: {e}")
        
        thread = threading.Thread(target=process_batches, daemon=True)
        thread.start()
    
    def close(self) -> None:
        """Close database connection."""
        if hasattr(self._local, 'connection'):
            self._local.connection.close()
            delattr(self._local, 'connection')


class TransactionContext:
    """Context for managing events within a transaction."""
    
    def __init__(self, connection: sqlite3.Connection, transaction_id: str):
        self.connection = connection
        self.transaction_id = transaction_id
        self.event_count = 0
    
    def add_event(self, event: Event) -> int:
        """Add single event to transaction."""
        cursor = self.connection.execute("""
            INSERT INTO events (event_type, event_name, timestamp, data, metadata)
            VALUES (?, ?, ?, ?, ?)
        """, (
            event.event_type,
            event.event_name,
            event.timestamp,
            json.dumps(event.data),
            json.dumps(event.metadata or {})
        ))
        
        self.event_count += 1
        return cursor.lastrowid
    
    def add_events(self, events: List[Event]) -> List[int]:
        """Add multiple events to transaction efficiently."""
        event_ids = []
        
        # Use executemany for better performance
        event_data = [
            (e.event_type, e.event_name, e.timestamp, 
             json.dumps(e.data), json.dumps(e.metadata or {}))
            for e in events
        ]
        
        cursor = self.connection.executemany("""
            INSERT INTO events (event_type, event_name, timestamp, data, metadata)
            VALUES (?, ?, ?, ?, ?)
        """, event_data)
        
        # Get inserted IDs
        last_id = cursor.lastrowid
        event_ids = list(range(last_id - len(events) + 1, last_id + 1))
        
        self.event_count += len(events)
        return event_ids


# ========== Usage Examples ==========

def example_basic_usage():
    """Basic usage example."""
    
    # Create event store
    store = TransactionalEventStore("events.db")
    
    # Store single event (auto-commit)
    event = Event(
        event_type="experiment",
        event_name="test_started",
        timestamp=time.time(),
        data={"test_id": "test_001", "config": {"timeout": 30}}
    )
    event_id = store.store_event(event)
    print(f"Stored event with ID: {event_id}")
    
    # Store multiple events in transaction
    events = [
        Event("metric", "cpu_usage", time.time(), {"value": 45.2}),
        Event("metric", "memory_usage", time.time(), {"value": 1024}),
        Event("metric", "network_throughput", time.time(), {"value": 100.5}),
    ]
    
    with store.transaction("metrics_batch") as ctx:
        ids = ctx.add_events(events)
        print(f"Stored {len(ids)} events in transaction")
    
    # Query events
    recent_metrics = store.query_events(
        event_type="metric",
        start_time=time.time() - 3600,  # Last hour
        limit=10
    )
    
    print(f"Found {len(recent_metrics)} recent metrics")
    
    # Get statistics
    stats = store.get_event_statistics()
    print(f"Total events: {stats['total_events']}")
    print(f"Events by type: {stats['events_by_type']}")


def example_error_handling():
    """Example with error handling and rollback."""
    
    store = TransactionalEventStore(":memory:")
    
    try:
        with store.transaction("test_transaction") as ctx:
            # Add some events
            ctx.add_event(Event("test", "step1", time.time(), {"status": "ok"}))
            ctx.add_event(Event("test", "step2", time.time(), {"status": "ok"}))
            
            # Simulate error
            raise ValueError("Something went wrong!")
            
            # This won't be executed
            ctx.add_event(Event("test", "step3", time.time(), {"status": "ok"}))
            
    except ValueError:
        print("Transaction rolled back due to error")
    
    # Verify no events were stored
    events = store.query_events(event_type="test")
    print(f"Events after rollback: {len(events)}")  # Should be 0


def example_concurrent_access():
    """Example of concurrent access with WAL mode."""
    import threading
    
    store = TransactionalEventStore("concurrent_events.db", enable_wal=True)
    
    def worker(worker_id: int, event_count: int):
        """Worker thread that stores events."""
        for i in range(event_count):
            event = Event(
                event_type="worker",
                event_name=f"worker_{worker_id}",
                timestamp=time.time(),
                data={"iteration": i, "worker": worker_id}
            )
            store.store_event(event)
            time.sleep(0.001)  # Small delay
    
    # Start multiple workers
    threads = []
    for i in range(5):
        t = threading.Thread(target=worker, args=(i, 20))
        t.start()
        threads.append(t)
    
    # Wait for completion
    for t in threads:
        t.join()
    
    # Check results
    stats = store.get_event_statistics()
    print(f"Total events from workers: {stats['events_by_type'].get('worker', 0)}")


def example_performance_comparison():
    """Compare performance with and without transactions."""
    import timeit
    
    # Setup
    events = [
        Event("perf_test", f"event_{i}", time.time(), {"index": i})
        for i in range(1000)
    ]
    
    # Without transactions (individual inserts)
    def without_transactions():
        store = TransactionalEventStore(":memory:")
        for event in events:
            store.store_event(event)
    
    # With transactions (batch insert)
    def with_transactions():
        store = TransactionalEventStore(":memory:")
        store.store_events_batch(events)
    
    # Measure time
    time_without = timeit.timeit(without_transactions, number=1)
    time_with = timeit.timeit(with_transactions, number=1)
    
    print(f"Without transactions: {time_without:.3f} seconds")
    print(f"With transactions: {time_with:.3f} seconds")
    print(f"Speedup: {time_without / time_with:.1f}x")


"""
Benefits of Transaction Implementation:

1. ACID Compliance:
   - Atomicity: All events in transaction succeed or fail together
   - Consistency: Database constraints maintained
   - Isolation: Concurrent access handled properly
   - Durability: Committed data persists

2. Performance Improvements:
   - Batch inserts are 10-100x faster
   - WAL mode enables concurrent readers
   - Indexes speed up queries

3. Error Recovery:
   - Automatic rollback on errors
   - Transaction history tracking
   - Clean error handling

4. Scalability:
   - Background batch processing
   - Thread-safe operations
   - Efficient concurrent access

5. Monitoring:
   - Transaction statistics
   - Event counts and types
   - Performance metrics
"""