"""
Comprehensive tests for the fast-fail implementation in PANTHER.

This module tests the actual fast-fail system implementation including:
- FastFailHandler
- PantherException hierarchy
- ErrorHandlerMixin integration
- Exception severity and categories
"""

import logging
from typing import Optional
from unittest.mock import Mock, MagicMock, patch
import pytest

from panther.core.exceptions.fast_fail import (
    FastFailHandler,
    PantherException,
    ErrorSeverity,
    ErrorCategory,
    DockerBuildException,
    PluginLoadException,
    ServiceStartException,
)
from panther.core.exceptions.error_handler_mixin import ErrorHandlerMixin
from panther.core.exceptions.experiment_exceptions import (
    ExperimentInitializationError,
    ConfigurationError,
    TestExecutionError,
    PluginValidationError,
)


class TestPantherException:
    """Test the base PantherException class."""
    
    def test_exception_initialization(self):
        """Test PantherException basic initialization."""
        exception = PantherException(
            message="Test error",
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.COMMAND_EXECUTION,
            context={"key": "value"}
        )
        
        assert str(exception) == "Test error"
        assert exception.severity == ErrorSeverity.HIGH
        assert exception.category == ErrorCategory.COMMAND_EXECUTION
        assert exception.context["key"] == "value"
        assert hasattr(exception, "timestamp")
    
    def test_should_terminate_critical(self):
        """Test that CRITICAL severity returns True for should_terminate."""
        exception = PantherException(
            message="Critical error",
            severity=ErrorSeverity.CRITICAL,
            category=ErrorCategory.DOCKER_BUILD
        )
        
        assert exception.should_terminate() is True
    
    def test_should_terminate_non_critical(self):
        """Test that non-CRITICAL severity returns False for should_terminate."""
        for severity in [ErrorSeverity.HIGH, ErrorSeverity.MEDIUM, ErrorSeverity.LOW]:
            exception = PantherException(
                message="Test error",
                severity=severity,
                category=ErrorCategory.COMMAND_EXECUTION
            )
            
            assert exception.should_terminate() is False


class TestDockerBuildException:
    """Test DockerBuildException functionality."""
    
    def test_docker_build_exception_initialization(self):
        """Test DockerBuildException initialization."""
        exception = DockerBuildException(
            message="Build failed",
            image_name="test_image",
            dockerfile="/path/to/Dockerfile",
            build_error="Command failed"
        )
        
        assert str(exception) == "Build failed"
        assert exception.severity == ErrorSeverity.CRITICAL
        assert exception.category == ErrorCategory.DOCKER_BUILD
        assert exception.context["image_name"] == "test_image"
        assert exception.context["dockerfile"] == "/path/to/Dockerfile"
        assert exception.context["build_error"] == "Command failed"
        assert exception.should_terminate() is True


class TestPluginLoadException:
    """Test PluginLoadException functionality."""
    
    def test_plugin_load_exception_default_severity(self):
        """Test PluginLoadException with default severity."""
        exception = PluginLoadException(
            message="Plugin load failed",
            plugin_name="test_plugin",
            plugin_type="service"
        )
        
        assert str(exception) == "Plugin load failed"
        assert exception.severity == ErrorSeverity.HIGH
        assert exception.category == ErrorCategory.PLUGIN_LOAD
        assert exception.context["plugin_name"] == "test_plugin"
        assert exception.context["plugin_type"] == "service"
    
    def test_plugin_load_exception_custom_severity(self):
        """Test PluginLoadException with custom severity."""
        exception = PluginLoadException(
            message="Optional plugin failed",
            plugin_name="optional_plugin",
            plugin_type="tester",
            severity=ErrorSeverity.MEDIUM
        )
        
        assert exception.severity == ErrorSeverity.MEDIUM


