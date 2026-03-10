"""Tests for ServiceConfig after PR2 field merge, plus enums, constraints, and metadata."""

import pytest

from panther.config.core.models.service import RestartPolicy, ServiceConfig


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


class TestRestartPolicyEnum:
    def test_valid_values(self):
        for val in ["no", "always", "on-failure", "unless-stopped"]:
            assert RestartPolicy(val) == RestartPolicy(val)

    def test_invalid_value(self):
        with pytest.raises(ValueError):
            RestartPolicy("invalid")

    def test_service_config_accepts_string(self):
        sc = ServiceConfig(
            implementation={"name": "test", "type": "iut"},
            protocol={"name": "quic", "role": "server"},
            restart_policy="always",
        )
        # BaseConfig has use_enum_values=True, so the value is stored as a string
        assert sc.restart_policy == RestartPolicy.ALWAYS.value

    def test_service_config_default(self):
        sc = ServiceConfig(
            implementation={"name": "test", "type": "iut"},
            protocol={"name": "quic", "role": "server"},
        )
        # BaseConfig has use_enum_values=True, so the value is stored as a string
        assert sc.restart_policy == RestartPolicy.NO.value


class TestServiceFieldConstraints:
    def test_port_too_high(self):
        with pytest.raises(Exception):
            ServiceConfig(
                implementation={"name": "test", "type": "iut"},
                protocol={"name": "quic", "role": "server"},
                network={"port": 99999},
            )

    def test_port_zero(self):
        with pytest.raises(Exception):
            ServiceConfig(
                implementation={"name": "test", "type": "iut"},
                protocol={"name": "quic", "role": "server"},
                network={"port": 0},
            )

    def test_timeout_too_high(self):
        with pytest.raises(Exception):
            ServiceConfig(
                implementation={"name": "test", "type": "iut"},
                protocol={"name": "quic", "role": "server"},
                timeout=100000,
            )

    def test_protocol_name_empty(self):
        with pytest.raises(Exception):
            ServiceConfig(
                implementation={"name": "test", "type": "iut"},
                protocol={"name": "", "role": "server"},
            )

    def test_impl_name_empty(self):
        with pytest.raises(Exception):
            ServiceConfig(
                implementation={"name": "", "type": "iut"},
                protocol={"name": "quic", "role": "server"},
            )
