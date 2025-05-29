import pytest
from unittest.mock import MagicMock
from panther.plugins.environments.network_environment.network_environment_interface import (
    INetworkEnvironment,
)
from panther.plugins.environments.config_schema import EnvironmentConfig
from panther.core.observer.event_manager import EventManager


class MockNetworkEnvironment(INetworkEnvironment):
    def generate_environment_services(self, paths, timestamp):
        pass

    def prepare_environment(self):
        pass

    def launch_environment_services(self):
        pass

    def deploy_services(self):
        pass

    def setup_environment(self):
        pass

    def teardown_environment(self):
        pass


@pytest.fixture
def mock_environment_config():
    return MagicMock(spec=EnvironmentConfig)


@pytest.fixture
def mock_event_manager():
    return MagicMock(spec=EventManager)


@pytest.fixture
def network_environment(mock_environment_config, mock_event_manager):
    return MockNetworkEnvironment(
        env_config_to_test=mock_environment_config,
        output_dir="/tmp",
        env_type="test_env",
        env_sub_type="test_sub_env",
        event_manager=mock_event_manager,
    )


def test_is_network_environment(network_environment):
    assert network_environment.is_network_environment() is True


def test_resolve_environment_variables(network_environment):
    env_vars = {"VAR1": "value1", "VAR2": "${VAR1}/value2", "VAR3": "$VAR2/value3"}
    resolved_vars = network_environment.resolve_environment_variables(env_vars)
    assert resolved_vars["VAR1"] == "value1"
    assert resolved_vars["VAR2"] == "value1/value2"
    assert resolved_vars["VAR3"] == "value1/value2/value3"
