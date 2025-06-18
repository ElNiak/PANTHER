"""
Unified Plugin Manager for Panther Framework

This is the single source of truth for all plugin management operations,
combining discovery, catalog management, Docker integration, event handling,
and plugin lifecycle management in one cohesive class.
"""

import inspect
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Tuple, Union

if TYPE_CHECKING:
    from panther.config import ServiceConfig, TestConfig

from panther.config import GlobalConfig
from panther.core.docker_builder import DockerBuilder
from panther.core.exceptions.fast_fail import FastFailHandler
from panther.core.observer.impl.plugin_observer import PluginObserver
from panther.core.observer.management.event_manager import EventManager
from panther.core.utils.logging_mixin import LoggerMixin
from panther.plugins.environments.environment_interface import IEnvironmentPlugin
from panther.plugins.environments.execution_environment.execution_environment_interface import (
    IExecutionEnvironment,
)
from panther.plugins.environments.network_environment.network_environment_interface import (
    INetworkEnvironment,
)
from panther.plugins.plugin_catalog import PluginCatalog
from panther.plugins.plugin_manifest import PluginRegistration, PluginManifest, PluginType as ManifestPluginType
from panther.plugins.services.services_interface import IServiceManager
from panther.config.core.models import ProtocolConfig
from panther.config.core.models.service import ImplementationConfig

# Import unified core components
from panther.plugins.core.plugin_metadata import (
    PluginMetadata, PluginMetadataLoader, PluginType, PluginStatus
)
from panther.plugins.core.plugin_factory import PluginFactory
from panther.plugins.plugin_decorators import (
    get_decorated_plugins, 
    get_version_configs,
    get_protocol_plugins,
    get_protocol_by_name
)


