"""Test that PantherIvyConfig has a declared version field."""

from panther.plugins.services.testers.panther_ivy.config_schema import (
    PantherIvyConfig,
    PantherIvyVersion,
)


class TestPantherIvyVersionField:
    def test_version_in_model_fields(self):
        """Version must be a declared field, not just extra='allow'."""
        assert "version" in PantherIvyConfig.model_fields

    def test_version_type(self):
        """Version field should be typed as PantherIvyVersion."""
        cfg = PantherIvyConfig()
        assert isinstance(cfg.version, PantherIvyVersion)
