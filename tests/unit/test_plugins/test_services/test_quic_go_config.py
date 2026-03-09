"""Tests for QuicGoConfig hierarchy (PR2)."""

import pytest

from panther.config.core.models.service import ImplementationType, ServiceConfig


class TestQuicGoConfigHierarchy:
    def test_isinstance_service_config(self):
        from panther.plugins.services.iut.quic.quic_go.config_schema import QuicGoConfig

        qc = QuicGoConfig()
        assert isinstance(qc, ServiceConfig)

    def test_implementation_defaults(self):
        from panther.plugins.services.iut.quic.quic_go.config_schema import QuicGoConfig

        qc = QuicGoConfig()
        assert qc.implementation.name == "quic-go"
        assert qc.implementation.type == ImplementationType.IUT

    def test_protocol_defaults(self):
        from panther.plugins.services.iut.quic.quic_go.config_schema import QuicGoConfig

        qc = QuicGoConfig()
        assert qc.protocol.name == "quic"

    def test_inherits_docker_fields(self):
        from panther.plugins.services.iut.quic.quic_go.config_schema import QuicGoConfig

        qc = QuicGoConfig()
        assert hasattr(qc, "docker_image")
        assert hasattr(qc, "build_from_source")

    def test_no_plugin_config_dict(self):
        from panther.plugins.services.iut.quic.quic_go.config_schema import QuicGoConfig

        assert "plugin_config" not in QuicGoConfig.model_fields

    def test_has_version_class(self):
        from panther.plugins.services.iut.quic.quic_go.config_schema import (
            QuicGoConfig,
            QuicGoVersion,
        )

        assert QuicGoConfig.VERSION_CLASS is QuicGoVersion
