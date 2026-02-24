"""
Unit tests for IExecutionEnvironment interface.

Tests the interface contract and abstract methods that all execution environments must implement.
"""

from abc import ABC, abstractmethod

import pytest

from panther.core.observer.management.event_manager import EventManager
from panther.plugins.environments.config_schema import EnvironmentConfig
from panther.plugins.environments.execution_environment.execution_environment_interface import (
    IExecutionEnvironment,
)


class ConcreteExecutionEnvironment(IExecutionEnvironment):
    """Concrete implementation for testing interface contract."""

    def setup_environment(self):
        """Test implementation of abstract method."""
        self.setup_called = True

    def teardown_environment(self):
        """Test implementation of abstract method."""
        self.teardown_called = True


class TestIExecutionEnvironmentInterface:
    """Test suite for IExecutionEnvironment interface."""

    def test_interface_is_abstract(self):
        """Test that IExecutionEnvironment is properly abstract."""
        # Should not be able to instantiate directly
        with pytest.raises(TypeError):
            IExecutionEnvironment(
                env_config_to_test=EnvironmentConfig(type="test"),
                output_dir="/tmp",
                env_type="test",
                env_sub_type="test",
                event_manager=EventManager(),
            )

    def test_interface_has_required_abstract_methods(self):
        """Test that interface defines required abstract methods."""
        abstract_methods = IExecutionEnvironment.__abstractmethods__
        expected_methods = {"setup_environment", "teardown_environment"}

        assert (
            abstract_methods == expected_methods
        ), f"Expected abstract methods {expected_methods}, got {abstract_methods}"

    def test_concrete_implementation_can_be_instantiated(
        self, base_environment_config, temp_output_dir, event_manager
    ):
        """Test that concrete implementations can be instantiated."""
        env = ConcreteExecutionEnvironment(
            env_config_to_test=base_environment_config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="concrete",
            event_manager=event_manager,
        )

        assert env is not None
        assert isinstance(env, IExecutionEnvironment)
        assert env.env_config_to_test == base_environment_config
        assert env.output_dir == temp_output_dir
        assert env.env_type == "execution"
        assert env.env_sub_type == "concrete"
        assert env.event_manager == event_manager

    def test_interface_initialization_attributes(
        self, base_environment_config, temp_output_dir, event_manager
    ):
        """Test that interface properly initializes all required attributes."""
        env = ConcreteExecutionEnvironment(
            env_config_to_test=base_environment_config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="concrete",
            event_manager=event_manager,
        )

        # Test required attributes are set
        assert hasattr(env, "env_config_to_test")
        assert hasattr(env, "output_dir")
        assert hasattr(env, "env_type")
        assert hasattr(env, "env_sub_type")
        assert hasattr(env, "event_manager")

        # Test default attributes are initialized
        assert hasattr(env, "services_managers")
        assert hasattr(env, "test_config")
        assert env.services_managers == []
        assert env.test_config is None

    def test_is_network_environment_default_behavior(
        self, base_environment_config, temp_output_dir, event_manager
    ):
        """Test default behavior of is_network_environment method."""
        env = ConcreteExecutionEnvironment(
            env_config_to_test=base_environment_config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="concrete",
            event_manager=event_manager,
        )

        # Execution environments should not be network environments by default
        assert not env.is_network_environment()

    def test_abstract_methods_must_be_implemented(
        self, base_environment_config, temp_output_dir, event_manager
    ):
        """Test that abstract methods can be called on concrete implementations."""
        env = ConcreteExecutionEnvironment(
            env_config_to_test=base_environment_config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="concrete",
            event_manager=event_manager,
        )

        # Test setup_environment can be called
        env.setup_environment()
        assert hasattr(env, "setup_called")
        assert env.setup_called is True

        # Test teardown_environment can be called
        env.teardown_environment()
        assert hasattr(env, "teardown_called")
        assert env.teardown_called is True

    def test_interface_inheritance_chain(self):
        """Test that IExecutionEnvironment properly inherits from ABC."""
        assert issubclass(IExecutionEnvironment, ABC)
        assert hasattr(IExecutionEnvironment, "__abstractmethods__")

    def test_services_managers_list_behavior(
        self, base_environment_config, temp_output_dir, event_manager
    ):
        """Test that services_managers list behaves correctly."""
        env = ConcreteExecutionEnvironment(
            env_config_to_test=base_environment_config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="concrete",
            event_manager=event_manager,
        )

        # Test initial state
        assert isinstance(env.services_managers, list)
        assert len(env.services_managers) == 0

        # Test list can be modified
        mock_service = "mock_service"
        env.services_managers.append(mock_service)
        assert len(env.services_managers) == 1
        assert env.services_managers[0] == mock_service

    def test_config_attribute_types(
        self, base_environment_config, temp_output_dir, event_manager
    ):
        """Test that configuration attributes have correct types."""
        env = ConcreteExecutionEnvironment(
            env_config_to_test=base_environment_config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="concrete",
            event_manager=event_manager,
        )

        assert isinstance(env.env_config_to_test, EnvironmentConfig)
        assert isinstance(env.output_dir, str)
        assert isinstance(env.env_type, str)
        assert isinstance(env.env_sub_type, str)
        assert isinstance(env.event_manager, EventManager)
        assert isinstance(env.services_managers, list)
        assert env.test_config is None  # Should be None initially


class TestIExecutionEnvironmentContract:
    """Test suite for interface contract validation."""

    def test_missing_setup_environment_method(self):
        """Test that missing setup_environment method prevents instantiation."""

        class IncompleteEnvironment(IExecutionEnvironment):
            def teardown_environment(self):
                pass

        with pytest.raises(TypeError) as exc_info:
            IncompleteEnvironment(
                env_config_to_test=EnvironmentConfig(type="test"),
                output_dir="/tmp",
                env_type="test",
                env_sub_type="test",
                event_manager=EventManager(),
            )

        assert "setup_environment" in str(exc_info.value)

    def test_missing_teardown_environment_method(self):
        """Test that missing teardown_environment method prevents instantiation."""

        class IncompleteEnvironment(IExecutionEnvironment):
            def setup_environment(self):
                pass

        with pytest.raises(TypeError) as exc_info:
            IncompleteEnvironment(
                env_config_to_test=EnvironmentConfig(type="test"),
                output_dir="/tmp",
                env_type="test",
                env_sub_type="test",
                event_manager=EventManager(),
            )

        assert "teardown_environment" in str(exc_info.value)

    def test_multiple_missing_methods(self):
        """Test error when multiple abstract methods are missing."""

        class EmptyEnvironment(IExecutionEnvironment):
            pass

        with pytest.raises(TypeError) as exc_info:
            EmptyEnvironment(
                env_config_to_test=EnvironmentConfig(type="test"),
                output_dir="/tmp",
                env_type="test",
                env_sub_type="test",
                event_manager=EventManager(),
            )

        error_msg = str(exc_info.value)
        assert "setup_environment" in error_msg
        assert "teardown_environment" in error_msg
