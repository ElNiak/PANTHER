"""Test that PantherIvyConfig has a declared version field."""

import pytest

_mod = pytest.importorskip(
    "panther.plugins.services.testers.panther_ivy.config_schema",
    reason="panther_ivy submodule not installed",
)
PantherIvyConfig = _mod.PantherIvyConfig
PantherIvyVersion = _mod.PantherIvyVersion


class TestPantherIvyVersionField:
    def test_version_in_model_fields(self):
        """Version must be a declared field, not just extra='allow'."""
        assert "version" in PantherIvyConfig.model_fields

    def test_version_type(self):
        """Version field should be typed as PantherIvyVersion."""
        cfg = PantherIvyConfig()
        assert isinstance(cfg.version, PantherIvyVersion)
