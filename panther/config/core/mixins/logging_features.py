"""Logging features mixin for ConfigurationManager."""

from typing import Dict, Optional

from panther.core.utils.logging_mixin import LoggerMixin


class LoggingFeaturesMixin(LoggerMixin):
    """Handles feature-specific log levels."""

    # Known feature names for validation
    KNOWN_FEATURES = {
        "docker_build",
        "service_start",
        "environment_setup",
        "test_execution",
        "metrics_collection",
        "event_processing",
        "plugin_loading",
        "configuration",
        "validation",
        "command_generation",
        "output_collection",
        "error_handling",
        "fast_fail",
        "observer",
        "state_management",
    }

    def _process_feature_log_levels(self, config: "LoggingConfig") -> None:
        """Process and validate feature log levels.

        Args:
            config: Logging configuration with feature levels
        """
        if not hasattr(config, "feature_levels") or not config.feature_levels:
            return

        self.logger.debug("Processing feature log levels")

        # Get feature levels as dict
        if hasattr(config.feature_levels, "to_dict"):
            feature_levels = config.feature_levels.to_dict()
        else:
            feature_levels = dict(config.feature_levels)

        # Validate and apply each feature level
        for feature, level in feature_levels.items():
            if level:  # Skip None values
                # Validate feature name
                if not self._validate_feature_name(feature):
                    self.logger.warning(f"Unknown feature name: {feature}")

                # Convert and validate level
                try:
                    from ..models.global_config import LoggingLevel

                    # Ensure level is uppercase string
                    level_str = str(level).upper()
                    # Validate by converting to enum
                    LoggingLevel(level_str)

                    # Apply feature level
                    self._set_feature_level(feature, level_str)
                except ValueError as e:
                    self.logger.error(
                        f"Invalid log level for feature '{feature}': {level}"
                    )

    def _validate_feature_names(self, features: Dict[str, str]) -> bool:
        """Validate all feature names.

        Args:
            features: Dictionary of feature names to log levels

        Returns:
            True if all feature names are valid
        """
        invalid_features = []

        for feature in features:
            if not self._validate_feature_name(feature):
                invalid_features.append(feature)

        if invalid_features:
            self.logger.warning(f"Unknown features: {invalid_features}")
            # Still return True to allow custom features
            return True

        return True

    def _validate_feature_name(self, feature: str) -> bool:
        """Validate a single feature name.

        Args:
            feature: Feature name to validate

        Returns:
            True if feature name is known
        """
        return feature in self.KNOWN_FEATURES

    def get_feature_log_level(self, feature: str) -> Optional[str]:
        """Get log level for a specific feature.

        Args:
            feature: Feature name

        Returns:
            Log level string or None
        """
        # Check if we have a logger factory with feature levels
        if hasattr(self, "logger_factory"):
            return self.logger_factory.get_feature_level(feature)

        # Fallback to checking config
        if hasattr(self, "current_global_config"):
            config = self.current_global_config
            if hasattr(config, "logging") and hasattr(config.logging, "feature_levels"):
                feature_levels = config.logging.feature_levels
                return getattr(feature_levels, feature, None)

        return None

    def set_feature_log_level(self, feature: str, level: str) -> None:
        """Set log level for a specific feature.

        Args:
            feature: Feature name
            level: Log level string
        """
        # Validate level
        from ..models.global_config import LoggingLevel

        try:
            LoggingLevel(level.upper())
        except ValueError:
            raise ValueError(f"Invalid log level: {level}")

        # Warn if unknown feature
        if not self._validate_feature_name(feature):
            self.logger.warning(f"Setting level for unknown feature: {feature}")

        # Apply the level
        self._set_feature_level(feature, level.upper())

        # Update config if available
        if hasattr(self, "current_global_config"):
            config = self.current_global_config
            if hasattr(config, "logging") and hasattr(config.logging, "feature_levels"):
                setattr(config.logging.feature_levels, feature, level.upper())

    def get_all_feature_levels(self) -> Dict[str, str]:
        """Get all configured feature log levels.

        Returns:
            Dictionary of feature to log level mappings
        """
        feature_levels = {}

        # Get from current config
        if hasattr(self, "current_global_config"):
            config = self.current_global_config
            if hasattr(config, "logging") and hasattr(config.logging, "feature_levels"):
                if hasattr(config.logging.feature_levels, "to_dict"):
                    feature_levels = config.logging.feature_levels.to_dict()
                else:
                    # Extract attributes
                    for feature in self.KNOWN_FEATURES:
                        level = getattr(config.logging.feature_levels, feature, None)
                        if level:
                            feature_levels[feature] = level

        return feature_levels

    def _set_feature_level(self, feature: str, level: str) -> None:
        """Internal method to set feature level.

        Args:
            feature: Feature name
            level: Log level string
        """
        # Apply to logger factory if available
        if hasattr(self, "logger_factory"):
            self.logger_factory.set_feature_level(feature, level)

        # Apply to any feature-specific loggers
        feature_logger_name = f"panther.{feature}"
        try:
            import logging

            logger = logging.getLogger(feature_logger_name)
            logger.setLevel(getattr(logging, level))
            self.logger.debug(f"Set {feature} log level to {level}")
        except Exception as e:
            self.logger.warning(f"Failed to set logger level for {feature}: {e}")

    def register_feature(self, feature: str) -> None:
        """Register a new feature for log level management.

        Args:
            feature: Feature name to register
        """
        self.KNOWN_FEATURES.add(feature)
        self.logger.debug(f"Registered new feature: {feature}")

    def apply_global_feature_filter(self, min_level: str) -> None:
        """Apply a minimum log level to all features.

        Args:
            min_level: Minimum log level to enforce
        """
        from ..models.global_config import LoggingLevel

        # Validate level
        try:
            min_level_enum = LoggingLevel(min_level.upper())
        except ValueError:
            raise ValueError(f"Invalid log level: {min_level}")

        # Apply to all features
        feature_levels = self.get_all_feature_levels()
        for feature, current_level in feature_levels.items():
            try:
                current_enum = LoggingLevel(current_level.upper())
                # If current level is less severe than minimum, update it
                if self._compare_log_levels(current_enum, min_level_enum) < 0:
                    self.set_feature_log_level(feature, min_level.upper())
            except ValueError:
                pass

    def _compare_log_levels(
        self, level1: "LoggingLevel", level2: "LoggingLevel"
    ) -> int:
        """Compare two log levels.

        Args:
            level1: First log level
            level2: Second log level

        Returns:
            -1 if level1 < level2, 0 if equal, 1 if level1 > level2
        """
        # Define level ordering (lower index = less severe)
        level_order = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        idx1 = level_order.index(level1.value)
        idx2 = level_order.index(level2.value)

        if idx1 < idx2:
            return -1
        elif idx1 > idx2:
            return 1
        else:
            return 0
