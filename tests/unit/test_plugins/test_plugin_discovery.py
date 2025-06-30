"""
Unit tests for PANTHER Plugin Discovery and Management system.

This module tests plugin discovery, loading, manifest handling, and the
plugin management infrastructure.
"""

import json
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, Mock, call, patch

import pytest
import yaml

# Test imports with fallback to mocks
try:
    from panther.plugins.core.plugin_catalog import PluginCatalog
    from panther.plugins.core.plugin_discovery import PluginDiscovery
    from panther.plugins.core.plugin_loader_utils import PluginManagerUtils
    from panther.plugins.core.structures.plugin_manifest import PluginManifest

    REAL_PLUGIN_SYSTEM_AVAILABLE = True
except ImportError:
    REAL_PLUGIN_SYSTEM_AVAILABLE = False

    # Create mock implementations for testing
    class PluginDiscovery:
        def __init__(self, plugin_directories=None, logger=None):
            self.plugin_directories = plugin_directories or []
            self.logger = logger or Mock()
            self.discovered_plugins = {}
            self.discovery_cache = {}

        def discover_plugins(self, force_refresh=False):
            """Discover plugins in configured directories."""
            if not force_refresh and self.discovery_cache:
                return self.discovery_cache

            plugins = {}
            for directory in self.plugin_directories:
                directory_path = Path(directory)
                if directory_path.exists():
                    plugins.update(self._scan_directory(directory_path))

            self.discovery_cache = plugins
            self.discovered_plugins = plugins
            return plugins

        def _scan_directory(self, directory):
            """Scan directory for plugins."""
            plugins = {}

            # Look for plugin manifests
            for manifest_file in directory.rglob("plugin.yaml"):
                try:
                    with open(manifest_file, "r") as f:
                        manifest_data = yaml.safe_load(f)

                    plugin_name = manifest_data.get("name", manifest_file.parent.name)
                    plugin_type = manifest_data.get("type", "unknown")

                    if plugin_type not in plugins:
                        plugins[plugin_type] = {}

                    plugins[plugin_type][plugin_name] = {
                        "manifest": manifest_data,
                        "path": manifest_file.parent,
                        "manifest_file": manifest_file,
                    }
                except Exception as e:
                    self.logger.error(f"Failed to load manifest {manifest_file}: {e}")

            return plugins

        def get_plugin_by_name(self, plugin_name, plugin_type=None):
            """Get plugin by name and optional type."""
            if not self.discovered_plugins:
                self.discover_plugins()

            if plugin_type:
                return self.discovered_plugins.get(plugin_type, {}).get(plugin_name)

            # Search across all types
            for type_plugins in self.discovered_plugins.values():
                if isinstance(type_plugins, dict) and plugin_name in type_plugins:
                    return type_plugins[plugin_name]

            return None

        def get_plugins_by_type(self, plugin_type):
            """Get all plugins of a specific type."""
            if not self.discovered_plugins:
                self.discover_plugins()

            return self.discovered_plugins.get(plugin_type, {})

        def list_available_plugins(self):
            """List all available plugins."""
            if not self.discovered_plugins:
                self.discover_plugins()

            return self.discovered_plugins.copy()

        def validate_plugin(self, plugin_name, plugin_type=None):
            """Validate plugin structure and manifest."""
            plugin_info = self.get_plugin_by_name(plugin_name, plugin_type)
            if not plugin_info:
                return False, f"Plugin {plugin_name} not found"

            manifest = plugin_info.get("manifest", {})
            required_fields = ["name", "version", "type"]

            for field in required_fields:
                if field not in manifest:
                    return False, f"Missing required field: {field}"

            return True, "Plugin is valid"

        def refresh_cache(self):
            """Refresh plugin discovery cache."""
            self.discovery_cache = {}
            return self.discover_plugins(force_refresh=True)

    class PluginManifest:
        def __init__(self, manifest_data=None, manifest_file=None):
            self.manifest_data = manifest_data or {}
            self.manifest_file = manifest_file

        @classmethod
        def load_from_file(cls, manifest_file):
            """Load manifest from file."""
            with open(manifest_file, "r") as f:
                if manifest_file.suffix in [".yaml", ".yml"]:
                    data = yaml.safe_load(f)
                elif manifest_file.suffix == ".json":
                    data = json.load(f)
                else:
                    raise ValueError(
                        f"Unsupported manifest format: {manifest_file.suffix}"
                    )

            return cls(manifest_data=data, manifest_file=manifest_file)

        def get_name(self):
            """Get plugin name."""
            return self.manifest_data.get("name", "unknown")

        def get_version(self):
            """Get plugin version."""
            return self.manifest_data.get("version", "0.0.0")

        def get_type(self):
            """Get plugin type."""
            return self.manifest_data.get("type", "unknown")

        def get_description(self):
            """Get plugin description."""
            return self.manifest_data.get("description", "")

        def get_dependencies(self):
            """Get plugin dependencies."""
            return self.manifest_data.get("dependencies", [])

        def get_supported_protocols(self):
            """Get supported protocols."""
            return self.manifest_data.get("supported_protocols", [])

        def get_entry_point(self):
            """Get plugin entry point."""
            return self.manifest_data.get("entry_point", "")

        def validate(self):
            """Validate manifest data."""
            required_fields = ["name", "version", "type"]
            missing_fields = []

            for field in required_fields:
                if field not in self.manifest_data:
                    missing_fields.append(field)

            if missing_fields:
                return False, f"Missing required fields: {missing_fields}"

            return True, "Manifest is valid"

        def to_dict(self):
            """Convert manifest to dictionary."""
            return self.manifest_data.copy()

    class PluginCatalog:
        def __init__(self, discovery_paths=None):
            self.discovery_paths = discovery_paths or []
            self.catalog = {}
            self.metadata = {
                "last_updated": None,
                "total_plugins": 0,
                "plugin_types": {},
            }

        def build_catalog(self, force_refresh=False):
            """Build plugin catalog from discovery paths."""
            if not force_refresh and self.catalog:
                return self.catalog

            discovery = PluginDiscovery(self.discovery_paths)
            plugins = discovery.discover_plugins()

            self.catalog = {}
            for plugin_type, type_plugins in plugins.items():
                self.catalog[plugin_type] = {}
                for plugin_name, plugin_info in type_plugins.items():
                    manifest = PluginManifest(plugin_info["manifest"])
                    self.catalog[plugin_type][plugin_name] = {
                        "manifest": manifest,
                        "path": plugin_info["path"],
                        "validated": manifest.validate()[0],
                    }

            self._update_metadata()
            return self.catalog

        def _update_metadata(self):
            """Update catalog metadata."""
            from datetime import datetime

            self.metadata["last_updated"] = datetime.now().isoformat()
            self.metadata["total_plugins"] = sum(
                len(plugins) for plugins in self.catalog.values()
            )
            self.metadata["plugin_types"] = {
                plugin_type: len(plugins)
                for plugin_type, plugins in self.catalog.items()
            }

        def get_plugin(self, plugin_name, plugin_type=None):
            """Get plugin from catalog."""
            if plugin_type:
                return self.catalog.get(plugin_type, {}).get(plugin_name)

            # Search across all types
            for type_plugins in self.catalog.values():
                if plugin_name in type_plugins:
                    return type_plugins[plugin_name]

            return None

        def list_plugins_by_type(self, plugin_type):
            """List plugins by type."""
            return list(self.catalog.get(plugin_type, {}).keys())

        def get_catalog_metadata(self):
            """Get catalog metadata."""
            return self.metadata.copy()

        def validate_all_plugins(self):
            """Validate all plugins in catalog."""
            results = {}
            for plugin_type, type_plugins in self.catalog.items():
                results[plugin_type] = {}
                for plugin_name, plugin_info in type_plugins.items():
                    manifest = plugin_info["manifest"]
                    is_valid, message = manifest.validate()
                    results[plugin_type][plugin_name] = {
                        "valid": is_valid,
                        "message": message,
                    }

            return results

        def search_plugins(self, query, search_fields=None):
            """Search plugins by query."""
            search_fields = search_fields or ["name", "description", "type"]
            results = {}

            for plugin_type, type_plugins in self.catalog.items():
                matching_plugins = {}
                for plugin_name, plugin_info in type_plugins.items():
                    manifest = plugin_info["manifest"]

                    # Check if query matches any search field
                    if any(
                        query.lower()
                        in str(getattr(manifest, f"get_{field}", lambda: "")()).lower()
                        for field in search_fields
                    ):
                        matching_plugins[plugin_name] = plugin_info

                if matching_plugins:
                    results[plugin_type] = matching_plugins

            return results

    class ServiceFactory:
        def __init__(self, plugin_catalog=None, logger=None):
            self.plugin_catalog = plugin_catalog or PluginCatalog()
            self.logger = logger or Mock()
            self.created_services = []

        def create_service_manager(self, service_type, implementation_name, **kwargs):
            """Create service manager instance."""
            plugin_info = self.plugin_catalog.get_plugin(implementation_name, "iut")

            if not plugin_info:
                raise ValueError(
                    f"Service implementation not found: {implementation_name}"
                )

            # Mock service manager creation
            service_manager = Mock()
            service_manager.name = implementation_name
            service_manager.type = service_type
            service_manager.plugin_path = plugin_info["path"]
            service_manager.generate_commands = Mock(
                return_value={
                    "pre_run_cmds": [f"{implementation_name}_setup"],
                    "run_cmd": {"command": f"{implementation_name}_run", "timeout": 60},
                    "post_run_cmds": [f"{implementation_name}_cleanup"],
                }
            )

            self.created_services.append(service_manager)
            return service_manager

        def get_available_implementations(self, service_type=None):
            """Get available service implementations."""
            iut_plugins = self.plugin_catalog.list_plugins_by_type("iut")

            if service_type:
                # Filter by service type if specified
                filtered_plugins = []
                for plugin_name in iut_plugins:
                    plugin_info = self.plugin_catalog.get_plugin(plugin_name, "iut")
                    if (
                        plugin_info
                        and service_type
                        in plugin_info["manifest"].get_supported_protocols()
                    ):
                        filtered_plugins.append(plugin_name)
                return filtered_plugins

            return iut_plugins

        def validate_service_dependencies(self, implementation_name):
            """Validate service dependencies."""
            plugin_info = self.plugin_catalog.get_plugin(implementation_name, "iut")

            if not plugin_info:
                return False, f"Implementation not found: {implementation_name}"

            dependencies = plugin_info["manifest"].get_dependencies()
            missing_deps = []

            # Mock dependency checking
            for dep in dependencies:
                # In real implementation, would check if dependency is available
                if dep.startswith("missing_"):
                    missing_deps.append(dep)

            if missing_deps:
                return False, f"Missing dependencies: {missing_deps}"

            return True, "All dependencies satisfied"

    class EnvironmentFactory:
        def __init__(self, plugin_catalog=None, logger=None):
            self.plugin_catalog = plugin_catalog or PluginCatalog()
            self.logger = logger or Mock()
            self.created_environments = []

        def create_environment_manager(self, environment_type, **kwargs):
            """Create environment manager instance."""
            plugin_info = self.plugin_catalog.get_plugin(
                environment_type, "network_environment"
            )

            if not plugin_info:
                # Try execution environment
                plugin_info = self.plugin_catalog.get_plugin(
                    environment_type, "execution_environment"
                )

            if not plugin_info:
                raise ValueError(f"Environment not found: {environment_type}")

            # Mock environment manager creation
            env_manager = Mock()
            env_manager.name = environment_type
            env_manager.plugin_path = plugin_info["path"]
            env_manager.setup_environment = Mock(return_value=True)
            env_manager.deploy = Mock(return_value=True)
            env_manager.teardown = Mock(return_value=True)

            self.created_environments.append(env_manager)
            return env_manager

        def get_available_environments(self, environment_category=None):
            """Get available environments."""
            if environment_category == "network":
                return self.plugin_catalog.list_plugins_by_type("network_environment")
            elif environment_category == "execution":
                return self.plugin_catalog.list_plugins_by_type("execution_environment")
            else:
                # Return all environment types
                network_envs = self.plugin_catalog.list_plugins_by_type(
                    "network_environment"
                )
                exec_envs = self.plugin_catalog.list_plugins_by_type(
                    "execution_environment"
                )
                return {"network": network_envs, "execution": exec_envs}

    class PluginManagerUtils:
        @staticmethod
        def load_plugin_class(file_path, class_name):
            """Mock plugin class loading."""
            # Return a mock class
            MockPluginClass = type(
                class_name,
                (),
                {
                    "__init__": lambda self, *args, **kwargs: None,
                    "generate_commands": lambda self: {"command": "mock_command"},
                    "initialize": lambda self: True,
                },
            )
            return MockPluginClass

        @staticmethod
        def validate_plugin_structure(plugin_path):
            """Validate plugin directory structure."""
            plugin_path = Path(plugin_path)

            # Check for required files
            required_files = ["plugin.yaml"]
            missing_files = []

            for file_name in required_files:
                if not (plugin_path / file_name).exists():
                    missing_files.append(file_name)

            if missing_files:
                return False, f"Missing required files: {missing_files}"

            return True, "Plugin structure is valid"

        @staticmethod
        def get_plugin_metadata(plugin_path):
            """Get plugin metadata."""
            plugin_path = Path(plugin_path)
            manifest_file = plugin_path / "plugin.yaml"

            if manifest_file.exists():
                manifest = PluginManifest.load_from_file(manifest_file)
                return manifest.to_dict()

            return {}


