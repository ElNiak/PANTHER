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

        # LoggerFactory already handles handlers and formatting, so we don't need to add more
        # If output_file is specified, add a file handler
        if output_file:
            from pathlib import Path

            LoggerFactory.add_file_handler(Path(output_file), level=None)

        return logger
