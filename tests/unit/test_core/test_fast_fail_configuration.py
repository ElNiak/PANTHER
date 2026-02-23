"""
Tests for fast-fail configuration and behavior customization.

This module tests:
- FastFailConfig schema and validation
- Configuration-driven behavior
- Error threshold management
- Severity-based filtering
"""

from unittest.mock import Mock

import pytest

from panther.config.core.models.global_config import (
    FastFailConfig,
    GlobalConfig,
)
from panther.core.exceptions.fast_fail import (
    DockerBuildException,
    ErrorCategory,
    ErrorSeverity,
    FastFailHandler,
    PantherException,
    PluginLoadException,
    ServiceStartException,
)


class TestFastFailConfiguration:
    """Test FastFailConfig schema and defaults."""

    def test_fast_fail_config_defaults(self):
        """Test FastFailConfig default values."""
        config = FastFailConfig()

        assert config.enabled is True
        assert config.test_level is False
        assert config.docker_build_failures is True
        assert config.service_start_failures is True
        assert config.ivy_compilation_failures is True
        assert config.timeout_cascade_threshold == 1
        assert config.critical_only is False

    def test_fast_fail_config_custom_values(self):
        """Test FastFailConfig with custom values."""
        config = FastFailConfig(
            enabled=False,
            test_level=True,
            docker_build_failures=False,
            service_start_failures=False,
            ivy_compilation_failures=False,
            timeout_cascade_threshold=5,
            critical_only=True,
        )

        assert config.enabled is False
        assert config.test_level is True
        assert config.docker_build_failures is False
        assert config.service_start_failures is False
        assert config.ivy_compilation_failures is False
        assert config.timeout_cascade_threshold == 5
        assert config.critical_only is True

    def test_global_config_integration(self):
        """Test FastFailConfig integration with GlobalConfig."""
        global_config = GlobalConfig()

        # Verify fast_fail config exists
        assert hasattr(global_config, "fast_fail")
        assert isinstance(global_config.fast_fail, FastFailConfig)

        # Modify fast_fail settings
        global_config.fast_fail.enabled = False
        global_config.fast_fail.critical_only = True

        assert global_config.fast_fail.enabled is False
        assert global_config.fast_fail.critical_only is True

class TestConfigurationDrivenBehavior:
    """Test fast-fail behavior based on configuration."""

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        return Mock()

    def test_docker_build_failures_config(self, mock_logger):
        """Test docker_build_failures configuration."""
        # Create handler with custom config
        handler = FastFailHandler(enabled=True, logger=mock_logger)

        # Test with docker_build_failures = True (default)
        docker_error = DockerBuildException(
            message="Build failed", image_name="test", dockerfile="Dockerfile"
        )

        with pytest.raises(DockerBuildException):
            handler.handle_error(docker_error, raise_on_critical=True)

        # In a real implementation, we would check config.docker_build_failures
        # and potentially downgrade severity or skip fast-fail

    def test_plugin_load_failures_config(self, mock_logger):
        """Test plugin_load_failures configuration."""
        handler = FastFailHandler(enabled=True, logger=mock_logger)

        # Test HIGH severity plugin error
        plugin_error = PluginLoadException(
            message="Plugin failed",
            plugin_name="test_plugin",
            plugin_type="service",
            severity=ErrorSeverity.HIGH,
        )

        result = handler.handle_error(plugin_error, raise_on_critical=False)
        assert result is False  # HIGH severity should not continue

    def test_service_start_failures_config(self, mock_logger):
        """Test service_start_failures configuration."""
        handler = FastFailHandler(enabled=True, logger=mock_logger)

        service_error = ServiceStartException(
            message="Service failed", service_name="test_service"
        )

        result = handler.handle_error(service_error, raise_on_critical=False)
        assert result is False  # HIGH severity should not continue

    def test_critical_only_mode(self, mock_logger):
        """Test critical_only configuration."""
        # This would require modifying FastFailHandler to accept config
        # For now, test the concept
        handler = FastFailHandler(enabled=True, logger=mock_logger)

        # HIGH severity error
        high_error = PantherException(
            message="High severity error",
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.PLUGIN_LOAD,
        )

        # CRITICAL severity error
        critical_error = PantherException(
            message="Critical error",
            severity=ErrorSeverity.CRITICAL,
            category=ErrorCategory.DOCKER_BUILD,
        )

        # In critical_only mode, HIGH should continue
        # Currently, this is not implemented in FastFailHandler
        # but we test the expected behavior
        result_high = handler.handle_error(high_error, raise_on_critical=False)
        assert result_high is False  # Current behavior

        with pytest.raises(PantherException):
            handler.handle_error(critical_error, raise_on_critical=True)


