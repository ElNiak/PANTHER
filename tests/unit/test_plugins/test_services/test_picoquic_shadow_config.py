"""Tests for PicoquicShadowConfig hierarchy (PR2)."""

import pytest

from panther.config.core.models.service import ImplementationType, ServiceConfig


class TestPicoquicShadowConfigHierarchy:
    def test_isinstance_service_config(self):
        from panther.plugins.services.iut.quic.picoquic_shadow.config_schema import (
            PicoquicShadowConfig,
        )

        pc = PicoquicShadowConfig()
        assert isinstance(pc, ServiceConfig)

    def test_implementation_defaults(self):
        from panther.plugins.services.iut.quic.picoquic_shadow.config_schema import (
            PicoquicShadowConfig,
        )

        pc = PicoquicShadowConfig()
        assert pc.implementation.name == "picoquic_shadow"
        assert pc.implementation.type == ImplementationType.IUT

    def test_protocol_defaults(self):
        from panther.plugins.services.iut.quic.picoquic_shadow.config_schema import (
            PicoquicShadowConfig,
        )

        pc = PicoquicShadowConfig()
        assert pc.protocol.name == "quic"

    def test_inherits_docker_fields(self):
        from panther.plugins.services.iut.quic.picoquic_shadow.config_schema import (
            PicoquicShadowConfig,
        )

        pc = PicoquicShadowConfig()
        assert hasattr(pc, "docker_image")
        assert hasattr(pc, "build_from_source")

    def test_no_plugin_config_dict(self):
        from panther.plugins.services.iut.quic.picoquic_shadow.config_schema import (
            PicoquicShadowConfig,
        )

        assert "plugin_config" not in PicoquicShadowConfig.model_fields

    def test_has_version_class(self):
        from panther.plugins.services.iut.quic.picoquic_shadow.config_schema import (
            PicoquicShadowConfig,
            PicoquicShadowVersion,
        )

        assert PicoquicShadowConfig.VERSION_CLASS is PicoquicShadowVersion
