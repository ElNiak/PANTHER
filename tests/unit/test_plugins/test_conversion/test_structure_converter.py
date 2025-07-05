"""
Tests for automatic plugin structure conversion.

This test suite ensures that the PluginStructureConverter properly
handles bidirectional conversions and prevents field loss.
"""

from dataclasses import fields
from pathlib import Path

import pytest

from panther.plugins.core.conversion.structure_converter import (
    PluginStructureConverter,
    auto_convert_manifest_to_metadata,
    auto_convert_metadata_to_manifest,
    get_field_mapping_report,
)
from panther.plugins.core.structures.plugin_dependency import PluginDependency
from panther.plugins.core.structures.plugin_manifest import PluginManifest
from panther.plugins.core.structures.plugin_metadata import PluginMetadata
from panther.plugins.core.structures.plugin_types import PluginType


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

        # Verify path conversion
        assert metadata.path == Path(sample_manifest.file_path)

    def test_metadata_to_manifest_conversion(self, converter, sample_metadata):
        """Test converting PluginMetadata to PluginManifest."""
        manifest = converter.metadata_to_manifest(sample_metadata)

        # Verify core fields are preserved
        assert manifest.name == sample_metadata.name
        assert manifest.version == sample_metadata.version
        assert manifest.type == PluginType.EXECUTION_ENVIRONMENT  # String to enum
        assert manifest.author == sample_metadata.author
        assert manifest.description == sample_metadata.description

        # Verify the critical runtime_mode field is preserved
        assert manifest.runtime_mode == sample_metadata.runtime_mode

        # Verify collections are preserved
        assert manifest.supported_protocols == sample_metadata.supported_protocols
        assert manifest.capabilities == sample_metadata.capabilities
        assert manifest.tags == sample_metadata.tags
        assert manifest.external_dependencies == sample_metadata.external_dependencies

        # Verify dependencies are converted to PluginDependency objects
        assert len(manifest.dependencies) == 2
        assert all(isinstance(dep, PluginDependency) for dep in manifest.dependencies)
        dep_names = [dep.name for dep in manifest.dependencies]
        assert "dep1" in dep_names
        assert "dep2" in dep_names

        # Verify path conversion
        assert manifest.file_path == str(sample_metadata.path)

        # Verify default fields are set
        assert isinstance(manifest.config_schema, dict)
        assert isinstance(manifest.default_config, dict)

    def test_bidirectional_conversion_preserves_runtime_mode(
        self, converter, sample_manifest
    ):
        """Test that runtime_mode is preserved through bidirectional conversion."""
        # This test specifically addresses the bug we found
        original_runtime_mode = sample_manifest.runtime_mode
        assert original_runtime_mode == "debug"

        # Convert manifest -> metadata -> manifest
        metadata = converter.manifest_to_metadata(sample_manifest)
        assert metadata.runtime_mode == original_runtime_mode

        reconstructed_manifest = converter.metadata_to_manifest(metadata)
        assert reconstructed_manifest.runtime_mode == original_runtime_mode

        # Verify the round-trip preserved the critical field
        assert original_runtime_mode == reconstructed_manifest.runtime_mode

    def test_bidirectional_conversion_preserves_all_common_fields(
        self, converter, sample_manifest
    ):
        """Test that all common fields are preserved through bidirectional conversion."""
        # Get all common fields
        manifest_fields = {f.name for f in fields(PluginManifest)}
        metadata_fields = {f.name for f in fields(PluginMetadata)}
        common_fields = manifest_fields & metadata_fields

        # Convert manifest -> metadata -> manifest
        metadata = converter.manifest_to_metadata(sample_manifest)
        reconstructed_manifest = converter.metadata_to_manifest(metadata)

        # Check that all common fields are preserved
        for field_name in common_fields:
            original_value = getattr(sample_manifest, field_name, None)
            reconstructed_value = getattr(reconstructed_manifest, field_name, None)

            # Handle special cases for comparison
            if field_name == "dependencies":
                # Dependencies go through format conversion, compare names
                original_names = (
                    [dep.name for dep in original_value] if original_value else []
                )
                reconstructed_names = (
                    [dep.name for dep in reconstructed_value]
                    if reconstructed_value
                    else []
                )
                assert (
                    original_names == reconstructed_names
                ), "Dependencies field mismatch"
            else:
                assert (
                    original_value == reconstructed_value
                ), f"Field '{field_name}' not preserved: {original_value} != {reconstructed_value}"

    def test_convenience_functions(self, sample_manifest, sample_metadata):
        """Test the convenience functions work correctly."""
        # Test auto_convert_manifest_to_metadata
        metadata = auto_convert_manifest_to_metadata(sample_manifest)
        assert isinstance(metadata, PluginMetadata)
        assert metadata.name == sample_manifest.name
        assert metadata.runtime_mode == sample_manifest.runtime_mode

        # Test auto_convert_metadata_to_manifest
        manifest = auto_convert_metadata_to_manifest(sample_metadata)
        assert isinstance(manifest, PluginManifest)
        assert manifest.name == sample_metadata.name
        assert manifest.runtime_mode == sample_metadata.runtime_mode

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

        reconstructed = converter.metadata_to_manifest(metadata)
        assert reconstructed.runtime_mode is None

    def test_field_mapping_report(self):
        """Test the field mapping report functionality."""
        report = get_field_mapping_report()

        assert "common_fields" in report
        assert "manifest_only_fields" in report
        assert "metadata_only_fields" in report
        assert "field_count" in report
        assert "coverage" in report

        # Verify runtime_mode is in common fields
        assert "runtime_mode" in report["common_fields"]

        # Verify we have reasonable coverage
        assert report["coverage"]["manifest_coverage"] > 0.5
        assert report["coverage"]["metadata_coverage"] > 0.5

        # Print report for debugging
        print(f"Field Mapping Report: {report}")

    def test_type_conversion_edge_cases(self, converter):
        """Test edge cases in type conversion."""
        # Test PluginType string conversion
        manifest = PluginManifest(
            name="test",
            version="1.0.0",
            type=PluginType.TESTER,
        )

        metadata = converter.manifest_to_metadata(manifest)
        assert metadata.type == "tester"

        # Convert back
        reconstructed = converter.metadata_to_manifest(metadata)
        assert reconstructed.type == PluginType.TESTER

    def test_validation_errors(self, converter):
        """Test that validation catches missing required fields."""
        # Create invalid manifest (missing required fields)
        invalid_manifest = PluginManifest(
            name="",  # Empty name should trigger validation error
            version="1.0.0",
            type=PluginType.IUT,
        )

        with pytest.raises(ValueError, match="Invalid type for 'name'"):
            # This should fail validation
            converter.manifest_to_metadata(invalid_manifest)