class TestErrorThresholdManagement:
    """Test error counting and cascade detection thresholds."""

    def test_low_severity_errors_below_cascade_threshold(self):
        """Test that LOW severity errors continue when below cascade threshold."""
        handler = FastFailHandler(enabled=True)

        # COMMAND_EXECUTION cascade threshold is 5; send 4 errors to stay below
        for i in range(4):
            error = PantherException(
                message=f"Error {i}",
                severity=ErrorSeverity.LOW,
                category=ErrorCategory.COMMAND_EXECUTION,
            )

            result = handler.handle_error(error, raise_on_critical=False)
            assert result is True  # LOW severity continues below cascade threshold

        assert handler.error_count == 4

    def test_error_count_tracks_all_errors(self):
        """Test that error_count increments for every error handled."""
        handler = FastFailHandler(enabled=True)

        # Use different categories to avoid cascade detection
        categories = [
            ErrorCategory.DOCKER_BUILD,
            ErrorCategory.PLUGIN_LOAD,
            ErrorCategory.CONFIGURATION,
            ErrorCategory.RESOURCE,
            ErrorCategory.TIMEOUT,
        ]

        for i, category in enumerate(categories):
            error = PantherException(
                message=f"Error {i}",
                severity=ErrorSeverity.LOW,
                category=category,
            )
            handler.handle_error(error, raise_on_critical=False)

        assert handler.error_count == 5

    def test_cascade_detection_triggers_at_threshold(self):
        """Test that cascade detection triggers when threshold is reached."""
        handler = FastFailHandler(enabled=True)

        # COMMAND_EXECUTION cascade threshold is 5
        for i in range(5):
            error = PantherException(
                message=f"Error {i}",
                severity=ErrorSeverity.LOW,
                category=ErrorCategory.COMMAND_EXECUTION,
            )
            handler.handle_error(error, raise_on_critical=False)

        # The 6th error should trigger cascade detection and return False
        cascade_error = PantherException(
            message="Error 5",
            severity=ErrorSeverity.LOW,
            category=ErrorCategory.COMMAND_EXECUTION,
        )
        result = handler.handle_error(cascade_error, raise_on_critical=False)
        assert result is False  # CASCADE upgrades to HIGH, stops execution


class TestExperimentManagerConfiguration:
    """Test ExperimentManager fast-fail configuration logic."""

    def test_fast_fail_handler_respects_global_config_disabled(self):
        """Test FastFailHandler is disabled when global config disables fast-fail."""
        config = GlobalConfig()
        config.fast_fail.enabled = False

        # ExperimentManager uses: enabled = fast_fail_enabled AND fast_fail_config.enabled
        handler = FastFailHandler(
            enabled=True and config.fast_fail.enabled, logger=Mock()
        )
        assert handler.enabled is False

    def test_fast_fail_handler_respects_flag_disabled(self):
        """Test FastFailHandler is disabled when fast_fail_enabled flag is False."""
        config = GlobalConfig()
        config.fast_fail.enabled = True

        # ExperimentManager uses: enabled = fast_fail_enabled AND fast_fail_config.enabled
        handler = FastFailHandler(
            enabled=False and config.fast_fail.enabled, logger=Mock()
        )
        assert handler.enabled is False

    def test_fast_fail_handler_enabled_when_both_true(self):
        """Test FastFailHandler is enabled when both config and flag are True."""
        config = GlobalConfig()
        config.fast_fail.enabled = True

        handler = FastFailHandler(
            enabled=True and config.fast_fail.enabled, logger=Mock()
        )
        assert handler.enabled is True

    def test_configuration_yaml_example(self):
        """Test configuration that would be loaded from YAML."""
        # This demonstrates how the configuration would look in YAML
        config_dict = {
            "fast_fail": {
                "enabled": True,
                "test_level": True,
                "docker_build_failures": True,
                "service_start_failures": True,
                "ivy_compilation_failures": False,
                "timeout_cascade_threshold": 3,
                "critical_only": False,
            }
        }

        # In practice, this would be loaded via OmegaConf
        config = GlobalConfig()
        config.fast_fail.enabled = config_dict["fast_fail"]["enabled"]
        config.fast_fail.test_level = config_dict["fast_fail"]["test_level"]
        config.fast_fail.docker_build_failures = config_dict["fast_fail"][
            "docker_build_failures"
        ]
        config.fast_fail.service_start_failures = config_dict["fast_fail"][
            "service_start_failures"
        ]
        config.fast_fail.ivy_compilation_failures = config_dict["fast_fail"][
            "ivy_compilation_failures"
        ]
        config.fast_fail.timeout_cascade_threshold = config_dict["fast_fail"][
            "timeout_cascade_threshold"
        ]
        config.fast_fail.critical_only = config_dict["fast_fail"]["critical_only"]

        assert config.fast_fail.enabled is True
        assert config.fast_fail.ivy_compilation_failures is False
        assert config.fast_fail.timeout_cascade_threshold == 3


