"""
Observer Interface Module

This module defines the core interface for all observer implementations in the PANTHER framework.
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Optional

from panther.core.events.base.event_base import BaseEvent

# Try to import ColoredFormatter, fallback gracefully if not available
try:
    from colorlog import ColoredFormatter
except ImportError:
    ColoredFormatter = None


class IObserver(ABC):
    """
    Enhanced observer interface with interest checking and prioritization.
    This extends the original IObserver interface with additional capabilities.
    """

    def __init__(self):
        self.processed_events_uuids: List[str] = []

    @abstractmethod
    def on_event(self, event: BaseEvent):
        """
        Handle an event.

        Args:
            event: The event to handle
        """
        pass

    def is_interested(self, event_type: str) -> bool:
        """
        Check if this observer is interested in an event type.
        Default implementation is interested in all events.

        Args:
            event_type: Type of event to check interest for

        Returns:
            bool: True if the observer is interested in events of this type
        """
        return True

    def get_priority(self) -> int:
        """
        Get the priority for this observer.
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
        """
        Set up logging for an observer.

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
        """Add a lazy file handler that only creates files when content is written."""
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
