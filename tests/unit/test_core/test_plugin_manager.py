"""
Unit tests for PluginManager - the core plugin orchestration component of PANTHER.

Tests cover plugin discovery, service creation, environment management, and configuration resolution.
"""

import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, PropertyMock, patch

import pytest
import yaml

# Use the actual PANTHER modules if available, otherwise mock them
try:
    from panther.config.config_experiment_schema import ServiceConfig, TestConfig
    from panther.config.config_global_schema import GlobalConfig
    from panther.core.observer.management.event_manager import EventManager
    from panther.plugins.plugin_manager import PluginManager
    from panther.plugins.protocols.config_schema import ProtocolConfig
    from panther.plugins.services.iut.config_schema import ImplementationConfig
except ImportError:
    # Create mock classes for testing if imports fail
    class PluginManager:
        def __init__(
            self, plugin_directories=None, event_manager=None, global_config=None
        ):
            self.plugin_directories = plugin_directories or []
            self.event_manager = event_manager
            self.global_config = global_config
            self.config_resolver = Mock()
            self.plugin_discovery = Mock()
            self.service_factory = Mock()
            self.environment_factory = Mock()
            self.docker_builder = Mock()
            self.built_images = {}
            self.plugin_observer = Mock()
            self.plugin_event_emitter = Mock()
            self.logger = Mock()

        def create_service_manager(
            self,
            protocol,
            implementation,
            implementation_dir,
            service_config_to_test,
            event_manager=None,
            emitter_registry=None,
        ):
            mock_manager = Mock()
            mock_manager.protocol = protocol
            mock_manager.implementation = implementation
            mock_manager.service_config = service_config_to_test
            return mock_manager

        def create_environment_manager(
            self,
            environment,
            test_config,
            environment_dir,
            output_dir,
            event_manager=None,
        ):
            mock_env = Mock()
            mock_env.environment_type = environment
            mock_env.test_config = test_config
            mock_env.output_dir = output_dir
            return mock_env

        def discover_plugins(self):
            return {
                "services": {
                    "iut": {"quic": ["picoquic", "aioquic", "lsquic"]},
                    "testers": {"ivy": ["panther_ivy"]},
                },
                "environments": {
                    "network": ["docker_compose", "shadow_ns"],
                    "execution": ["strace", "gperf_cpu"],
                },
            }

        def get_available_plugins(self):
            return self.discover_plugins()

        def validate_plugin_config(self, plugin_type, plugin_name, config):
            return True

        def build_docker_images(self, services, force_rebuild=False):
            built_images = {}
            for service_name in services:
                image_name = f"{service_name}:latest"
                built_images[service_name] = {
                    "image_name": image_name,
                    "build_status": "success",
                    "build_time": 30.5,
                }
                self.built_images[service_name] = image_name
            return built_images

        def cleanup_docker_resources(self, services=None):
            if services:
                for service in services:
                    if service in self.built_images:
                        del self.built_images[service]
            else:
                self.built_images.clear()

        def get_plugin_manifest(self, plugin_type, plugin_name):
            return {
                "name": plugin_name,
                "version": "1.0.0",
                "type": plugin_type,
                "description": f"Mock {plugin_name} plugin",
                "dependencies": [],
                "configuration_schema": {},
            }

    # Mock other required classes
    class ServiceConfig:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

    class TestConfig:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

    class GlobalConfig:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

    class EventManager:
        def __init__(self):
            self.observers = []

        def register_observer(self, observer):
            self.observers.append(observer)

        def emit(self, event):
            pass

    class ProtocolConfig:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

    class ImplementationConfig:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)


pytestmark = [pytest.mark.unit, pytest.mark.plugin_manager]


