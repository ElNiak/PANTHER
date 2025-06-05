"""
Observer Interface Module

This module defines the core interface for all observer implementations in the PANTHER framework.
"""

from abc import ABC, abstractmethod
import logging

# Import from new location - will be created later
from panther.core.observer.core.core_events import Event

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
        self.processed_events_uuids: list[str] = []

    @abstractmethod
    def on_event(self, event: Event):
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
        output_file: str | None = None,
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
        logger = logging.getLogger(logger_name)
        logger.setLevel(log_level)

        # Clear any existing handlers to avoid duplicates
        logger.handlers.clear()

        # Configure logger to not propagate to parent handlers to avoid duplicate logs
        logger.propagate = False

        # Console handler
        console_handler = logging.StreamHandler()

        if structured_output:
            console_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
        elif enable_colors and ColoredFormatter:
            # Use ColoredFormatter for colored output if available
            console_formatter = ColoredFormatter(
                fmt="%(log_color)s%(asctime)s %(levelname)s %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
                log_colors={
                    "DEBUG": "white",
                    "INFO": "green",
                    "WARNING": "yellow",
                    "ERROR": "bold_red",
                    "CRITICAL": "bold_red,bg_white",
                },
                reset=True,
            )
        else:
            # Standard formatter for non-colored output
            console_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        # File handler if specified
        if output_file:
            file_handler = logging.FileHandler(output_file)
            file_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)

        return logger
