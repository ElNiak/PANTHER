"""
Integration tests for the new unified plugin architecture.

Tests the complete plugin lifecycle including:
- Plugin discovery and cataloging
- Plugin loading and instantiation
- Integration with experiment manager
- Backward compatibility with existing plugins
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import yaml

from panther.plugins.plugin_manager import PluginManager
from panther.plugins.plugin_catalog import PluginCatalog
from panther.plugins.plugin_manifest import PluginManifest
from panther.core.experiment_manager import ExperimentManager
from panther.config.config_manager import ConfigLoader
from panther.core.observer.management.event_manager import EventManager
from panther.config.config_experiment_schema import ServiceConfig, TestConfig
from panther.plugins.protocols.config_schema import ProtocolConfig
from panther.plugins.services.iut.config_schema import ImplementationConfig


class TestPluginArchitectureIntegration:
    """Test the integration of the new plugin architecture."""

    @pytest.fixture
    def temp_plugin_dir(self):
        """Create a temporary plugin directory."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def mock_event_manager(self):
        """Create a mock event manager."""
        return Mock(spec=EventManager)

    @pytest.fixture
    def plugin_manager(self, mock_event_manager):
        """Create a PluginManager instance."""
        return PluginManager(event_manager=mock_event_manager)

    @pytest.fixture
    def sample_manifest(self, temp_plugin_dir):
        """Create a sample plugin manifest."""
        manifest = {
            "name": "test_plugin",
            "version": "1.0.0",
            "type": "service",
            "description": "Test plugin for integration testing",
            "author": "Test Author",
            "dependencies": [],
            "configuration": {
                "timeout": {"type": "integer", "default": 60},
                "debug": {"type": "boolean", "default": False},
            },
        }

        manifest_path = temp_plugin_dir / "plugin.yaml"
        with open(manifest_path, "w") as f:
            yaml.dump(manifest, f)

        return manifest_path

    def test_plugin_catalog_discovery(self, temp_plugin_dir, sample_manifest):
        """Test that the plugin catalog can discover plugins."""
        # sample_manifest fixture ensures the manifest file is created
        catalog = PluginCatalog(discovery_paths=[str(temp_plugin_dir)])
        # Disable cache for test to ensure fresh scan of temp directory
        plugins = catalog.scan_plugins(use_cache=False)

        assert len(plugins) > 0
        plugin_names = [manifest.name for manifest in plugins.values()]
        assert "test_plugin" in plugin_names

    def test_plugin_loading_with_manifest(self, plugin_manager, temp_plugin_dir):
        """Test loading a plugin with a manifest."""
        # Create a mock plugin module
        plugin_name = "test_service"
        plugin_path = temp_plugin_dir / "services" / "iut" / "test_protocol" / plugin_name
        plugin_path.mkdir(parents=True)

        # Create plugin manifest
        manifest = {
            "name": plugin_name,
            "version": "1.0.0",
            "type": "service",
            "description": "Test service plugin",
        }

        with open(plugin_path / "plugin.yaml", "w") as f:
            yaml.dump(manifest, f)

        # Create plugin module
        plugin_module = plugin_path / f"{plugin_name}.py"
        plugin_module.write_text(
            """
from panther.plugins.services.service_plugin_base import ServicePluginBase

class TestServiceServiceManager(ServicePluginBase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def generate_pre_compile_commands(self):
        return []

    def generate_compile_commands(self):
        return []

    def generate_post_compile_commands(self):
        return []

    def generate_run_commands(self):
        return [{"cmd": "echo 'Test service running'"}]

    def generate_post_run_commands(self):
        return []
"""
        )

        # Test loading with temporary plugin directory
        with patch("panther.plugins.plugin_manager.PluginCatalog") as mock_catalog:
            mock_catalog.return_value.get_plugin.return_value = PluginManifest.from_dict(manifest)

            # Should not raise an exception
            plugin_manager.catalog = mock_catalog.return_value

    def test_service_manager_creation(self, plugin_manager):
        """Test creating a service manager through the unified plugin manager."""
        service_config = ServiceConfig(
            name="test_service",
            implementation=ImplementationConfig(name="picoquic", type="iut"),
            protocol=ProtocolConfig(name="quic", version="rfc9000", role="server"),
            timeout=60,
        )

        # Mock the plugin loading
        with patch(
            "panther.plugins.plugin_manager.importlib.util.spec_from_file_location"
        ) as mock_spec:
            mock_module = MagicMock()
            mock_spec.return_value.loader.exec_module = MagicMock()

            # Mock the service manager class
            mock_service_manager_class = MagicMock()
            mock_service_manager = MagicMock()
            mock_service_manager_class.return_value = mock_service_manager

            with patch(
                "panther.plugins.plugin_manager.importlib.util.module_from_spec"
            ) as mock_module_from_spec:
                mock_module_from_spec.return_value = mock_module
                setattr(mock_module, "PicoquicServiceManager", mock_service_manager_class)

                # Create service manager
                result = plugin_manager.create_service_manager(
                    implementation=service_config.implementation,
                    protocol=service_config.protocol,
                    implementation_dir=Path("/mock/path"),
                    service_config_to_test=service_config,
                )

                assert result == mock_service_manager
                mock_service_manager_class.assert_called_once()

    def test_environment_manager_creation(self, plugin_manager, temp_plugin_dir):
        """Test creating an environment manager through the unified plugin manager."""
        test_config = TestConfig(
            name="test",
            description="Test environment",
            network_environment={"type": "docker_compose"},
            services={},
        )

        # Mock the environment plugin loading
        with patch(
            "panther.plugins.plugin_manager.importlib.util.spec_from_file_location"
        ) as mock_spec:
            mock_module = MagicMock()
            mock_spec.return_value.loader.exec_module = MagicMock()

            # Mock the environment class
            mock_env_class = MagicMock()
            mock_env_instance = MagicMock()
            mock_env_class.return_value = mock_env_instance
            with patch(
                "panther.plugins.plugin_manager.importlib.util.module_from_spec"
            ) as mock_module_from_spec:
                mock_module_from_spec.return_value = mock_module
                setattr(mock_module, "DockerComposeEnvironment", mock_env_class)
                # Create environment manager
                result = plugin_manager.create_environment_manager(
                    environment="docker_compose",
                    test_config=test_config,
                    environment_dir=temp_plugin_dir,
                    output_dir=temp_plugin_dir,
                    event_manager=plugin_manager.event_manager,
                )
                assert result == mock_env_instance
                mock_env_class.assert_called_once()

    def test_plugin_validation_in_experiment(self, temp_plugin_dir):
        """Test that plugin validation works in the experiment context."""
        # Create a minimal experiment config
        config = {
            "logging": {"level": "INFO"},
            "paths": {
                "output_dir": str(temp_plugin_dir / "output"),
                "plugin_dir": str(temp_plugin_dir),
            },
            "tests": [
                {
                    "name": "test",
                    "description": "Test experiment",
                    "iterations": 1,
                    "network_environment": {"type": "docker_compose"},
                    "services": {
                        "server": {
                            "name": "server",
                            "implementation": {"name": "picoquic", "type": "iut"},
                            "protocol": {"name": "quic", "version": "rfc9000", "role": "server"},
                        }
                    },
                }
            ],
        }

        config_path = temp_plugin_dir / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        # Test that configuration loads and validates plugins
        config_loader = ConfigLoader(str(config_path))

        # Mock plugin validation and config loading
        with patch.object(PluginManager, "validate_experiment_plugins") as mock_validate:
            mock_validate.return_value = (True, [])  # No errors

            # Mock the problematic config loading methods
            with patch.object(
                config_loader, "load_and_validate_implementation_config"
            ) as mock_impl:
                # Return a proper ImplementationConfig instance
                mock_impl.return_value = ImplementationConfig(name="picoquic", type="IUT")

                with patch.object(config_loader, "load_and_validate_protocol_config") as mock_proto:
                    # Return a proper ProtocolConfig instance
                    mock_proto.return_value = ProtocolConfig(
                        name="quic", version="rfc9000", role="server"
                    )

                    # Should not raise an exception
                    experiment_config = config_loader.load_and_validate_experiment_config()
                    assert experiment_config is not None

                    # Verify we got a proper ExperimentConfig
                    assert hasattr(experiment_config, "tests")
                    assert len(experiment_config.tests) > 0

    def test_backward_compatibility(self, plugin_manager):
        """Test that old-style plugins still work with the new system."""
        # Test loading a plugin without a manifest (backward compatibility)
        service_config = ServiceConfig(
            name="test_service",
            implementation=ImplementationConfig(name="legacy_plugin", type="iut"),
            protocol=ProtocolConfig(name="test", version="1.0", role="client"),
        )

        # Mock the legacy plugin loading
        with patch(
            "panther.plugins.plugin_manager.importlib.util.spec_from_file_location"
        ) as mock_spec:
            mock_module = MagicMock()
            mock_spec.return_value.loader.exec_module = MagicMock()

            # Mock the service manager class (old style)
            mock_service_manager_class = MagicMock()
            mock_service_manager = MagicMock()
            mock_service_manager_class.return_value = mock_service_manager

            with patch(
                "panther.plugins.plugin_manager.importlib.util.module_from_spec"
            ) as mock_module_from_spec:
                mock_module_from_spec.return_value = mock_module
                setattr(mock_module, "LegacyPluginServiceManager", mock_service_manager_class)

                # Should work without a manifest
                # Patch the catalog dictionary directly
                with patch.object(plugin_manager.plugin_catalog, "catalog", {}):
                    result = plugin_manager.create_service_manager(
                        implementation=service_config.implementation,
                        protocol=service_config.protocol,
                        implementation_dir=Path("/mock/path"),
                        service_config_to_test=service_config,
                    )

                    assert result == mock_service_manager

    def test_plugin_lifecycle_events(self, plugin_manager, mock_event_manager):
        """Test that plugin lifecycle events are properly emitted."""
        # Test that events are emitted during plugin operations
        service_config = ServiceConfig(
            name="test_service",
            implementation=ImplementationConfig(name="test_plugin", type="iut"),
            protocol=ProtocolConfig(name="test", version="1.0", role="server"),
        )

        # The plugin manager should have an event manager
        assert plugin_manager.event_manager == mock_event_manager

        # Test plugin validation with event manager
        experiment_config = MagicMock()
        experiment_config.tests = [MagicMock()]
        experiment_config.tests[0].services = {
            "test_service": MagicMock(implementation=MagicMock(name="test_plugin", type="iut"))
        }

        # Validation should work even with missing plugins
        is_valid, errors = plugin_manager.validate_experiment_plugins(experiment_config)

        # Should not be valid because plugin doesn't exist
        assert not is_valid
        assert len(errors) > 0

        # Verify service config is processed
        assert service_config.implementation.name == "test_plugin"

    def test_plugin_dependency_resolution(self, temp_plugin_dir):
        """Test that plugin dependencies are properly resolved."""
        catalog = PluginCatalog(discovery_paths=[str(temp_plugin_dir)])

        # Create plugins with dependencies
        plugin_a = {"name": "plugin_a", "version": "1.0.0", "type": "service", "dependencies": []}

        plugin_b = {
            "name": "plugin_b",
            "version": "1.0.0",
            "type": "service",
            "dependencies": [{"name": "plugin_a", "version": ">=1.0.0"}],
        }

        plugin_c = {
            "name": "plugin_c",
            "version": "1.0.0",
            "type": "service",
            "dependencies": [{"name": "plugin_b", "version": ">=1.0.0"}],
        }

        # Create plugin directories and manifests
        for plugin_data in [plugin_a, plugin_b, plugin_c]:
            plugin_path = temp_plugin_dir / "services" / plugin_data["name"]
            plugin_path.mkdir(parents=True)

            with open(plugin_path / "plugin.yaml", "w") as f:
                yaml.dump(plugin_data, f)

        # Test dependency resolution
        plugins = catalog.scan_plugins(use_cache=False)
        plugin_ids = list(plugins.keys())
        resolved_order, missing_deps = catalog.resolve_dependencies(plugin_ids)

        # Should have no missing dependencies
        assert len(missing_deps) == 0

        # Get the actual plugin manifests in resolved order
        resolved_plugins = [catalog.catalog[pid] for pid in resolved_order]
        plugin_names = [p.name for p in resolved_plugins]

        # Check that plugins are in correct order
        assert plugin_names.index("plugin_a") < plugin_names.index("plugin_b")
        assert plugin_names.index("plugin_b") < plugin_names.index("plugin_c")

    @pytest.mark.requires_docker
    @pytest.mark.skip(reason="Requires real plugin paths and Docker setup")
    def test_full_experiment_with_new_architecture(self, temp_plugin_dir):
        """Test running a complete experiment with the new plugin architecture."""
        # This test requires Docker and tests the full integration
        # Create a minimal but complete experiment configuration
        config = {
            "logging": {"level": "INFO"},
            "paths": {
                "output_dir": str(temp_plugin_dir / "output"),
                "plugin_dir": "panther/plugins",  # Use real plugins
            },
            "docker": {"build_docker_image": False},
            "tests": [
                {
                    "name": "integration_test",
                    "description": "Full integration test",
                    "network_environment": {"type": "docker_compose"},
                    "services": {
                        "server": {
                            "implementation": {"name": "picoquic", "type": "iut"},
                            "protocol": {"name": "quic", "version": "rfc9000", "role": "server"},
                            "timeout": 30,
                            "ports": ["4443:4443"],
                        },
                        "client": {
                            "implementation": {"name": "picoquic", "type": "iut"},
                            "protocol": {
                                "name": "quic",
                                "version": "rfc9000",
                                "role": "client",
                                "target": "server",
                            },
                            "timeout": 30,
                        },
                    },
                    "steps": {"wait": 10},
                }
            ],
        }

        config_path = temp_plugin_dir / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        # Create experiment manager with new architecture
        config_loader = ConfigLoader(str(config_path))
        experiment_config = config_loader.load_and_validate_experiment_config()

        # This will use the PluginManager internally
        experiment_manager = ExperimentManager(
            experiment_config=experiment_config, global_config=config_loader.global_config
        )

        # Mock Docker operations to avoid actual container creation
        with patch(
            "panther.plugins.environments.network_environment.docker_compose.docker_compose.subprocess.run"
        ):
            with patch(
                "panther.plugins.environments.network_environment.docker_compose.docker_compose.DockerComposeNetworkEnvironment._wait_for_services"
            ):
                # Initialize should work with new plugin system
                experiment_manager.initialize()

                # Verify plugin manager is PluginManager
                assert hasattr(experiment_manager, "plugin_manager")
                assert isinstance(experiment_manager.plugin_manager, PluginManager)


