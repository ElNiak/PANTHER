import pytest

from panther.config.core.models.experiment import TestConfig
from panther.config.core.models.global_config import GlobalConfig
from panther.core.observer.management.event_manager import EventManager
from panther.plugins.environments.execution_environment.strace.config_schema import (
    StraceConfig,
)
from panther.plugins.environments.execution_environment.strace.strace import (
    StraceEnvironment,
)
from panther.plugins.plugin_manager import PluginManager


@pytest.fixture
def strace_environment():
    env_config_to_test = StraceConfig()
    output_dir = "/tmp"
    env_type = "execution_environment"
    env_sub_type = "strace"
    event_manager = EventManager()
    return StraceEnvironment(
        env_config_to_test, output_dir, env_type, env_sub_type, event_manager
    )


def test_strace_environment_initialization(strace_environment):
    assert isinstance(strace_environment, StraceEnvironment)
    assert strace_environment.env_config_to_test is not None
    # On macOS, /tmp is a symlink to /private/tmp; compare resolved paths
    import os

    assert os.path.realpath(strace_environment.output_dir) == os.path.realpath("/tmp")
    assert isinstance(strace_environment.event_manager, EventManager)


def test_strace_environment_to_command(strace_environment):
    command = strace_environment.to_command()
    assert isinstance(command, str)
    assert "strace" in command


def test_strace_environment_setup_environment(strace_environment):
    from unittest.mock import MagicMock

    services_managers = []
    test_config = MagicMock(spec=TestConfig)
    global_config = MagicMock(spec=GlobalConfig)
    timestamp = "2023-10-10_10-10-10"
    plugin_manager = PluginManager()

    strace_environment.setup_environment(
        services_managers, test_config, global_config, timestamp, plugin_manager
    )
    assert strace_environment.services_managers == services_managers
    assert strace_environment.test_config == test_config
    assert strace_environment.global_config == global_config
    assert strace_environment.plugin_manager == plugin_manager


def test_strace_environment_repr(strace_environment):
    repr_str = repr(strace_environment)
    assert isinstance(repr_str, str)
    assert "StraceEnvironment" in repr_str