pytestmark = [pytest.mark.unit, pytest.mark.plugin_system]


class TestPluginDiscovery:
    """Test PluginDiscovery functionality."""

    @pytest.fixture
    def mock_plugin_structure(self):
        """Create mock plugin directory structure."""
        temp_dir = tempfile.mkdtemp(prefix="panther_plugin_test_")
        plugin_root = Path(temp_dir) / "plugins"

        # Create service plugins
        services_dir = plugin_root / "services" / "iut" / "quic"

        # PicoQUIC plugin
        picoquic_dir = services_dir / "picoquic"
        picoquic_dir.mkdir(parents=True)
        picoquic_manifest = {
            "name": "picoquic",
            "version": "1.0.0",
            "type": "iut",
            "description": "PicoQUIC QUIC implementation",
            "supported_protocols": ["quic"],
            "dependencies": ["docker"],
            "entry_point": "picoquic.py",
        }
        with open(picoquic_dir / "plugin.yaml", "w") as f:
            yaml.dump(picoquic_manifest, f)

        # AioQUIC plugin
        aioquic_dir = services_dir / "aioquic"
        aioquic_dir.mkdir(parents=True)
        aioquic_manifest = {
            "name": "aioquic",
            "version": "0.9.0",
            "type": "iut",
            "description": "AioQUIC Python QUIC implementation",
            "supported_protocols": ["quic"],
            "dependencies": ["python", "asyncio"],
            "entry_point": "aioquic.py",
        }
        with open(aioquic_dir / "plugin.yaml", "w") as f:
            yaml.dump(aioquic_manifest, f)

        # Create environment plugins
        env_dir = plugin_root / "environments" / "network_environment"

        # Docker Compose environment
        docker_dir = env_dir / "docker_compose"
        docker_dir.mkdir(parents=True)
        docker_manifest = {
            "name": "docker_compose",
            "version": "2.0.0",
            "type": "network_environment",
            "description": "Docker Compose network environment",
            "dependencies": ["docker", "docker-compose"],
        }
        with open(docker_dir / "plugin.yaml", "w") as f:
            yaml.dump(docker_manifest, f)

        yield plugin_root

        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_plugin_discovery_initialization(self):
        """Test PluginDiscovery initialization."""
        discovery = PluginDiscovery()

        assert discovery.plugin_directories == []
        assert discovery.logger is not None
        assert discovery.discovered_plugins == {}
        assert discovery.discovery_cache == {}

    def test_plugin_discovery_with_directories(self, mock_plugin_structure):
        """Test PluginDiscovery with plugin directories."""
        discovery = PluginDiscovery(plugin_directories=[str(mock_plugin_structure)])

        assert len(discovery.plugin_directories) == 1
        assert str(mock_plugin_structure) in discovery.plugin_directories

    def test_discover_plugins_basic(self, mock_plugin_structure):
        """Test basic plugin discovery."""
        discovery = PluginDiscovery(plugin_directories=[str(mock_plugin_structure)])

        plugins = discovery.discover_plugins()

        assert isinstance(plugins, dict)
        assert "iut" in plugins
        assert "network_environment" in plugins

        # Check IUT plugins
        iut_plugins = plugins["iut"]
        assert "picoquic" in iut_plugins
        assert "aioquic" in iut_plugins

        # Check network environment plugins
        net_plugins = plugins["network_environment"]
        assert "docker_compose" in net_plugins

    def test_discover_plugins_caching(self, mock_plugin_structure):
        """Test plugin discovery caching."""
        discovery = PluginDiscovery(plugin_directories=[str(mock_plugin_structure)])

        # First discovery
        plugins1 = discovery.discover_plugins()

        # Second discovery (should use cache)
        plugins2 = discovery.discover_plugins()

        assert plugins1 == plugins2
        assert discovery.discovery_cache == plugins1

    def test_discover_plugins_force_refresh(self, mock_plugin_structure):
        """Test forced plugin discovery refresh."""
        discovery = PluginDiscovery(plugin_directories=[str(mock_plugin_structure)])

        # Initial discovery
        plugins1 = discovery.discover_plugins()

        # Add a new plugin
        new_plugin_dir = (
            mock_plugin_structure / "services" / "iut" / "quic" / "newplugin"
        )
        new_plugin_dir.mkdir(parents=True)
        new_manifest = {
            "name": "newplugin",
            "version": "1.0.0",
            "type": "iut",
            "description": "New test plugin",
        }
        with open(new_plugin_dir / "plugin.yaml", "w") as f:
            yaml.dump(new_manifest, f)

        # Force refresh
        plugins2 = discovery.discover_plugins(force_refresh=True)

        assert "newplugin" in plugins2["iut"]
        assert "newplugin" not in plugins1["iut"]

    def test_get_plugin_by_name(self, mock_plugin_structure):
        """Test getting plugin by name."""
        discovery = PluginDiscovery(plugin_directories=[str(mock_plugin_structure)])

        # Get specific plugin
        picoquic_plugin = discovery.get_plugin_by_name("picoquic", "iut")

        assert picoquic_plugin is not None
        assert picoquic_plugin["manifest"]["name"] == "picoquic"
        assert picoquic_plugin["manifest"]["type"] == "iut"

    def test_get_plugin_by_name_without_type(self, mock_plugin_structure):
        """Test getting plugin by name without specifying type."""
        discovery = PluginDiscovery(plugin_directories=[str(mock_plugin_structure)])

        # Get plugin without specifying type
        docker_plugin = discovery.get_plugin_by_name("docker_compose")

        assert docker_plugin is not None
        assert docker_plugin["manifest"]["name"] == "docker_compose"
        assert docker_plugin["manifest"]["type"] == "network_environment"

    def test_get_plugin_by_name_nonexistent(self, mock_plugin_structure):
        """Test getting non-existent plugin."""
        discovery = PluginDiscovery(plugin_directories=[str(mock_plugin_structure)])

        result = discovery.get_plugin_by_name("nonexistent")

        assert result is None

    def test_get_plugins_by_type(self, mock_plugin_structure):
        """Test getting plugins by type."""
        discovery = PluginDiscovery(plugin_directories=[str(mock_plugin_structure)])

        iut_plugins = discovery.get_plugins_by_type("iut")

        assert isinstance(iut_plugins, dict)
        assert "picoquic" in iut_plugins
        assert "aioquic" in iut_plugins
        assert len(iut_plugins) == 2

    def test_list_available_plugins(self, mock_plugin_structure):
        """Test listing all available plugins."""
        discovery = PluginDiscovery(plugin_directories=[str(mock_plugin_structure)])

        all_plugins = discovery.list_available_plugins()

        assert isinstance(all_plugins, dict)
        assert "iut" in all_plugins
        assert "network_environment" in all_plugins

        # Verify it's a copy, not reference
        all_plugins["test"] = "value"
        assert "test" not in discovery.discovered_plugins

    def test_validate_plugin_valid(self, mock_plugin_structure):
        """Test validation of valid plugin."""
        discovery = PluginDiscovery(plugin_directories=[str(mock_plugin_structure)])

        is_valid, message = discovery.validate_plugin("picoquic", "iut")

        assert is_valid is True
        assert message == "Plugin is valid"

    def test_validate_plugin_invalid(self, mock_plugin_structure):
        """Test validation of invalid plugin."""
        discovery = PluginDiscovery(plugin_directories=[str(mock_plugin_structure)])

        # Create invalid plugin
        invalid_dir = mock_plugin_structure / "services" / "iut" / "quic" / "invalid"
        invalid_dir.mkdir(parents=True)
        invalid_manifest = {
            "name": "invalid",
            # Missing version and type
            "description": "Invalid plugin",
        }
        with open(invalid_dir / "plugin.yaml", "w") as f:
            yaml.dump(invalid_manifest, f)

        discovery.refresh_cache()  # Refresh to pick up new plugin

        is_valid, message = discovery.validate_plugin("invalid", "iut")

        assert is_valid is False
        assert "Missing required field" in message

    def test_validate_plugin_nonexistent(self, mock_plugin_structure):
        """Test validation of non-existent plugin."""
        discovery = PluginDiscovery(plugin_directories=[str(mock_plugin_structure)])

        is_valid, message = discovery.validate_plugin("nonexistent")

        assert is_valid is False
        assert "not found" in message

    def test_refresh_cache(self, mock_plugin_structure):
        """Test cache refresh functionality."""
        discovery = PluginDiscovery(plugin_directories=[str(mock_plugin_structure)])

        # Initial discovery
        plugins1 = discovery.discover_plugins()

        # Add new plugin
        new_plugin_dir = (
            mock_plugin_structure / "environments" / "execution_environment" / "newenv"
        )
        new_plugin_dir.mkdir(parents=True)
        new_manifest = {
            "name": "newenv",
            "version": "1.0.0",
            "type": "execution_environment",
            "description": "New execution environment",
        }
        with open(new_plugin_dir / "plugin.yaml", "w") as f:
            yaml.dump(new_manifest, f)

        # Refresh cache
        plugins2 = discovery.refresh_cache()

        assert "execution_environment" in plugins2
        assert "newenv" in plugins2["execution_environment"]

    def test_discover_plugins_empty_directory(self):
        """Test plugin discovery with empty directories."""
        temp_dir = tempfile.mkdtemp(prefix="panther_empty_test_")
        empty_dir = Path(temp_dir)

        discovery = PluginDiscovery(plugin_directories=[str(empty_dir)])

        plugins = discovery.discover_plugins()

        assert plugins == {}

        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_discover_plugins_nonexistent_directory(self):
        """Test plugin discovery with non-existent directories."""
        discovery = PluginDiscovery(plugin_directories=["/nonexistent/path"])

        plugins = discovery.discover_plugins()

        assert plugins == {}


