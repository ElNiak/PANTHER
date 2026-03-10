"""Tests for MvfstConfig hierarchy (PR2)."""

import pytest

from panther.config.core.models.service import ImplementationType, ServiceConfig


class TestMvfstConfigHierarchy:
    def test_isinstance_service_config(self):
        from panther.plugins.services.iut.quic.mvfst.config_schema import MvfstConfig

        mc = MvfstConfig()
        assert isinstance(mc, ServiceConfig)

    def test_implementation_defaults(self):
        from panther.plugins.services.iut.quic.mvfst.config_schema import MvfstConfig

        mc = MvfstConfig()
        assert mc.implementation.name == "mvfst"
        assert mc.implementation.type == ImplementationType.IUT

    def test_protocol_defaults(self):
        from panther.plugins.services.iut.quic.mvfst.config_schema import MvfstConfig

        mc = MvfstConfig()
        assert mc.protocol.name == "quic"

    def test_inherits_docker_fields(self):
        from panther.plugins.services.iut.quic.mvfst.config_schema import MvfstConfig

        mc = MvfstConfig()
        assert hasattr(mc, "docker_image")
        assert hasattr(mc, "build_from_source")

    def test_no_plugin_config_dict(self):
        from panther.plugins.services.iut.quic.mvfst.config_schema import MvfstConfig

        assert "plugin_config" not in MvfstConfig.model_fields

    def test_has_version_class(self):
        from panther.plugins.services.iut.quic.mvfst.config_schema import (
            MvfstConfig,
            MvfstVersion,
        )

        assert MvfstConfig.VERSION_CLASS is MvfstVersion
