import pytest

from panther.config.core.models import ProtocolConfig, ServiceConfig
from panther.config.core.models.service import ImplementationConfig
from panther.plugins.services.service_manager_mixin import ServiceManagerMixin
from panther.plugins.services.services_interface import IServiceManager


class MockServiceManager(ServiceManagerMixin, IServiceManager):
    def prepare(self, plugin_loader=None):
        pass

    def generate_deployment_commands(self, service_params=None, environment=None):
        return {}

    def handle_event(self, event):
        pass


@pytest.fixture
def service_config():
    return ServiceConfig(
        name="test_service",
        implementation=ImplementationConfig(
            name="test_impl",
            type="iut",
        ),
        protocol=ProtocolConfig(
            name="test_protocol",
            version="1.0",
            role="client",
            target="target_service",
        ),
    )


@pytest.fixture
def protocol_config():
    return ProtocolConfig(
        name="test_protocol",
        version="1.0",
        role="client",
        target="target_service",
    )


@pytest.fixture
def service_manager(service_config, protocol_config):
    return MockServiceManager(
        service_config_to_test=service_config,
        service_type="testers",
        protocol=protocol_config,
        implementation_name="test_implementation",
    )


def test_initialize_commands(service_manager):
    service_manager.initialize_commands()
    run_cmd = service_manager.run_cmd

    assert isinstance(run_cmd, dict)
    assert "pre_compile_cmds" in run_cmd
    assert "compile_cmds" in run_cmd
    assert "post_compile_cmds" in run_cmd
    assert "pre_run_cmds" in run_cmd
    assert "run_cmd" in run_cmd
    assert "post_run_cmds" in run_cmd

    assert isinstance(run_cmd["pre_compile_cmds"], list)
    assert isinstance(run_cmd["compile_cmds"], list)
    assert isinstance(run_cmd["post_compile_cmds"], list)
    assert isinstance(run_cmd["pre_run_cmds"], list)
    assert isinstance(run_cmd["run_cmd"], dict)
    assert isinstance(run_cmd["post_run_cmds"], list)