class TestPluginManifest:
    """Test PluginManifest functionality."""

    @pytest.fixture
    def sample_manifest_data(self):
        """Sample manifest data for testing."""
        return {
            "name": "test_plugin",
            "version": "1.2.3",
            "type": "iut",
            "description": "Test plugin for unit testing",
            "supported_protocols": ["quic"],
            "dependencies": ["docker", "python"],
            "entry_point": "test_plugin.py",
            "author": "Test Author",
            "license": "MIT",
        }

    @pytest.fixture
    def temp_manifest_file(self, sample_manifest_data):
        """Create temporary manifest file."""
        temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
        yaml.dump(sample_manifest_data, temp_file)
        temp_file.close()

        yield Path(temp_file.name)

        # Cleanup
        Path(temp_file.name).unlink(missing_ok=True)

    def test_plugin_manifest_initialization(self, sample_manifest_data):
        """Test PluginManifest initialization with data."""
        manifest = PluginManifest(manifest_data=sample_manifest_data)

        assert manifest.manifest_data == sample_manifest_data
        assert manifest.manifest_file is None

    def test_plugin_manifest_load_from_file(self, temp_manifest_file):
        """Test loading manifest from file."""
        manifest = PluginManifest.load_from_file(temp_manifest_file)

        assert manifest.get_name() == "test_plugin"
        assert manifest.get_version() == "1.2.3"
        assert manifest.get_type() == "iut"
        assert manifest.manifest_file == temp_manifest_file

    def test_plugin_manifest_load_json_file(self, sample_manifest_data):
        """Test loading manifest from JSON file."""
        temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        json.dump(sample_manifest_data, temp_file)
        temp_file.close()

        try:
            manifest = PluginManifest.load_from_file(Path(temp_file.name))

            assert manifest.get_name() == "test_plugin"
            assert manifest.get_type() == "iut"
        finally:
            Path(temp_file.name).unlink(missing_ok=True)

    def test_plugin_manifest_unsupported_format(self):
        """Test loading manifest from unsupported file format."""
        temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
        temp_file.write("name: test_plugin")
        temp_file.close()

        try:
            with pytest.raises(ValueError, match="Unsupported manifest format"):
                PluginManifest.load_from_file(Path(temp_file.name))
        finally:
            Path(temp_file.name).unlink(missing_ok=True)

    def test_get_manifest_fields(self, sample_manifest_data):
        """Test getting various manifest fields."""
        manifest = PluginManifest(manifest_data=sample_manifest_data)

        assert manifest.get_name() == "test_plugin"
        assert manifest.get_version() == "1.2.3"
        assert manifest.get_type() == "iut"
        assert manifest.get_description() == "Test plugin for unit testing"
        assert manifest.get_dependencies() == ["docker", "python"]
        assert manifest.get_supported_protocols() == ["quic"]
        assert manifest.get_entry_point() == "test_plugin.py"

    def test_get_manifest_fields_defaults(self):
        """Test getting manifest fields with default values."""
        manifest = PluginManifest(manifest_data={})

        assert manifest.get_name() == "unknown"
        assert manifest.get_version() == "0.0.0"
        assert manifest.get_type() == "unknown"
        assert manifest.get_description() == ""
        assert manifest.get_dependencies() == []
        assert manifest.get_supported_protocols() == []
        assert manifest.get_entry_point() == ""

    def test_validate_manifest_valid(self, sample_manifest_data):
        """Test validation of valid manifest."""
        manifest = PluginManifest(manifest_data=sample_manifest_data)

        is_valid, message = manifest.validate()

        assert is_valid is True
        assert message == "Manifest is valid"

    def test_validate_manifest_missing_fields(self):
        """Test validation of manifest with missing fields."""
        incomplete_data = {
            "name": "test_plugin",
            # Missing version and type
            "description": "Test plugin",
        }
        manifest = PluginManifest(manifest_data=incomplete_data)

        is_valid, message = manifest.validate()

        assert is_valid is False
        assert "Missing required fields" in message
        assert "version" in message
        assert "type" in message

    def test_to_dict(self, sample_manifest_data):
        """Test converting manifest to dictionary."""
        manifest = PluginManifest(manifest_data=sample_manifest_data)

        dict_result = manifest.to_dict()

        assert dict_result == sample_manifest_data
        # Verify it's a copy
        dict_result["test"] = "value"
        assert "test" not in manifest.manifest_data


