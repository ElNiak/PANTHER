"""Tests for AioquicConfig hierarchy (PR2)."""

import pytest

from panther.config.core.models.service import ImplementationType, ServiceConfig


class TestAioquicConfigHierarchy:
    def test_isinstance_service_config(self):
        from panther.plugins.services.iut.quic.aioquic.config_schema import (
            AioquicConfig,
        )

        ac = AioquicConfig()
        assert isinstance(ac, ServiceConfig)

    def test_implementation_defaults(self):
        from panther.plugins.services.iut.quic.aioquic.config_schema import (
            AioquicConfig,
        )

        ac = AioquicConfig()
        assert ac.implementation.name == "aioquic"
        assert ac.implementation.type == ImplementationType.IUT

    def test_protocol_defaults(self):
        from panther.plugins.services.iut.quic.aioquic.config_schema import (
            AioquicConfig,
        )

        ac = AioquicConfig()
        assert ac.protocol.name == "quic"

    def test_plugin_specific_fields(self):
        from panther.plugins.services.iut.quic.aioquic.config_schema import (
            AioquicConfig,
        )

        ac = AioquicConfig()
        assert ac.server_root == "/var/www"
        assert ac.enable_http3 is True

    def test_inherits_docker_fields(self):
        from panther.plugins.services.iut.quic.aioquic.config_schema import (
            AioquicConfig,
        )

        ac = AioquicConfig()
        assert hasattr(ac, "docker_image")
        assert hasattr(ac, "build_from_source")

    def test_no_plugin_config_dict(self):
        from panther.plugins.services.iut.quic.aioquic.config_schema import (
            AioquicConfig,
        )

        assert "plugin_config" not in AioquicConfig.model_fields
