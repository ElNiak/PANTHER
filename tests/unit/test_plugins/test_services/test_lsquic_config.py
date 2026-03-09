"""Tests for LsquicConfig hierarchy (PR2)."""

import pytest

from panther.config.core.models.service import ImplementationType, ServiceConfig


class TestLsquicConfigHierarchy:
    def test_isinstance_service_config(self):
        from panther.plugins.services.iut.quic.lsquic.config_schema import LsquicConfig

        lc = LsquicConfig()
        assert isinstance(lc, ServiceConfig)

    def test_implementation_defaults(self):
        from panther.plugins.services.iut.quic.lsquic.config_schema import LsquicConfig

        lc = LsquicConfig()
        assert lc.implementation.name == "lsquic"
        assert lc.implementation.type == ImplementationType.IUT

    def test_protocol_defaults(self):
        from panther.plugins.services.iut.quic.lsquic.config_schema import LsquicConfig

        lc = LsquicConfig()
        assert lc.protocol.name == "quic"

    def test_plugin_specific_fields(self):
        from panther.plugins.services.iut.quic.lsquic.config_schema import LsquicConfig

        lc = LsquicConfig()
        assert lc.doc_root == "/var/www"
        assert lc.enable_push is True

    def test_inherits_docker_fields(self):
        from panther.plugins.services.iut.quic.lsquic.config_schema import LsquicConfig

        lc = LsquicConfig()
        assert hasattr(lc, "docker_image")
        assert hasattr(lc, "build_from_source")

    def test_no_plugin_config_dict(self):
        from panther.plugins.services.iut.quic.lsquic.config_schema import LsquicConfig

        assert "plugin_config" not in LsquicConfig.model_fields
