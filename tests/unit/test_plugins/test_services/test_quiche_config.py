"""Tests for QuicheConfig hierarchy (PR2)."""

import pytest

from panther.config.core.models.service import ImplementationType, ServiceConfig


class TestQuicheConfigHierarchy:
    def test_isinstance_service_config(self):
        from panther.plugins.services.iut.quic.quiche.config_schema import QuicheConfig

        qc = QuicheConfig()
        assert isinstance(qc, ServiceConfig)

    def test_implementation_defaults(self):
        from panther.plugins.services.iut.quic.quiche.config_schema import QuicheConfig

        qc = QuicheConfig()
        assert qc.implementation.name == "quiche"
        assert qc.implementation.type == ImplementationType.IUT

    def test_protocol_defaults(self):
        from panther.plugins.services.iut.quic.quiche.config_schema import QuicheConfig

        qc = QuicheConfig()
        assert qc.protocol.name == "quic"

    def test_inherits_docker_fields(self):
        from panther.plugins.services.iut.quic.quiche.config_schema import QuicheConfig

        qc = QuicheConfig()
        assert hasattr(qc, "docker_image")
        assert hasattr(qc, "build_from_source")

    def test_no_plugin_config_dict(self):
        from panther.plugins.services.iut.quic.quiche.config_schema import QuicheConfig

        assert "plugin_config" not in QuicheConfig.model_fields

    def test_has_version_class(self):
        from panther.plugins.services.iut.quic.quiche.config_schema import (
            QuicheConfig,
            QuicheVersion,
        )

        assert QuicheConfig.VERSION_CLASS is QuicheVersion
