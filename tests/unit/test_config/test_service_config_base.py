"""Tests for ServiceConfig after PR2 field merge."""

import pytest

from panther.config.core.models.service import ServiceConfig


class TestServiceConfigMergedFields:
    """ServiceConfig should have fields merged from ServicePluginConfig."""

    def test_has_docker_image(self):
        sc = ServiceConfig(
            implementation={"name": "test", "type": "iut"},
            protocol={"name": "quic", "role": "server"},
        )
        assert sc.docker_image is None

    def test_has_build_from_source(self):
        sc = ServiceConfig(
            implementation={"name": "test", "type": "iut"},
            protocol={"name": "quic", "role": "server"},
        )
        assert sc.build_from_source is True

    def test_has_source_repository(self):
        sc = ServiceConfig(
            implementation={"name": "test", "type": "iut"},
            protocol={"name": "quic", "role": "server"},
        )
        assert sc.source_repository is None

    def test_no_plugin_config_field(self):
        assert "plugin_config" not in ServiceConfig.model_fields

    def test_no_get_plugin_config_method(self):
        assert not hasattr(ServiceConfig, "get_plugin_config")


class TestOldClassesRemoved:
    def test_no_service_plugin_config(self):
        from panther.config.core.models import plugin

        assert not hasattr(plugin, "ServicePluginConfig")

    def test_no_base_plugin_config(self):
        from panther.config.core.models import plugin

        assert not hasattr(plugin, "BasePluginConfig")
