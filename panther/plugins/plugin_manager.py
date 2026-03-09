"""Unified Plugin Manager for Panther Framework.

Single source of truth for plugin management: discovery, lifecycle,
caching, Docker integration, and event coordination.
"""

import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Tuple, Union

from panther.plugins.core.plugin_discovery import PluginDiscovery
from panther.plugins.core.structures.plugin_manifest import PluginManifest
from panther.plugins.core.structures.plugin_registration import PluginRegistration

if TYPE_CHECKING:
    from panther.config.core.models import ServiceConfig, TestConfig

from panther.config.core.models import ProtocolConfig
from panther.config.core.models.global_config import GlobalConfig
from panther.config.core.models.service import ImplementationConfig
from panther.core.docker_builder import DockerBuilder
from panther.core.exceptions.fast_fail import FastFailHandler
from panther.core.observer.impl.plugin_observer import PluginObserver
from panther.core.observer.management.event_manager import EventManager
from panther.core.utils.logging_mixin import LoggerMixin
from panther.plugins.core.plugin_catalog import PluginCatalog
from panther.plugins.core.plugin_factory import PluginFactory
from panther.plugins.core.structures.plugin_manifest import PluginManifest

# Import plugins core components
from panther.plugins.core.structures.plugin_metadata import PluginMetadata, PluginType
from panther.plugins.environments.environment_interface import IEnvironmentPlugin
from panther.plugins.services.services_interface import IServiceManager