class TestServiceStartException:
    """Test ServiceStartException functionality."""
    
    def test_service_start_exception(self):
        """Test ServiceStartException initialization."""
        exception = ServiceStartException(
            message="Service failed to start",
            service_name="test_service"
        )
        
        assert str(exception) == "Service failed to start"
        assert exception.severity == ErrorSeverity.HIGH
        assert exception.category == ErrorCategory.SERVICE_START
        assert exception.context["service_name"] == "test_service"


class TestFastFailHandler:
    """Test FastFailHandler functionality."""
    
    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        return Mock(spec=logging.Logger)
    
    @pytest.fixture
    def handler(self, mock_logger):
        """Create a FastFailHandler for testing."""
        return FastFailHandler(enabled=True, logger=mock_logger)
    
    def test_handler_initialization(self, mock_logger):
        """Test FastFailHandler initialization."""
        handler = FastFailHandler(enabled=True, logger=mock_logger)
        
        assert handler.enabled is True
        assert handler.logger == mock_logger
        assert handler.error_count == 0
        assert handler.critical_error is None
    
    def test_handle_error_critical_enabled(self, handler):
        """Test handling critical error with fast-fail enabled."""
        error = PantherException(
            message="Critical error",
            severity=ErrorSeverity.CRITICAL,
            category=ErrorCategory.DOCKER_BUILD
        )
        
        with pytest.raises(PantherException) as exc_info:
            handler.handle_error(error, raise_on_critical=True)
        
        assert exc_info.value == error
        assert handler.error_count == 1
        assert handler.critical_error == error
        handler.logger.critical.assert_called_once()
    
    def test_handle_error_critical_disabled(self):
        """Test handling critical error with fast-fail disabled."""
        mock_logger = Mock(spec=logging.Logger)
        handler = FastFailHandler(enabled=False, logger=mock_logger)
        
        error = PantherException(
            message="Critical error",
            severity=ErrorSeverity.CRITICAL,
            category=ErrorCategory.DOCKER_BUILD
        )
        
        result = handler.handle_error(error, raise_on_critical=True)
        
        assert result is True  # Continue when disabled
        assert handler.error_count == 1
        mock_logger.critical.assert_called_once()
    
    def test_handle_error_high_severity(self, handler):
        """Test handling high severity error."""
        error = PantherException(
            message="High severity error",
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.PLUGIN_LOAD
        )
        
        result = handler.handle_error(error, raise_on_critical=True)
        
        assert result is False  # Should not continue
        assert handler.error_count == 1
        handler.logger.error.assert_called_once()
    
    def test_handle_error_medium_severity(self, handler):
        """Test handling medium severity error."""
        error = PantherException(
            message="Medium severity error",
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.COMMAND_EXECUTION
        )
        
        result = handler.handle_error(error, raise_on_critical=True)
        
        assert result is True  # Should continue
        assert handler.error_count == 1
        handler.logger.warning.assert_called_once()
    
    def test_handle_error_low_severity(self, handler):
        """Test handling low severity error."""
        error = PantherException(
            message="Low severity error",
            severity=ErrorSeverity.LOW,
            category=ErrorCategory.COMMAND_EXECUTION
        )
        
        result = handler.handle_error(error, raise_on_critical=True)
        
        assert result is True  # Should continue
        assert handler.error_count == 1
        handler.logger.info.assert_called_once()
    
    def test_handle_regular_exception(self, handler):
        """Test handling regular (non-Panther) exception."""
        error = ValueError("Regular error")
        
        result = handler.handle_error(error, raise_on_critical=False)
        
        assert result is True  # Medium severity continues
        assert handler.error_count == 1
        handler.logger.warning.assert_called_once()
    
    def test_format_error(self, handler):
        """Test error formatting."""
        error = PantherException(
            message="Test error",
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.DOCKER_BUILD,
            context={"image": "test", "tag": "latest"}
        )
        
        formatted = handler._format_error(error)
        
        assert "[DOCKER_BUILD]" in formatted
        assert "HIGH:" in formatted
        assert "Test error" in formatted
        assert "image=test" in formatted
        assert "tag=latest" in formatted
    
    def test_check_critical(self, handler):
        """Test check_critical method."""
        # No critical error
        handler.check_critical()  # Should not raise
        
        # Set critical error
        error = PantherException(
            message="Critical error",
            severity=ErrorSeverity.CRITICAL,
            category=ErrorCategory.DOCKER_BUILD
        )
        handler.critical_error = error
        
        with pytest.raises(PantherException) as exc_info:
            handler.check_critical()
        
        assert exc_info.value == error
    
    def test_check_critical_disabled(self):
        """Test check_critical when fast-fail is disabled."""
        handler = FastFailHandler(enabled=False)
        
        # Set critical error
        error = PantherException(
            message="Critical error",
            severity=ErrorSeverity.CRITICAL,
            category=ErrorCategory.DOCKER_BUILD
        )
        handler.critical_error = error
        
        # Should not raise when disabled
        handler.check_critical()


