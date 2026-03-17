"""Observer Interface Module - Core observer contract for PANTHER.

This module defines the base ``IObserver`` abstract class that all observer
implementations must extend. It provides the foundational contract for event
processing with built-in deduplication protection, interest-based filtering,
and priority-based notification ordering.

Key contracts:
    - ``on_event(event)`` -- abstract, must be implemented by all subclasses
    - ``is_interested(event_type)`` -- override to filter events (default: all)
    - ``get_priority()`` -- override to control notification order (default: 0)

Example:
    Create a custom observer that tracks test events::

        from panther.core.observer.base.observer_interface import IObserver
        from panther.core.events.base.event_base import BaseEvent

        class TestTracker(IObserver):
            def __init__(self):
                super().__init__()
                self.event_count = 0

            def is_interested(self, event_type: str) -> bool:
                return event_type.startswith("test.")

            def on_event(self, event: BaseEvent):
                if event.id in self.processed_events_uuids:
                    return  # Skip duplicate
                self.processed_events_uuids.add(event.id)
                self.event_count += 1

See Also:
    `panther.core.observer.base.typed_observer_interface.ITypedObserver`
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional

from panther.core.events.base.event_base import BaseEvent


class IObserver(ABC):
    """Core interface for all observer implementations in PANTHER.

    Defines the contract for event processing with deduplication protection
    and interest-based filtering. All observers must implement ``on_event()``
    and may optionally override ``is_interested()`` and ``get_priority()``.

    Attributes:
        processed_events_uuids: Set of UUIDs for events already processed
            by this observer, used for O(1) deduplication lookup.

    Example:
        Minimal observer implementation::

            class MinimalObserver(IObserver):
                def on_event(self, event: BaseEvent):
                    if event.id in self.processed_events_uuids:
                        return
                    # process event ...
                    self.processed_events_uuids.add(event.id)

    See Also:
        `ITypedObserver` for automatic event routing by type.
    """

    def __init__(self):
        """Initialize IObserver."""
        self.processed_events_uuids: set = set()  # O(1) dedup lookup

    @abstractmethod
    def on_event(self, event: BaseEvent):
        """Handle an event.

        Args:
            event: The event to handle
        """
        pass

    def is_interested(self, event_type: str) -> bool:
        """Check if this observer is interested in an event type.

        Default implementation is interested in all events.

        Args:
            event_type: Type of event to check interest for

        Returns:
            bool: True if the observer is interested in events of this type
        """
        return True

    def _get_event_type_safely(self, event: BaseEvent) -> str:
        """Safely get the event type from an event object."""
        if hasattr(event, "get_type") and callable(getattr(event, "get_type")):
            return event.get_type()
        elif hasattr(event, "name"):
            return event.name
        else:
            return str(event.__class__.__name__)

    def get_priority(self) -> int:
        """Get the priority for this observer.

        Higher values mean higher priority.

        Returns:
            int: Observer priority (default: 0)
        """
        return 0

    def _setup_logging(
        self,
        logger_name: str,
        log_level: int,
        enable_colors: bool = True,
        output_file: Optional[str] = None,
        structured_output: bool = False,
    ):
        """Set up logging for an observer.

        Args:
            logger_name: Name for the logger
            log_level: Logging level (e.g., logging.DEBUG)
            enable_colors: Whether to use colored output
            output_file: Path to optional log file
            structured_output: Whether to output in structured format

        Returns:
            logging.Logger: Configured logger instance
        """
        # Use LoggerFactory for consistent logging
        from panther.core.utils.logger_factory import LoggerFactory

        logger = LoggerFactory.get_logger(logger_name)

        # If a specific log level is requested, update it
        if log_level != logger.level:
            logger.setLevel(log_level)

        # Store output file path for lazy file handler creation
        # Only create the file when there's actual content to write
        if output_file:
            self._pending_log_file = output_file
            # Add a custom handler that creates file only when needed
            self._add_lazy_file_handler(logger, output_file)

        return logger

    def _add_lazy_file_handler(self, logger, output_file):
        """Add a lazy file handler that only creates the file on first write.

        Args:
            logger: Logger instance to attach the handler to.
            output_file: Path to the output log file.
        """
        import logging
        from pathlib import Path

        class LazyFileHandler(logging.Handler):
            """File handler that only creates the file when first log is written."""

            def __init__(self, filepath, mode="a"):
                super().__init__()
                self.filepath = Path(filepath)
                self.mode = mode
                self._file_handler = None

            def emit(self, record):
                # Create the actual file handler only when first log is emitted
                if self._file_handler is None:
                    # Ensure directory exists
                    self.filepath.parent.mkdir(parents=True, exist_ok=True)
                    self._file_handler = logging.FileHandler(
                        self.filepath, mode=self.mode
                    )
                    # Use LoggerFactory formatter for consistency
                    from panther.core.utils.logger_factory import LoggerFactory

                    self._file_handler.setFormatter(LoggerFactory._create_formatter())

                # Delegate to the actual file handler
                self._file_handler.emit(record)

            def close(self):
                if self._file_handler:
                    self._file_handler.close()
                super().close()

        # Add the lazy handler to the logger
        lazy_handler = LazyFileHandler(output_file)
        logger.addHandler(lazy_handler)
