"""Tests for QuantConfig hierarchy (PR2)."""

import pytest

from panther.config.core.models.service import ImplementationType, ServiceConfig


class TestQuantConfigHierarchy:
    def test_isinstance_service_config(self):
        from panther.plugins.services.iut.quic.quant.config_schema import QuantConfig

        qc = QuantConfig()
        assert isinstance(qc, ServiceConfig)

    def test_implementation_defaults(self):
        from panther.plugins.services.iut.quic.quant.config_schema import QuantConfig

        qc = QuantConfig()
        assert qc.implementation.name == "quant"
        assert qc.implementation.type == ImplementationType.IUT

    def test_protocol_defaults(self):
        from panther.plugins.services.iut.quic.quant.config_schema import QuantConfig

        qc = QuantConfig()
        assert qc.protocol.name == "quic"

    def test_inherits_docker_fields(self):
        from panther.plugins.services.iut.quic.quant.config_schema import QuantConfig

        qc = QuantConfig()
        assert hasattr(qc, "docker_image")
        assert hasattr(qc, "build_from_source")

    def test_no_plugin_config_dict(self):
        from panther.plugins.services.iut.quic.quant.config_schema import QuantConfig

        assert "plugin_config" not in QuantConfig.model_fields

    def test_has_version_class(self):
        from panther.plugins.services.iut.quic.quant.config_schema import (
            QuantConfig,
            QuantVersion,
        )

        assert QuantConfig.VERSION_CLASS is QuantVersion