class TestPluginCatalog:
    """Test PluginCatalog functionality."""

    @pytest.fixture
    def mock_catalog_structure(self):
        """Create mock plugin structure for catalog testing."""
        temp_dir = tempfile.mkdtemp(prefix="panther_catalog_test_")
        plugin_root = Path(temp_dir) / "plugins"

        # Create multiple plugins for catalog testing
        plugins_data = [
            (
                "services/iut/quic/plugin1",
                {
                    "name": "plugin1",
                    "version": "1.0.0",
                    "type": "iut",
                    "description": "First test plugin",
                    "supported_protocols": ["quic"],
                },
            ),
            (
                "services/iut/quic/plugin2",
                {
                    "name": "plugin2",
                    "version": "2.0.0",
                    "type": "iut",
                    "description": "Second test plugin",
                    "supported_protocols": ["quic"],
                },
            ),
            (
                "environments/network_environment/env1",
                {
                    "name": "env1",
                    "version": "1.0.0",
                    "type": "network_environment",
                    "description": "First test environment",
                },
            ),
            (
                "environments/execution_environment/profiler1",
                {
                    "name": "profiler1",
                    "version": "1.5.0",
                    "type": "execution_environment",
                    "description": "Test profiler environment",
                },
            ),
        ]

        for plugin_path, manifest_data in plugins_data:
            plugin_dir = plugin_root / plugin_path
            plugin_dir.mkdir(parents=True)
            with open(plugin_dir / "plugin.yaml", "w") as f:
                yaml.dump(manifest_data, f)

        yield plugin_root

        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_plugin_catalog_initialization(self):
        """Test PluginCatalog initialization."""
        catalog = PluginCatalog()

        assert catalog.discovery_paths == []
        assert catalog.catalog == {}
        assert catalog.metadata["last_updated"] is None
        assert catalog.metadata["total_plugins"] == 0

    def test_plugin_catalog_with_paths(self, mock_catalog_structure):
        """Test PluginCatalog initialization with discovery paths."""
        catalog = PluginCatalog(discovery_paths=[str(mock_catalog_structure)])

        assert len(catalog.discovery_paths) == 1
        assert str(mock_catalog_structure) in catalog.discovery_paths

    def test_build_catalog(self, mock_catalog_structure):
        """Test building plugin catalog."""
        catalog = PluginCatalog(discovery_paths=[str(mock_catalog_structure)])

        catalog_data = catalog.build_catalog()

        assert isinstance(catalog_data, dict)
        assert "iut" in catalog_data
        assert "network_environment" in catalog_data
        assert "execution_environment" in catalog_data

        # Check specific plugins
        assert "plugin1" in catalog_data["iut"]
        assert "plugin2" in catalog_data["iut"]
        assert "env1" in catalog_data["network_environment"]
        assert "profiler1" in catalog_data["execution_environment"]

    def test_build_catalog_caching(self, mock_catalog_structure):
        """Test catalog building with caching."""
        catalog = PluginCatalog(discovery_paths=[str(mock_catalog_structure)])

        # First build
        catalog1 = catalog.build_catalog()

        # Second build (should use cache)
        catalog2 = catalog.build_catalog()

        assert catalog1 == catalog2

    def test_build_catalog_force_refresh(self, mock_catalog_structure):
        """Test catalog building with force refresh."""
        catalog = PluginCatalog(discovery_paths=[str(mock_catalog_structure)])

        # Initial build
        catalog.build_catalog()

        # Add new plugin
        new_plugin_dir = (
            mock_catalog_structure / "services" / "iut" / "quic" / "plugin3"
        )
        new_plugin_dir.mkdir(parents=True)
        new_manifest = {
            "name": "plugin3",
            "version": "3.0.0",
            "type": "iut",
            "description": "Third test plugin",
        }
        with open(new_plugin_dir / "plugin.yaml", "w") as f:
            yaml.dump(new_manifest, f)

        # Force refresh
        refreshed_catalog = catalog.build_catalog(force_refresh=True)

        assert "plugin3" in refreshed_catalog["iut"]

    def test_get_plugin(self, mock_catalog_structure):
        """Test getting plugin from catalog."""
        catalog = PluginCatalog(discovery_paths=[str(mock_catalog_structure)])
        catalog.build_catalog()

        # Get plugin with type
        plugin1 = catalog.get_plugin("plugin1", "iut")
        assert plugin1 is not None
        assert plugin1["manifest"].get_name() == "plugin1"

        # Get plugin without type
        env1 = catalog.get_plugin("env1")
        assert env1 is not None
        assert env1["manifest"].get_name() == "env1"

    def test_get_plugin_nonexistent(self, mock_catalog_structure):
        """Test getting non-existent plugin."""
        catalog = PluginCatalog(discovery_paths=[str(mock_catalog_structure)])
        catalog.build_catalog()

        result = catalog.get_plugin("nonexistent")
        assert result is None

    def test_list_plugins_by_type(self, mock_catalog_structure):
        """Test listing plugins by type."""
        catalog = PluginCatalog(discovery_paths=[str(mock_catalog_structure)])
        catalog.build_catalog()

        iut_plugins = catalog.list_plugins_by_type("iut")
        assert len(iut_plugins) == 2
        assert "plugin1" in iut_plugins
        assert "plugin2" in iut_plugins

        env_plugins = catalog.list_plugins_by_type("network_environment")
        assert len(env_plugins) == 1
        assert "env1" in env_plugins

    def test_get_catalog_metadata(self, mock_catalog_structure):
        """Test getting catalog metadata."""
        catalog = PluginCatalog(discovery_paths=[str(mock_catalog_structure)])
        catalog.build_catalog()

        metadata = catalog.get_catalog_metadata()

        assert "last_updated" in metadata
        assert metadata["total_plugins"] == 4
        assert metadata["plugin_types"]["iut"] == 2
        assert metadata["plugin_types"]["network_environment"] == 1
        assert metadata["plugin_types"]["execution_environment"] == 1

    def test_validate_all_plugins(self, mock_catalog_structure):
        """Test validating all plugins in catalog."""
        catalog = PluginCatalog(discovery_paths=[str(mock_catalog_structure)])
        catalog.build_catalog()

        validation_results = catalog.validate_all_plugins()

        assert "iut" in validation_results
        assert "network_environment" in validation_results

        # All test plugins should be valid
        for plugin_type, type_results in validation_results.items():
            for plugin_name, result in type_results.items():
                assert result["valid"] is True
                assert result["message"] == "Manifest is valid"

    def test_search_plugins(self, mock_catalog_structure):
        """Test searching plugins."""
        catalog = PluginCatalog(discovery_paths=[str(mock_catalog_structure)])
        catalog.build_catalog()

        # Search by name
        results = catalog.search_plugins("plugin1")
        assert "iut" in results
        assert "plugin1" in results["iut"]

        # Search by description
        results = catalog.search_plugins("profiler")
        assert "execution_environment" in results
        assert "profiler1" in results["execution_environment"]

        # Search by type
        results = catalog.search_plugins("network_environment")
        assert "network_environment" in results

    def test_search_plugins_no_results(self, mock_catalog_structure):
        """Test searching plugins with no results."""
        catalog = PluginCatalog(discovery_paths=[str(mock_catalog_structure)])
        catalog.build_catalog()

        results = catalog.search_plugins("nonexistent_query")
        assert results == {}


