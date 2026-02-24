"""
Unit tests for BaseExecutionEnvironment class.

Tests the base functionality and mixin integration for execution environments.
"""

from typing import List
from unittest.mock import MagicMock, Mock, patch

import pytest

from panther.config.core.models.global_config import GlobalConfig
from panther.plugins.environments.execution_environment.base_execution_environment import (
    BaseExecutionEnvironment,
)
from panther.plugins.services.services_interface import IServiceManager


class ConcreteBaseExecutionEnvironment(BaseExecutionEnvironment):
    """Concrete implementation for testing BaseExecutionEnvironment."""

    def _setup_plugin_specific_environment(
        self, services_managers: List[IServiceManager], timestamp: str
    ):
        """Test implementation of abstract method."""
        self.plugin_setup_called = True
        self.plugin_setup_services_count = len(services_managers)
        self.plugin_setup_timestamp = timestamp

    def to_command(self, *args, **kwargs) -> str:
        """Test implementation of abstract method."""
        return "test_command"

    def initialize(self, test_config, output_dir, event_manager, global_config):
        """Test implementation of initialize method."""
        self.init_called = True
        return True


class TestBaseExecutionEnvironment:
    """Test suite for BaseExecutionEnvironment class."""

    def test_inheritance_chain(self):
        """Test that BaseExecutionEnvironment has the correct inheritance."""
        from abc import ABC

        from panther.core.command_processor.mixins import CommandModificationMixin
        from panther.core.outputs.output_environment_mixins import (
            StandardOutputCollectorMixin,
        )
        from panther.core.utils.string_representation_mixin import (
            StringRepresentationMixin,
        )
        from panther.plugins.environments.execution_environment.execution_environment_interface import (
            IExecutionEnvironment,
        )
        from panther.plugins.environments.execution_environment_mixin import (
            ExecutionEnvironmentMixin,
        )

        assert issubclass(BaseExecutionEnvironment, ExecutionEnvironmentMixin)
        assert issubclass(BaseExecutionEnvironment, StandardOutputCollectorMixin)
        assert issubclass(BaseExecutionEnvironment, CommandModificationMixin)
        assert issubclass(BaseExecutionEnvironment, IExecutionEnvironment)
        assert issubclass(BaseExecutionEnvironment, StringRepresentationMixin)
        assert issubclass(BaseExecutionEnvironment, ABC)

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_initialization(
        self, mock_std_init, base_environment_config, temp_output_dir, event_manager
    ):
        """Test BaseExecutionEnvironment initialization."""
        env = ConcreteBaseExecutionEnvironment(
            env_config_to_test=base_environment_config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="concrete",
            event_manager=event_manager,
        )

        # Verify standardized_environment_initialization was called
        mock_std_init.assert_called_once_with(
            base_environment_config,
            temp_output_dir,
            "execution",
            "concrete",
            event_manager,
        )

        # Verify attributes are set correctly
        assert env.env_config_to_test == base_environment_config
        assert env.output_dir == temp_output_dir
        assert env.env_type == "execution"
        assert env.env_sub_type == "concrete"
        assert env.event_manager == event_manager

    def test_abstract_methods_exist(self):
        """Test that required abstract methods are defined."""
        abstract_methods = BaseExecutionEnvironment.__abstractmethods__
        expected_methods = {"_setup_plugin_specific_environment", "to_command"}

        assert expected_methods.issubset(
            abstract_methods
        ), f"Missing abstract methods: {expected_methods - abstract_methods}"

    def test_cannot_instantiate_base_class_directly(
        self, base_environment_config, temp_output_dir, event_manager
    ):
        """Test that BaseExecutionEnvironment cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseExecutionEnvironment(
                env_config_to_test=base_environment_config,
                output_dir=temp_output_dir,
                env_type="execution",
                env_sub_type="base",
                event_manager=event_manager,
            )

    def test_initialize_method_raises_not_implemented(
        self, base_environment_config, temp_output_dir, event_manager
    ):
        """Test that base initialize method raises NotImplementedError."""

        class PartialImplementation(BaseExecutionEnvironment):
            def _setup_plugin_specific_environment(self, services_managers, timestamp):
                pass

            def to_command(self, *args, **kwargs):
                return "test"

        env = PartialImplementation(
            env_config_to_test=base_environment_config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="partial",
            event_manager=event_manager,
        )

        with pytest.raises(NotImplementedError) as exc_info:
            env.initialize(None, temp_output_dir, event_manager, GlobalConfig())

        assert "Each plugin must implement its own initialization logic" in str(
            exc_info.value
        )


class TestBaseExecutionEnvironmentServiceDeployment:
    """Test suite for service deployment functionality."""

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_do_deploy_services_logging(
        self, mock_std_init, base_environment_config, temp_output_dir, event_manager
    ):
        """Test that _do_deploy_services logs appropriately."""
        env = ConcreteBaseExecutionEnvironment(
            env_config_to_test=base_environment_config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="concrete",
            event_manager=event_manager,
        )

        with patch.object(env, "logger") as mock_logger:
            env._do_deploy_services()
            mock_logger.debug.assert_called_once_with(
                "ConcreteBaseExecutionEnvironment deployment: no specific deployment needed"
            )

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_do_teardown_environment_logging(
        self, mock_std_init, base_environment_config, temp_output_dir, event_manager
    ):
        """Test that _do_teardown_environment logs appropriately."""
        env = ConcreteBaseExecutionEnvironment(
            env_config_to_test=base_environment_config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="concrete",
            event_manager=event_manager,
        )

        with patch.object(env, "logger") as mock_logger:
            env._do_teardown_environment()
            mock_logger.debug.assert_called_once_with(
                "ConcreteBaseExecutionEnvironment teardown: cleaning up resources"
            )


class TestBaseExecutionEnvironmentEventHandling:
    """Test suite for event handling functionality."""

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_handle_service_started_event(
        self, mock_std_init, base_environment_config, temp_output_dir, event_manager
    ):
        """Test handling of ServiceStartedEvent."""
        env = ConcreteBaseExecutionEnvironment(
            env_config_to_test=base_environment_config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="concrete",
            event_manager=event_manager,
        )

        # Create mock event
        mock_event = Mock()
        mock_event.__class__.__name__ = "ServiceStartedEvent"

        with patch.object(env, "logger") as mock_logger:
            env.handle_event(mock_event)

            # Verify correct logging
            assert mock_logger.debug.call_count == 2
            mock_logger.debug.assert_any_call(
                "ConcreteBaseExecutionEnvironment received event: %s",
                "ServiceStartedEvent",
            )
            mock_logger.debug.assert_any_call(
                "Service started, environment monitoring should be active"
            )

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_handle_service_stopped_event(
        self, mock_std_init, base_environment_config, temp_output_dir, event_manager
    ):
        """Test handling of ServiceStoppedEvent."""
        env = ConcreteBaseExecutionEnvironment(
            env_config_to_test=base_environment_config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="concrete",
            event_manager=event_manager,
        )

        # Create mock event
        mock_event = Mock()
        mock_event.__class__.__name__ = "ServiceStoppedEvent"

        with patch.object(env, "logger") as mock_logger:
            env.handle_event(mock_event)

            # Verify correct logging
            assert mock_logger.debug.call_count == 2
            mock_logger.debug.assert_any_call(
                "ConcreteBaseExecutionEnvironment received event: %s",
                "ServiceStoppedEvent",
            )
            mock_logger.debug.assert_any_call(
                "Service stopped, environment collection complete"
            )

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_handle_unknown_event(
        self, mock_std_init, base_environment_config, temp_output_dir, event_manager
    ):
        """Test handling of unknown event types."""
        env = ConcreteBaseExecutionEnvironment(
            env_config_to_test=base_environment_config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="concrete",
            event_manager=event_manager,
        )

        # Create mock event with unknown type
        mock_event = Mock()
        mock_event.__class__.__name__ = "UnknownEvent"

        with patch.object(env, "logger") as mock_logger:
            env.handle_event(mock_event)

            # Verify correct logging
            assert mock_logger.debug.call_count == 2
            mock_logger.debug.assert_any_call(
                "ConcreteBaseExecutionEnvironment received event: %s", "UnknownEvent"
            )
            mock_logger.debug.assert_any_call(
                "Unhandled event type: %s", "UnknownEvent"
            )


class TestBaseExecutionEnvironmentSetup:
    """Test suite for environment setup functionality."""

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.log_omega_config_summary"
    )
    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.setup_execution_environment"
    )
    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_setup_environment_call_sequence(
        self,
        mock_std_init,
        mock_setup_exec,
        mock_log_summary,
        base_environment_config,
        temp_output_dir,
        event_manager,
    ):
        """Test that setup_environment calls methods in correct sequence."""
        env = ConcreteBaseExecutionEnvironment(
            env_config_to_test=base_environment_config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="concrete",
            event_manager=event_manager,
        )

        # Mock dependencies
        services_managers = [Mock(spec=IServiceManager)]
        test_config = Mock()
        global_config = GlobalConfig()
        timestamp = "20241224_120000"
        plugin_manager = Mock()

        with patch.object(env, "logger") as mock_logger:
            env.setup_environment(
                services_managers=services_managers,
                test_config=test_config,
                global_config=global_config,
                timestamp=timestamp,
                plugin_manager=plugin_manager,
            )

            # Verify setup_execution_environment was called
            mock_setup_exec.assert_called_once_with(
                services_managers, test_config, global_config, timestamp, plugin_manager
            )

            # Verify plugin-specific setup was called
            assert hasattr(env, "plugin_setup_called")
            assert env.plugin_setup_called is True
            assert env.plugin_setup_services_count == 1
            assert env.plugin_setup_timestamp == timestamp

            # Verify logging occurred
            assert mock_logger.debug.call_count >= 4  # Various debug messages

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_setup_environment_services_logging(
        self, mock_std_init, base_environment_config, temp_output_dir, event_manager
    ):
        """Test that setup_environment logs service information correctly."""
        env = ConcreteBaseExecutionEnvironment(
            env_config_to_test=base_environment_config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="concrete",
            event_manager=event_manager,
        )

        # Create mock services with names
        service1 = Mock(spec=IServiceManager)
        service1.service_name = "service1"
        service2 = Mock(spec=IServiceManager)
        service2.__class__.__name__ = "Service2Manager"

        services_managers = [service1, service2]

        with patch.object(env, "logger") as mock_logger:
            with patch.object(env, "setup_execution_environment"):
                env.setup_environment(
                    services_managers=services_managers,
                    test_config=Mock(),
                    global_config=GlobalConfig(),
                    timestamp="test_timestamp",
                    plugin_manager=Mock(),
                )

            # Verify service count logging
            mock_logger.debug.assert_any_call("Services managers count: 2")
            # Verify service names logging (should handle both service_name attribute and class name fallback)
            mock_logger.debug.assert_any_call(
                "Service names: ['service1', 'Service2Manager']"
            )


class TestBaseExecutionEnvironmentOutputPatterns:
    """Test suite for output pattern functionality."""

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_get_output_patterns_default(
        self, mock_std_init, base_environment_config, temp_output_dir, event_manager
    ):
        """Test default output patterns."""
        env = ConcreteBaseExecutionEnvironment(
            env_config_to_test=base_environment_config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="concrete",
            event_manager=event_manager,
        )

        patterns = env.get_output_patterns()

        expected_patterns = [
            ("profile", "concrete_{service_name}.log"),
            ("summary", "concrete_summary_{service_name}.txt"),
            ("raw", "concrete_raw_{service_name}.dat"),
        ]

        assert patterns == expected_patterns

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_get_additional_output_discovery_patterns_default(
        self, mock_std_init, base_environment_config, temp_output_dir, event_manager
    ):
        """Test default additional output discovery patterns."""
        env = ConcreteBaseExecutionEnvironment(
            env_config_to_test=base_environment_config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="concrete",
            event_manager=event_manager,
        )

        patterns = env.get_additional_output_discovery_patterns()
        assert patterns == {}


class TestBaseExecutionEnvironmentStringRepresentation:
    """Test suite for string representation functionality."""

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_get_key_attributes_with_services(
        self, mock_std_init, base_environment_config, temp_output_dir, event_manager
    ):
        """Test _get_key_attributes includes service count."""
        env = ConcreteBaseExecutionEnvironment(
            env_config_to_test=base_environment_config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="concrete",
            event_manager=event_manager,
        )

        # Add some mock services
        env.services_managers = [Mock(), Mock(), Mock()]

        with patch("super") as mock_super:
            mock_super.return_value._get_key_attributes.return_value = {"base": "value"}

            attrs = env._get_key_attributes()

            assert "services" in attrs
            assert attrs["services"] == 3
            assert attrs["base"] == "value"

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_get_key_attributes_without_services(
        self, mock_std_init, base_environment_config, temp_output_dir, event_manager
    ):
        """Test _get_key_attributes without services."""
        env = ConcreteBaseExecutionEnvironment(
            env_config_to_test=base_environment_config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="concrete",
            event_manager=event_manager,
        )

        # Ensure no services
        env.services_managers = []

        with patch("super") as mock_super:
            mock_super.return_value._get_key_attributes.return_value = {"base": "value"}

            attrs = env._get_key_attributes()

            assert "services" not in attrs
            assert attrs["base"] == "value"


class TestConcreteImplementationRequirements:
    """Test suite for concrete implementation requirements."""

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_concrete_implementation_works(
        self, mock_std_init, base_environment_config, temp_output_dir, event_manager
    ):
        """Test that our concrete implementation works as expected."""
        env = ConcreteBaseExecutionEnvironment(
            env_config_to_test=base_environment_config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="concrete",
            event_manager=event_manager,
        )

        # Test abstract method implementations
        command = env.to_command()
        assert command == "test_command"

        # Test plugin-specific setup
        env._setup_plugin_specific_environment([], "test_timestamp")
        assert env.plugin_setup_called is True
        assert env.plugin_setup_services_count == 0
        assert env.plugin_setup_timestamp == "test_timestamp"

        # Test initialize
        result = env.initialize(Mock(), temp_output_dir, event_manager, GlobalConfig())
        assert result is True
        assert env.init_called is True
