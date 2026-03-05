"""Storage Module - Event Persistence for PANTHER.

Provides persistent SQLite-backed event storage with batch operations,
automatic retention-based cleanup, and historical analysis capability.

<!> Not Finished: This module is under active development. The current implementation

Architecture::

    EventStore
        │
        ├── SQLite Backend      ── persistent event storage
        ├── Batch Processing    ── configurable max_batch_size
        ├── Thread-Safe Queue   ── RLock-protected operations
        └── Auto-Cleanup        ── retention_days-based pruning

Key Features:
    - **Repository Pattern**: persistent data access layer for events
    - **Batch Writes**: configurable batch size for performance
    - **Thread Safety**: RLock-protected queue operations
    - **Retention Policy**: automatic cleanup of old events

Example::

    from panther.core.storage import EventStore

    store = EventStore(db_path="events.db", retention_days=30)
    store.store(event)
    events = store.query(entity_type="test", limit=100)

See Also:
    :mod:`panther.core.events` -- event types stored by EventStore
    :mod:`panther.core.observer` -- observers that trigger event storage
"""

from .event_store import EventStore

__all__ = ["EventStore"]