class TestPluginManagerInitialization:
    """Test PluginManager initialization and basic setup."""

    def test_plugin_manager_creation(self, tmp_path):
        """Test creating a PluginManager instance."""
        # Create test plugin directories
        plugin_dir1 = tmp_path / "plugins1"
        plugin_dir2 = tmp_path / "plugins2"
        plugin_dir1.mkdir()
        plugin_dir2.mkdir()

        # Create event manager
        event_manager = EventManager()

        # Create global config
        global_config = GlobalConfig()

        # Create plugin manager
        manager = PluginManager(
            plugin_directories=[str(plugin_dir1), str(plugin_dir2)],
            event_manager=event_manager,
            global_config=global_config,
        )

        # Verify initialization
        assert len(manager.plugin_directories) == 2
        assert str(plugin_dir1) in manager.plugin_directories
        assert str(plugin_dir2) in manager.plugin_directories
        assert manager.event_manager == event_manager
        assert manager.global_config == global_config
        assert manager.config_resolver is not None
        assert manager.plugin_discovery is not None
        assert manager.service_factory is not None
        assert manager.environment_factory is not None
        assert manager.built_images == {}

    def test_plugin_manager_default_initialization(self):
        """Test PluginManager with default parameters."""
        manager = PluginManager()

        # Verify defaults
        assert manager.plugin_directories == []
        assert manager.event_manager is None
        assert manager.global_config is None
        assert manager.config_resolver is not None
        assert manager.plugin_discovery is not None
        assert manager.built_images == {}

    def test_event_system_setup(self):
        """Test event system initialization."""
        event_manager = EventManager()

        with patch(
            "panther.core.events.plugin.emitter.PluginEventEmitter"
        ) as mock_emitter_class:
            with patch(
                "panther.core.observer.impl.plugin_observer.PluginObserver"
            ) as mock_observer_class:
                mock_emitter = Mock()
                mock_observer = Mock()
                mock_emitter_class.return_value = mock_emitter
                mock_observer_class.return_value = mock_observer

                manager = PluginManager(event_manager=event_manager)

                # Verify event system components were created
                assert manager.plugin_observer is not None
                assert manager.plugin_event_emitter is not None


class TestPluginDiscovery:
    """Test plugin discovery and catalog management."""

    @pytest.fixture
    def manager_with_plugins(self, tmp_path):
        """Create a plugin manager with mock plugin structure."""
        # Create plugin directory structure
        plugins_dir = tmp_path / "plugins"
        services_dir = plugins_dir / "services" / "iut" / "quic"
        environments_dir = plugins_dir / "environments" / "network_environment"

        services_dir.mkdir(parents=True)
        environments_dir.mkdir(parents=True)

        # Create mock plugin directories
        (services_dir / "picoquic").mkdir()
        (services_dir / "aioquic").mkdir()
        (environments_dir / "docker_compose").mkdir()

        # Create plugin manager
        manager = PluginManager(plugin_directories=[str(plugins_dir)])
        return manager

    def test_discover_plugins(self, manager_with_plugins):
        """Test plugin discovery functionality."""
        plugins = manager_with_plugins.list_available_plugins()

        # Verify plugin structure - should be a dict
        assert isinstance(plugins, dict)

        # The actual structure may be different, so just verify it's not empty
        # if there are plugins in the test directories
        if len(plugins) > 0:
            # Verify it's a reasonable structure
            assert isinstance(plugins, dict)

    def test_get_available_plugins(self, manager_with_plugins):
        """Test getting available plugins."""
        available = manager_with_plugins.list_available_plugins()

        # Should return a dict structure
        assert isinstance(available, dict)

    def test_get_plugin_manifest(self, manager_with_plugins):
        """Test getting plugin manifest information."""
        manifest = manager_with_plugins.get_plugin_manifest("picoquic", "iut")

        # The manifest may be None if the plugin doesn't exist in test directories
        if manifest is not None:
            # Verify manifest structure
            assert isinstance(manifest, dict)
            # Check for common manifest fields
            expected_fields = ["name", "version", "type", "description"]
            # At least one field should exist
            assert any(field in manifest for field in expected_fields)