class TestErrorHandlerMixinIntegration:
    """Test ErrorHandlerMixin integration with FastFailHandler."""
    
    class TestClass(ErrorHandlerMixin):
        """Test class using ErrorHandlerMixin."""
        def __init__(self):
            super().__init__()
            self.event_emitter = None
    
    @pytest.fixture
    def test_instance(self):
        """Create test instance with mixin."""
        return self.TestClass()
    
    def test_mixin_initialization(self, test_instance):
        """Test mixin creates FastFailHandler."""
        assert hasattr(test_instance, "fast_fail_handler")
        assert isinstance(test_instance.fast_fail_handler, FastFailHandler)
        assert test_instance.fast_fail_handler.enabled is True
    
    def test_handle_error_with_severity(self, test_instance):
        """Test handle_error with severity parameter."""
        error = ValueError("Test error")
        
        with patch.object(test_instance.fast_fail_handler, 'handle_error') as mock_handle:
            mock_handle.return_value = True
            
            test_instance.handle_error(
                error,
                "test operation",
                reraise=False,
                severity=ErrorSeverity.HIGH,
                category=ErrorCategory.PLUGIN_LOAD
            )
            
            # Check that PantherException was created with correct severity
            mock_handle.assert_called_once()
            panther_error = mock_handle.call_args[0][0]
            assert isinstance(panther_error, PantherException)
            assert panther_error.severity == ErrorSeverity.HIGH
            assert panther_error.category == ErrorCategory.PLUGIN_LOAD
    
    def test_handle_error_panther_exception(self, test_instance):
        """Test handle_error with PantherException."""
        error = DockerBuildException(
            message="Build failed",
            image_name="test",
            dockerfile="Dockerfile",
            build_error="Error"
        )
        
        with patch.object(test_instance.fast_fail_handler, 'handle_error') as mock_handle:
            mock_handle.return_value = False
            
            with pytest.raises(DockerBuildException):
                test_instance.handle_error(error, "docker build", reraise=True)
            
            # Should pass the original exception
            mock_handle.assert_called_once()
            assert mock_handle.call_args[0][0] == error
    
    def test_safe_execute_with_fast_fail(self, test_instance):
        """Test safe_execute integration with fast-fail."""
        def failing_operation():
            raise ValueError("Operation failed")
        
        result = test_instance.safe_execute(
            failing_operation,
            "test operation",
            error_return="error",
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.COMMAND_EXECUTION
        )
        
        assert result == "error"
        assert test_instance.fast_fail_handler.error_count == 1
    
    def test_with_error_handling_decorator(self, test_instance):
        """Test with_error_handling decorator with fast-fail."""
        @test_instance.with_error_handling(
            "test method",
            severity=ErrorSeverity.LOW,
            category=ErrorCategory.COMMAND_EXECUTION,
            reraise=False,
            error_return="failed"
        )
        def test_method():
            raise RuntimeError("Method failed")
        
        result = test_method()
        
        assert result == "failed"
        assert test_instance.fast_fail_handler.error_count == 1


