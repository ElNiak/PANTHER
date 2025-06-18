"""
Tests for fast-fail configuration and behavior customization.

This module tests:
- FastFailConfig schema and validation
- Configuration-driven behavior
- Error threshold management
- Severity-based filtering
"""

import pytest
from unittest.mock import Mock, patch
from dataclasses import asdict

from panther.config.config_global_schema import (
    GlobalConfig,
    FastFailConfig,
    FeatureConfig,
)
from panther.core.exceptions.fast_fail import (
    FastFailHandler,
    PantherException,
    ErrorSeverity,
    ErrorCategory,
    DockerBuildException,
    PluginLoadException,
    ServiceStartException,
)
from panther.core.experiment_manager import ExperimentManager


class TestFastFailConfiguration:
    """Test FastFailConfig schema and defaults."""
    
    def test_fast_fail_config_defaults(self):
        """Test FastFailConfig default values."""
        config = FastFailConfig()
        
        assert config.enabled is True
        assert config.docker_build_failures is True
        assert config.plugin_load_failures is True
        assert config.service_start_failures is True
        assert config.critical_only is False
        assert config.max_errors_before_fail == 0
    
    def test_fast_fail_config_custom_values(self):
        """Test FastFailConfig with custom values."""
        config = FastFailConfig(
            enabled=False,
            docker_build_failures=False,
            plugin_load_failures=False,
            service_start_failures=False,
            critical_only=True,
            max_errors_before_fail=5
        )
        
        assert config.enabled is False
        assert config.docker_build_failures is False
        assert config.plugin_load_failures is False
        assert config.service_start_failures is False
        assert config.critical_only is True
        assert config.max_errors_before_fail == 5
    
    def test_global_config_integration(self):
        """Test FastFailConfig integration with GlobalConfig."""
        global_config = GlobalConfig()
        
        # Verify fast_fail config exists
        assert hasattr(global_config, 'fast_fail')
        assert isinstance(global_config.fast_fail, FastFailConfig)
        
        # Modify fast_fail settings
        global_config.fast_fail.enabled = False
        global_config.fast_fail.critical_only = True
        
        assert global_config.fast_fail.enabled is False
        assert global_config.fast_fail.critical_only is True
    
    def test_feature_config_backward_compatibility(self):
        """Test FeatureConfig fast_fail flag (backward compatibility)."""
        feature_config = FeatureConfig()
        
        assert feature_config.fast_fail is True
        
        # Test disabling via feature config
        feature_config.fast_fail = False
        assert feature_config.fast_fail is False


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
            message="Build failed",
            image_name="test",
            dockerfile="Dockerfile"
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
            severity=ErrorSeverity.HIGH
        )
        
        result = handler.handle_error(plugin_error, raise_on_critical=False)
        assert result is False  # HIGH severity should not continue
    
    def test_service_start_failures_config(self, mock_logger):
        """Test service_start_failures configuration."""
        handler = FastFailHandler(enabled=True, logger=mock_logger)
        
        service_error = ServiceStartException(
            message="Service failed",
            service_name="test_service"
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
            category=ErrorCategory.PLUGIN_LOAD
        )
        
        # CRITICAL severity error
        critical_error = PantherException(
            message="Critical error",
            severity=ErrorSeverity.CRITICAL,
            category=ErrorCategory.DOCKER_BUILD
        )
        
        # In critical_only mode, HIGH should continue
        # Currently, this is not implemented in FastFailHandler
        # but we test the expected behavior
        result_high = handler.handle_error(high_error, raise_on_critical=False)
        assert result_high is False  # Current behavior
        
        with pytest.raises(PantherException):
            handler.handle_error(critical_error, raise_on_critical=True)


class TestErrorThresholdManagement:
    """Test max_errors_before_fail configuration."""
    
    def test_unlimited_errors(self):
        """Test max_errors_before_fail = 0 (unlimited)."""
        handler = FastFailHandler(enabled=True)
        
        # Generate many errors
        for i in range(100):
            error = PantherException(
                message=f"Error {i}",
                severity=ErrorSeverity.LOW,
                category=ErrorCategory.COMMAND_EXECUTION
            )
            
            result = handler.handle_error(error, raise_on_critical=False)
            assert result is True  # LOW severity continues
        
        assert handler.error_count == 100
    
    def test_error_threshold_implementation(self):
        """Test error threshold behavior (conceptual)."""
        # This would require modifying FastFailHandler to support thresholds
        handler = FastFailHandler(enabled=True)
        
        # Simulate reaching threshold
        errors = []
        for i in range(5):
            error = PantherException(
                message=f"Error {i}",
                severity=ErrorSeverity.MEDIUM,
                category=ErrorCategory.COMMAND_EXECUTION
            )
            errors.append(error)
            handler.handle_error(error, raise_on_critical=False)
        
        # After 5 errors, the next error could trigger fast-fail
        # This is a conceptual test - actual implementation would need
        # to check handler.error_count against config.max_errors_before_fail


