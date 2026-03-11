"""Tests for automatic plugin structure conversion.

This test suite ensures that the PluginStructureConverter properly
handles bidirectional conversions and prevents field loss.
"""

from pathlib import Path

import pytest

from panther.plugins.core.conversion.structure_converter import (
    PluginStructureConverter,
    auto_convert_manifest_to_metadata,
)
from panther.plugins.core.structures.plugin_dependency import PluginDependency
from panther.plugins.core.structures.plugin_manifest import PluginManifest
from panther.plugins.core.structures.plugin_metadata import PluginMetadata
from panther.plugins.core.structures.plugin_type import PluginType


class TestPluginStructureConverter:
    """Test the PluginStructureConverter class."""

    @pytest.fixture
    def converter(self):
        """Create a PluginStructureConverter instance."""
        return PluginStructureConverter()

    @pytest.fixture
    def sample_manifest(self):
        """Create a sample PluginManifest with all fields populated."""
        return PluginManifest(
            name="test_plugin",
            version="1.0.0",
            type=PluginType.EXECUTION_ENVIRONMENT,
            author="Test Author",
            description="Test plugin for conversion testing",
            license="MIT",
            homepage="https://example.com",
            min_panther_version="1.0.0",
            max_panther_version="2.0.0",
            dependencies=[
                PluginDependency(name="dep1", version_spec=">=1.0.0"),
                PluginDependency(name="dep2", version_spec="*"),
            ],
            config_schema={"timeout": {"type": "number", "default": 60}},
            default_config={"timeout": 60},
            entry_point="test.plugin.TestPlugin",
            file_path="/path/to/plugin.py",
            runtime_mode="debug",  # This is the field that was getting lost!
            supported_protocols=["quic", "tcp"],
            supported_events=["start", "stop"],
            capabilities=["debugging", "profiling"],
            tags=["testing", "development"],
            external_dependencies=["strace>=4.0"],
        )

    @pytest.fixture
    def sample_metadata(self):
        """Create a sample PluginMetadata with all fields populated."""
        return PluginMetadata(
            name="test_plugin",
            version="1.0.0",
            type="execution_environment",
            author="Test Author",
            description="Test plugin for conversion testing",
            path=Path("/path/to/plugin.py"),
            dependencies=["dep1", "dep2"],
            supported_protocols=["quic", "tcp"],
            capabilities=["debugging", "profiling"],
            tags=["testing", "development"],
            runtime_mode="debug",  # Critical field to preserve
            external_dependencies=["strace>=4.0"],
        )

    def test_manifest_to_metadata_conversion(self, converter, sample_manifest):
        """Test converting PluginManifest to PluginMetadata."""
        metadata = converter.manifest_to_metadata(sample_manifest)

        # Verify core fields are preserved
        assert metadata.name == sample_manifest.name
        assert metadata.version == sample_manifest.version
        assert metadata.type == sample_manifest.type.value  # Enum to string
        assert metadata.author == sample_manifest.author
        assert metadata.description == sample_manifest.description

        # Verify the critical runtime_mode field is preserved
        assert metadata.runtime_mode == sample_manifest.runtime_mode

        # Verify collections are preserved
        assert metadata.supported_protocols == sample_manifest.supported_protocols
        assert metadata.capabilities == sample_manifest.capabilities
        assert metadata.tags == sample_manifest.tags
        assert metadata.external_dependencies == sample_manifest.external_dependencies

        # Verify dependencies are converted to strings
        assert len(metadata.dependencies) == 2
        assert "dep1" in metadata.dependencies
        assert "dep2" in metadata.dependencies

        # Verify path conversion: file_path (manifest) is mapped to path (metadata)
        # via _apply_special_mappings_to_metadata reading manifest.file_path directly.
        assert metadata.path == Path(sample_manifest.file_path)

    def test_convenience_function_manifest_to_metadata(self, sample_manifest):
        """Test the auto_convert_manifest_to_metadata convenience function."""
        metadata = auto_convert_manifest_to_metadata(sample_manifest)
        assert type(metadata).__name__ == "PluginMetadata"
        assert metadata.name == sample_manifest.name
        assert metadata.runtime_mode == sample_manifest.runtime_mode

    def test_missing_runtime_mode_handling(self, converter):
        """Test handling of plugins without runtime_mode."""
        manifest_without_runtime = PluginManifest(
            name="test_plugin",
            version="1.0.0",
            type=PluginType.IUT,
            runtime_mode=None,  # Explicitly None
        )

        metadata = converter.manifest_to_metadata(manifest_without_runtime)
        assert metadata.runtime_mode is None

    def test_type_conversion_edge_cases(self, converter):
        """Test edge cases in type conversion."""
        manifest = PluginManifest(
            name="test",
            version="1.0.0",
            type=PluginType.TESTER,
        )

        metadata = converter.manifest_to_metadata(manifest)
        assert metadata.type == "tester"

    def test_validation_errors(self, converter):
        """Test that validation catches type errors on required fields."""
        # The _validate_metadata_conversion checks isinstance(data["name"], str).
        # To trigger that, we need to inject a non-string name into the conversion
        # data. We do this by creating a manifest with a valid name, then patching
        # the manifest's name attribute to an integer before conversion.
        invalid_manifest = PluginManifest(
            name="valid",
            version="1.0.0",
            type=PluginType.IUT,
        )
        # Patch name to int; dataclass doesn't enforce types at construction
        object.__setattr__(invalid_manifest, "name", 123)

        with pytest.raises(ValueError, match="Invalid type for 'name'"):
            converter.manifest_to_metadata(invalid_manifest)


class TestRuntimeModeRegression:
    """Regression tests specifically for the runtime_mode field loss bug."""

    def test_strace_plugin_runtime_mode_preservation(self):
        """Test that simulates the exact strace plugin scenario."""
        strace_manifest = PluginManifest(
            name="strace",
            version="1.0.0",
            type=PluginType.EXECUTION_ENVIRONMENT,
            author="PANTHER Team",
            description="System call tracing execution environment",
            capabilities=["syscall_tracing", "performance_analysis", "debugging"],
            external_dependencies=["strace>=4.0"],
            runtime_mode="debug",
        )

        # Convert to metadata (as done in PluginDiscovery)
        metadata = auto_convert_manifest_to_metadata(strace_manifest)
        assert metadata.runtime_mode == "debug"

    def test_all_runtime_modes_preserved(self):
        """Test that all valid runtime modes are preserved through manifest->metadata."""
        runtime_modes = ["minimal", "debug", "profile"]

        for mode in runtime_modes:
            manifest = PluginManifest(
                name=f"test_{mode}",
                version="1.0.0",
                type=PluginType.EXECUTION_ENVIRONMENT,
                runtime_mode=mode,
            )

            metadata = auto_convert_manifest_to_metadata(manifest)
            assert metadata.runtime_mode == mode