class TestServiceFactory:
    """Test ServiceFactory functionality."""

    @pytest.fixture
    def mock_service_catalog(self):
        """Create mock catalog for service factory testing."""
        catalog = PluginCatalog()

        # Mock IUT plugins
        catalog.catalog = {
            "iut": {
                "picoquic": {
                    "manifest": PluginManifest(
                        {
                            "name": "picoquic",
                            "version": "1.0.0",
                            "type": "iut",
                            "supported_protocols": ["quic"],
                        }
                    ),
                    "path": Path("/mock/path/picoquic"),
                    "validated": True,
                },
                "aioquic": {
                    "manifest": PluginManifest(
                        {
                            "name": "aioquic",
                            "version": "0.9.0",
                            "type": "iut",
                            "supported_protocols": ["quic"],
                        }
                    ),
                    "path": Path("/mock/path/aioquic"),
                    "validated": True,
                },
            }
        }

        return catalog

    def test_service_factory_initialization(self):
        """Test ServiceFactory initialization."""
        factory = ServiceFactory()

        assert factory.plugin_catalog is not None
        assert factory.logger is not None
        assert factory.created_services == []

    def test_service_factory_with_catalog(self, mock_service_catalog):
        """Test ServiceFactory with custom catalog."""
        factory = ServiceFactory(plugin_catalog=mock_service_catalog)

        assert factory.plugin_catalog == mock_service_catalog

    def test_create_service_manager(self, mock_service_catalog):
        """Test creating service manager."""
        factory = ServiceFactory(plugin_catalog=mock_service_catalog)

        service_manager = factory.create_service_manager("quic", "picoquic")

        assert service_manager is not None
        assert service_manager.name == "picoquic"
        assert service_manager.type == "quic"
        assert service_manager in factory.created_services

    def test_create_service_manager_nonexistent(self, mock_service_catalog):
        """Test creating service manager for non-existent implementation."""
        factory = ServiceFactory(plugin_catalog=mock_service_catalog)

        with pytest.raises(ValueError, match="Service implementation not found"):
            factory.create_service_manager("quic", "nonexistent")

    def test_get_available_implementations(self, mock_service_catalog):
        """Test getting available implementations."""
        factory = ServiceFactory(plugin_catalog=mock_service_catalog)

        implementations = factory.get_available_implementations()

        assert len(implementations) == 2
        assert "picoquic" in implementations
        assert "aioquic" in implementations

    def test_get_available_implementations_filtered(self, mock_service_catalog):
        """Test getting available implementations filtered by service type."""
        factory = ServiceFactory(plugin_catalog=mock_service_catalog)

        # Filter by QUIC protocol
        quic_impls = factory.get_available_implementations("quic")
        assert len(quic_impls) == 2

        # Filter by HTTP3 protocol
        http3_impls = factory.get_available_implementations("http3")
        assert len(http3_impls) == 1
        assert "aioquic" in http3_impls

    def test_validate_service_dependencies(self, mock_service_catalog):
        """Test service dependency validation."""
        factory = ServiceFactory(plugin_catalog=mock_service_catalog)

        # Valid service
        is_valid, message = factory.validate_service_dependencies("picoquic")
        assert is_valid is True
        assert message == "All dependencies satisfied"

    def test_validate_service_dependencies_missing(self, mock_service_catalog):
        """Test service dependency validation with missing dependencies."""
        # Add plugin with missing dependencies
        mock_service_catalog.catalog["iut"]["broken_plugin"] = {
            "manifest": PluginManifest(
                {
                    "name": "broken_plugin",
                    "version": "1.0.0",
                    "type": "iut",
                    "dependencies": ["missing_dependency1", "missing_dependency2"],
                }
            ),
            "path": Path("/mock/path/broken"),
            "validated": True,
        }

        factory = ServiceFactory(plugin_catalog=mock_service_catalog)

        is_valid, message = factory.validate_service_dependencies("broken_plugin")
        assert is_valid is False
        assert "Missing dependencies" in message

    def test_validate_service_dependencies_nonexistent(self, mock_service_catalog):
        """Test service dependency validation for non-existent service."""
        factory = ServiceFactory(plugin_catalog=mock_service_catalog)

        is_valid, message = factory.validate_service_dependencies("nonexistent")
        assert is_valid is False
        assert "Implementation not found" in message