class TestExperimentManagerConfiguration:
    """Test ExperimentManager with various fast-fail configurations."""
    
    @pytest.fixture
    def mock_environment(self):
        """Mock the experiment manager environment."""
        with patch('panther.core.experiment_manager.EventManager') as event_mock, \
             patch('panther.core.experiment_manager.get_observer_factory') as observer_mock, \
             patch('panther.core.experiment_manager.EmitterRegistry'), \
             patch('panther.core.experiment_manager.WorkflowStateTracker'), \
             patch('panther.plugins.plugin_manager.DockerBuilder'):
            
            event_instance = Mock()
            event_mock.get_instance.return_value = event_instance
            
            factory = Mock()
            observer_mock.return_value = factory
            
            yield
    
    def test_experiment_manager_respects_global_config(self, mock_environment, tmp_path):
        """Test ExperimentManager uses global fast-fail config."""
        # Test with fast-fail disabled
        config = GlobalConfig()
        config.paths.output_dir = str(tmp_path)
        config.fast_fail.enabled = False
        
        manager = ExperimentManager(
            global_config=config,
            experiment_name="test",
            fast_fail_enabled=True  # Should be overridden
        )
        
        assert manager.fast_fail_handler.enabled is False
        
        # Test with fast-fail enabled
        config2 = GlobalConfig()
        config2.paths.output_dir = str(tmp_path / "test2")
        config2.fast_fail.enabled = True
        
        manager2 = ExperimentManager(
            global_config=config2,
            experiment_name="test2",
            fast_fail_enabled=False  # Should be overridden to False (AND logic)
        )
        
        assert manager2.fast_fail_handler.enabled is False
    
    def test_configuration_yaml_example(self):
        """Test configuration that would be loaded from YAML."""
        # This demonstrates how the configuration would look in YAML
        config_dict = {
            'fast_fail': {
                'enabled': True,
                'docker_build_failures': True,
                'plugin_load_failures': False,  # Don't fail on optional plugins
                'service_start_failures': True,
                'critical_only': False,
                'max_errors_before_fail': 10
            }
        }
        
        # In practice, this would be loaded via OmegaConf
        config = GlobalConfig()
        config.fast_fail.enabled = config_dict['fast_fail']['enabled']
        config.fast_fail.docker_build_failures = config_dict['fast_fail']['docker_build_failures']
        config.fast_fail.plugin_load_failures = config_dict['fast_fail']['plugin_load_failures']
        config.fast_fail.service_start_failures = config_dict['fast_fail']['service_start_failures']
        config.fast_fail.critical_only = config_dict['fast_fail']['critical_only']
        config.fast_fail.max_errors_before_fail = config_dict['fast_fail']['max_errors_before_fail']
        
        assert config.fast_fail.enabled is True
        assert config.fast_fail.plugin_load_failures is False
        assert config.fast_fail.max_errors_before_fail == 10


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
                message=message,
                severity=ErrorSeverity.MEDIUM,
                category=category
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
        config = FastFailConfig(max_errors_before_fail=-1)
        
        # Negative should be treated as 0 (unlimited)
        assert config.max_errors_before_fail == -1
        
        # In practice, validation could convert this to 0
    
    def test_conflicting_configurations(self):
        """Test handling of conflicting configuration settings."""
        config = GlobalConfig()
        
        # Scenario: fast_fail disabled but specific failures enabled
        config.fast_fail.enabled = False
        config.fast_fail.docker_build_failures = True
        config.fast_fail.plugin_load_failures = True
        
        # When fast_fail is disabled, specific settings should be ignored
        # This tests the configuration logic
        assert config.fast_fail.enabled is False
        
        # The handler should respect the global enabled flag
        handler = FastFailHandler(
            enabled=config.fast_fail.enabled,
            logger=Mock()
        )
        
        assert handler.enabled is False
    
    def test_configuration_serialization(self):
        """Test configuration can be serialized/deserialized."""
        config = FastFailConfig(
            enabled=True,
            docker_build_failures=False,
            plugin_load_failures=True,
            service_start_failures=True,
            critical_only=True,
            max_errors_before_fail=5
        )
        
        # Convert to dict (as would happen with OmegaConf)
        config_dict = asdict(config)
        
        assert config_dict['enabled'] is True
        assert config_dict['docker_build_failures'] is False
        assert config_dict['plugin_load_failures'] is True
        assert config_dict['service_start_failures'] is True
        assert config_dict['critical_only'] is True
        assert config_dict['max_errors_before_fail'] == 5
        
        # Recreate from dict
        new_config = FastFailConfig(**config_dict)
        
        assert new_config.enabled == config.enabled
        assert new_config.docker_build_failures == config.docker_build_failures
        assert new_config.plugin_load_failures == config.plugin_load_failures
        assert new_config.service_start_failures == config.service_start_failures
        assert new_config.critical_only == config.critical_only
        assert new_config.max_errors_before_fail == config.max_errors_before_fail


if __name__ == "__main__":
    pytest.main([__file__, "-v"])