class TestPluginPerformance:
    """Test performance of the new plugin architecture."""

    @pytest.fixture
    def large_plugin_set(self, tmp_path):
        """Create a large set of plugins for performance testing."""
        plugin_dir = tmp_path / "plugins"

        # Create 50 mock plugins
        for i in range(50):
            plugin_path = plugin_dir / f"plugin_{i}"
            plugin_path.mkdir(parents=True)

            manifest = {
                "name": f"plugin_{i}",
                "version": "1.0.0",
                "type": "service",
                "description": f"Test plugin {i}",
                "dependencies": [],
            }

            # Add some dependencies to create a complex graph
            if i > 0:
                manifest["dependencies"] = [
                    {"name": f"plugin_{j}", "version": ">=1.0.0"} for j in range(max(0, i - 3), i)
                ]

            with open(plugin_path / "plugin.yaml", "w") as f:
                yaml.dump(manifest, f)

        return plugin_dir

    def test_catalog_discovery_performance(self, large_plugin_set, benchmark):
        """Benchmark plugin discovery performance."""
        catalog = PluginCatalog(discovery_paths=[str(large_plugin_set)])

        # Benchmark discovery
        result = benchmark(catalog.scan_plugins, use_cache=False)

        # Should discover all 50 plugins
        assert len(result) == 50

    def test_dependency_resolution_performance(self, large_plugin_set, benchmark):
        """Benchmark dependency resolution performance."""
        catalog = PluginCatalog(discovery_paths=[str(large_plugin_set)])
        plugins = catalog.scan_plugins(use_cache=False)

        # Benchmark dependency resolution
        plugin_ids = list(plugins.keys())
        result = benchmark(catalog.resolve_dependencies, plugin_ids)

        # Should resolve all dependencies (result is a tuple: resolved_order, missing_deps)
        resolved_order, missing_deps = result
        assert len(resolved_order) == 50
        assert len(missing_deps) == 0

    def test_plugin_loading_performance(self, benchmark):
        """Benchmark plugin loading performance."""
        plugin_manager = PluginManager()

        service_config = ServiceConfig(
            name="test_service",
            implementation=ImplementationConfig(name="picoquic", type="iut"),
            protocol=ProtocolConfig(name="quic", version="rfc9000", role="server"),
        )

        # Mock the actual loading to isolate plugin system performance
        with patch("panther.plugins.plugin_manager.importlib.util.spec_from_file_location"):
            with patch("panther.plugins.plugin_manager.importlib.util.module_from_spec"):
                mock_class = MagicMock()
                mock_class.return_value = MagicMock()

                with patch.object(plugin_manager, "_load_plugin_module") as mock_load:
                    mock_load.return_value = (MagicMock(), None)
                    setattr(mock_load.return_value[0], "PicoquicServiceManager", mock_class)

                    # Benchmark service manager creation
                    result = benchmark(
                        plugin_manager.create_service_manager,
                        implementation=service_config.implementation,
                        protocol=service_config.protocol,
                        implementation_dir=Path("/mock/path"),
                        service_config_to_test=service_config,
                    )

                    assert result is not None