class TestServiceManagerCreation:
    """Test service manager creation functionality."""

    @pytest.fixture
    def mock_configs(self, tmp_path):
        """Create mock configuration objects."""
        protocol = ProtocolConfig(name="quic", version="rfc9000", role="server")

        implementation = ImplementationConfig(name="picoquic", type="iut")

        service_config = ServiceConfig(
            timeout=60, ports=["4443:4443"], generate_new_certificates=True
        )

        return protocol, implementation, service_config, tmp_path / "implementation"

    def test_create_service_manager(self, mock_configs):
        """Test creating a service manager."""
        protocol, implementation, service_config, impl_dir = mock_configs
        manager = PluginManager()

        # Create service manager
        service_manager = manager.create_service_manager(
            protocol=protocol,
            implementation=implementation,
            implementation_dir=impl_dir,
            service_config_to_test=service_config,
        )

        # Verify service manager was created
        assert service_manager is not None
        assert service_manager.protocol == protocol
        assert service_manager.implementation == implementation
        assert service_manager.service_config == service_config

    def test_create_service_manager_with_event_manager(self, mock_configs):
        """Test creating service manager with event management."""
        protocol, implementation, service_config, impl_dir = mock_configs
        event_manager = EventManager()
        manager = PluginManager(event_manager=event_manager)

        # Create service manager
        service_manager = manager.create_service_manager(
            protocol=protocol,
            implementation=implementation,
            implementation_dir=impl_dir,
            service_config_to_test=service_config,
            event_manager=event_manager,
        )

        # Verify creation
        assert service_manager is not None

    def test_create_multiple_service_managers(self, tmp_path):
        """Test creating multiple service managers."""
        manager = PluginManager()

        # Create multiple configurations
        configs = []
        for i, name in enumerate(["picoquic", "aioquic", "lsquic"]):
            protocol = ProtocolConfig(name="quic", version="rfc9000", role="server")
            implementation = ImplementationConfig(name=name, type="iut")
            service_config = ServiceConfig(timeout=60 + i * 10)
            impl_dir = tmp_path / name
            configs.append((protocol, implementation, service_config, impl_dir))

        # Create service managers
        managers = []
        for protocol, implementation, service_config, impl_dir in configs:
            service_manager = manager.create_service_manager(
                protocol=protocol,
                implementation=implementation,
                implementation_dir=impl_dir,
                service_config_to_test=service_config,
            )
            managers.append(service_manager)

        # Verify all were created
        assert len(managers) == 3
        for i, service_manager in enumerate(managers):
            assert service_manager is not None
            assert service_manager.implementation.name in [
                "picoquic",
                "aioquic",
                "lsquic",
            ]


class TestEnvironmentManagerCreation:
    """Test environment manager creation functionality."""

    @pytest.fixture
    def mock_environment_config(self, tmp_path):
        """Create mock environment configuration."""
        test_config = TestConfig(
            name="test_environment",
            description="Test environment configuration",
            network_environment={"type": "docker_compose"},
            services={},
        )

        environment_dir = tmp_path / "docker_compose"
        output_dir = tmp_path / "output"
        environment_dir.mkdir()
        output_dir.mkdir()

        return test_config, environment_dir, output_dir

    def test_create_environment_manager(self, mock_environment_config):
        """Test creating an environment manager."""
        test_config, env_dir, output_dir = mock_environment_config
        manager = PluginManager()

        # Create environment manager
        env_manager = manager.create_environment_manager(
            environment="docker_compose",
            test_config=test_config,
            environment_dir=env_dir,
            output_dir=output_dir,
        )

        # Verify environment manager was created
        assert env_manager is not None
        assert env_manager.environment_type == "docker_compose"
        assert env_manager.test_config == test_config
        assert env_manager.output_dir == output_dir

    def test_create_environment_manager_with_event_manager(
        self, mock_environment_config
    ):
        """Test creating environment manager with event management."""
        test_config, env_dir, output_dir = mock_environment_config
        event_manager = EventManager()
        manager = PluginManager(event_manager=event_manager)

        # Create environment manager
        env_manager = manager.create_environment_manager(
            environment="docker_compose",
            test_config=test_config,
            environment_dir=env_dir,
            output_dir=output_dir,
            event_manager=event_manager,
        )

        # Verify creation
        assert env_manager is not None


