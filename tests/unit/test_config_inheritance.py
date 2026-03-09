#!/usr/bin/env python3
"""Test configuration inheritance hierarchy after fixes."""
import pytest
from pydantic import ValidationError

from panther.config.core.models.environment import (
    ExecutionEnvironmentConfig,
    NetworkEnvironmentConfig,
)
from panther.config.core.models.plugin import ServicePluginConfig
from panther.plugins.environments.execution_environment.strace.config_schema import (
    StraceConfig,
)
from panther.plugins.environments.network_environment.docker_compose.config_schema import (
    DockerComposeConfig,
)
from panther.plugins.environments.network_environment.localhost_single_container.config_schema import (
    LocalhostSingleContainerConfig,
)
from panther.plugins.environments.network_environment.shadow_ns.config_schema import (
    ShadowNSConfig,
)
from panther.plugins.services.iut.quic.picoquic.config_schema import PicoquicConfig


class TestConfigInheritance:
    """Test that all plugin configs properly inherit from base plugin config classes."""

    def test_network_environment_configs_inherit_correctly(self):
        """Test network environment configs inherit from NetworkEnvironmentConfig."""
        # Docker Compose
        dc_config = DockerComposeConfig()
        assert isinstance(dc_config, NetworkEnvironmentConfig)
        assert dc_config.type == "docker_compose"
        assert hasattr(dc_config, "enabled")  # From BasePluginConfig
        assert hasattr(dc_config, "network_name")  # From NetworkEnvironmentConfig

        # Localhost Single Container (now fixed)
        lsc_config = LocalhostSingleContainerConfig()
        assert isinstance(lsc_config, NetworkEnvironmentConfig)
        assert lsc_config.type == "localhost_single_container"
        assert hasattr(lsc_config, "enabled")
        assert hasattr(lsc_config, "network_name")

        # Shadow NS (now fixed)
        sns_config = ShadowNSConfig()
        assert isinstance(sns_config, NetworkEnvironmentConfig)
        assert sns_config.type == "shadow_ns"
        assert hasattr(sns_config, "enabled")
        assert hasattr(sns_config, "network_name")

    def test_execution_environment_configs_inherit_correctly(self):
        """Test execution environment configs inherit from ExecutionEnvironmentConfig."""
        strace_config = StraceConfig()
        assert isinstance(strace_config, ExecutionEnvironmentConfig)
        assert hasattr(strace_config, "enabled")  # From BasePluginConfig
        assert hasattr(
            strace_config, "output_format"
        )  # From ExecutionEnvironmentConfig
        assert hasattr(strace_config, "collect_metrics")

    def test_service_configs_inherit_correctly(self):
        """Test service configs inherit from ServicePluginConfig."""
        picoquic_config = PicoquicConfig()
        assert isinstance(picoquic_config, ServicePluginConfig)
        assert hasattr(picoquic_config, "enabled")  # From BasePluginConfig
        assert hasattr(picoquic_config, "docker_image")  # From ServicePluginConfig
        assert hasattr(picoquic_config, "build_from_source")

    def test_config_fields_are_pydantic_validated(self):
        """Test that configs use Pydantic validation."""
        # Test field validation
        with pytest.raises(ValidationError):
            # Invalid type for network_name
            LocalhostSingleContainerConfig(network_name=123)

        # Test default values work
        config = LocalhostSingleContainerConfig()
        assert config.network_name == "panther_network"  # From base class default
        assert config.version == "3.8"  # From specific class default

    def test_shadow_ns_nested_configs(self):
        """Test Shadow NS nested config structure."""
        config = ShadowNSConfig()

        # Check nested configs exist and have proper defaults
        assert config.general.stop_time == "300s"
        assert config.experimental.strace_logging_mode == "standard"
        assert config.network.latency == 10
        assert config.hosts.server.ip_addr == "11.0.0.1"
        assert config.hosts.client.ip_addr == "11.0.0.2"

    def test_config_serialization(self):
        """Test configs can be serialized to dict."""
        config = LocalhostSingleContainerConfig(
            environment={"TEST_VAR": "test_value"}, service_prefix="test_"
        )

        config_dict = config.dict()
        assert config_dict["type"] == "localhost_single_container"
        assert config_dict["environment"] == {"TEST_VAR": "test_value"}
        assert config_dict["service_prefix"] == "test_"
        assert "enabled" in config_dict  # From base class


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
