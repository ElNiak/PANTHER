"""Tests that ImplementationConfig correctly handles all declared + extra fields."""

import pytest

from panther.config.core.models.service import ImplementationConfig


class TestImplementationConfig:
    def test_declared_fields_preserved(self):
        """All 6 declared fields should be accessible after construction."""
        cfg = ImplementationConfig(
            name="test",
            type="iut",
            version="1.0",
            version_config={"commit": "abc"},
            shadow_compatible=True,
            gperf_compatible=True,
        )
        assert cfg.name == "test"
        assert cfg.version == "1.0"
        assert cfg.version_config == {"commit": "abc"}
        assert cfg.shadow_compatible is True
        assert cfg.gperf_compatible is True

    def test_extra_fields_in_model_extra(self):
        """Plugin-specific fields should be in model_extra, not lost."""
        cfg = ImplementationConfig(
            name="panther_ivy",
            type="testers",
            test="quic_client_test_max",
            build_mode="rel-lto",
        )
        assert cfg.name == "panther_ivy"
        # Extra fields accessible via model_extra
        assert cfg.model_extra["test"] == "quic_client_test_max"
        assert cfg.model_extra["build_mode"] == "rel-lto"

    def test_model_dump_includes_extras(self):
        """model_dump() should include both declared and extra fields."""
        cfg = ImplementationConfig(
            name="picoquic",
            type="iut",
            build_mode="rel-lto",
        )
        dumped = cfg.model_dump()
        assert dumped["name"] == "picoquic"
        assert dumped["build_mode"] == "rel-lto"

    def test_version_config_not_lost(self):
        """Regression test for the old __init__ that lost 3 declared fields.

        The old __init__ used known_fields={name,type,version}
        which lost version_config, shadow_compatible, gperf_compatible.
        """
        cfg = ImplementationConfig(
            name="test",
            type="iut",
            version_config={"commit": "abc", "branch": "main"},
            shadow_compatible=True,
        )
        dumped = cfg.model_dump()
        assert dumped["version_config"] == {"commit": "abc", "branch": "main"}
        assert dumped["shadow_compatible"] is True