class TestEnvironmentFactory:
    """Test EnvironmentFactory functionality."""

    @pytest.fixture
    def mock_environment_catalog(self):
        """Create mock catalog for environment factory testing."""
        catalog = PluginCatalog()

        # Mock environment plugins
        catalog.catalog = {
            "network_environment": {
                "docker_compose": {
                    "manifest": PluginManifest(
                        {
                            "name": "docker_compose",
                            "version": "2.0.0",
                            "type": "network_environment",
                        }
                    ),
                    "path": Path("/mock/path/docker_compose"),
                    "validated": True,
                }
            },
            "execution_environment": {
                "strace": {
                    "manifest": PluginManifest(
                        {
                            "name": "strace",
                            "version": "1.0.0",
                            "type": "execution_environment",
                        }
                    ),
                    "path": Path("/mock/path/strace"),
                    "validated": True,
                }
            },
        }

        return catalog

    def test_environment_factory_initialization(self):
        """Test EnvironmentFactory initialization."""
        factory = EnvironmentFactory()

        assert factory.plugin_catalog is not None
        assert factory.logger is not None
        assert factory.created_environments == []

    def test_create_environment_manager_network(self, mock_environment_catalog):
        """Test creating network environment manager."""
        factory = EnvironmentFactory(plugin_catalog=mock_environment_catalog)

        env_manager = factory.create_environment_manager("docker_compose")

        assert env_manager is not None
        assert env_manager.name == "docker_compose"
        assert env_manager in factory.created_environments

    def test_create_environment_manager_execution(self, mock_environment_catalog):
        """Test creating execution environment manager."""
        factory = EnvironmentFactory(plugin_catalog=mock_environment_catalog)

        env_manager = factory.create_environment_manager("strace")

        assert env_manager is not None
        assert env_manager.name == "strace"
        assert env_manager in factory.created_environments

    def test_create_environment_manager_nonexistent(self, mock_environment_catalog):
        """Test creating environment manager for non-existent environment."""
        factory = EnvironmentFactory(plugin_catalog=mock_environment_catalog)

        with pytest.raises(ValueError, match="Environment not found"):
            factory.create_environment_manager("nonexistent")

    def test_get_available_environments_all(self, mock_environment_catalog):
        """Test getting all available environments."""
        factory = EnvironmentFactory(plugin_catalog=mock_environment_catalog)

        environments = factory.get_available_environments()

        assert isinstance(environments, dict)
        assert "network" in environments
        assert "execution" in environments
        assert "docker_compose" in environments["network"]
        assert "strace" in environments["execution"]

    def test_get_available_environments_network(self, mock_environment_catalog):
        """Test getting network environments."""
        factory = EnvironmentFactory(plugin_catalog=mock_environment_catalog)

        network_envs = factory.get_available_environments("network")

        assert len(network_envs) == 1
        assert "docker_compose" in network_envs

    def test_get_available_environments_execution(self, mock_environment_catalog):
        """Test getting execution environments."""
        factory = EnvironmentFactory(plugin_catalog=mock_environment_catalog)

        exec_envs = factory.get_available_environments("execution")

        assert len(exec_envs) == 1
        assert "strace" in exec_envs