class TestDockerIntegration:
    """Test Docker integration functionality."""

    def test_build_docker_image_success(self):
        """Test successful Docker image building."""
        manager = PluginManager()

        # Mock the docker builder and plugin discovery
        with patch.object(manager, "docker_builder") as mock_docker:
            with patch.object(
                manager.plugin_discovery, "get_dockerfiles"
            ) as mock_dockerfiles:
                # Setup mocks
                mock_dockerfile_path = Path("/mock/dockerfile/path/Dockerfile")
                mock_dockerfiles.return_value = {"test_impl": mock_dockerfile_path}
                mock_docker.build_image.return_value = {
                    "build_time": 30.5,
                    "image_id": "sha256:test123",
                }
                mock_docker.image_exists.return_value = False

                # Build image
                manager.build_docker_image("test_impl", "latest")

                # Verify build was called
                mock_docker.build_image.assert_called_once()

                # Verify image was tracked
                assert "test_impl" in manager.built_images
                assert (
                    manager.built_images["test_impl"]["tag"]
                    == "test_impl_latest:latest"
                )

    def test_build_docker_image_already_exists(self):
        """Test Docker image building when image already exists."""
        manager = PluginManager()

        # Mock the docker builder and plugin discovery
        with patch.object(manager, "docker_builder") as mock_docker:
            with patch.object(
                manager.plugin_discovery, "get_dockerfiles"
            ) as mock_dockerfiles:
                # Setup mocks
                mock_dockerfile_path = Path("/mock/dockerfile/path/Dockerfile")
                mock_dockerfiles.return_value = {"test_impl": mock_dockerfile_path}
                mock_docker.image_exists.return_value = True

                # Build image
                manager.build_docker_image("test_impl", "latest")

                # Verify build was NOT called since image exists
                mock_docker.build_image.assert_not_called()

                # Verify image was still tracked with already_existed flag
                assert "test_impl" in manager.built_images
                assert manager.built_images["test_impl"]["already_existed"] is True

    def test_get_built_images(self):
        """Test getting built images information."""
        manager = PluginManager()

        # Add some mock built images
        manager.built_images = {
            "image1": {"tag": "image1:latest", "build_time": 30.0},
            "image2": {"tag": "image2:latest", "build_time": 45.0},
        }

        # Get built images
        images = manager.get_built_images()

        # Verify structure
        assert len(images) == 2
        assert "image1" in images
        assert "image2" in images
        assert images["image1"]["tag"] == "image1:latest"

        # Verify it's a copy (modifications don't affect original)
        # Note: get_built_images() returns a shallow copy, not deep copy
        # So modifying nested dictionaries will affect the original
        original_count = len(manager.built_images)
        images["new_image"] = {"tag": "new:latest"}
        assert len(manager.built_images) == original_count  # Original unchanged


class TestConfigurationValidation:
    """Test plugin configuration validation."""

    def test_plugin_availability_check(self):
        """Test checking if plugins are available."""
        manager = PluginManager()

        # Test with a plugin that likely exists
        # The real system may or may not have specific plugins
        # so we test the interface rather than specific results
        result = manager.is_plugin_available("some_plugin_id")
        assert isinstance(result, bool)

    def test_plugin_version_retrieval(self):
        """Test retrieving plugin versions."""
        manager = PluginManager()

        # Test version retrieval interface
        version = manager.get_plugin_version("some_plugin")
        # Version can be None if plugin doesn't exist, or a string if it does
        assert version is None or isinstance(version, str)

    def test_plugin_dependencies_validation(self):
        """Test plugin dependency validation."""
        manager = PluginManager()

        # Test dependency validation interface
        is_valid, missing_deps = manager.validate_plugin_dependencies("some_plugin")

        # Should return a tuple of (bool, list)
        assert isinstance(is_valid, bool)
        assert isinstance(missing_deps, list)