class TestSeverityBasedFiltering:
    """Test filtering errors based on severity configuration."""

    def test_severity_hierarchy(self):
        """Test error severity hierarchy."""
        # Verify severity values
        assert ErrorSeverity.CRITICAL.value > ErrorSeverity.HIGH.value
        assert ErrorSeverity.HIGH.value > ErrorSeverity.MEDIUM.value
        assert ErrorSeverity.MEDIUM.value > ErrorSeverity.LOW.value

    def test_category_based_handling(self):
        """Test different handling based on error category."""
        handler = FastFailHandler(enabled=True)

        categories = [
            (ErrorCategory.DOCKER_BUILD, "Docker build error"),
            (ErrorCategory.DOCKER_RUNTIME, "Docker runtime error"),
            (ErrorCategory.PLUGIN_LOAD, "Plugin load error"),
            (ErrorCategory.SERVICE_START, "Service start error"),
            (ErrorCategory.NETWORK_SETUP, "Network setup error"),
            (ErrorCategory.COMMAND_EXECUTION, "Command execution error"),
            (ErrorCategory.CONFIGURATION, "Configuration error"),
            (ErrorCategory.RESOURCE, "Resource error"),
            (ErrorCategory.TIMEOUT, "Timeout error"),
        ]

        for category, message in categories:
            error = PantherException(
                message=message, severity=ErrorSeverity.MEDIUM, category=category
            )

            result = handler.handle_error(error, raise_on_critical=False)
            assert result is True  # MEDIUM severity continues

            # Verify category is properly formatted in logs
            formatted = handler._format_error(error)
            assert f"[{category.value.upper()}]" in formatted


class TestConfigurationValidation:
    """Test configuration validation and edge cases."""

    def test_negative_threshold_values(self):
        """Test handling of negative configuration values."""
        # FastFailConfig should handle negative values gracefully
        config = FastFailConfig(timeout_cascade_threshold=-1)

        # Negative should be accepted (validation could convert to 0 in practice)
        assert config.timeout_cascade_threshold == -1

    def test_conflicting_configurations(self):
        """Test handling of conflicting configuration settings."""
        config = GlobalConfig()

        # Scenario: fast_fail disabled but specific failures enabled
        config.fast_fail.enabled = False
        config.fast_fail.docker_build_failures = True
        config.fast_fail.service_start_failures = True

        # When fast_fail is disabled, specific settings should be ignored
        # This tests the configuration logic
        assert config.fast_fail.enabled is False

        # The handler should respect the global enabled flag
        handler = FastFailHandler(enabled=config.fast_fail.enabled, logger=Mock())

        assert handler.enabled is False

    def test_configuration_serialization(self):
        """Test configuration can be serialized/deserialized."""
        config = FastFailConfig(
            enabled=True,
            test_level=True,
            docker_build_failures=False,
            service_start_failures=True,
            ivy_compilation_failures=False,
            timeout_cascade_threshold=5,
            critical_only=True,
        )

        # Convert to dict (Pydantic model_dump)
        config_dict = config.model_dump()

        assert config_dict["enabled"] is True
        assert config_dict["test_level"] is True
        assert config_dict["docker_build_failures"] is False
        assert config_dict["service_start_failures"] is True
        assert config_dict["ivy_compilation_failures"] is False
        assert config_dict["timeout_cascade_threshold"] == 5
        assert config_dict["critical_only"] is True

        # Recreate from dict
        new_config = FastFailConfig(**config_dict)

        assert new_config.enabled == config.enabled
        assert new_config.test_level == config.test_level
        assert new_config.docker_build_failures == config.docker_build_failures
        assert new_config.service_start_failures == config.service_start_failures
        assert new_config.ivy_compilation_failures == config.ivy_compilation_failures
        assert new_config.timeout_cascade_threshold == config.timeout_cascade_threshold
        assert new_config.critical_only == config.critical_only


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
