"""Tests for PingPongConfig hierarchy (PR2)."""

import pytest

from panther.config.core.models.service import ImplementationType, ServiceConfig


class TestPingPongConfigHierarchy:
    def test_isinstance_service_config(self):
        from panther.plugins.services.iut.minip.ping_pong.config_schema import (
            PingPongConfig,
        )

        pc = PingPongConfig()
        assert isinstance(pc, ServiceConfig)

    def test_implementation_defaults(self):
        from panther.plugins.services.iut.minip.ping_pong.config_schema import (
            PingPongConfig,
        )

        pc = PingPongConfig()
        assert pc.implementation.name == "ping-pong"
        assert pc.implementation.type == ImplementationType.IUT

    def test_protocol_defaults(self):
        from panther.plugins.services.iut.minip.ping_pong.config_schema import (
            PingPongConfig,
        )

        pc = PingPongConfig()
        assert pc.protocol.name == "minip"

    def test_inherits_docker_fields(self):
        from panther.plugins.services.iut.minip.ping_pong.config_schema import (
            PingPongConfig,
        )

        pc = PingPongConfig()
        assert hasattr(pc, "docker_image")
        assert hasattr(pc, "build_from_source")

    def test_no_plugin_config_dict(self):
        from panther.plugins.services.iut.minip.ping_pong.config_schema import (
            PingPongConfig,
        )

        assert "plugin_config" not in PingPongConfig.model_fields

    def test_has_version_class(self):
        from panther.plugins.services.iut.minip.ping_pong.config_schema import (
            PingPongConfig,
            PingPongVersion,
        )

        assert PingPongConfig.VERSION_CLASS is PingPongVersion
