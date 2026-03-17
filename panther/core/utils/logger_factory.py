"""Centralized logger factory for PANTHER framework.

Provides consistent logger creation with feature-aware log level management,
color terminal support, and optional statistics collection.

Design patterns:
    - **Factory Pattern**: Centralized logger creation with consistent configuration
    - **Singleton Pattern**: Global configuration state with thread-safe initialization
    - **Strategy Pattern**: Pluggable formatters and handlers based on capabilities
    - **Handler Chain Pattern**: Statistics collection via logging handler interception
"""

import contextlib
import logging
import sys
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

from .console_formatter import ConsoleFormatter
from .feature_registry import feature_registry
from .structured_formatter import StructuredJsonFormatter


class _FeatureInjectionFilter(logging.Filter):
    """Inject _panther_feature into every logging.LogRecord.

    Attached to individual loggers so that StructuredJsonFormatter
    can read the feature without needing a reference to the logger.
    """

    def __init__(self, feature: str):
        super().__init__()
        self._feature = feature

    def filter(self, record: logging.LogRecord) -> bool:
        record._panther_feature = self._feature  # type: ignore[attr-defined]
        return True


class LoggerFactory:
    """Centralized logger factory with feature-aware level management.

    Provides consistent logger creation with automatic feature detection,
    dynamic log level management, color terminal support, and optional
    statistics collection. Singleton pattern ensures unified configuration.

    Features:
        - Feature-aware logging with automatic level assignment by component
        - Dynamic runtime configuration updates
        - Multi-handler support (console + file with independent levels)
        - Optional statistics collection and export

    Example:
        >>> logger = LoggerFactory.get_logger(__name__)
        >>> LoggerFactory.update_feature_level("event_system", "DEBUG")
    """

    _DEBUG_FACTORY: bool = False
    _initialized = False
    _root_logger_configured = False
    _config: Dict[str, Any] = {}
    _handler_cache: Dict[str, logging.Handler] = {}
    _feature_levels: Dict[str, Any] = {}
    _verbose: bool = False

    # Logger names that get extra debug output when _DEBUG_FACTORY is True
    _DEBUG_LOGGERS: frozenset = frozenset(
        [
            "event_manager",
            "plugin_catalog",
            "plugin_discovery",
            "docker_cache_mixin",
            "docker_builder",
            "docker_registry",
            "EventManager",
        ]
    )

    # Feature to logger name mapping for intelligent routing
    FEATURE_MAPPINGS = {
        # Core Components
        "command_generation": [
            "command_processor",
            "command_builder",
            "command_utils",
            "command_summarizer",
        ],
        "template_rendering": ["template_renderer", "template_filters"],
        "docker_operations": ["docker_builder", "docker_operations", "docker_compose"],
        "config_processing": ["config_manager", "config_summarizer"],
        "event_system": ["event_emitter", "event_manager", "state_manager"],
        "file_operations": ["file_utils", "output_collector"],
        # Service Management
        "service_managers": ["service_manager", "services_interface"],
        "ivy_operations": ["panther_ivy", "ivy_client", "ivy_server"],
        "quic_services": [
            "picoquic",
            "aioquic",
            "lsquic",
            "mvfst",
            "quiche",
            "quinn",
            "quic_go",
        ],
        "plugin_loading": ["plugin_manager", "plugin_loader", "plugin_discovery"],
        "service_coordination": ["service_factory", "service_command_builder"],
        # Environment Management
        "network_environments": ["network_environment", "base_network_environment"],
        "execution_environment": [
            "execution_environment",
            "base_execution_environment",
        ],
        "docker_compose": ["docker_compose"],
        "shadow_ns": ["shadow_ns"],
        "localhost_container": ["localhost_single_container"],
        # Event System
        "event_emission": ["emitter"],
        "event_processing": ["observer", "event_manager"],
        "state_management": ["state_manager", "states"],
        "observer_operations": [
            "logger_observer",
            "metrics_observer",
            "storage_observer",
        ],
        # Protocol Operations
        "certificate_management": ["cert", "certificate", "tls"],
        "network_setup": ["network", "networking"],
        "port_management": ["port", "ports"],
        "protocol_communication": ["protocol", "quic", "http"],
        # Data and Metrics
        "metrics_collection": [
            "metrics_collector",
            "metrics_reporter",
            "resource_monitor",
        ],
        "data_storage": ["storage_handler", "event_store"],
        "result_processing": ["result_serialization"],
        "output_aggregation": ["output_aggregator", "output_collector"],
        # Development and Debugging
        "test_execution": ["test_case", "experiment_manager"],
        "experiment_workflow": ["experiment_manager", "workflow_tracker"],
        "error_handling": ["error_handler", "fast_fail"],
    }

    @classmethod
    def _ensure_early_initialization(cls):
        """Ensure LoggerFactory is initialized with sensible defaults if not already done."""
        if not cls._initialized:
            cls.initialize(
                {
                    "level": "ERROR",  # Default to ERROR level for early loggers
                    "format": "%(asctime)s [%(levelname)s] - %(module)s - %(message)s",
                    "enable_colors": True,
                }
            )

    @classmethod
    def initialize(cls, config: Dict[str, Any]) -> None:
        """Initialize the logger factory with configuration.

        Args:
            config: Logging configuration dictionary containing:
                - level: Logging level (DEBUG, INFO, etc.)
                - format: Log message format string
                - enable_colors: Whether to enable colored output
                - output_file: Optional log file path
                - feature_levels: Optional feature-specific logging levels
        """
        if cls._initialized:
            # If already initialized, update config if new one has more settings
            if config.get("enable_colors") is not None:
                cls._config.update(config)
            if config.get("feature_levels"):
                cls._feature_levels = cls._extract_feature_levels(
                    config.get("feature_levels")
                )
            return

        cls._config = config
        cls._feature_levels = cls._extract_feature_levels(config.get("feature_levels"))
        cls._setup_root_logger()
        cls._patch_logging_getlogger()
        cls._initialized = True

    @classmethod
    def _extract_feature_levels(cls, feature_config) -> Dict[str, str]:
        """Extract feature levels from configuration object."""
        if not feature_config:
            return {}

        feature_levels = {}

        # Debug logging to track feature levels extraction
        if cls._DEBUG_FACTORY:
            logging.debug(
                "_extract_feature_levels called with: %s", type(feature_config)
            )
            if hasattr(feature_config, "__dict__"):
                logging.debug(
                    "feature_config attributes: %s...",
                    list(feature_config.__dict__.keys())[:5],
                )
            elif isinstance(feature_config, dict):
                logging.debug(
                    "feature_config keys: %s...",
                    list(feature_config.keys())[:5],
                )

        # Handle different config formats (dict or dataclass)
        if hasattr(feature_config, "__dict__"):
            # Dataclass - extract attributes
            for attr_name in dir(feature_config):
                if not attr_name.startswith("_") and hasattr(feature_config, attr_name):
                    value = getattr(feature_config, attr_name)
                    if hasattr(value, "name"):  # Enum value
                        feature_levels[attr_name] = value.name
                    elif isinstance(value, str):
                        feature_levels[attr_name] = value
        elif isinstance(feature_config, dict):
            # Dictionary format
            for key, value in feature_config.items():
                if hasattr(value, "name"):  # Enum value
                    feature_levels[key] = value.name
                elif isinstance(value, str):
                    feature_levels[key] = value

        return feature_levels

    @classmethod
    def _setup_root_logger(cls) -> None:
        """Configure the root logger with our settings."""
        if cls._root_logger_configured:
            return

        root_logger = logging.getLogger()

        # Clear any existing handlers
        root_logger.handlers.clear()

        # Set root logger to DEBUG level to capture all messages
        # Individual handlers will filter based on their own levels
        root_logger.setLevel(logging.DEBUG)

        # Create formatter
        formatter = cls._create_formatter()

        # Console handler: use configured level
        console_level = getattr(logging, cls._config.get("level", "INFO").upper())
        console_handler = cls._get_or_create_handler(
            "console", logging.StreamHandler(sys.stdout)
        )
        console_handler.setLevel(console_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

        # Structured JSONL file handler (replaces old text file handler)
        structured_path = cls._config.get("output_file")
        if structured_path:
            structured_formatter = StructuredJsonFormatter()
            file_handler = cls._get_or_create_handler(
                "file", logging.FileHandler(structured_path, mode="a")
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(structured_formatter)
            root_logger.addHandler(file_handler)

        cls._root_logger_configured = True

    # Color mapping shared between console formatter creation paths
    _LOG_COLORS = {
        "TRACE": "blue",
        "DEBUG": "cyan",
        "INFO": "green",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "red,bg_white",
    }

    @classmethod
    def _create_formatter(cls) -> logging.Formatter:
        """Create a console formatter with optional color and context support.

        Returns a ``ConsoleFormatter`` that shows short timestamps, phase/service
        context from ``LogContext``, and abbreviated module names.  When
        ``enable_colors`` is true, the formatter delegates to
        ``colorlog.ColoredFormatter`` internally.
        """
        log_colors = (
            cls._LOG_COLORS if cls._config.get("enable_colors", False) else None
        )
        return ConsoleFormatter(log_colors=log_colors)

    @classmethod
    def _patch_logging_getlogger(cls) -> None:
        """Patch logging.getLogger to use our LoggerFactory for consistent formatting."""
        # Store the original getLogger function
        if not hasattr(logging, "_original_getLogger"):
            logging._original_getLogger = logging.getLogger

        def patched_getlogger(name=None):
            # For the root logger or None, use original
            if name is None or name == "root":
                return logging._original_getLogger(name)

            # For named loggers, always use our factory to ensure consistent formatting
            # This ensures ALL loggers get colored output if colors are enabled
            return cls.get_logger(name)

        # Replace the logging.getLogger function
        logging.getLogger = patched_getlogger

    @classmethod
    def _get_or_create_handler(
        cls, name: str, handler: logging.Handler
    ) -> logging.Handler:
        """Get or create a handler, avoiding duplicates."""
        if name not in cls._handler_cache:
            cls._handler_cache[name] = handler
        return cls._handler_cache[name]

    @classmethod
    def get_logger(cls, name: str, feature: Optional[str] = None) -> logging.Logger:
        """Get a logger with consistent configuration and feature-aware logging level.

        Args:
            name: Logger name (usually module or class name)
            feature: Optional feature name for feature-specific logging levels

        Returns:
            Configured logger instance
        """
        # Ensure factory is initialized with default config if needed
        cls._ensure_early_initialization()

        # Use original getLogger to avoid recursion
        if hasattr(logging, "_original_getLogger"):
            logger = logging._original_getLogger(name)
        else:
            logger = logging.getLogger(name)

        # If this logger already has handlers configured by us, return it
        if hasattr(logger, "_panther_configured"):
            # Update console handler level if feature-specific level is available
            if feature and feature in cls._feature_levels:
                feature_level = getattr(logging, cls._feature_levels[feature].upper())
                # Update only console handlers, keep file handlers at DEBUG
                for handler in logger.handlers:
                    if isinstance(handler, logging.StreamHandler) and not isinstance(
                        handler, logging.FileHandler
                    ):
                        handler.setLevel(feature_level)
            return logger

        # Determine console logging level (feature-specific or default)
        console_level = cls._get_effective_level(name, feature)

        # Set logger to DEBUG to capture all messages for file handler
        logger.setLevel(logging.DEBUG)

        # Clear existing handlers to avoid duplicates and set propagate to False
        logger.handlers.clear()
        logger.propagate = False

        # Create formatter like original code
        formatter = cls._create_formatter()

        # Add console handler with configured level
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(console_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # Add structured JSONL file handler if output_file is configured
        structured_path = cls._config.get("output_file")
        if structured_path:
            structured_formatter = StructuredJsonFormatter()
            file_handler = logging.FileHandler(structured_path, mode="a")
            file_handler.setLevel(
                logging.DEBUG
            )  # Always capture everything for post-mortem
            file_handler.setFormatter(structured_formatter)
            logger.addHandler(file_handler)

        # Store detected feature on the logger and inject it into every record
        # via a filter so StructuredJsonFormatter can access it
        detected = feature or cls._detect_feature_from_name(name)
        if detected:
            logger._panther_feature = detected
            logger.addFilter(_FeatureInjectionFilter(detected))

        # Mark this logger as configured by us
        logger._panther_configured = True

        return logger

    @classmethod
    def _get_effective_level(
        cls, logger_name: str, feature: Optional[str] = None
    ) -> int:
        """Get the effective logging level for a logger, considering feature mappings."""
        if cls._DEBUG_FACTORY:
            if logger_name in cls._DEBUG_LOGGERS:
                logging.debug(
                    "_get_effective_level for %s, feature=%s", logger_name, feature
                )
                logging.debug(
                    "Available feature_levels: %d features", len(cls._feature_levels)
                )

        # If explicit feature is provided and configured, use it
        if feature and feature in cls._feature_levels:
            level_name = cls._feature_levels[feature].upper()
            # Handle TRACE level specially
            return TRACE if level_name == "TRACE" else getattr(logging, level_name)
        # Try to auto-detect feature from logger name
        detected_feature = cls._detect_feature_from_name(logger_name)
        if detected_feature and detected_feature in cls._feature_levels:
            level_name = cls._feature_levels[detected_feature].upper()

            if cls._DEBUG_FACTORY and logger_name in cls._DEBUG_LOGGERS:
                logging.debug(
                    "%s -> %s -> %s", logger_name, detected_feature, level_name
                )

            # Handle TRACE level specially
            return TRACE if level_name == "TRACE" else getattr(logging, level_name)
        else:
            if cls._DEBUG_FACTORY and logger_name in cls._DEBUG_LOGGERS:
                logging.debug(
                    "%s -> %s (not in feature_levels)", logger_name, detected_feature
                )
                logging.debug(
                    "Available features: %s...", list(cls._feature_levels.keys())[:5]
                )

        # Fall back to default level
        level_name = cls._config.get("level", "INFO").upper()
        return TRACE if level_name == "TRACE" else getattr(logging, level_name)

    @classmethod
    def _detect_feature_from_name(cls, logger_name: str) -> Optional[str]:
        """Auto-detect feature from logger name using dynamic feature registry."""
        if detected := feature_registry.detect_feature(logger_name):
            return detected

        # Fallback to static mappings for backward compatibility
        for feature, patterns in cls.FEATURE_MAPPINGS.items():
            for pattern in patterns:
                if pattern.lower() in logger_name.lower():
                    return feature
        return None

    @classmethod
    def get_child_logger(
        cls, parent_name: str, child_name: str, feature: Optional[str] = None
    ) -> logging.Logger:
        """Get a child logger (e.g., for sub-components).

        Args:
            parent_name: Parent logger name
            child_name: Child component name
            feature: Optional feature name for feature-specific logging levels

        Returns:
            Child logger instance
        """
        full_name = f"{parent_name}.{child_name}"
        return cls.get_logger(full_name, feature)

    @classmethod
    def get_feature_logger(cls, name: str, feature: str) -> logging.Logger:
        """Get a logger explicitly configured for a specific feature.

        Args:
            name: Logger name
            feature: Feature name for feature-specific logging level

        Returns:
            Configured logger instance with feature-specific level
        """
        return cls.get_logger(name, feature)

    @classmethod
    def update_level(cls, level: str) -> None:
        """Update the logging level dynamically."""
        if cls._initialized:
            new_level = getattr(logging, level.upper())
            logging.getLogger().setLevel(new_level)
            cls._config["level"] = level

    @classmethod
    def update_feature_level(cls, feature: str, level: str) -> None:
        """Update the logging level for a specific feature."""
        if cls._initialized:
            cls._feature_levels[feature] = level.upper()

            # Update existing loggers that map to this feature
            for logger_name in logging.Logger.manager.loggerDict:
                if cls._detect_feature_from_name(logger_name) == feature:
                    logger = logging.getLogger(logger_name)
                    if hasattr(logger, "_panther_configured"):
                        level_name = level.upper()
                        # Handle TRACE level specially
                        if level_name == "TRACE":
                            new_level = TRACE
                        else:
                            new_level = getattr(logging, level_name)
                        logger.setLevel(new_level)
                        for handler in logger.handlers:
                            handler.setLevel(new_level)

    @classmethod
    def update_all_feature_levels(cls, feature_levels_dict: Dict[str, str]) -> None:
        """Update all feature levels at once and apply to existing loggers.

        This is useful when feature levels are loaded after some loggers have already been created.

        Args:
            feature_levels_dict: Dictionary mapping feature names to logging levels
        """
        if not cls._initialized:
            return

        if cls._DEBUG_FACTORY:
            logging.debug(
                "update_all_feature_levels called with %d features",
                len(feature_levels_dict),
            )
            logging.debug(
                "Existing loggers count: %d",
                len(logging.Logger.manager.loggerDict),
            )
            logging.debug(
                "Sample features being set: %s",
                list(feature_levels_dict.items())[:3],
            )
            logging.debug(
                "Current feature_levels before update: %s",
                (
                    list(cls._feature_levels.items())[:3]
                    if cls._feature_levels
                    else "empty"
                ),
            )

        # Update the internal feature levels dictionary
        cls._feature_levels.update(
            {k: v.upper() for k, v in feature_levels_dict.items()}
        )

        # Update all existing loggers that have been configured by us
        updated_count = 0
        skipped_count = 0
        for logger_name in logging.Logger.manager.loggerDict:
            logger = logging.getLogger(logger_name)
            if hasattr(logger, "_panther_configured"):
                # Detect the feature for this logger
                detected_feature = cls._detect_feature_from_name(logger_name)
                if detected_feature and detected_feature in cls._feature_levels:
                    level_name = cls._feature_levels[detected_feature]

                    # Handle TRACE level specially
                    if level_name == "TRACE":
                        new_level = TRACE
                    else:
                        new_level = getattr(logging, level_name, logging.INFO)

                    # Update only console handlers; structured file handlers stay at DEBUG
                    for handler in logger.handlers:
                        if isinstance(
                            handler, logging.StreamHandler
                        ) and not isinstance(handler, logging.FileHandler):
                            handler.setLevel(new_level)
                    updated_count += 1

                    if cls._DEBUG_FACTORY and logger_name in cls._DEBUG_LOGGERS:
                        logging.debug(
                            "Updated %s -> %s -> %s",
                            logger_name,
                            detected_feature,
                            level_name,
                        )
                else:
                    skipped_count += 1
            else:
                skipped_count += 1
                if cls._DEBUG_FACTORY and logger_name in cls._DEBUG_LOGGERS:
                    logging.debug("Skipped %s (no _panther_configured)", logger_name)

        if cls._DEBUG_FACTORY:
            logging.debug(
                "Updated %d loggers, skipped %d", updated_count, skipped_count
            )

    @classmethod
    def set_console_level(cls, level: int) -> None:
        """Set the console log level on all StreamHandlers across all configured loggers.

        Iterates the root logger and every logger in the manager dict,
        setting only ``StreamHandler`` (non-``FileHandler``) handlers to
        *level*.  ``FileHandler`` instances are left at DEBUG so that
        structured JSONL output continues to capture everything.

        This is the recommended way to honour ``--verbose`` / ``--debug``
        CLI flags *after* ``LoggerFactory.initialize()`` has already run.

        Args:
            level: The numeric logging level to apply to console handlers
                (e.g. ``logging.DEBUG``, ``logging.INFO``, or the custom
                ``TRACE`` constant which equals 5).
        """
        if not cls._initialized:
            return

        # Track verbose mode for components that adapt output (e.g. Docker build)
        cls._verbose = level <= logging.DEBUG

        def _apply_to_handlers(lgr: logging.Logger) -> None:
            for handler in lgr.handlers:
                if isinstance(handler, logging.StreamHandler) and not isinstance(
                    handler, logging.FileHandler
                ):
                    handler.setLevel(level)

        # Root logger
        _apply_to_handlers(logging.getLogger())

        # All named loggers that we have configured
        for logger_name in logging.Logger.manager.loggerDict:
            logger_obj = logging.Logger.manager.loggerDict[logger_name]
            if isinstance(logger_obj, logging.Logger):
                _apply_to_handlers(logger_obj)

    @classmethod
    def add_file_handler(cls, filepath: Path, level: Optional[str] = None) -> None:
        """Add a file handler dynamically."""
        if not cls._initialized:
            return

        formatter = cls._create_formatter()
        file_handler = logging.FileHandler(filepath, mode="a")
        file_handler.setFormatter(formatter)

        if level:
            file_handler.setLevel(getattr(logging, level.upper()))

        logging.getLogger().addHandler(file_handler)

    # Statistics Support
    @classmethod
    def enable_statistics(cls, config: Dict[str, Any]) -> None:
        """Enable log statistics collection with configuration.

        Args:
            config: Statistics configuration dictionary containing:
                - enabled: Whether to enable statistics collection
                - buffer_size: Size of message buffer
                - track_performance: Whether to track performance metrics
                - handler_type: Type of handler ('standard' or 'buffered')
        """
        # Avoid circular import by importing here
        from .log_statistics_collector import LogStatisticsCollector
        from .log_statistics_handler import create_statistics_handler

        if not config.get("enabled", False):
            cls.disable_statistics()
            return

        if hasattr(cls, "_statistics_collector"):
            # Statistics already enabled, update configuration if needed
            return

        # Create statistics collector
        buffer_size = config.get("buffer_size", 1000)
        track_performance = config.get("track_performance", True)
        cls._statistics_collector = LogStatisticsCollector(
            buffer_size=buffer_size, track_performance=track_performance
        )

        # Create statistics handler
        handler_type = config.get("handler_type", "standard")
        handler_config = {
            "level": logging.NOTSET,  # Capture all messages
        }

        if handler_type == "buffered":
            handler_config.update(
                {
                    "buffer_size": config.get("handler_buffer_size", 100),
                    "flush_interval": config.get("flush_interval", 1.0),
                }
            )

        cls._statistics_handler = create_statistics_handler(
            cls._statistics_collector, handler_type=handler_type, **handler_config
        )

        # Add statistics handler to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(cls._statistics_handler)

        cls._statistics_enabled = True

    @classmethod
    def disable_statistics(cls) -> None:
        """Disable log statistics collection."""
        if hasattr(cls, "_statistics_handler"):
            # Remove handler from root logger
            root_logger = logging.getLogger()
            if cls._statistics_handler in root_logger.handlers:
                root_logger.removeHandler(cls._statistics_handler)

            # Close and cleanup handler
            cls._statistics_handler.close()
            delattr(cls, "_statistics_handler")

        if hasattr(cls, "_statistics_collector"):
            delattr(cls, "_statistics_collector")

        cls._statistics_enabled = False

    @classmethod
    def get_log_statistics(cls) -> Optional[Dict]:
        """Get current log statistics if enabled.

        Returns:
            Dictionary containing current statistics or None if disabled
        """
        if hasattr(cls, "_statistics_collector"):
            return cls._statistics_collector.get_real_time_stats()
        return None

    @classmethod
    def generate_statistics_report(cls) -> Optional[Dict]:
        """Generate comprehensive statistics report.

        Returns:
            Detailed statistics report or None if disabled
        """
        if hasattr(cls, "_statistics_collector"):
            return cls._statistics_collector.generate_summary_report()
        return None

    @classmethod
    def export_statistics(cls, format: str = "json") -> Optional[str]:
        """Export statistics in specified format.

        Args:
            format: Export format ('json', 'csv', 'text')

        Returns:
            Formatted statistics string or None if disabled
        """
        if hasattr(cls, "_statistics_collector"):
            return cls._statistics_collector.export_statistics(format)
        return None

    @classmethod
    def reset_statistics(cls) -> None:
        """Reset all collected statistics."""
        if hasattr(cls, "_statistics_collector"):
            cls._statistics_collector.reset_statistics()
        if hasattr(cls, "_statistics_handler"):
            cls._statistics_handler.reset_stats()

    @classmethod
    def is_statistics_enabled(cls) -> bool:
        """Check if statistics collection is enabled."""
        return getattr(cls, "_statistics_enabled", False)

    @classmethod
    def get_statistics_handler_stats(cls) -> Optional[Dict]:
        """Get performance statistics for the statistics handler.

        Returns:
            Handler performance metrics or None if disabled
        """
        if hasattr(cls, "_statistics_handler"):
            return cls._statistics_handler.get_handler_stats()
        return None


# Add TRACE level support
TRACE = 5
logging.addLevelName(TRACE, "TRACE")


def trace(self, message, *args, **kwargs):
    """Log a message at TRACE level."""
    if self.isEnabledFor(TRACE):
        self._log(TRACE, message, args, **kwargs)


logging.Logger.trace = trace

# Initialize LoggerFactory with default colors as soon as the module is imported
# This ensures that any early components get colored output by default
LoggerFactory._ensure_early_initialization()