class TestPluginValidation:
    """Test plugin validation functionality."""

    @pytest.fixture
    def temp_plugin_dir(self):
        """Create a temporary plugin directory."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def mock_event_manager(self):
        """Create a mock event manager."""
        return Mock(spec=EventManager)

    @pytest.fixture
    def plugin_manager(self, mock_event_manager):
        """Create a PluginManager instance."""
        return PluginManager(event_manager=mock_event_manager)

    def test_validate_missing_plugin(self, plugin_manager):
        """Test validation of missing plugins."""
        # Create a mock experiment config with non-existent plugin
        experiment_config = MagicMock()
        experiment_config.tests = [MagicMock()]
        experiment_config.tests[0].services = {
            "service1": {"implementation": {"name": "nonexistent_plugin", "type": "iut"}}
        }
        # Test validation
        is_valid, errors = plugin_manager.validate_experiment_plugins(experiment_config)
        assert not is_valid
        assert any("not found" in error for error in errors)

    def test_validate_plugin_configuration(self, plugin_manager, temp_plugin_dir):
        """Test validation of plugin configuration."""
        # Create a plugin with configuration schema
        plugin_path = temp_plugin_dir / "test_plugin"
        plugin_path.mkdir(parents=True)

        manifest = {
            "name": "test_plugin",
            "version": "1.0.0",
            "type": "service",
            "config_schema": {"required_param": "string", "optional_param": "number"},
            "default_config": {"optional_param": 42},
        }

        with open(plugin_path / "plugin.yaml", "w") as f:
            yaml.dump(manifest, f)

        # Test configuration validation
        catalog = PluginCatalog(discovery_paths=[str(temp_plugin_dir)])
        catalog.scan_plugins(use_cache=False)  # Load the plugins first
        plugin_manager.plugin_catalog = catalog

        # Valid configuration
        valid_config = {"required_param": "test"}
        # This should not raise an exception
        is_valid, errors = catalog.validate_plugin_config("service:test_plugin", valid_config)
        assert is_valid
        assert len(errors) == 0

        # Invalid configuration (missing required parameter)
        invalid_config = {"optional_param": 100}
        is_valid, errors = catalog.validate_plugin_config("service:test_plugin", invalid_config)
        assert not is_valid
        assert any("Missing required" in error for error in errors)
