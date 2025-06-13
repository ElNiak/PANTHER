"""
Logging Mixin

This module provides a reusable logging mixin for classes across PANTHER.
"""

import logging


class LoggerMixin:
    """
    Mixin class that provides consistent logging functionality.

    This mixin automatically creates a logger based on the class name
    and provides common logging patterns used throughout PANTHER.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._logger: logging.Logger | None = None

    @property
    def logger(self) -> logging.Logger:
        """
        Get or create a logger for this class.

        Returns:
            logging.Logger: Logger instance named after the class
        """
        if self._logger is None:
            self._logger = logging.getLogger(self.__class__.__name__)
        return self._logger

    def log_initialization(self, entity_name: str, additional_info: str = "") -> None:
        """
        Log initialization of an entity with consistent format.

        Args:
            entity_name: Name of the entity being initialized
            additional_info: Additional information to log
        """
        message = f"Initializing {self.__class__.__name__} for '{entity_name}'"
        if additional_info:
            message += f" - {additional_info}"
        self.logger.debug(message)

    def log_config_loaded(self, config: dict, entity_name: str = "") -> None:
        """
        Log configuration loading with consistent format.

        Args:
            config: Configuration dictionary that was loaded
            entity_name: Optional entity name for context
        """
        entity_part = f" for '{entity_name}'" if entity_name else ""
        self.logger.debug(
            f"Loaded {self.__class__.__name__} configuration{entity_part}: %s", config
        )

    def log_operation_start(self, operation: str, **kwargs) -> None:
        """
        Log the start of an operation.

        Args:
            operation: Name of the operation starting
            **kwargs: Additional context to include in the log
        """
        context = f" with {kwargs}" if kwargs else ""
        self.logger.info(f"Starting {operation}{context}")

    def log_operation_complete(self, operation: str, **kwargs) -> None:
        """
        Log the completion of an operation.

        Args:
            operation: Name of the operation completed
            **kwargs: Additional context to include in the log
        """
        context = f" with {kwargs}" if kwargs else ""
        self.logger.info(f"Completed {operation}{context}")

    def log_operation_failed(self, operation: str, error: Exception, **kwargs) -> None:
        """
        Log the failure of an operation.

        Args:
            operation: Name of the operation that failed
            error: Exception that caused the failure
            **kwargs: Additional context to include in the log
        """
        context = f" with {kwargs}" if kwargs else ""
        self.logger.error(f"Failed {operation}{context}: {error}", exc_info=True)
