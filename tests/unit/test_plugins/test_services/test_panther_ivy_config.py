"""Tests for PantherIvyConfig hierarchy (PR2)."""

import pytest

from panther.config.core.models.service import ImplementationType, ServiceConfig


class TestPantherIvyConfigHierarchy:
    def test_isinstance_service_config(self):
        from panther.plugins.services.testers.panther_ivy.config_schema import (
            PantherIvyConfig,
        )

        ic = PantherIvyConfig()
        assert isinstance(ic, ServiceConfig)

    def test_implementation_defaults(self):
        from panther.plugins.services.testers.panther_ivy.config_schema import (
            PantherIvyConfig,
        )

        ic = PantherIvyConfig()
        assert ic.implementation.name == "panther_ivy"
        assert ic.implementation.type == ImplementationType.TESTERS

    def test_protocol_defaults(self):
        from panther.plugins.services.testers.panther_ivy.config_schema import (
            PantherIvyConfig,
        )

        ic = PantherIvyConfig()
        assert ic.protocol.name == "quic"

    def test_plugin_specific_fields(self):
        from panther.plugins.services.testers.panther_ivy.config_schema import (
            PantherIvyConfig,
        )

        ic = PantherIvyConfig()
        assert hasattr(ic, "build_mode")
        assert hasattr(ic, "test")
        assert hasattr(ic, "z3_source")
        assert ic.z3_source == "local"

    def test_inherits_docker_fields(self):
        from panther.plugins.services.testers.panther_ivy.config_schema import (
            PantherIvyConfig,
        )

        ic = PantherIvyConfig()
        assert hasattr(ic, "docker_image")
        assert hasattr(ic, "build_from_source")

    def test_no_plugin_config_dict(self):
        from panther.plugins.services.testers.panther_ivy.config_schema import (
            PantherIvyConfig,
        )

        assert "plugin_config" not in PantherIvyConfig.model_fields

    def test_has_version_class(self):
        from panther.plugins.services.testers.panther_ivy.config_schema import (
            PantherIvyConfig,
            PantherIvyVersion,
        )

        assert PantherIvyConfig.VERSION_CLASS is PantherIvyVersion
