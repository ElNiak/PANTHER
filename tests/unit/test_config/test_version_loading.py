"""Tests for VERSION_CLASS pattern and ServicePluginConfig.load_version()."""

from typing import Dict, List

import pytest
import yaml

from panther.config.core.models.plugin import ServicePluginConfig
from panther.config.core.models.service import VersionBase

pytestmark = [pytest.mark.unit]


class DummyVersion(VersionBase):
    """Test version class with defaults."""

    version: str = ""
    commit: str = ""
    dependencies: List[Dict[str, str]] = []


class DummyPluginConfig(ServicePluginConfig):
    """Plugin config with VERSION_CLASS set."""

    VERSION_CLASS = DummyVersion
    type: str = "iut"


class NoVersionPluginConfig(ServicePluginConfig):
    """Plugin config without VERSION_CLASS."""

    type: str = "iut"


class TestLoadVersionWithoutVersionClass:
    """Test load_version when VERSION_CLASS is None."""

    def test_returns_none(self):
        result = NoVersionPluginConfig.load_version()
        assert result is None


class TestLoadVersionWithVersionClass:
    """Test load_version when VERSION_CLASS is set."""

    def test_returns_defaults_when_no_version_dir(self, tmp_path):
        """When version_configs_dir doesn't exist, returns VERSION_CLASS() defaults."""
        result = DummyPluginConfig.load_version(
            version_configs_dir=str(tmp_path / "nonexistent")
        )
        assert isinstance(result, DummyVersion)
        assert result.version == ""
        assert result.commit == ""

    def test_returns_defaults_when_dir_empty(self, tmp_path):
        """When version_configs_dir exists but has no YAML files."""
        version_dir = tmp_path / "version_configs"
        version_dir.mkdir()
        result = DummyPluginConfig.load_version(version_configs_dir=str(version_dir))
        assert isinstance(result, DummyVersion)

    def test_loads_specific_version(self, tmp_path):
        """When a specific version is requested, loads that file."""
        version_dir = tmp_path / "version_configs"
        version_dir.mkdir()
        (version_dir / "rfc9000.yaml").write_text(
            yaml.dump({"version": "1.2.3", "commit": "abc123"})
        )

        result = DummyPluginConfig.load_version(
            version_configs_dir=str(version_dir), version="rfc9000"
        )
        assert result.version == "1.2.3"
        assert result.commit == "abc123"

    def test_loads_first_version_when_none_specified(self, tmp_path):
        """When no version specified, loads first YAML file (sorted)."""
        version_dir = tmp_path / "version_configs"
        version_dir.mkdir()
        (version_dir / "beta.yaml").write_text(
            yaml.dump({"version": "0.9", "commit": "bbb"})
        )
        (version_dir / "alpha.yaml").write_text(
            yaml.dump({"version": "0.1", "commit": "aaa"})
        )

        result = DummyPluginConfig.load_version(version_configs_dir=str(version_dir))
        # Should load alpha.yaml (sorted first)
        assert result.version == "0.1"
        assert result.commit == "aaa"

    def test_raises_on_missing_specific_version(self, tmp_path):
        """When a specific version file doesn't exist, raises FileNotFoundError."""
        version_dir = tmp_path / "version_configs"
        version_dir.mkdir()

        with pytest.raises(FileNotFoundError, match="not found"):
            DummyPluginConfig.load_version(
                version_configs_dir=str(version_dir), version="nonexistent"
            )

    def test_merges_partial_yaml_over_defaults(self, tmp_path):
        """Partial YAML files produce valid config via OmegaConf merge."""
        version_dir = tmp_path / "version_configs"
        version_dir.mkdir()
        (version_dir / "partial.yaml").write_text(yaml.dump({"version": "2.0"}))

        result = DummyPluginConfig.load_version(
            version_configs_dir=str(version_dir), version="partial"
        )
        assert result.version == "2.0"
        assert result.commit == ""  # default from DummyVersion

    def test_protocol_version_override_takes_precedence(self, tmp_path):
        """protocol_version_override should be used over version param."""
        version_dir = tmp_path / "version_configs"
        version_dir.mkdir()
        (version_dir / "override.yaml").write_text(
            yaml.dump({"version": "override-ver"})
        )
        (version_dir / "original.yaml").write_text(
            yaml.dump({"version": "original-ver"})
        )

        result = DummyPluginConfig.load_version(
            version_configs_dir=str(version_dir),
            version="original",
            protocol_version_override="override",
        )
        assert result.version == "override-ver"