class TestExperimentExceptionsIntegration:
    """Test experiment exceptions with fast-fail system."""
    
    def test_experiment_initialization_error(self):
        """Test ExperimentInitializationError severity."""
        error = ExperimentInitializationError(
            message="Experiment init failed",
            experiment_name="test_exp",
            config_path="/path/to/config"
        )
        
        assert error.severity == ErrorSeverity.CRITICAL
        assert error.should_terminate() is True
        assert error.context["experiment_name"] == "test_exp"
        assert error.context["config_path"] == "/path/to/config"
    
    def test_configuration_error(self):
        """Test ConfigurationError severity."""
        error = ConfigurationError(
            message="Invalid config",
            config_field="test_field",
            config_value="invalid"
        )
        
        assert error.severity == ErrorSeverity.CRITICAL
        assert error.should_terminate() is True
        assert error.context["config_field"] == "test_field"
        assert error.context["config_value"] == "invalid"
    
    def test_test_execution_error(self):
        """Test TestExecutionError with custom severity."""
        error = TestExecutionError(
            message="Test failed",
            test_name="test_case_1",
            phase="execution",
            severity=ErrorSeverity.MEDIUM
        )
        
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.should_terminate() is False
        assert error.context["test_name"] == "test_case_1"
        assert error.context["phase"] == "execution"


class TestFastFailScenarios:
    """Test realistic fast-fail scenarios."""
    
    def test_docker_build_failure_scenario(self):
        """Test Docker build failure triggering fast-fail."""
        handler = FastFailHandler(enabled=True)
        
        # Simulate Docker build failure
        error = DockerBuildException(
            message="Failed to build Docker image",
            image_name="test_service",
            dockerfile="/app/Dockerfile",
            build_error="RUN command failed"
        )
        
        with pytest.raises(DockerBuildException) as exc_info:
            handler.handle_error(error, raise_on_critical=True)
        
        assert handler.critical_error == error
        assert exc_info.value.should_terminate() is True
    
    def test_plugin_cascade_failure(self):
        """Test cascading plugin failures."""
        handler = FastFailHandler(enabled=True)
        
        # First plugin fails with HIGH severity
        error1 = PluginLoadException(
            message="Required plugin failed",
            plugin_name="core_plugin",
            plugin_type="service",
            severity=ErrorSeverity.HIGH
        )
        
        result1 = handler.handle_error(error1, raise_on_critical=False)
        assert result1 is False  # Should not continue
        
        # Second plugin fails
        error2 = PluginLoadException(
            message="Another plugin failed",
            plugin_name="optional_plugin",
            plugin_type="tester",
            severity=ErrorSeverity.MEDIUM
        )
        
        result2 = handler.handle_error(error2, raise_on_critical=False)
        assert result2 is True  # Medium severity continues
        
        assert handler.error_count == 2
    
    def test_experiment_lifecycle_with_fast_fail(self):
        """Test experiment lifecycle with various error severities."""
        handler = FastFailHandler(enabled=True)
        
        # Configuration warning - should continue
        config_warning = PantherException(
            message="Config deprecated",
            severity=ErrorSeverity.LOW,
            category=ErrorCategory.CONFIGURATION
        )
        assert handler.handle_error(config_warning, raise_on_critical=False) is True
        
        # Plugin validation error - should not continue
        plugin_error = PluginValidationError(
            message="Plugin validation failed",
            plugin_name="test_plugin",
            severity=ErrorSeverity.HIGH
        )
        assert handler.handle_error(plugin_error, raise_on_critical=False) is False
        
        # Critical experiment error - should terminate
        critical_error = ExperimentInitializationError(
            message="Failed to initialize experiment",
            experiment_name="test"
        )
        
        with pytest.raises(ExperimentInitializationError):
            handler.handle_error(critical_error, raise_on_critical=True)
        
        assert handler.error_count == 3
        assert handler.critical_error == critical_error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])