#!/usr/bin/env python3
"""
Comprehensive test suite for PANTHER's packaging system.
Tests build integrity, plugin inclusion, and backward compatibility.
"""

import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Get project root
PROJECT_ROOT = Path(__file__).parent.parent.parent


class TestBuildSystem:
    """Test core build system functionality."""

    @pytest.fixture
    def temp_build_dir(self):
        """Create temporary directory for build testing."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    def test_package_builds_successfully(self, temp_build_dir):
        """Ensure package builds without errors using current build system."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "build",
                "--wheel",
                "--no-isolation",
                "--outdir",
                str(temp_build_dir),
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, f"Build failed: {result.stderr}"

        # Check wheel was created
        wheel_files = list(temp_build_dir.glob("*.whl"))
        assert len(wheel_files) == 1, f"Expected 1 wheel file, found {len(wheel_files)}"

        return wheel_files[0]

    def test_all_plugin_files_included(self, temp_build_dir):
        """Verify all plugin files are included in built package."""
        # Build the wheel
        wheel_path = self.test_package_builds_successfully(temp_build_dir)

        # Extract and check contents
        with zipfile.ZipFile(wheel_path, "r") as wheel:
            wheel_files = wheel.namelist()

            # Critical plugin patterns to check
            critical_patterns = [
                # Service plugins
                "panther/plugins/services/iut/quic/picoquic/",
                "panther/plugins/services/iut/quic/aioquic/",
                "panther/plugins/services/testers/panther_ivy/",
                # Environment plugins
                "panther/plugins/environments/network_environment/docker_compose/",
                "panther/plugins/environments/execution_environment/strace/",
                # Plugin configuration files
                "config_schema.py",
                "Dockerfile",
                ".yaml",
                ".jinja",
                ".j2",
                # Webapp resources
                "panther/webapp/",
                # Type hints
                "panther/py.typed",
            ]

            for pattern in critical_patterns:
                matching_files = [f for f in wheel_files if pattern in f]
                assert (
                    len(matching_files) > 0
                ), f"No files matching pattern '{pattern}' found in wheel"

    def test_entry_points_preserved(self, temp_build_dir):
        """Ensure CLI entry points are correctly configured."""
        wheel_path = self.test_package_builds_successfully(temp_build_dir)

        with zipfile.ZipFile(wheel_path, "r") as wheel:
            # Check for entry_points.txt in metadata
            metadata_files = [f for f in wheel.namelist() if f.endswith("METADATA")]
            assert len(metadata_files) > 0, "No METADATA file found"

            metadata_content = wheel.read(metadata_files[0]).decode("utf-8")

            # Check for required entry points
            assert "panther = panther.__main__:main" in metadata_content
            assert "panther-metrics = panther.metrics.cli:main" in metadata_content
            assert (
                "panther-plugin-tool = panther.plugins.plugin_migration_tool:create_cli"
                in metadata_content
            )

    def test_docker_integration_preserved(self):
        """Ensure Docker-related builder commands still work."""
        # Import the builder
        sys.path.insert(0, str(PROJECT_ROOT))
        from panther_builder import BuildManager

        build_manager = BuildManager()

        # Test Docker detection
        assert hasattr(build_manager, "docker_available")

        # Test that Docker commands are available
        assert hasattr(build_manager, "remove_images_all")
        assert hasattr(build_manager, "remove_images_services")
        assert hasattr(build_manager, "remove_volume")

    def test_metrics_integration_optional(self):
        """Ensure metrics integration works when available."""
        sys.path.insert(0, str(PROJECT_ROOT))
        from panther_builder import BuildManager

        build_manager = BuildManager()

        # Test metrics methods exist
        assert hasattr(build_manager, "start_metrics_collection")
        assert hasattr(build_manager, "stop_metrics_collection_and_flush")

    def test_development_commands_available(self):
        """Ensure all development commands are available."""
        sys.path.insert(0, str(PROJECT_ROOT))
        from panther_builder import BuildManager

        build_manager = BuildManager()

        required_commands = [
            "clean",
            "install_dependencies",
            "build_wheel",
            "install_wheel",
            "install_editable",
            "run_tests",
            "build_docs",
            "serve_docs",
            "check_code_quality",
            "install_precommit",
            "zip_outputs",
        ]

        for command in required_commands:
            assert hasattr(build_manager, command), f"Command '{command}' not found"


