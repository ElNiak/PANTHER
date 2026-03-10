"""Tests for QuinnConfig hierarchy (PR2)."""

import pytest

from panther.config.core.models.service import ImplementationType, ServiceConfig


class TestQuinnConfigHierarchy:
    def test_isinstance_service_config(self):
        from panther.plugins.services.iut.quic.quinn.config_schema import QuinnConfig

        qc = QuinnConfig()
        assert isinstance(qc, ServiceConfig)

    def test_implementation_defaults(self):
        from panther.plugins.services.iut.quic.quinn.config_schema import QuinnConfig

        qc = QuinnConfig()
        assert qc.implementation.name == "quinn"
        assert qc.implementation.type == ImplementationType.IUT

    def test_protocol_defaults(self):
        from panther.plugins.services.iut.quic.quinn.config_schema import QuinnConfig

        qc = QuinnConfig()
        assert qc.protocol.name == "quic"

    def test_inherits_docker_fields(self):
        from panther.plugins.services.iut.quic.quinn.config_schema import QuinnConfig

        qc = QuinnConfig()
        assert hasattr(qc, "docker_image")
        assert hasattr(qc, "build_from_source")

    def test_no_plugin_config_dict(self):
        from panther.plugins.services.iut.quic.quinn.config_schema import QuinnConfig

        assert "plugin_config" not in QuinnConfig.model_fields

    def test_has_version_class(self):
        from panther.plugins.services.iut.quic.quinn.config_schema import (
            QuinnConfig,
            QuinnVersion,
        )

        assert QuinnConfig.VERSION_CLASS is QuinnVersion