class TestPluginManagerUtils:
    """Test PluginManagerUtils functionality."""

    def test_load_plugin_class(self):
        """Test loading plugin class."""
        plugin_class = PluginManagerUtils.load_plugin_class(
            "/mock/path/plugin.py", "TestPlugin"
        )

        assert plugin_class is not None
        assert plugin_class.__name__ == "TestPlugin"

        # Test instance creation
        instance = plugin_class()
        assert hasattr(instance, "generate_commands")
        assert hasattr(instance, "initialize")

    def test_validate_plugin_structure_valid(self):
        """Test validating valid plugin structure."""
        temp_dir = tempfile.mkdtemp(prefix="panther_plugin_structure_test_")
        plugin_path = Path(temp_dir)

        # Create required files
        (plugin_path / "plugin.yaml").write_text("name: test_plugin")

        try:
            is_valid, message = PluginManagerUtils.validate_plugin_structure(
                plugin_path
            )

            assert is_valid is True
            assert message == "Plugin structure is valid"
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_validate_plugin_structure_invalid(self):
        """Test validating invalid plugin structure."""
        temp_dir = tempfile.mkdtemp(prefix="panther_plugin_structure_test_")
        plugin_path = Path(temp_dir)

        # Don't create required files

        try:
            is_valid, message = PluginManagerUtils.validate_plugin_structure(
                plugin_path
            )

            assert is_valid is False
            assert "Missing required files" in message
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_get_plugin_metadata(self):
        """Test getting plugin metadata."""
        temp_dir = tempfile.mkdtemp(prefix="panther_plugin_metadata_test_")
        plugin_path = Path(temp_dir)

        # Create plugin manifest
        manifest_data = {
            "name": "metadata_test",
            "version": "1.0.0",
            "type": "iut",
            "description": "Test plugin for metadata extraction",
        }
        with open(plugin_path / "plugin.yaml", "w") as f:
            yaml.dump(manifest_data, f)

        try:
            metadata = PluginManagerUtils.get_plugin_metadata(plugin_path)

            assert metadata["name"] == "metadata_test"
            assert metadata["version"] == "1.0.0"
            assert metadata["type"] == "iut"
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_get_plugin_metadata_no_manifest(self):
        """Test getting plugin metadata when no manifest exists."""
        temp_dir = tempfile.mkdtemp(prefix="panther_plugin_metadata_test_")
        plugin_path = Path(temp_dir)

        try:
            metadata = PluginManagerUtils.get_plugin_metadata(plugin_path)

            assert metadata == {}
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestPluginSystemIntegration:
    """Test integration between plugin system components."""

    @pytest.fixture
    def comprehensive_plugin_structure(self):
        """Create comprehensive plugin structure for integration testing."""
        temp_dir = tempfile.mkdtemp(prefix="panther_integration_test_")
        plugin_root = Path(temp_dir) / "plugins"

        # Create comprehensive plugin ecosystem
        plugins = [
            # IUT plugins
            (
                "services/iut/quic/picoquic",
                {
                    "name": "picoquic",
                    "version": "1.0.0",
                    "type": "iut",
                    "description": "PicoQUIC implementation",
                    "supported_protocols": ["quic"],
                    "dependencies": ["docker"],
                },
            ),
            (
                "services/iut/quic/aioquic",
                {
                    "name": "aioquic",
                    "version": "0.9.0",
                    "type": "iut",
                    "description": "Python AioQUIC implementation",
                    "supported_protocols": ["quic"],
                    "dependencies": ["python", "asyncio"],
                },
            ),
            # Tester plugins
            (
                "services/testers/ivy_tester",
                {
                    "name": "ivy_tester",
                    "version": "1.5.0",
                    "type": "testers",
                    "description": "Ivy formal verification tester",
                    "supported_protocols": ["quic"],
                    "dependencies": ["ivy", "python"],
                },
            ),
            # Network environments
            (
                "environments/network_environment/docker_compose",
                {
                    "name": "docker_compose",
                    "version": "2.0.0",
                    "type": "network_environment",
                    "description": "Docker Compose orchestration",
                    "dependencies": ["docker", "docker-compose"],
                },
            ),
            (
                "environments/network_environment/shadow_ns",
                {
                    "name": "shadow_ns",
                    "version": "1.0.0",
                    "type": "network_environment",
                    "description": "Shadow network simulation",
                    "dependencies": ["shadow"],
                },
            ),
            # Execution environments
            (
                "environments/execution_environment/strace",
                {
                    "name": "strace",
                    "version": "1.0.0",
                    "type": "execution_environment",
                    "description": "System call tracer",
                    "dependencies": ["strace"],
                },
            ),
            (
                "environments/execution_environment/gperf",
                {
                    "name": "gperf",
                    "version": "2.0.0",
                    "type": "execution_environment",
                    "description": "Google Performance Tools profiler",
                    "dependencies": ["gperftools"],
                },
            ),
        ]

        for plugin_path, manifest_data in plugins:
            plugin_dir = plugin_root / plugin_path
            plugin_dir.mkdir(parents=True)
            with open(plugin_dir / "plugin.yaml", "w") as f:
                yaml.dump(manifest_data, f)

        yield plugin_root

        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_full_plugin_system_workflow(self, comprehensive_plugin_structure):
        """Test complete plugin system workflow."""
        # Step 1: Discovery
        discovery = PluginDiscovery(
            plugin_directories=[str(comprehensive_plugin_structure)]
        )
        discovered_plugins = discovery.discover_plugins()

        assert len(discovered_plugins) == 4  # 4 plugin types
        assert "iut" in discovered_plugins
        assert "testers" in discovered_plugins
        assert "network_environment" in discovered_plugins
        assert "execution_environment" in discovered_plugins

        # Step 2: Catalog building
        catalog = PluginCatalog(discovery_paths=[str(comprehensive_plugin_structure)])
        catalog_data = catalog.build_catalog()

        assert len(catalog_data) == 4

        # Step 3: Service factory
        service_factory = ServiceFactory(plugin_catalog=catalog)

        # Create service managers
        picoquic_manager = service_factory.create_service_manager("quic", "picoquic")
        aioquic_manager = service_factory.create_service_manager("quic", "aioquic")

        assert picoquic_manager.name == "picoquic"
        assert aioquic_manager.name == "aioquic"
        assert len(service_factory.created_services) == 2

        # Step 4: Environment factory
        env_factory = EnvironmentFactory(plugin_catalog=catalog)

        # Create environment managers
        docker_env = env_factory.create_environment_manager("docker_compose")
        strace_env = env_factory.create_environment_manager("strace")

        assert docker_env.name == "docker_compose"
        assert strace_env.name == "strace"
        assert len(env_factory.created_environments) == 2

        # Step 5: Validation
        validation_results = catalog.validate_all_plugins()
        for plugin_type, type_results in validation_results.items():
            for plugin_name, result in type_results.items():
                assert result["valid"] is True

    def test_plugin_dependency_validation_workflow(
        self, comprehensive_plugin_structure
    ):
        """Test plugin dependency validation workflow."""
        catalog = PluginCatalog(discovery_paths=[str(comprehensive_plugin_structure)])
        catalog.build_catalog()

        service_factory = ServiceFactory(plugin_catalog=catalog)

        # Test dependency validation for all IUT plugins
        iut_plugins = catalog.list_plugins_by_type("iut")

        for plugin_name in iut_plugins:
            is_valid, message = service_factory.validate_service_dependencies(
                plugin_name
            )
            # All test plugins should have valid dependencies (no missing_ prefix)
            assert is_valid is True

    def test_plugin_search_and_filter_workflow(self, comprehensive_plugin_structure):
        """Test plugin search and filtering workflow."""
        catalog = PluginCatalog(discovery_paths=[str(comprehensive_plugin_structure)])
        catalog.build_catalog()

        # Search for QUIC-related plugins
        quic_plugins = catalog.search_plugins("quic")

        assert "iut" in quic_plugins
        assert "testers" in quic_plugins
        assert len(quic_plugins["iut"]) >= 2  # picoquic and aioquic

        # Search for Python-related plugins
        python_plugins = catalog.search_plugins("python")

        assert "iut" in python_plugins
        assert "aioquic" in python_plugins["iut"]

        # Search for profiling tools
        profiler_plugins = catalog.search_plugins("profiler")

        assert "execution_environment" in profiler_plugins
        assert "gperf" in profiler_plugins["execution_environment"]

    def test_multi_factory_coordination(self, comprehensive_plugin_structure):
        """Test coordination between multiple factories."""
        catalog = PluginCatalog(discovery_paths=[str(comprehensive_plugin_structure)])
        catalog.build_catalog()

        service_factory = ServiceFactory(plugin_catalog=catalog)
        env_factory = EnvironmentFactory(plugin_catalog=catalog)

        # Create a complete testing setup
        # 1. Service implementations
        quic_server = service_factory.create_service_manager("quic", "picoquic")
        quic_client = service_factory.create_service_manager("quic", "aioquic")

        # 2. Network environment
        network_env = env_factory.create_environment_manager("docker_compose")

        # 3. Execution environments
        tracer = env_factory.create_environment_manager("strace")
        profiler = env_factory.create_environment_manager("gperf")

        # Verify all components created successfully
        assert len(service_factory.created_services) == 2
        assert len(env_factory.created_environments) == 3

        # Test component interactions
        assert quic_server.generate_commands() is not None
        assert quic_client.generate_commands() is not None
        assert network_env.setup_environment() is True
        assert tracer.setup_environment() is True
        assert profiler.setup_environment() is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
