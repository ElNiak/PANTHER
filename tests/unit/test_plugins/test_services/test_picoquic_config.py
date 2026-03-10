"""Tests for PicoquicConfig hierarchy (PR2)."""

import pytest

from panther.config.core.models.service import ImplementationType, ServiceConfig


class TestPicoquicConfigHierarchy:
    def test_isinstance_service_config(self):
        from panther.plugins.services.iut.quic.picoquic.config_schema import (
            PicoquicConfig,
        )

        pc = PicoquicConfig()
        assert isinstance(pc, ServiceConfig)

    def test_implementation_defaults(self):
        from panther.plugins.services.iut.quic.picoquic.config_schema import (
            PicoquicConfig,
        )

        pc = PicoquicConfig()
        assert pc.implementation.name == "picoquic"
        assert pc.implementation.type == ImplementationType.IUT

    def test_protocol_defaults(self):
        from panther.plugins.services.iut.quic.picoquic.config_schema import (
            PicoquicConfig,
        )

        pc = PicoquicConfig()
        assert pc.protocol.name == "quic"

    def test_plugin_specific_fields(self):
        from panther.plugins.services.iut.quic.picoquic.config_schema import (
            PicoquicConfig,
        )

        pc = PicoquicConfig()
        assert pc.alpn is None
        assert hasattr(pc, "initial_rtt")
        assert hasattr(pc, "max_stream_data")
        assert hasattr(pc, "max_data")

    def test_inherits_docker_fields(self):
        from panther.plugins.services.iut.quic.picoquic.config_schema import (
            PicoquicConfig,
        )

        pc = PicoquicConfig()
        assert hasattr(pc, "docker_image")
        assert hasattr(pc, "build_from_source")

    def test_no_plugin_config_dict(self):
        from panther.plugins.services.iut.quic.picoquic.config_schema import (
            PicoquicConfig,
        )

        assert "plugin_config" not in PicoquicConfig.model_fields

    def test_has_version_class(self):
        from panther.plugins.services.iut.quic.picoquic.config_schema import (
            PicoquicConfig,
            PicoquicVersion,
        )

        assert PicoquicConfig.VERSION_CLASS is PicoquicVersion
