"""Feature-aware logging utilities for PANTHER components.

This module provides the ``get_feature_logger()`` convenience function
for obtaining feature-scoped loggers.
"""

from .logger_factory import LoggerFactory


def get_feature_logger(name: str, feature: str):
    """Convenience function to get a feature-aware logger.

    Args:
        name: Logger name
        feature: Feature name

    Returns:
        Configured logger instance
    """
    return LoggerFactory.get_feature_logger(name, feature)
