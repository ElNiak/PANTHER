"""Tests for registry-first lookup in ExperimentBuilder._build_network_environment."""

from unittest.mock import patch

import pytest

from panther.config.core.components.builders import ExperimentBuilder
from panther.config.core.models.environment import NetworkEnvironmentConfig

pytestmark = [pytest.mark.unit]


class TestBuilderRegistryLookup:
    """Test _build_network_environment uses schema registry first."""

    @pytest.fixture
    def builder(self):
        b = ExperimentBuilder()
        b.reset_context()
        return b

    def test_falls_back_to_hardcoded_docker_compose(self, builder):
        """Without registry, falls back to hardcoded DockerComposeConfig."""
        with patch(
            "panther.plugins.core.plugin_decorators.get_config_model",
            return_value=None,
        ):
            result = builder._build_network_environment({"type": "docker_compose"})
            assert result is not None

    def test_uses_registry_when_available(self, builder):
        """If registry has a config model, validate via it and return dict."""

        class FakeEnvConfig(NetworkEnvironmentConfig):
            type: str = "custom_env"

        with patch(
            "panther.plugins.core.plugin_decorators.get_config_model",
            return_value=FakeEnvConfig,
        ):
            result = builder._build_network_environment({"type": "custom_env"})
            assert isinstance(result, dict)
            assert result["type"] == "custom_env"

    def test_unknown_type_uses_base_class(self, builder):
        """Unknown env type with no registry match returns raw dict."""
        with patch(
            "panther.plugins.core.plugin_decorators.get_config_model",
            return_value=None,
        ):
            result = builder._build_network_environment({"type": "totally_unknown"})
            assert isinstance(result, dict)
            assert result["type"] == "totally_unknown"

    def test_resolver_also_tries_registry(self):
        """PluginConfigResolver.resolve_service_config_class checks registry first."""
        from panther.config.core.models.service import ServiceConfig
        from panther.plugins.core.plugin_config_resolver import PluginConfigResolver

        class FakeServiceConfig(ServiceConfig):
            pass

        resolver = PluginConfigResolver()

        with patch(
            "panther.plugins.core.plugin_decorators.get_config_model",
            return_value=FakeServiceConfig,
        ):
            result = resolver.resolve_service_config_class("iut", "quic", "fake_impl")
            assert result is FakeServiceConfig