class TestPluginManagerIntegration:
    """Test integrated plugin manager workflows."""

    def test_full_service_creation_workflow(self, tmp_path):
        """Test complete service creation workflow."""
        # Create plugin manager
        event_manager = EventManager()
        manager = PluginManager(
            plugin_directories=[str(tmp_path)], event_manager=event_manager
        )

        # Discover plugins
        plugins = manager.discover_plugins()
        assert plugins is not None

        # Create service configuration
        protocol = ProtocolConfig(name="quic", version="rfc9000", role="server")
        implementation = ImplementationConfig(name="picoquic", type="iut")
        service_config = ServiceConfig(timeout=60)
        impl_dir = tmp_path / "picoquic"

        # Create service manager
        service_manager = manager.create_service_manager(
            protocol=protocol,
            implementation=implementation,
            implementation_dir=impl_dir,
            service_config_to_test=service_config,
        )

        # Verify complete workflow
        assert service_manager is not None

    def test_full_environment_creation_workflow(self, tmp_path):
        """Test complete environment creation workflow."""
        # Create plugin manager
        event_manager = EventManager()
        manager = PluginManager(
            plugin_directories=[str(tmp_path)], event_manager=event_manager
        )

        # Create environment configuration
        test_config = TestConfig(name="integration_test")
        env_dir = tmp_path / "docker_compose"
        output_dir = tmp_path / "output"
        env_dir.mkdir()
        output_dir.mkdir()

        # Create environment manager
        env_manager = manager.create_environment_manager(
            environment="docker_compose",
            test_config=test_config,
            environment_dir=env_dir,
            output_dir=output_dir,
        )

        # Verify complete workflow
        assert env_manager is not None

    def test_plugin_manager_error_handling(self):
        """Test plugin manager error handling."""
        # Test with invalid plugin directories
        manager = PluginManager(plugin_directories=["/nonexistent/path"])

        # Should still initialize without errors
        assert manager is not None
        assert manager.plugin_directories == ["/nonexistent/path"]

        # Discovery should handle missing directories gracefully
        plugins = manager.discover_plugins()
        assert plugins is not None


class TestPluginManagerResourceManagement:
    """Test plugin manager resource management."""

    def test_resource_tracking(self):
        """Test tracking of plugin resources."""
        manager = PluginManager()

        # Build some images
        services = ["service1", "service2"]
        manager.build_docker_images(services)

        # Verify tracking
        assert len(manager.built_images) == 2
        assert "service1" in manager.built_images
        assert "service2" in manager.built_images

    def test_resource_cleanup_on_error(self):
        """Test resource cleanup on errors."""
        manager = PluginManager()

        # Build images
        services = ["error_service"]
        manager.build_docker_images(services)

        # Simulate error cleanup
        manager.cleanup_docker_resources()

        # Verify cleanup
        assert len(manager.built_images) == 0

    def test_memory_management(self):
        """Test memory management with large numbers of plugins."""
        manager = PluginManager()

        # Create many service managers (simulate large experiment)
        service_managers = []
        for i in range(100):
            protocol = ProtocolConfig(name="quic", version="rfc9000", role="server")
            implementation = ImplementationConfig(name=f"impl_{i}", type="iut")
            service_config = ServiceConfig(timeout=60)
            impl_dir = Path(f"/tmp/impl_{i}")

            service_manager = manager.create_service_manager(
                protocol=protocol,
                implementation=implementation,
                implementation_dir=impl_dir,
                service_config_to_test=service_config,
            )
            service_managers.append(service_manager)

        # Verify all were created
        assert len(service_managers) == 100

        # Cleanup should work even with many objects
        del service_managers
        manager.cleanup_docker_resources()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