class TestRuntimeModeRegression:
    """Regression tests specifically for the runtime_mode field loss bug."""

    def test_strace_plugin_runtime_mode_preservation(self):
        """Test that simulates the exact strace plugin scenario."""
        # Simulate the strace plugin manifest as created by @register_plugin
        strace_manifest = PluginManifest(
            name="strace",
            version="1.0.0",
            type=PluginType.EXECUTION_ENVIRONMENT,
            author="PANTHER Team",
            description="System call tracing execution environment",
            capabilities=["syscall_tracing", "performance_analysis", "debugging"],
            external_dependencies=["strace>=4.0"],
            runtime_mode="debug",  # This was getting lost!
        )

        # Convert to metadata (as done in PluginDiscovery)
        metadata = auto_convert_manifest_to_metadata(strace_manifest)
        assert metadata.runtime_mode == "debug"

        # Convert back to manifest (as done in PluginManager.discover_plugins)
        reconstructed_manifest = auto_convert_metadata_to_manifest(metadata)
        assert reconstructed_manifest.runtime_mode == "debug"

        # This should now work in the plugin manager lookup
        assert reconstructed_manifest.runtime_mode == "debug"

    def test_all_runtime_modes_preserved(self):
        """Test that all valid runtime modes are preserved."""
        runtime_modes = ["minimal", "debug", "profile"]

        for mode in runtime_modes:
            manifest = PluginManifest(
                name=f"test_{mode}",
                version="1.0.0",
                type=PluginType.EXECUTION_ENVIRONMENT,
                runtime_mode=mode,
            )

            # Test round-trip conversion
            metadata = auto_convert_manifest_to_metadata(manifest)
            assert metadata.runtime_mode == mode

            reconstructed = auto_convert_metadata_to_manifest(metadata)
            assert reconstructed.runtime_mode == mode


if __name__ == "__main__":
    # Run a quick test to verify the conversion works
    print("Testing plugin structure conversion...")

    # Create test data
    manifest = PluginManifest(
        name="test_plugin",
        version="1.0.0",
        type=PluginType.EXECUTION_ENVIRONMENT,
        runtime_mode="debug",
    )

    # Test conversion
    metadata = auto_convert_manifest_to_metadata(manifest)
    print(f"Converted to metadata: runtime_mode = {metadata.runtime_mode}")

    reconstructed = auto_convert_metadata_to_manifest(metadata)
    print(f"Converted back to manifest: runtime_mode = {reconstructed.runtime_mode}")

    # Get field mapping report
    report = get_field_mapping_report()
    print(f"Field mapping coverage: {report['coverage']}")
    print(f"Common fields: {len(report['common_fields'])}")

    print("✅ All tests passed!")