class PluginManager(LoggerMixin):
    """Central orchestrator for PANTHER's plugin ecosystem.

    Thread-safe singleton managing plugin discovery, lifecycle, dependency
    resolution, Docker integration, and multi-level caching with TTL.

    Subsequent instantiation attempts update configuration parameters
    rather than creating new instances.

    Example:
        >>> manager = PluginManager()
        >>> plugins = manager.discover_plugins()
        >>> versions = manager.discover_protocol_versions("quic")
    """

    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        """Create or return the singleton instance.

        If an instance already exists, returns it and allows updating
        configuration parameters if provided.
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        plugin_directories: Optional[List[str]] = None,
        event_manager: Optional[EventManager] = None,
        global_config: Optional[GlobalConfig] = None,
        fast_fail_handler: Optional[FastFailHandler] = None,
        enable_cache: bool = True,
        cache_ttl: int = 3600,  # 1 hour TODO add parameters
        experiment_context: Optional[Any] = None,
    ):
        """Initialize the unified plugin manager.

        Args:
            plugin_directories: Directories to scan for plugins
            event_manager: Event manager for plugin events
            global_config: Global configuration for Docker and other settings
            fast_fail_handler: Fast fail handler for critical error management
            enable_cache: Enable plugin metadata caching
            cache_ttl: Cache time-to-live in seconds
            experiment_context: Reference to the ExperimentManager instance for
                lifecycle coordination. Creates a circular reference by design.

        Note: Configuration parameters can be updated on subsequent calls.
        """
        # Allow parameter updates even for existing instances
        if getattr(self, "_initialized", False):
            # Update parameters on existing instance
            updated_params = []

            if (
                plugin_directories is not None
                and getattr(self, "plugin_directories", None) != plugin_directories
            ):
                self.plugin_directories = plugin_directories
                # Update plugin discovery with new directories
                self.plugin_discovery.plugin_directories = plugin_directories
                updated_params.append(f"plugin_directories={plugin_directories}")

            if (
                global_config is not None
                and getattr(self, "global_config", None) != global_config
            ):
                self.global_config = global_config
                updated_params.append("global_config=<updated>")

            if (
                fast_fail_handler is not None
                and getattr(self, "fast_fail_handler", None) != fast_fail_handler
            ):
                self.fast_fail_handler = fast_fail_handler
                updated_params.append("fast_fail_handler=<updated>")

            if hasattr(self, "enable_cache") and self.enable_cache != enable_cache:
                self.enable_cache = enable_cache
                # Update plugin discovery cache setting
                if hasattr(self, "plugin_discovery"):
                    self.plugin_discovery.enable_cache = enable_cache
                updated_params.append(f"enable_cache={enable_cache}")

            if hasattr(self, "cache_ttl") and self.cache_ttl != cache_ttl:
                self.cache_ttl = cache_ttl
                # Update plugin discovery cache TTL
                if hasattr(self, "plugin_discovery"):
                    self.plugin_discovery.cache_ttl = cache_ttl
                updated_params.append(f"cache_ttl={cache_ttl}")

            if updated_params:
                self.logger.debug(
                    f"Updated PluginManager parameters: {', '.join(updated_params)}"
                )
            else:
                self.logger.debug("PluginManager parameters unchanged.")
            return

        # First-time initialization
        super().__init__()
        self.__class__._initialized = True
        self.logger.info("Initializing PluginManager singleton instance")

        # Configuration
        self.plugin_directories = plugin_directories or self._get_default_directories()
        # Use provided event_manager or get the singleton instance
        self.event_manager = event_manager or EventManager.get_instance()
        self.global_config = global_config
        self.fast_fail_handler = fast_fail_handler
        self.enable_cache = enable_cache
        self.cache_ttl = cache_ttl
        self.experiment_context = experiment_context
        # Core components
        self.plugin_discovery = PluginDiscovery(
            plugin_directories=self.plugin_directories,
            enable_cache=enable_cache,
            cache_ttl=cache_ttl,
        )  # Use PluginDiscovery for discovery
        self.plugin_catalog = PluginCatalog(self.plugin_directories)
        self.plugin_factory = PluginFactory(
            plugin_manager=self,
            event_manager=event_manager,
            fast_fail_handler=fast_fail_handler,
        )

        # Plugin registry and metadata cache
        self.plugins: Dict[str, PluginMetadata] = {}
        self.registrations: Dict[str, PluginRegistration] = {}

        # Caches with TTL
        self._cache_timestamp = 0
        self._discovery_cache: Optional[Dict[str, PluginMetadata]] = None
        self._version_cache: Dict[str, List[str]] = {}
        self._dependency_graph: Dict[str, Set[str]] = {}

        # Statistics
        self._discovery_count = 0
        self._last_discovery_time = 0

        # Event system setup
        self.plugin_observer = None
        self.plugin_event_emitter = None
        if self.event_manager:
            self._setup_event_system()

        # Docker management - Initialize singleton with configuration
        try:
            # PluginManager initializes DockerBuilder singleton with global config
            build_log_file = (
                global_config.docker.log_docker_image_build
                if global_config and hasattr(global_config, "docker")
                else False
            )
            self.docker_builder = DockerBuilder.get_instance(
                build_log_file=build_log_file,
                enable_cache=True,
                global_config=self.global_config,
                experiment_context=self.experiment_context,
            )
        except Exception as e:
            self.logger.warning("Failed to initialize DockerBuilder: %s", e)
            self.docker_builder = None
            raise RuntimeError(
                "DockerBuilder initialization failed. "
                "Ensure Docker is configured correctly in global config."
            ) from e

        # Auto-discover on initialization
        self.logger.info("Initializing unified plugin manager")
        self.discover_plugins()

    @property
    def experiment_context_for_plugins(self):
        """Provide experiment context access for plugin instances.

        This allows service managers and environments that use this
        plugin manager to access experiment context for Docker operations.
        """
        return self.experiment_context

    def _get_default_directories(self) -> List[str]:
        """Get default plugin directories."""
        base_path = Path(__file__).parent
        return [
            str(
                base_path / "protocols"
            ),  # Add protocols directory for protocol plugin discovery
            str(base_path / "services" / "iut"),
            str(base_path / "services" / "testers"),
            str(base_path / "environments" / "network_environment"),
            str(base_path / "environments" / "execution_environment"),
        ]

    def set_experiment_context(self, context: Any) -> None:
        """Set the experiment context for this plugin manager.

        This allows service managers and environments to access the experiment context
        for Docker operations and other configurations.

        Args:
            context: Experiment context object
        """
        self.experiment_context = context
        self.logger.debug("Experiment context set for PluginManager")

        # Update DockerBuilder with new context if available
        if self.docker_builder:
            self.docker_builder.set_experiment_context(context)

    def _setup_event_system(self) -> None:
        """Set up the event system for plugin management."""
        try:
            # Import event emitter
            from panther.core.events.plugin.emitter import PluginEventEmitter

            # Create plugin observer
            self.plugin_observer = PluginObserver(event_manager=self.event_manager)

            # Create plugin event emitter
            self.plugin_event_emitter = PluginEventEmitter(self.event_manager)

            self.logger.debug("Plugin event system initialized successfully")
        except Exception as e:
            self.logger.warning("Failed to initialize plugin event system: %s", e)

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid based on TTL and filesystem changes."""
        if not self.enable_cache or not self._discovery_cache:
            return False

        # Check TTL first (fastest check)
        adaptive_ttl = self._get_adaptive_cache_ttl()
        if time.time() - self._cache_timestamp >= adaptive_ttl:
            self.logger.debug("Cache expired based on adaptive TTL: %ds", adaptive_ttl)
            return False

        # Check for filesystem changes (more expensive but necessary)
        if self._check_plugin_directories_changed():
            self.logger.info("Plugin directories modified, cache invalidated")
            return False

        return True

    def _get_adaptive_cache_ttl(self) -> int:
        """Get cache TTL based on recent filesystem activity."""
        base_ttl = self.cache_ttl

        # Check for recent changes in last hour
        recent_changes = self._count_recent_plugin_changes(3600)  # 1 hour

        if recent_changes > 5:
            # High activity - reduce cache to 5 minutes
            return 300
        elif recent_changes > 0:
            # Some activity - reduce cache to 15 minutes
            return 900
        else:
            # No recent activity - use full TTL
            return base_ttl

    def _count_recent_plugin_changes(self, time_window: int) -> int:
        """Count number of files changed in plugin directories within time window."""
        changes = 0
        cutoff_time = time.time() - time_window

        for directory in self.plugin_directories:
            dir_path = Path(directory)
            if dir_path.exists():
                try:
                    for file_path in dir_path.rglob("*.py"):
                        if file_path.stat().st_mtime > cutoff_time:
                            changes += 1
                except (OSError, PermissionError):
                    # Skip directories we can't access
                    continue

        return changes

    def _check_plugin_directories_changed(self) -> bool:
        """Check if any plugin directories have been modified since last cache."""
        if not hasattr(self, "_dir_mtimes"):
            # First time - record directory modification times
            self._dir_mtimes = {}
            for directory in self.plugin_directories:
                dir_path = Path(directory)
                if dir_path.exists():
                    try:
                        # Get most recent modification time in directory tree
                        newest_mtime = max(
                            (
                                p.stat().st_mtime
                                for p in dir_path.rglob("*.py")
                                if p.is_file()
                            ),
                            default=0,
                        )
                        self._dir_mtimes[directory] = newest_mtime
                    except (OSError, PermissionError):
                        self._dir_mtimes[directory] = 0
            return False

        # Check if any directories have newer files
        for directory in self.plugin_directories:
            dir_path = Path(directory)
            if dir_path.exists():
                try:
                    newest_mtime = max(
                        (
                            p.stat().st_mtime
                            for p in dir_path.rglob("*.py")
                            if p.is_file()
                        ),
                        default=0,
                    )
                    if newest_mtime > self._dir_mtimes.get(directory, 0):
                        self.logger.debug(f"Directory {directory} has newer files")
                        # Update cache
                        self._dir_mtimes[directory] = newest_mtime
                        return True
                except (OSError, PermissionError):
                    continue

        return False

    def discover_plugins(
        self, force_refresh: bool = False
    ) -> Dict[str, PluginMetadata]:
        """Discover all available plugins using PluginDiscovery.

        This method delegates to PluginDiscovery for actual discovery,
        following DRY and SOLID principles.

        Returns:
            Dict mapping plugin names to metadata
        """
        start_time = time.time()

        # Check cache
        if self._is_cache_valid() and not force_refresh:
            self.logger.info(
                "Using cached plugin discovery results (cache age: %.2fs)",
                time.time() - self._cache_timestamp,
            )
            return self._discovery_cache.copy()

        self.logger.info("Starting fresh plugin discovery")
        self._discovery_count += 1
        self.logger.debug(
            "This is plugin discovery #%d for this singleton instance",
            self._discovery_count,
        )

        # Delegate discovery to PluginDiscovery (DRY principle)
        external_paths = (
            getattr(self.global_config, "external_plugin_paths", None)
            if self.global_config
            else None
        )
        discovered_plugins = self.plugin_discovery.discover_plugins(
            force_refresh=force_refresh, external_plugin_paths=external_paths
        )

        # Update cache
        self._discovery_cache = discovered_plugins
        self._cache_timestamp = time.time()
        self.plugins.update(discovered_plugins)

        # Also update the catalog for compatibility with validation
        for plugin_name, metadata in discovered_plugins.items():
            # Convert string dependencies to PluginDependency objects
            from panther.plugins.core.structures.plugin_dependency import (
                PluginDependency,
            )

            plugin_deps = []
            if metadata.dependencies:
                for dep in metadata.dependencies:
                    if isinstance(dep, str):
                        # Simple string dependency - create basic PluginDependency
                        plugin_deps.append(PluginDependency(name=dep, version_spec="*"))
                    elif isinstance(dep, dict):
                        # Dictionary with name and version_spec
                        plugin_deps.append(
                            PluginDependency(
                                name=dep.get("name", dep.get("dependency", "")),
                                version_spec=dep.get("version_spec", "*"),
                            )
                        )
                    else:
                        # Already a PluginDependency object
                        plugin_deps.append(dep)

            # Create a manifest from metadata for catalog compatibility
            manifest = PluginManifest(
                name=metadata.name,
                version=metadata.version,
                type=metadata.type,
                supported_protocols=metadata.supported_protocols,
                entry_point=getattr(metadata, "entry_point", ""),
                config_schema=getattr(metadata, "config_schema", {}),
                dependencies=plugin_deps,
                description=metadata.description,
                author=metadata.author,
                capabilities=metadata.capabilities,
                tags=getattr(metadata, "tags", []),
                file_path=str(metadata.path) if metadata.path else None,
                runtime_mode=metadata.runtime_mode,  # Fix: Include runtime_mode from metadata
            )
            plugin_id = f"{metadata.type}:{metadata.name}"
            self.plugin_catalog.catalog[plugin_id] = manifest

        # Update statistics
        self._last_discovery_time = time.time() - start_time

        self.logger.info(
            "Discovered %d plugins in %.2fs",
            len(discovered_plugins),
            self._last_discovery_time,
        )

        return discovered_plugins.copy()

    def _merge_metadata(
        self, existing: PluginMetadata, new: PluginMetadata
    ) -> PluginMetadata:
        """Merge two metadata objects, preferring more complete information."""
        # Create a copy of existing
        merged_data = existing.to_dict()
        new_data = new.to_dict()

        # Merge fields, preferring non-empty values
        for key, value in new_data.items():
            if value and (
                not merged_data.get(key)
                or (
                    isinstance(value, list)
                    and len(value) > len(merged_data.get(key, []))
                )
            ):
                merged_data[key] = value

        return PluginMetadata.from_dict(merged_data)

    def _manifest_to_metadata(
        self, manifest: PluginManifest
    ) -> Optional[PluginMetadata]:
        """Convert PluginManifest from decorator to PluginMetadata."""
        try:
            # Convert dependencies to list of strings
            deps = []
            if manifest.dependencies:
                for dep in manifest.dependencies:
                    if hasattr(dep, "name"):
                        deps.append(dep.name)
                    else:
                        deps.append(str(dep))

            return PluginMetadata(
                name=manifest.name,
                version=manifest.version,
                type=(
                    manifest.type.value
                    if hasattr(manifest.type, "value")
                    else str(manifest.type)
                ),
                supported_protocols=manifest.supported_protocols or [],
                path=Path(manifest.file_path) if manifest.file_path else None,
                dependencies=deps,
                description=manifest.description or "",
                author=manifest.author or "",
                capabilities=manifest.capabilities or [],
            )
        except Exception as e:
            self.logger.error(f"Failed to convert manifest to metadata: {e}")
            return None

    def get_plugin(self, name: str) -> Optional[PluginMetadata]:
        """Get plugin metadata by name.

        Args:
            name: Plugin name

        Returns:
            Plugin metadata or None if not found
        """
        # Check cache first
        plugins = self.discover_plugins()
        return plugins.get(name)

    def validate_experiment_plugins(self, experiment_config) -> Tuple[bool, List[str]]:
        """Validate that all plugins required by an experiment are available.

        Delegates to PluginCatalog for actual validation implementation.

        Args:
            experiment_config: Experiment configuration

        Returns:
            Tuple of (is_valid, error_messages)
        """
        return self.plugin_catalog.validate_experiment_plugins(experiment_config)

    def get_plugins_by_type(
        self, plugin_type: Union[str, PluginType]
    ) -> List[PluginMetadata]:
        """Get all plugins of a specific type.

        Args:
            plugin_type: Plugin type to filter by

        Returns:
            List of matching plugins
        """
        plugins = self.discover_plugins()

        # Convert string to PluginType enum if needed
        if isinstance(plugin_type, str):
            try:
                plugin_type = PluginType(plugin_type)
            except ValueError:
                raise ValueError(
                    f"Invalid plugin type: '{plugin_type}'. "
                    f"Valid types are: {', '.join(pt.value for pt in PluginType)}"
                )

        # Get the string value for comparison
        type_str = plugin_type.value

        return [plugin for plugin in plugins.values() if plugin.type == type_str]

    def get_plugins_by_protocol(self, protocol: str) -> List[PluginMetadata]:
        """Get all plugins supporting a specific protocol.

        Args:
            protocol: Protocol name

        Returns:
            List of supporting plugins
        """
        plugins = self.discover_plugins()
        return [
            plugin
            for plugin in plugins.values()
            if plugin.is_compatible_with(protocol=protocol)
        ]

    def validate_plugin_dependencies(self, plugin_name: str) -> Tuple[bool, List[str]]:
        """Validate plugin dependencies.

        Delegates to PluginCatalog for actual dependency validation implementation.

        Args:
            plugin_name: Name of plugin to validate

        Returns:
            Tuple of (all_satisfied, missing_dependencies)
        """
        return self.plugin_catalog.validate_plugin_dependencies(plugin_name)

    def discover_protocol_versions(
        self, protocol: Optional[str] = None
    ) -> Dict[str, List[str]]:
        """Discover available protocol versions.

        Delegates to PluginDiscovery for actual discovery implementation.

        Args:
            protocol: Optional protocol to filter by

        Returns:
            Dictionary mapping protocols to version lists
        """
        return self.plugin_discovery.discover_protocol_versions(protocol)

    def refresh_plugins(self):
        """Force refresh of all plugin information."""
        self.logger.info("Force refreshing plugin cache")
        self._discovery_cache = None
        self._cache_timestamp = 0
        self._version_cache.clear()
        self.plugin_catalog.refresh()
        self.discover_plugins(force_refresh=True)

    def _validate_cached_plugin_images(
        self,
        plugin_metadata: PluginMetadata,
        version: str = None,
        build_mode: str = None,
        runtime_mode: str = "minimal",
        z3_source: str = "",
    ) -> bool:
        """Validate that Docker images referenced by plugin are still available.

        Args:
            plugin_metadata: Plugin metadata containing name and other info
            version: Optional version (e.g., 'rfc9000') to include in image name
            build_mode: Optional build mode (e.g., 'rel-lto') to include in image name
            runtime_mode: Optional runtime mode (e.g., 'debug', 'profile') to include in image name
            z3_source: Optional Z3 source ('local', 'pip') to include in image name
        """
        if not self.docker_builder:
            self.logger.debug("No Docker builder available, skipping image validation")
            return True

        # Use DockerBuilder's generate_image_tag method for consistent tag generation
        plugin_name = plugin_metadata.name

        # Get target platform from docker builder to match build-time tag generation
        target_platform = ""
        if hasattr(self.docker_builder, "get_target_platform"):
            target_platform = self.docker_builder.get_target_platform()

        # Generate expected image tag using the same logic as docker builds
        expected_image = self.docker_builder.generate_image_tag(
            impl_name=plugin_name,
            version=version or "",
            tag_version="latest",
            build_mode=build_mode or "",
            runtime_mode=runtime_mode,
            target_platform=target_platform,
            z3_source=z3_source,
        )

        try:
            if (
                hasattr(self.docker_builder, "image_cache")
                and self.docker_builder.image_cache
            ):
                exists = self.docker_builder.image_cache.image_exists(expected_image)
                if not exists:
                    self.logger.info(
                        f"Docker image {expected_image} not found for plugin {plugin_metadata.name} - will be built when needed"
                    )
                    # Don't return False here - let service manager handle image building when needed
                    return True
            else:
                # Fallback to direct Docker check if image cache not available
                self.logger.debug(
                    "No image cache available, skipping Docker image validation"
                )
        except Exception as e:
            self.logger.warning(
                f"Error checking Docker image for {plugin_metadata.name}: {e}"
            )
            # Don't fail validation on Docker errors - just log the issue
            return True

        return True

    def _validate_plugin_metadata_consistency(
        self, plugin_metadata: PluginMetadata
    ) -> bool:
        """Validate that cached plugin metadata is consistent with filesystem."""
        if not plugin_metadata.path or not Path(plugin_metadata.path).exists():
            self.logger.warning(f"Plugin file {plugin_metadata.path} no longer exists")
            return False

        # Check if plugin file has been modified since cache
        try:
            file_mtime = Path(plugin_metadata.path).stat().st_mtime
            if file_mtime > self._cache_timestamp:
                self.logger.debug(
                    f"Plugin file {plugin_metadata.path} modified since cache"
                )
                return False
        except (OSError, AttributeError):
            return True  # Don't fail on filesystem errors

        return True

    def _invalidate_stale_cache_for_plugin(
        self,
        plugin_name: str,
        version: str = None,
        build_mode: str = None,
        runtime_mode: str = "minimal",
    ) -> bool:
        """Check and invalidate cache if plugin metadata is stale."""
        plugin_metadata = self.plugins.get(plugin_name)
        if not plugin_metadata:
            return False

        # Validate Docker images with version, build_mode, and runtime_mode context
        if not self._validate_cached_plugin_images(
            plugin_metadata,
            version=version,
            build_mode=build_mode,
            runtime_mode=runtime_mode,
        ):
            self.logger.info(
                f"Invalidating cache due to missing Docker image for {plugin_name}"
            )
            self.refresh_plugins()
            return True

        # Validate metadata consistency
        if not self._validate_plugin_metadata_consistency(plugin_metadata):
            self.logger.info(
                f"Invalidating cache due to stale metadata for {plugin_name}"
            )
            self.refresh_plugins()
            return True

        return False

    # Plugin Factory Methods (Direct Integration)
    def create_service_manager(
        self,
        protocol: ProtocolConfig,
        implementation: ImplementationConfig,
        implementation_dir: Path,
        service_config_to_test: "ServiceConfig",
        event_manager: Optional[EventManager] = None,
        emitter_registry=None,
        global_config=None,
        experiment_context=None,
    ) -> IServiceManager:
        """Create a service manager instance with cache validation."""
        # Validate cache before creating service manager
        implementation_name = implementation.name

        # Extract version, build_mode, and runtime_mode from configuration for accurate image name validation
        version = protocol.version if protocol else None
        build_mode = None
        runtime_mode = "minimal"  # Default runtime mode

        # Extract build_mode from service config if available (for panther_ivy)
        if (
            hasattr(service_config_to_test, "plugin_config")
            and isinstance(service_config_to_test.plugin_config, dict)
            and "build_mode" in service_config_to_test.plugin_config
        ):
            build_mode = service_config_to_test.plugin_config.get("build_mode")
        elif hasattr(service_config_to_test, "implementation") and hasattr(
            service_config_to_test.implementation, "build_mode"
        ):
            build_mode = getattr(
                service_config_to_test.implementation, "build_mode", None
            )

        # Extract runtime_mode from service config if available
        if (
            hasattr(service_config_to_test, "plugin_config")
            and isinstance(service_config_to_test.plugin_config, dict)
            and "runtime_mode" in service_config_to_test.plugin_config
        ):
            runtime_mode = service_config_to_test.plugin_config.get(
                "runtime_mode", "minimal"
            )
        elif hasattr(service_config_to_test, "implementation") and hasattr(
            service_config_to_test.implementation, "runtime_mode"
        ):
            runtime_mode = getattr(
                service_config_to_test.implementation, "runtime_mode", "minimal"
            )

        cache_invalidated = self._invalidate_stale_cache_for_plugin(
            implementation_name,
            version=version,
            build_mode=build_mode,
            runtime_mode=runtime_mode,
        )

        if cache_invalidated:
            self.logger.info(
                f"Cache was invalidated for {implementation_name}, using fresh metadata"
            )

        # Use passed global_config or fall back to self.global_config
        config_to_use = (
            global_config if global_config is not None else self.global_config
        )

        # Update experiment_context for runtime_mode detection in downstream code
        if experiment_context and not self.experiment_context:
            self.set_experiment_context(experiment_context)

        return self.plugin_factory.create_service_manager(
            protocol=protocol,
            implementation=implementation,
            implementation_dir=implementation_dir,
            service_config_to_test=service_config_to_test,
            event_manager=event_manager or self.event_manager,
            emitter_registry=emitter_registry,
            global_config=config_to_use,
            experiment_context=experiment_context,
            test_case=experiment_context,
        )

    def create_environment_manager(
        self,
        environment: str,
        test_config: "TestConfig",
        environment_dir: Path,
        output_dir: Path,
        event_manager: EventManager,
    ) -> IEnvironmentPlugin:
        """Create an environment manager instance with cache validation."""
        # Validate cache before creating environment manager
        # Environment managers typically use default version/build_mode/runtime_mode
        cache_invalidated = self._invalidate_stale_cache_for_plugin(
            environment, version=None, build_mode=None, runtime_mode="minimal"
        )

        if cache_invalidated:
            self.logger.info(
                f"Cache was invalidated for environment {environment}, using fresh metadata"
            )

        return self.plugin_factory.create_environment_manager(
            environment=environment,
            test_config=test_config,
            environment_dir=environment_dir,
            output_dir=output_dir,
            event_manager=event_manager,
            target_platform=self.docker_builder.get_target_platform(),
        )

    def create_observer_plugin(self, plugin_name: str, *args, **kwargs):
        """Create an observer plugin instance."""
        return self.plugin_factory.create_observer_plugin(plugin_name, *args, **kwargs)

    def get_statistics(self) -> Dict[str, Any]:
        """Get plugin manager statistics.

        Returns:
            Dictionary containing statistics
        """
        plugins = self.discover_plugins()

        return {
            "total_plugins": len(plugins),
            "plugins_by_type": {
                ptype.value: len(self.get_plugins_by_type(ptype))
                for ptype in PluginType
            },
            "discovery_count": self._discovery_count,
            "last_discovery_time": self._last_discovery_time,
            "cache_enabled": self.enable_cache,
            "cache_valid": self._is_cache_valid(),
            "directories_scanned": len(self.plugin_directories),
            "event_system_enabled": self.plugin_event_emitter is not None,
            "docker_builder_available": self.docker_builder is not None,
        }

    @classmethod
    def reset_singleton(cls):
        """Reset the singleton instance.

        This method should only be used in testing scenarios where
        a fresh instance is needed.
        """
        cls._instance = None
        cls._initialized = False

    @classmethod
    def get_instance(cls, *args, **kwargs) -> "PluginManager":
        """Get the singleton instance of PluginManager.

        This method returns the singleton instance and allows updating
        configuration parameters even if the instance already exists.

        Args:
            *args: Positional arguments to pass to __init__.
            **kwargs: Keyword arguments to pass to __init__.

        Returns:
            The singleton PluginManager instance (with updated parameters if provided)
        """
        return cls(*args, **kwargs)