class TestPluginCompatibility:
    """Test plugin system compatibility after packaging changes."""

    @pytest.mark.skipif(
        not Path(PROJECT_ROOT / "panther").exists(), reason="Requires installed package"
    )
    def test_plugin_loading_after_packaging_changes(self):
        """Ensure all plugins load correctly after packaging changes."""
        try:
            from panther.plugins.plugin_manager import PluginManager

            pm = PluginManager()
            pm.discover_plugins()

            # Test each plugin type
            plugin_types = ["services", "environments", "protocols"]
            for plugin_type in plugin_types:
                plugins = pm.get_plugins_by_type(plugin_type)
                assert len(plugins) > 0, f"No {plugin_type} plugins found"
        except ImportError:
            pytest.skip("Plugin manager not available in test environment")

    def test_plugin_files_accessibility(self):
        """Test that plugin data files are accessible after installation."""
        plugin_base = PROJECT_ROOT / "panther" / "plugins"

        # Check critical plugin data files
        critical_files = [
            plugin_base / "services" / "iut" / "quic" / "picoquic" / "Dockerfile",
            plugin_base / "services" / "iut" / "quic" / "picoquic" / "config_schema.py",
            plugin_base
            / "environments"
            / "network_environment"
            / "docker_compose"
            / "docker_compose.py",
        ]

        for file_path in critical_files:
            assert file_path.exists(), f"Critical plugin file missing: {file_path}"


class TestPackagingMigration:
    """Test packaging system migration compatibility."""

    def test_setuptools_compatibility(self):
        """Ensure current setuptools configuration works."""
        pyproject_path = PROJECT_ROOT / "pyproject.toml"
        assert pyproject_path.exists(), "pyproject.toml not found"

        # Try to load and validate pyproject.toml
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib

        with open(pyproject_path, "rb") as f:
            config = tomllib.load(f)

        # Check build system configuration
        assert "build-system" in config
        assert "requires" in config["build-system"]
        assert "build-backend" in config["build-system"]

        # Check project metadata
        assert "project" in config
        assert "name" in config["project"]
        assert "version" in config["project"]
        assert "dependencies" in config["project"]

    def test_manifest_inclusion(self):
        """Test MANIFEST.in file inclusion rules."""
        manifest_path = PROJECT_ROOT / "MANIFEST.in"
        assert manifest_path.exists(), "MANIFEST.in not found"

        with open(manifest_path, "r") as f:
            manifest_content = f.read()

        # Check critical inclusions
        assert "recursive-include panther" in manifest_content
        assert "include LICENSE.md" in manifest_content
        assert "include README.md" in manifest_content
        assert "prune outputs" in manifest_content


class TestBuildPerformance:
    """Test and benchmark build performance."""

    def test_build_time_baseline(self, temp_build_dir):
        """Establish baseline build time for comparison."""
        import time

        start_time = time.time()

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "build",
                "--wheel",
                "--no-isolation",
                "--outdir",
                str(temp_build_dir),
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
        )

        build_time = time.time() - start_time

        assert result.returncode == 0, "Build failed"

        # Log build time for future comparison
        print(f"Build time: {build_time:.2f} seconds")

        # Create metrics file for tracking
        metrics_file = temp_build_dir / "build_metrics.json"
        metrics = {
            "build_time_seconds": build_time,
            "build_backend": "setuptools",
            "python_version": sys.version,
        }

        with open(metrics_file, "w") as f:
            json.dump(metrics, f, indent=2)

        # Reasonable build time expectation (adjust as needed)
        assert build_time < 300, f"Build took too long: {build_time:.2f} seconds"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