class PluginManager(LoggerMixin):
    """
    Unified plugin manager consolidating all plugin management functionality.
    
    This class serves as the single source of truth for:
    - Plugin discovery and catalog management
    - Plugin metadata and manifest handling  
    - Plugin instantiation and lifecycle management
    - Version and schema discovery
    - Dependency resolution and validation
    - Docker integration and image building
    - Event system integration
    - Fast-fail error handling
    """
    
    def __init__(
        self,
        plugin_directories: Optional[List[str]] = None,
        event_manager: Optional[EventManager] = None,
        global_config: Optional[GlobalConfig] = None,
        fast_fail_handler: Optional[FastFailHandler] = None,
        enable_cache: bool = True,
        cache_ttl: int = 3600  # 1 hour
    ):
        """
        Initialize the unified plugin manager.
        
        Args:
            plugin_directories: Directories to scan for plugins
            event_manager: Event manager for plugin events
            global_config: Global configuration for Docker and other settings
            fast_fail_handler: Fast fail handler for critical error management
            enable_cache: Enable plugin metadata caching
            cache_ttl: Cache time-to-live in seconds
        """
        super().__init__()
        
        # Configuration
        self.plugin_directories = plugin_directories or self._get_default_directories()
        self.event_manager = event_manager
        self.global_config = global_config
        self.fast_fail_handler = fast_fail_handler
        self.enable_cache = enable_cache
        self.cache_ttl = cache_ttl
        
        # Core components
        self.plugin_catalog = PluginCatalog(self.plugin_directories)
        self.plugin_factory = PluginFactory(
            plugin_manager=self,
            event_manager=event_manager,
            fast_fail_handler=fast_fail_handler
        )
        
        # Plugin registry and metadata cache
        self.plugins: Dict[str, PluginMetadata] = {}
        self.registrations: Dict[str, PluginRegistration] = {}
        
        # Caches with TTL
        self._cache_timestamp = 0
        self._discovery_cache: Optional[Dict[str, PluginMetadata]] = None
        self._version_cache: Dict[str, List[str]] = {}
        self._schema_cache: Dict[str, Dict[str, Any]] = {}
        self._dependency_graph: Dict[str, Set[str]] = {}
        
        # Statistics
        self._discovery_count = 0
        self._last_discovery_time = 0
        
        # Event system setup
        self.plugin_observer = None
        self.plugin_event_emitter = None
        if self.event_manager:
            self._setup_event_system()
        
        # Docker management
        try:
            self.docker_builder = DockerBuilder(
                build_log_file=(
                    global_config.docker.log_docker_image_build
                    if global_config
                    else None
                )
            )
        except Exception as e:
            self.logger.warning("Failed to initialize DockerBuilder: %s", e)
            self.docker_builder = None
        
        # Built images tracking
        self.built_images = {}
        
        # Auto-discover on initialization
        self.logger.info("Initializing unified plugin manager")
        self.discover_plugins()
    
    def _get_default_directories(self) -> List[str]:
        """Get default plugin directories."""
        base_path = Path(__file__).parent
        return [
            str(base_path / "services" / "iut"),
            str(base_path / "services" / "testers"),
            str(base_path / "environments" / "network_environment"),
            str(base_path / "environments" / "execution_environment"),
        ]
    
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
        """Check if cache is still valid."""
        if not self.enable_cache or not self._discovery_cache:
            return False
        return time.time() - self._cache_timestamp < self.cache_ttl
    
    def discover_plugins(self, force_refresh: bool = False) -> Dict[str, PluginMetadata]:
        """
        Discover all available plugins.
        
        Args:
            force_refresh: Force cache refresh
            
        Returns:
            Dictionary mapping plugin names to metadata
        """
        # Use cache if valid
        if not force_refresh and self._is_cache_valid():
            self.logger.debug("Using cached plugin discovery results")
            return self._discovery_cache.copy()
        
        start_time = time.time()
        self.logger.info("Discovering plugins from %d directories", len(self.plugin_directories))
        
        discovered_plugins = {}
        
        # First, scan directories and import plugin modules to trigger decorators
        self._scan_and_import_plugin_modules()
        
        # Load plugins from decorator registry (ONLY SOURCE)
        decorator_plugins = self._load_from_decorator_registry()
        discovered_plugins.update(decorator_plugins)
        self.logger.info(f"Discovered {len(decorator_plugins)} plugins from decorator registry")
        
        # Update cache
        self._discovery_cache = discovered_plugins
        self._cache_timestamp = time.time()
        self.plugins.update(discovered_plugins)
        
        # Update plugin catalog with discovered plugins
        for plugin_name, metadata in discovered_plugins.items():
            # Create plugin ID in the format expected by validation
            plugin_type_str = metadata.type
            if hasattr(plugin_type_str, 'value'):
                plugin_type_str = plugin_type_str.value
            plugin_id = f"{plugin_type_str}:{plugin_name}"
            
            # Convert string type to PluginType enum for manifest
            plugin_type_enum = None
            for ptype in ManifestPluginType:
                if ptype.value == plugin_type_str:
                    plugin_type_enum = ptype
                    break
            
            if plugin_type_enum:
                # Convert metadata to manifest for catalog compatibility
                manifest = PluginManifest(
                    name=metadata.name,
                    type=plugin_type_enum,
                    version=metadata.version,
                    description=metadata.description,
                    author=metadata.author,
                    entry_point=getattr(metadata, 'entry_point', ''),
                    supported_protocols=getattr(metadata, 'supported_protocols', []),
                    dependencies=[],
                    file_path=str(metadata.path) if metadata.path else ''
                )
                self.plugin_catalog.catalog[plugin_id] = manifest
                
                self.logger.debug(f"Added to catalog: {plugin_id}")
            else:
                self.logger.warning(f"Could not map plugin type '{plugin_type_str}' to enum for {plugin_name}")
        
        # Update statistics
        self._discovery_count += 1
        self._last_discovery_time = time.time() - start_time
        
        self.logger.info(
            "Discovered %d plugins in %.2fs",
            len(discovered_plugins),
            self._last_discovery_time
        )
        
        return discovered_plugins.copy()
    
    def _convert_manifest_to_metadata(self, manifest) -> Optional[PluginMetadata]:
        """Convert legacy manifest to unified metadata."""
        try:
            # Extract basic information
            data = {
                'name': getattr(manifest, 'name', ''),
                'type': getattr(manifest, 'plugin_type', getattr(manifest, 'type', 'service')),
                'path': getattr(manifest, 'file_path', ''),
                'version': getattr(manifest, 'version', '1.0.0'),
                'description': getattr(manifest, 'description', ''),
                'author': getattr(manifest, 'author', ''),
                'supported_protocols': getattr(manifest, 'supported_protocols', []),
                'dependencies': getattr(manifest, 'dependencies', []),
                'capabilities': getattr(manifest, 'capabilities', []),
            }
            
            return PluginMetadata.from_dict(data)
        except Exception as e:
            self.logger.debug(f"Failed to convert manifest: {e}")
            return None
    
    def _scan_directory_enhanced(self, directory: Path) -> List[PluginMetadata]:
        """Enhanced directory scanning with metadata extraction."""
        plugins = []
        
        if not directory.exists():
            return plugins
        
        # Scan services
        services_dir = directory / "services"
        if services_dir.exists():
            plugins.extend(self._scan_service_plugins(services_dir))
        
        # Scan environments
        environments_dir = directory / "environments"
        if environments_dir.exists():
            plugins.extend(self._scan_environment_plugins(environments_dir))
        
        # Scan protocols
        protocols_dir = directory / "protocols"
        if protocols_dir.exists():
            plugins.extend(self._scan_protocol_plugins(protocols_dir))
        
        return plugins
    
    def _scan_service_plugins(self, services_dir: Path) -> List[PluginMetadata]:
        """Scan service plugins (IUT and testers)."""
        plugins = []
        
        for service_type in ["iut", "testers"]:
            type_dir = services_dir / service_type
            if not type_dir.exists():
                continue
            
            # Handle protocol subdirectories
            for protocol_dir in type_dir.iterdir():
                if not protocol_dir.is_dir() or protocol_dir.name.startswith('_'):
                    continue
                
                protocol_name = protocol_dir.name
                
                # Find implementations
                for impl_dir in protocol_dir.iterdir():
                    if not impl_dir.is_dir() or impl_dir.name.startswith('_'):
                        continue
                    
                    metadata = PluginMetadataLoader.load_from_directory(
                        impl_dir, service_type, protocol_name
                    )
                    if metadata:
                        metadata.status = PluginStatus.DISCOVERED
                        plugins.append(metadata)
        
        return plugins
    
    def _scan_environment_plugins(self, environments_dir: Path) -> List[PluginMetadata]:
        """Scan environment plugins."""
        plugins = []
        
        for env_type in ["network_environment", "execution_environment"]:
            type_dir = environments_dir / env_type
            if not type_dir.exists():
                continue
            
            # Find environment implementations
            for impl_dir in type_dir.iterdir():
                if not impl_dir.is_dir() or impl_dir.name.startswith('_'):
                    continue
                
                metadata = PluginMetadataLoader.load_from_directory(impl_dir, env_type)
                if metadata:
                    metadata.status = PluginStatus.DISCOVERED
                    plugins.append(metadata)
        
        return plugins
    
    def _scan_protocol_plugins(self, protocols_dir: Path) -> List[PluginMetadata]:
        """Scan protocol plugins."""
        plugins = []
        
        for category in ["client_server", "peer_to_peer"]:
            category_dir = protocols_dir / category
            if not category_dir.exists():
                continue
            
            for proto_dir in category_dir.iterdir():
                if not proto_dir.is_dir() or proto_dir.name.startswith('_'):
                    continue
                
                metadata = PluginMetadataLoader.load_from_directory(
                    proto_dir, "protocol"
                )
                if metadata:
                    metadata.category = category
                    metadata.status = PluginStatus.DISCOVERED
                    plugins.append(metadata)
        
        return plugins
    
    def _merge_metadata(self, existing: PluginMetadata, new: PluginMetadata) -> PluginMetadata:
        """Merge two metadata objects, preferring more complete information."""
        # Create a copy of existing
        merged_data = existing.to_dict()
        new_data = new.to_dict()
        
        # Merge fields, preferring non-empty values
        for key, value in new_data.items():
            if value and (not merged_data.get(key) or 
                         (isinstance(value, list) and len(value) > len(merged_data.get(key, [])))):
                merged_data[key] = value
        
        return PluginMetadata.from_dict(merged_data)
    
    def _load_from_decorator_registry(self) -> Dict[str, PluginMetadata]:
        """
        Load plugins from the decorator registry.
        
        This method converts decorated plugin manifests to PluginMetadata objects.
        As plugin.yml files are phased out, this will become the primary plugin source.
        
        Returns:
            Dictionary mapping plugin names to PluginMetadata objects
        """
        plugins = {}
        
        # First, load protocol plugins
        try:
            protocol_plugins = get_protocol_plugins()
            for protocol_id, (cls, protocol_metadata) in protocol_plugins.items():
                self.logger.debug(
                    f"Loaded protocol plugin: {protocol_metadata['name']} with versions: {protocol_metadata.get('versions', [])}"
                )
        except Exception as e:
            self.logger.warning(f"Failed to load protocol plugins: {e}")
        
        try:
            decorated_plugins = get_decorated_plugins()
            
            for plugin_id, (cls, manifest) in decorated_plugins.items():
                try:
                    # Convert PluginManifest to PluginMetadata
                    metadata_data = {
                        'name': manifest.name,
                        'type': manifest.type.value if hasattr(manifest.type, 'value') else str(manifest.type),
                        'version': manifest.version,
                        'description': manifest.description,
                        'author': manifest.author,
                        'license': getattr(manifest, 'license', ''),
                        'homepage': getattr(manifest, 'homepage', ''),
                        'path': getattr(manifest, 'file_path', '') or '',  # Use file_path from decorator
                        'entry_point': manifest.entry_point,
                        'supported_protocols': getattr(manifest, 'supported_protocols', []),
                        'capabilities': getattr(manifest, 'capabilities', []),
                        'dependencies': [
                            {'name': dep.name, 'version_spec': dep.version_spec or '*'}
                            for dep in (manifest.dependencies or [])
                        ],
                        'config_schema': getattr(manifest, 'config_schema', {}),
                        'default_config': getattr(manifest, 'default_config', {}),
                        'tags': getattr(manifest, 'tags', []),
                        'external_dependencies': getattr(manifest, 'external_dependencies', []),
                        'status': PluginStatus.ACTIVE,
                        'min_panther_version': manifest.min_panther_version,
                        'max_panther_version': getattr(manifest, 'max_panther_version', None),
                    }
                    
                    # Try to auto-discover dockerfile_path from plugin directory
                    # First try to get directory from file_path if available
                    plugin_dir = None
                    if hasattr(manifest, 'file_path') and manifest.file_path:
                        plugin_file = Path(manifest.file_path)
                        if plugin_file.exists():
                            plugin_dir = plugin_file.parent
                    
                    # If that doesn't work, try the _find_plugin_path method
                    if not plugin_dir:
                        plugin_dir = self._find_plugin_path(manifest.name, manifest.type)
                    
                    if plugin_dir and plugin_dir.exists():
                        dockerfile_path = plugin_dir / "Dockerfile"
                        if dockerfile_path.exists():
                            metadata_data['dockerfile_path'] = str(dockerfile_path)
                            self.logger.debug(f"Found Dockerfile for {manifest.name}: {dockerfile_path}")
                        else:
                            self.logger.debug(f"No Dockerfile found at {dockerfile_path} for {manifest.name}")
                    else:
                        self.logger.debug(f"Plugin directory not found for {manifest.name} (type: {manifest.type})")
                    
                    metadata = PluginMetadata.from_dict(metadata_data)
                    
                    # Check for auto-discovery of versions based on protocol
                    if hasattr(manifest, 'supported_protocols') and manifest.supported_protocols:
                        # Get the primary protocol (first one)
                        primary_protocol = manifest.supported_protocols[0]
                        
                        # Try to auto-discover versions if not already loaded
                        version_configs = get_version_configs(manifest.name)
                        if not version_configs:
                            # Attempt to find plugin path and load versions
                            plugin_path = self._find_plugin_path(manifest.name, manifest.type)
                            if plugin_path:
                                from panther.plugins.version_loader import discover_plugin_versions
                                discovered_versions = discover_plugin_versions(
                                    manifest.name,
                                    plugin_path,
                                    primary_protocol
                                )
                                if discovered_versions:
                                    version_configs = discovered_versions
                                    self.logger.info(
                                        f"Auto-discovered {len(discovered_versions)} versions for {manifest.name} "
                                        f"based on protocol {primary_protocol}"
                                    )
                    else:
                        # Use manually registered version configs
                        version_configs = get_version_configs(manifest.name)
                    
                    if version_configs:
                        metadata.available_versions = list(version_configs.keys())
                        # Store version configs in metadata for later use
                        if not hasattr(metadata, 'version_configs'):
                            metadata.version_configs = version_configs
                        self.logger.debug(f"Loaded {len(version_configs)} version configs for {manifest.name}")
                    
                    plugins[metadata.name] = metadata
                    
                    self.logger.debug(f"Loaded decorated plugin: {metadata.name} v{metadata.version}")
                    
                except Exception as e:
                    self.logger.warning(f"Failed to convert decorated plugin {plugin_id}: {e}")
                    
        except Exception as e:
            self.logger.error(f"Failed to load decorator registry: {e}")
            
        return plugins
    
    def _scan_and_import_plugin_modules(self):
        """
        Scan plugin directories and import Python modules to trigger decorator registration.
        
        This method walks through the plugin directories and imports plugin Python files,
        which causes the @register_plugin decorators to execute and register the plugins.
        """
        # Import key plugins early to ensure they're registered
        self._import_core_plugins()
        
        self.logger.debug(f"Scanning plugin directories: {self.plugin_directories}")
        for directory in self.plugin_directories:
            directory_path = Path(directory)
            if not directory_path.exists():
                self.logger.debug(f"Directory does not exist: {directory_path}")
                continue
            self.logger.debug(f"Scanning directory: {directory_path}")
            
            # Check if this is already a specific plugin type directory
            dir_name = directory_path.name
            
            if dir_name == "protocols":
                # This is the protocols directory itself
                self._import_modules_in_directory(directory_path, recursive=True)
            elif dir_name == "services":
                # This is the services directory itself
                self.logger.debug(f"Processing services directory: {directory_path}")
                # Import IUT plugins
                iut_dir = directory_path / "iut"
                if iut_dir.exists():
                    self.logger.debug(f"Importing IUT plugins from: {iut_dir}")
                    self._import_modules_in_directory(iut_dir, recursive=True)
                
                # Import tester plugins
                testers_dir = directory_path / "testers"
                if testers_dir.exists():
                    self.logger.debug(f"Importing tester plugins from: {testers_dir}")
                    self._import_modules_in_directory(testers_dir, recursive=True)
                else:
                    self.logger.warning(f"Testers directory not found: {testers_dir}")
            elif dir_name == "environments":
                # This is the environments directory itself
                self._import_modules_in_directory(directory_path, recursive=True)
            else:
                # This is a base plugins directory, scan for subdirectories
                # Import protocol plugins
                protocols_dir = directory_path / "protocols"
                if protocols_dir.exists():
                    self._import_modules_in_directory(protocols_dir, recursive=True)
                
                # Import service plugins
                services_dir = directory_path / "services"
                if services_dir.exists():
                    # Import IUT plugins
                    iut_dir = services_dir / "iut"
                    if iut_dir.exists():
                        self._import_modules_in_directory(iut_dir, recursive=True)
                    
                    # Import tester plugins
                    testers_dir = services_dir / "testers"
                    if testers_dir.exists():
                        self._import_modules_in_directory(testers_dir, recursive=True)
                
                # Import environment plugins
                environments_dir = directory_path / "environments"
                if environments_dir.exists():
                    self._import_modules_in_directory(environments_dir, recursive=True)
    
    def _import_modules_in_directory(self, directory: Path, recursive: bool = True):
        """
        Import Python modules in a directory.
        
        Args:
            directory: Directory to scan
            recursive: Whether to scan subdirectories
        """
        self.logger.debug(f"Importing modules from directory: {directory} (recursive={recursive})")
        try:
            if recursive:
                # Walk through all subdirectories
                for py_file in directory.rglob("*.py"):
                    if py_file.name.startswith("_") or py_file.name == "setup.py":
                        continue
                    
                    # Skip test files
                    if "test" in py_file.parts or py_file.name.startswith("test_"):
                        continue
                    
                    # Skip __pycache__ directories
                    if "__pycache__" in py_file.parts:
                        continue
                    
                    # Skip Ivy internal files
                    if "panther_ivy" in py_file.parts and any(skip in str(py_file) for skip in ["ivy/", "submodules/", "protocol-testing/"]):
                        continue
                    
                    # Only import the main plugin file for each plugin
                    # Main plugin files are typically named after their parent directory
                    parent_name = py_file.parent.name
                    if py_file.stem == parent_name or py_file.name.endswith("_protocol.py"):
                        # This is likely a main plugin file
                        self.logger.info(f"Found main plugin file: {py_file} (matches parent: {parent_name})")
                    else:
                        # Skip non-main files unless they're special cases
                        self.logger.debug(f"Skipping non-main file: {py_file} (parent: {parent_name})")
                        continue
                    
                    self._import_module_file(py_file)
            else:
                # Only scan immediate directory
                for py_file in directory.glob("*.py"):
                    if py_file.name.startswith("_") or py_file.name == "setup.py":
                        continue
                    
                    if py_file.name.startswith("test_"):
                        continue
                        
                    self._import_module_file(py_file)
                    
        except Exception as e:
            self.logger.debug(f"Error scanning directory {directory}: {e}")
    
    def _import_module_file(self, file_path: Path):
        """
        Import a single Python module file.
        
        Args:
            file_path: Path to the Python file
        """
        try:
            # Generate a unique module name based on the file path
            module_name = str(file_path).replace("/", ".").replace("\\", ".").replace(".py", "")
            
            # Use the plugin loader utils to import the module
            from panther.plugins.plugin_loader_utils import PluginManagerUtils
            
            PluginManagerUtils.load_module_from_file(file_path, module_name)
            self.logger.info(f"Imported plugin module: {file_path}")
            
        except Exception as e:
            # Don't fail on import errors - some files may not be plugins
            self.logger.warning(f"Could not import {file_path}: {e}")
            import traceback
            self.logger.debug(f"Traceback: {traceback.format_exc()}")
    
    def _import_core_plugins(self):
        """Import core plugins that are commonly used."""
        try:
            # Import protocol plugins
            from panther.plugins.protocols.client_server.quic.quic_protocol import QUICProtocol
            self.logger.debug("Imported QUIC protocol plugin")
        except Exception as e:
            self.logger.debug(f"Could not import QUIC protocol: {e}")
        
        try:
            # Import critical service plugins
            from panther.plugins.services.iut.quic.picoquic.picoquic import PicoquicServiceManager
            self.logger.debug("Imported PicoQUIC plugin")
        except Exception as e:
            self.logger.debug(f"Could not import PicoQUIC: {e}")
            
        try:
            from panther.plugins.services.testers.panther_ivy.panther_ivy import PantherIvyServiceManager
            self.logger.debug("Imported panther_ivy plugin")
        except Exception as e:
            self.logger.debug(f"Could not import panther_ivy: {e}")
            
        try:
            # Import critical environment plugins
            from panther.plugins.environments.network_environment.docker_compose.docker_compose import DockerComposeEnvironment
            self.logger.debug("Imported docker_compose plugin")
        except Exception as e:
            self.logger.debug(f"Could not import docker_compose: {e}")
    
    def _find_plugin_path(self, plugin_name: str, plugin_type) -> Optional[Path]:
        """
        Find the directory path for a plugin.
        
        Args:
            plugin_name: Name of the plugin
            plugin_type: Type of the plugin
            
        Returns:
            Path to plugin directory or None if not found
        """
        # Convert plugin type to directory structure
        if hasattr(plugin_type, 'value'):
            type_str = plugin_type.value
        else:
            type_str = str(plugin_type)
            
        # Map plugin types to directory patterns
        type_patterns = {
            'iut': ['services/iut/*/{plugin_name}'],
            'tester': ['services/testers/{plugin_name}'],
            'testers': ['services/testers/{plugin_name}'],
            'network_environment': ['environments/network_environment/{plugin_name}'],
            'execution_environment': ['environments/execution_environment/{plugin_name}'],
            'environment': ['environments/*/{plugin_name}'],
        }
        
        patterns = type_patterns.get(type_str, [])
        
        for base_dir in self.plugin_directories:
            base_path = Path(base_dir)
            for pattern in patterns:
                # Handle wildcard in pattern
                if '*' in pattern:
                    # Split pattern and search
                    parts = pattern.split('*')
                    if len(parts) == 2:
                        prefix = parts[0]
                        suffix = parts[1].format(plugin_name=plugin_name)
                        
                        search_dir = base_path / prefix.rstrip('/')
                        if search_dir.exists():
                            for subdir in search_dir.iterdir():
                                if subdir.is_dir():
                                    full_path = subdir / suffix.lstrip('/')
                                    if full_path.exists():
                                        self.logger.debug(f"Found plugin path for {plugin_name}: {full_path}")
                                        return full_path
                else:
                    # Direct path
                    full_path = base_path / pattern.format(plugin_name=plugin_name)
                    if full_path.exists():
                        self.logger.debug(f"Found plugin path for {plugin_name}: {full_path}")
                        return full_path
                        
        self.logger.debug(f"Could not find plugin path for {plugin_name} (type: {type_str})")
        return None
    
    def get_plugin(self, name: str) -> Optional[PluginMetadata]:
        """
        Get plugin metadata by name.
        
        Args:
            name: Plugin name
            
        Returns:
            Plugin metadata or None if not found
        """
        # Check cache first
        plugins = self.discover_plugins()
        return plugins.get(name)
    
    def validate_experiment_plugins(self, experiment_config) -> Tuple[bool, List[str]]:
        """
        Validate that all plugins required by an experiment are available.
        
        Args:
            experiment_config: Experiment configuration
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        required_plugins = set()
        
        # Ensure plugins are discovered
        if not self.plugins:
            self.discover_plugins()
        
        # Extract required plugins from experiment config
        for test in experiment_config.tests:
            # Check network environment
            if hasattr(test, "network_environment") and test.network_environment:
                env_type = test.network_environment.type
                if env_type:
                    required_plugins.add((env_type, "network environment"))
            
            # Check execution environments
            if hasattr(test, "execution_environment") and test.execution_environment:
                for exec_env in test.execution_environment:
                    if hasattr(exec_env, "type") and exec_env.type:
                        required_plugins.add((exec_env.type, "execution environment"))
            
            # Check services
            if hasattr(test, "services") and test.services:
                for _, service_config in test.services.items():
                    if hasattr(service_config, "implementation"):
                        impl = service_config.implementation
                        impl_name = impl.name
                        impl_type = impl.type if hasattr(impl, "type") else "iut"
                        
                        # Handle string or enum type
                        impl_type_str = (
                            impl_type if isinstance(impl_type, str) else impl_type.value
                        )
                        if impl_type_str.lower() == "testers":
                            required_plugins.add((impl_name, "tester"))
                        else:
                            required_plugins.add((impl_name, "IUT implementation"))
        
        # Validate each required plugin
        for plugin_name, plugin_desc in required_plugins:
            if plugin_name not in self.plugins:
                errors.append(
                    f"Required {plugin_desc} plugin '{plugin_name}' not found"
                )
        
        return len(errors) == 0, errors
    
    @property
    def plugin_discovery(self):
        """Compatibility property for legacy code expecting plugin_discovery attribute."""
        return self
    
    def get_plugins_by_type(self, plugin_type: Union[str, PluginType]) -> List[PluginMetadata]:
        """
        Get all plugins of a specific type.
        
        Args:
            plugin_type: Plugin type to filter by
            
        Returns:
            List of matching plugins
        """
        if isinstance(plugin_type, str):
            try:
                plugin_type = PluginType(plugin_type)
            except ValueError:
                # Handle legacy type mappings
                type_mapping = {
                    "testers": PluginType.TESTER,
                    "iut": PluginType.IUT,
                    "network_environment": PluginType.NETWORK_ENVIRONMENT,
                    "execution_environment": PluginType.EXECUTION_ENVIRONMENT,
                }
                plugin_type = type_mapping.get(plugin_type, PluginType.SERVICE)
        
        plugins = self.discover_plugins()
        return [plugin for plugin in plugins.values() if plugin.type == plugin_type]
    
    def get_plugins_by_protocol(self, protocol: str) -> List[PluginMetadata]:
        """
        Get all plugins supporting a specific protocol.
        
        Args:
            protocol: Protocol name
            
        Returns:
            List of supporting plugins
        """
        plugins = self.discover_plugins()
        return [
            plugin for plugin in plugins.values()
            if plugin.is_compatible_with(protocol=protocol)
        ]
    
    def validate_plugin_dependencies(self, plugin_name: str) -> Tuple[bool, List[str]]:
        """
        Validate plugin dependencies.
        
        Args:
            plugin_name: Name of plugin to validate
            
        Returns:
            Tuple of (all_satisfied, missing_dependencies)
        """
        plugin = self.get_plugin(plugin_name)
        if not plugin:
            return False, [f"Plugin '{plugin_name}' not found"]
        
        available_plugins = self.discover_plugins()
        missing = plugin.validate_dependencies(available_plugins)
        
        return len(missing) == 0, missing
    
    def discover_protocol_versions(self, protocol: Optional[str] = None) -> Dict[str, List[str]]:
        """
        Discover available protocol versions.
        
        Args:
            protocol: Optional protocol to filter by
            
        Returns:
            Dictionary mapping protocols to version lists
        """
        cache_key = protocol or "all"
        
        if cache_key in self._version_cache and self._is_cache_valid():
            return (
                {protocol: self._version_cache[cache_key]}
                if protocol
                else self._version_cache.copy()
            )
        
        self.logger.info(f"Discovering versions for protocol: {protocol or 'all'}")
        
        versions = {}
        
        # Scan protocol directories and service implementations
        for directory in self.plugin_directories:
            directory_path = Path(directory)
            
            # Check protocols directory
            protocols_dir = directory_path / "protocols"
            if protocols_dir.exists():
                for category in ["client_server", "peer_to_peer"]:
                    category_dir = protocols_dir / category
                    if category_dir.exists():
                        for proto_dir in category_dir.iterdir():
                            if not proto_dir.is_dir():
                                continue
                            
                            proto_name = proto_dir.name
                            if protocol and proto_name != protocol:
                                continue
                            
                            proto_versions = self._discover_versions_in_directory(proto_dir)
                            if proto_versions:
                                versions[proto_name] = proto_versions
            
            # Check service implementations
            services_dir = directory_path / "services"
            if services_dir.exists():
                for impl_type in ["iut", "testers"]:
                    type_dir = services_dir / impl_type
                    if type_dir.exists():
                        for proto_dir in type_dir.iterdir():
                            if not proto_dir.is_dir():
                                continue
                            
                            proto_name = proto_dir.name
                            if protocol and proto_name != protocol:
                                continue
                            
                            # Check each implementation
                            for impl_dir in proto_dir.iterdir():
                                if impl_dir.is_dir():
                                    impl_versions = self._discover_versions_in_directory(impl_dir)
                                    if impl_versions:
                                        if proto_name not in versions:
                                            versions[proto_name] = []
                                        versions[proto_name].extend(impl_versions)
        
        # Deduplicate and sort
        for proto in versions:
            versions[proto] = sorted(list(set(versions[proto])))
            self._version_cache[proto] = versions[proto]
        
        if not protocol:
            self._version_cache["all"] = versions
        
        return versions
    
    def _discover_versions_in_directory(self, directory: Path) -> List[str]:
        """Discover version files in a directory."""
        versions = []
        
        # Look for versions directory
        versions_dir = directory / "versions"
        if versions_dir.exists():
            for item in versions_dir.iterdir():
                if item.is_file() and item.suffix in ['.yaml', '.yml', '.json']:
                    versions.append(item.stem)
                elif item.is_dir():
                    versions.append(item.name)
        
        # Look for version files in config directory
        config_dir = directory / "config"
        if config_dir.exists():
            for item in config_dir.glob("version_*.y*ml"):
                version = item.stem.replace("version_", "")
                versions.append(version)
        
        # Check for hardcoded versions in config_schema.py
        config_schema = directory / "config_schema.py"
        if config_schema.exists() and "quic" in str(directory):
            # Add common QUIC versions if not found
            default_versions = ["rfc9000", "draft-29"]
            for v in default_versions:
                if v not in versions:
                    versions.append(v)
        
        return versions
    
    def discover_plugin_schemas(self) -> Dict[str, Dict[str, Any]]:
        """
        Discover all plugin configuration schemas.
        
        Returns:
            Dictionary mapping plugin names to schema information
        """
        if self._schema_cache and self._is_cache_valid():
            return self._schema_cache.copy()
        
        self.logger.info("Discovering plugin schemas")
        
        schemas = {}
        plugins = self.discover_plugins()
        
        for plugin_name, plugin in plugins.items():
            if plugin.config_schema_path and plugin.config_schema_path.exists():
                try:
                    schema_info = self._load_schema(plugin.config_schema_path)
                    if schema_info:
                        schemas[plugin_name] = {
                            'schema': schema_info,
                            'path': str(plugin.config_schema_path),
                            'type': plugin.type.value,
                            'protocol': plugin.protocol
                        }
                except Exception as e:
                    self.logger.warning(f"Failed to load schema for {plugin_name}: {e}")
        
        self._schema_cache = schemas
        return schemas.copy()
    
    def _load_schema(self, schema_path: Path) -> Optional[Dict[str, Any]]:
        """Load schema from file."""
        try:
            with open(schema_path) as f:
                if schema_path.suffix.lower() in ['.yaml', '.yml']:
                    import yaml
                    return yaml.safe_load(f)
                elif schema_path.suffix.lower() == '.json':
                    import json
                    return json.load(f)
                elif schema_path.suffix.lower() == '.py':
                    # For Python schema files - simplified extraction
                    return {'type': 'python_schema', 'path': str(schema_path)}
        except Exception:
            pass
        return None
    
    def get_plugin_schema(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """
        Get schema for a specific plugin.
        
        Args:
            plugin_name: Plugin name
            
        Returns:
            Schema information or None
        """
        schemas = self.discover_plugin_schemas()
        return schemas.get(plugin_name)
    
    def refresh_plugins(self):
        """Force refresh of all plugin information."""
        self.logger.info("Force refreshing plugin cache")
        self._discovery_cache = None
        self._cache_timestamp = 0
        self._version_cache.clear()
        self._schema_cache.clear()
        self.plugin_catalog.refresh()
        self.discover_plugins(force_refresh=True)
    
    # Plugin Factory Methods (Direct Integration)
    def create_service_manager(
        self,
        protocol: ProtocolConfig,
        implementation: ImplementationConfig,
        implementation_dir: Path,
        service_config_to_test: "ServiceConfig",
        event_manager: Optional[EventManager] = None,
        emitter_registry=None,
    ) -> IServiceManager:
        """Create a service manager instance."""
        return self.plugin_factory.create_service_manager(
            protocol=protocol,
            implementation=implementation,
            implementation_dir=implementation_dir,
            service_config_to_test=service_config_to_test,
            event_manager=event_manager or self.event_manager,
            emitter_registry=emitter_registry,
        )
    
    def create_environment_manager(
        self,
        environment: str,
        test_config: "TestConfig",
        environment_dir: Path,
        output_dir: Path,
        event_manager: EventManager,
    ) -> IEnvironmentPlugin:
        """Create an environment manager instance."""
        return self.plugin_factory.create_environment_manager(
            environment=environment,
            test_config=test_config,
            environment_dir=environment_dir,
            output_dir=output_dir,
            event_manager=event_manager,
        )
    
    def create_observer_plugin(self, plugin_name: str, *args, **kwargs):
        """Create an observer plugin instance."""
        return self.plugin_factory.create_observer_plugin(plugin_name, *args, **kwargs)
    
    # Docker Management Methods
    def build_docker_image(self, impl_name: str, version: Dict[str, Any]):
        """
        Build Docker image for a plugin implementation.
        
        Args:
            impl_name: Implementation name
            version: Version configuration (can be string or dict)
        """
        if not self.docker_builder:
            self.logger.warning("Docker builder not available")
            return
        
        try:
            # Get dockerfile path from plugin metadata
            plugin = self.get_plugin(impl_name)
            dockerfile_path = plugin.dockerfile_path if plugin else None
            
            if not dockerfile_path:
                self.logger.warning(
                    "No Dockerfile found for implementation: %s", impl_name
                )
                return
            
            # Ensure version string is safe for Docker tag (no special characters)
            safe_version = version["version"] if isinstance(version, dict) else version
            # Build the image
            image_tag = f"{impl_name}_{safe_version}:latest"
            config = {}
            config["dependencies"] = (
                version.get("dependencies", {}) if isinstance(version, dict) else {}
            )
            config["commit"] = (
                version.get("commit", "master")
                if isinstance(version, dict)
                else "master"
            )
            
            # Check if image already exists and whether to force rebuild
            force_build = self._should_force_build()
            
            if self._check_and_add_existing_image(
                impl_name, dockerfile_path, image_tag, force_build
            ):
                return
            
            build_result = self.docker_builder.build_image(
                impl_name=impl_name,
                version=safe_version,
                dockerfile_path=dockerfile_path,
                context_path=dockerfile_path.parent,
                config=config,
            )
            
            if build_result:
                # Handle different return types from docker_builder.build_image()
                self.logger.debug(
                    "Docker build result type: %s, value: %s",
                    type(build_result).__name__,
                    str(build_result)[:100],  # Limit length for logging
                )
                if isinstance(build_result, dict):
                    build_info = {
                        "tag": image_tag,
                        "dockerfile": str(dockerfile_path),
                        "build_time": build_result.get("build_time"),
                        "image_id": build_result.get("image_id"),
                    }
                else:
                    # If build_result is not a dict (e.g., string or other type), use basic info
                    build_info = {
                        "tag": image_tag,
                        "dockerfile": str(dockerfile_path),
                        "build_time": None,
                        "image_id": str(build_result) if build_result else None,
                    }
                
                self.built_images[impl_name] = build_info
                self.logger.info("Successfully built Docker image: %s", image_tag)
            else:
                self.logger.error("Failed to build Docker image: %s", image_tag)
        
        except Exception as e:
            self.logger.error("Error building Docker image for %s: %s", impl_name, e)
            import traceback
            self.logger.debug("Full traceback: %s", traceback.format_exc())
    
    def build_docker_image_from_path(
        self, path: Path, name: str, version: Optional[str] = None
    ):
        """
        Build Docker image from a specific path.
        
        Args:
            path: Path to Dockerfile or build context
            name: Image name
            version: Image version (optional)
        """
        if not self.docker_builder:
            self.logger.warning("Docker builder not available")
            return
        
        try:
            # Determine dockerfile path
            if path.is_file() and path.name == "Dockerfile":
                dockerfile_path = path
                build_context = path.parent
            elif path.is_dir():
                dockerfile_path = path / "Dockerfile"
                build_context = path
                if not dockerfile_path.exists():
                    self.logger.error("No Dockerfile found in directory: %s", path)
                    return
            else:
                self.logger.error("Invalid path for Docker build: %s", path)
                return
            
            # Build image tag
            image_tag = f"{name}_{version}:latest" if version else f"{name}:latest"
            
            # Check if image already exists and whether to force rebuild
            force_build = self._should_force_build()
            
            if self._check_and_add_existing_image(
                name, dockerfile_path, image_tag, force_build
            ):
                return
            
            self.logger.info(
                "Building Docker image %s from %s", image_tag, dockerfile_path
            )
            
            build_result = self.docker_builder.build_image(
                impl_name=name,
                version=version or "latest",
                dockerfile_path=dockerfile_path,
                context_path=build_context,
                config={},
            )
            
            if build_result:
                if isinstance(build_result, dict):
                    build_info = {
                        "tag": image_tag,
                        "dockerfile": str(dockerfile_path),
                        "build_time": build_result.get("build_time"),
                        "image_id": build_result.get("image_id"),
                    }
                else:
                    build_info = {
                        "tag": image_tag,
                        "dockerfile": str(dockerfile_path),
                        "build_time": None,
                        "image_id": str(build_result) if build_result else None,
                    }
                
                self.built_images[name] = build_info
                self.logger.info("Successfully built Docker image: %s", image_tag)
            else:
                self.logger.error("Failed to build Docker image: %s", image_tag)
        
        except Exception as e:
            self.logger.error("Error building Docker image from path %s: %s", path, e)
            import traceback
            self.logger.debug("Full traceback: %s", traceback.format_exc())
    
    def _check_and_add_existing_image(
        self, impl_name, dockerfile_path, image_tag, force_build
    ):
        """Check if image exists and add to tracking."""
        if not force_build and self.docker_builder.image_exists(image_tag):
            self.logger.info(
                "Docker image %s already exists, skipping build", image_tag
            )
            self.built_images[impl_name] = {
                "tag": image_tag,
                "dockerfile": str(dockerfile_path),
                "build_time": None,
                "image_id": None,
                "already_existed": True,
            }
            return True
        return False
    
    def _should_force_build(self):
        """Determine if we should force rebuild images."""
        force_build = (
            self.global_config.docker.build_docker_image
            if (
                self.global_config
                and hasattr(self.global_config.docker, "build_docker_image")
            )
            else True
        )
        return force_build
    
    
    # Additional utility methods
    def get_built_images(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about built Docker images.
        
        Returns:
            Dictionary mapping image names to build information
        """
        return self.built_images.copy()
    
    def is_image_built(self, image_name: str) -> bool:
        """
        Check if a Docker image has been built.
        
        Args:
            image_name: Name of the image to check
            
        Returns:
            True if image has been built, False otherwise
        """
        return image_name in self.built_images
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get plugin manager statistics.
        
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
            "built_images": len(self.built_images),
            "event_system_enabled": self.plugin_event_emitter is not None,
            "docker_builder_available": self.docker_builder is not None,
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the plugin manager state.
        
        Returns:
            Dictionary containing summary information
        """
        return self.get_statistics()
    
    def get_network_environment_plugin(self, environment_type: str) -> Optional[type]:
        """
        Get a network environment plugin class.
        
        Args:
            environment_type: Type of network environment
            
        Returns:
            Network environment plugin class or None if not found
        """
        try:
            self.logger.debug(f"Looking for network environment plugin: {environment_type}")
            
            # Import the plugin module directly
            if environment_type == "docker_compose":
                from panther.plugins.environments.network_environment.docker_compose.docker_compose import DockerComposeEnvironment
                return DockerComposeEnvironment
            elif environment_type == "localhost_single_container":
                from panther.plugins.environments.network_environment.localhost_single_container.localhost_single_container import LocalhostSingleContainerEnvironment
                return LocalhostSingleContainerEnvironment
            elif environment_type == "shadow_ns":
                from panther.plugins.environments.network_environment.shadow_ns.shadow_ns import ShadowNSEnvironment
                return ShadowNSEnvironment
            else:
                self.logger.error(f"Unknown network environment type: {environment_type}")
                return None
            
        except ImportError as e:
            self.logger.error(f"Failed to import network environment plugin {environment_type}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Failed to get network environment plugin {environment_type}: {e}")
            return None
    
    def get_execution_environment_plugin(
        self, 
        environment_type: str,
        output_dir: str = "/tmp",
        event_manager: Optional[EventManager] = None,
        global_config: Optional[GlobalConfig] = None,
        config: Optional[Any] = None
    ) -> Optional[type]:
        """
        Get an execution environment plugin class.
        
        Args:
            environment_type: Type of execution environment
            output_dir: Output directory for environment (unused)
            event_manager: Event manager instance (unused)
            global_config: Global configuration (unused)  
            config: Environment-specific configuration (unused)
            
        Returns:
            Execution environment plugin class or None if not found
        """
        try:
            self.logger.debug(f"Looking for execution environment plugin: {environment_type}")
            
            # Import the plugin module directly
            if environment_type == "strace":
                from panther.plugins.environments.execution_environment.strace.strace import StraceEnvironment
                return StraceEnvironment
            elif environment_type == "gperf_cpu":
                from panther.plugins.environments.execution_environment.gperf_cpu.gperf_cpu import GperfCpuEnvironment
                return GperfCpuEnvironment
            elif environment_type == "gperf_heap":
                from panther.plugins.environments.execution_environment.gperf_heap.gperf_heap import GperfHeapEnvironment
                return GperfHeapEnvironment
            elif environment_type == "memcheck":
                from panther.plugins.environments.execution_environment.memcheck.memcheck import MemcheckEnvironment
                return MemcheckEnvironment
            elif environment_type == "helgrind":
                from panther.plugins.environments.execution_environment.helgrind.helgrind import HelgrindEnvironment
                return HelgrindEnvironment
            elif environment_type == "iterations":
                from panther.plugins.environments.execution_environment.iterations.iterations import IterationsEnvironment
                return IterationsEnvironment
            else:
                self.logger.error(f"Unknown execution environment type: {environment_type}")
                return None
            
        except ImportError as e:
            self.logger.error(f"Failed to import execution environment plugin {environment_type}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Failed to get execution environment plugin {environment_type}: {e}")
            return None