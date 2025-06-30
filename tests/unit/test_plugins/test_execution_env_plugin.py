import pytest
from panther.plugins.environments.config_schema import EnvironmentConfig
from panther.core.observer.management.event_manager import EventManager
from panther.plugins.environments.execution_environment.execution_environment_interface import (
    IExecutionEnvironment,
)


class MockExecutionEnvironment(IExecutionEnvironment):

    def __init__(self, env_config_to_test, output_dir, env_type, env_sub_type, event_manager):
        super().__init__(env_config_to_test, output_dir, env_type, env_sub_type, event_manager)

    def setup_environment(self):
        pass

    def teardown_environment(self):
        pass


@pytest.fixture
def environment_config():
    return EnvironmentConfig(type="execution")


@pytest.fixture
def event_manager():
    return EventManager()


def test_execution_environment_init(environment_config, event_manager):
    output_dir = "/tmp/test_output"
    env_type = "execution"
    env_sub_type = "mock"

    env = MockExecutionEnvironment(
        env_config_to_test=environment_config,
        output_dir=output_dir,
        env_type=env_type,
        env_sub_type=env_sub_type,
        event_manager=event_manager,
    )

    assert env.env_config_to_test == environment_config
    assert env.output_dir == output_dir
    assert env.env_type == env_type
    assert env.env_sub_type == env_sub_type
    assert env.event_manager == event_manager
    assert env.services_managers == []
    assert env.test_config is None
    assert not env.is_network_environment()
