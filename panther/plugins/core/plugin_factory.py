"""
Central Plugin Factory

This module provides centralized plugin instantiation for all plugin types,
consolidating the separate service and environment factories.
"""

import importlib
import inspect
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union

from panther.core.exceptions.fast_fail import (
    ErrorSeverity,
    FastFailHandler,
    PluginLoadException,
)
from panther.core.observer.management.event_manager import EventManager
from panther.core.utils.logging_mixin import LoggerMixin
from panther.plugins.plugin_config_resolver import PluginConfigResolver

from .plugin_metadata import PluginMetadata, PluginType


class PluginFactory(LoggerMixin):
    """
    Central factory for creating all types of plugin instances.
    
    This factory consolidates service creation, environment management,
    observer plugins, and any other plugin types into a single interface.
    """
    
    def __init__(
        self,
        plugin_manager: 'PluginManager',
        config_resolver: Optional[PluginConfigResolver] = None,
        event_manager: Optional[EventManager] = None,
        fast_fail_handler: Optional[FastFailHandler] = None
    ):
        """
        Initialize the plugin factory.
        
        Args:
            plugin_manager: Reference to the central plugin manager
            config_resolver: Configuration resolver instance
            event_manager: Event manager for plugin events
            fast_fail_handler: Fast fail handler for critical errors
        """
        super().__init__()
        
        self.plugin_manager = plugin_manager
        self.config_resolver = config_resolver or PluginConfigResolver()
        self.event_manager = event_manager
        self.fast_fail_handler = fast_fail_handler
        
        # Cache for loaded plugin classes
        self._class_cache: Dict[str, Type] = {}
        
        # Plugin type to interface mapping
        self._interface_mapping = {
            PluginType.SERVICE: "IServiceManager",
            PluginType.IUT: "IServiceManager", 
            PluginType.TESTER: "IServiceManager",
            PluginType.NETWORK_ENVIRONMENT: "INetworkEnvironment",
            PluginType.EXECUTION_ENVIRONMENT: "IExecutionEnvironment",
            PluginType.ENVIRONMENT: "IEnvironmentPlugin",
            PluginType.OBSERVER: "IPluginObserver",
        }
    
    def create_plugin_instance(
        self,
        plugin_name: str,
        plugin_type: Union[str, PluginType],
        *args,
        **kwargs
    ) -> Any:
        """
        Create a plugin instance of any type.
        
        Args:
            plugin_name: Name of the plugin
            plugin_type: Type of plugin to create
            *args: Positional arguments for plugin constructor
            **kwargs: Keyword arguments for plugin constructor
            
        Returns:
            Plugin instance
            
        Raises:
            PluginLoadException: If plugin cannot be created
        """
        # Normalize plugin type
        if isinstance(plugin_type, str):
            try:
                plugin_type = PluginType(plugin_type)
            except ValueError:
                # Handle legacy type names
                type_mapping = {
                    "testers": PluginType.TESTER,
                    "iut": PluginType.IUT,
                    "network_environment": PluginType.NETWORK_ENVIRONMENT,
                    "execution_environment": PluginType.EXECUTION_ENVIRONMENT,
                }
                plugin_type = type_mapping.get(plugin_type, PluginType.SERVICE)
        
        # Get plugin metadata
        plugin_metadata = self.plugin_manager.get_plugin(plugin_name)
        if not plugin_metadata:
            error = f"Plugin '{plugin_name}' not found"
            self._handle_plugin_error(error, ErrorSeverity.CRITICAL)
            raise PluginLoadException(error, plugin_name, plugin_type.value if hasattr(plugin_type, 'value') else str(plugin_type))
        
        # Validate plugin type matches
        if plugin_metadata.type != plugin_type:
            error = (
                f"Plugin type mismatch: '{plugin_name}' is type "
                f"'{plugin_metadata.type.value}', expected '{plugin_type.value}'"
            )
            self._handle_plugin_error(error, ErrorSeverity.HIGH)
            raise PluginLoadException(error, plugin_name, plugin_type.value if hasattr(plugin_type, 'value') else str(plugin_type))
        
        # Load and instantiate plugin class
        try:
            plugin_class = self._load_plugin_class(plugin_metadata)
            
            # Inject common dependencies
            if self.event_manager and 'event_manager' not in kwargs:
                kwargs['event_manager'] = self.event_manager
            
            # Create instance
            instance = plugin_class(*args, **kwargs)
            
            self.logger.debug(
                "Created plugin instance: %s (%s)",
                plugin_name,
                plugin_type.value
            )
            
            return instance
            
        except Exception as e:
            error = f"Failed to create plugin '{plugin_name}': {str(e)}"
            self._handle_plugin_error(error, ErrorSeverity.HIGH)
            raise PluginLoadException(error, plugin_name, plugin_type.value if hasattr(plugin_type, 'value') else str(plugin_type)) from e
    
    def _find_plugin_file(self, plugin_name: str, plugin_type: str) -> Path:
        """
        Find the plugin file based on plugin name and type.
        
        Args:
            plugin_name: Name of the plugin
            plugin_type: Type of the plugin (iut, tester, etc.)
            
        Returns:
            Path to the plugin file
            
        Raises:
            PluginLoadException: If plugin file not found
        """
        # Common plugin locations
        search_paths = []
        
        if plugin_type in ["iut", "testers", "tester"]:
            # Service plugins
            if plugin_type == "tester" or plugin_type == "testers":
                search_paths.append(Path("panther/plugins/services/testers") / plugin_name / f"{plugin_name}.py")
            else:
                # IUT plugins might be in protocol subdirectories
                for protocol in ["quic", "http", "minip"]:
                    search_paths.append(Path(f"panther/plugins/services/iut/{protocol}") / plugin_name / f"{plugin_name}.py")
                search_paths.append(Path("panther/plugins/services/iut") / plugin_name / f"{plugin_name}.py")
        elif plugin_type == "environment":
            # Environment plugins
            search_paths.extend([
                Path("panther/plugins/environments/network_environment") / plugin_name / f"{plugin_name}.py",
                Path("panther/plugins/environments/execution_environment") / plugin_name / f"{plugin_name}.py",
            ])
        
        # Try to find the file
        for path in search_paths:
            if path.exists():
                return path
        
        # If not found, raise error
        error = f"Plugin file not found for '{plugin_name}' (type: {plugin_type}). Searched paths: {search_paths}"
        raise PluginLoadException(error, plugin_name, plugin_type)
    
    def create_service_manager(
        self,
        protocol,
        implementation,
        implementation_dir: Path,
        service_config_to_test,
        event_manager: Optional[EventManager] = None,
        emitter_registry=None,
    ):
        """
        Create a service manager instance using the exact interface from ServiceFactory.
        
        Args:
            protocol: Protocol configuration (ProtocolConfig)
            implementation: Implementation configuration (ImplementationConfig) 
            implementation_dir: Directory containing implementation files
            service_config_to_test: Service configuration to test (ServiceConfig)
            event_manager: Event manager instance
            emitter_registry: Emitter registry for events
            
        Returns:
            Service manager instance (IServiceManager)
        """
        implementation_name = implementation.name
        implementation_type = implementation.type
        
        self.logger.debug(
            "Creating service manager for %s (%s)",
            implementation_name,
            implementation_type,
        )
        
        # Get plugin metadata
        plugin_metadata = self.plugin_manager.get_plugin(implementation_name)
        if not plugin_metadata:
            error = f"Plugin '{implementation_name}' not found"
            self._handle_plugin_error(error, ErrorSeverity.CRITICAL)
            raise PluginLoadException(error, implementation_name, implementation_type)
        
        try:
            # Load plugin class using the same approach as ServiceFactory
            from panther.plugins.plugin_loader_utils import PluginManagerUtils
            
            # If implementation_dir is not valid or is a file path, use the plugin's discovered path
            if implementation_dir and implementation_dir.is_dir():
                service_file_path = implementation_dir / f"{implementation_name}.py"
            else:
                # Use the path from plugin metadata or find it
                if hasattr(plugin_metadata, 'path') and plugin_metadata.path:
                    plugin_dir = Path(plugin_metadata.path)
                    if plugin_dir.is_file():
                        service_file_path = plugin_dir
                    else:
                        service_file_path = plugin_dir / f"{implementation_name}.py"
                else:
                    # Fallback: try to find the plugin file
                    service_file_path = self._find_plugin_file(implementation_name, implementation_type)
            
            service_manager_class = PluginManagerUtils.load_plugin_class(
                plugin_path=service_file_path,
                class_suffix="ServiceManager",
                name_transform=lambda name: "".join(word.title() for word in name.split("_")),
            )
            
            # Create the instance - try with emitter_registry first, fallback without it
            # This ensures backward compatibility with service managers that don't support emitter_registry yet
            try:
                service_manager = service_manager_class(
                    service_config_to_test=service_config_to_test,
                    service_type=implementation_type,
                    protocol=protocol,
                    implementation_name=implementation_name,
                    event_manager=event_manager or self.event_manager,
                    emitter_registry=emitter_registry,
                )
            except TypeError as e:
                if "emitter_registry" in str(e):
                    # Service manager doesn't support emitter_registry yet, fallback to legacy approach
                    self.logger.debug(
                        "Service manager %s doesn't support emitter_registry parameter, using legacy approach",
                        implementation_name,
                    )
                    service_manager = service_manager_class(
                        service_config_to_test=service_config_to_test,
                        service_type=implementation_type,
                        protocol=protocol,
                        implementation_name=implementation_name,
                        event_manager=event_manager or self.event_manager,
                    )
                else:
                    self.logger.error(f"Error creating service manager: {e}")
                    raise
            
            self.logger.info(
                "Successfully created service manager for %s (%s)",
                implementation_name,
                implementation_type,
            )
            return service_manager
            
        except Exception as e:
            error = f"Failed to create service manager for '{implementation_name}': {str(e)}"
            self._handle_plugin_error(error, ErrorSeverity.HIGH)
            raise PluginLoadException(error, implementation_name, implementation_type) from e
    
    def create_environment_manager(
        self,
        environment: str,
        test_config,
        environment_dir: Path,
        output_dir: Path,
        event_manager: EventManager,
    ):
        """
        Create an environment manager instance using the exact interface from EnvironmentFactory.
        
        Args:
            environment: Environment name (matches EnvironmentFactory signature)
            test_config: Test configuration (TestConfig)
            environment_dir: Directory containing environment files
            output_dir: Output directory for environment data
            event_manager: Event manager instance
            
        Returns:
            Environment manager instance (IEnvironmentPlugin)
        """
        self.logger.debug("Creating environment manager for %s", environment)
        
        # Get plugin metadata
        plugin_metadata = self.plugin_manager.get_plugin(environment)
        if not plugin_metadata:
            error = f"Environment plugin '{environment}' not found"
            self._handle_plugin_error(error, ErrorSeverity.CRITICAL)
            raise PluginLoadException(error, environment, "environment")
        
        try:
            # Determine environment type and subtype (matching EnvironmentFactory logic)
            env_type = None
            env_sub_type = environment
            
            # Try to infer from metadata
            if plugin_metadata.type == PluginType.NETWORK_ENVIRONMENT:
                env_type = "network_environment"
            elif plugin_metadata.type == PluginType.EXECUTION_ENVIRONMENT:
                env_type = "execution_environment"
            else:
                # Check capabilities or default to network environment
                if plugin_metadata.has_capability("network") or "network" in plugin_metadata.tags:
                    env_type = "network_environment"
                elif plugin_metadata.has_capability("execution") or "execution" in plugin_metadata.tags:
                    env_type = "execution_environment"
                else:
                    # Default to network environment
                    env_type = "network_environment"
            
            # Determine file path
            env_file_path = environment_dir / f"{env_sub_type}.py"
            
            self.logger.debug("Loading environment module from %s", env_file_path)
            
            # Use PluginManagerUtils to load the plugin class (matching EnvironmentFactory)
            from panther.plugins.plugin_loader_utils import PluginManagerUtils
            
            env_manager_class = PluginManagerUtils.load_plugin_class(
                plugin_path=env_file_path,
                class_suffix="Environment",
                name_transform=lambda name: f"{name.title()}",
            )
            
            # Extract environment configuration (matching EnvironmentFactory logic)
            from panther.config.core.models.environment import EnvironmentConfig
            
            env_config = getattr(test_config, env_type, {})
            if isinstance(env_config, dict):
                env_config_to_test = EnvironmentConfig(**env_config)
            else:
                env_config_to_test = env_config
            
            # Create instance (matching EnvironmentFactory arguments)
            env_manager = env_manager_class(
                env_config_to_test=env_config_to_test,
                output_dir=str(output_dir),
                env_type=env_type,
                env_sub_type=env_sub_type,
                event_manager=event_manager,
            )
            
            self.logger.info(
                "Successfully created environment manager for %s", environment
            )
            return env_manager
            
        except Exception as e:
            error = f"Failed to create environment manager for '{environment}': {str(e)}"
            self._handle_plugin_error(error, ErrorSeverity.HIGH)
            raise PluginLoadException(error, environment, "environment") from e
    
    def create_observer_plugin(
        self,
        plugin_name: str,
        *args,
        **kwargs
    ):
        """
        Create an observer plugin instance.
        
        Args:
            plugin_name: Name of the observer plugin
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Observer plugin instance
        """
        self.logger.debug("Creating observer plugin: %s", plugin_name)
        
        # For observer plugins, we need special handling since they may come from
        # the legacy observer plugin registry
        try:
            return self.create_plugin_instance(
                plugin_name,
                PluginType.OBSERVER,
                *args,
                **kwargs
            )
        except PluginLoadException:
            # Fallback to legacy observer plugin registry
            self.logger.debug("Falling back to legacy observer plugin registry for %s", plugin_name)
            return self._create_legacy_observer_plugin(plugin_name, *args, **kwargs)
    
    def _create_legacy_observer_plugin(self, plugin_name: str, *args, **kwargs):
        """Create observer plugin using legacy registry as fallback."""
        try:
            from panther.core.observer.plugins.plugin_registry import PluginRegistry
            
            # Create a temporary registry
            registry = PluginRegistry()
            plugins = registry.discover_plugins()
            
            plugin_class = plugins.get(plugin_name)
            if plugin_class:
                return plugin_class(*args, **kwargs)
            else:
                raise PluginLoadException(f"Observer plugin '{plugin_name}' not found in legacy registry", plugin_name, "observer")
                
        except Exception as e:
            raise PluginLoadException(f"Failed to create observer plugin '{plugin_name}': {str(e)}", plugin_name, "observer") from e
    
    def _load_plugin_class(self, plugin_metadata: PluginMetadata) -> Type:
        """
        Load plugin class from metadata.
        
        Args:
            plugin_metadata: Plugin metadata
            
        Returns:
            Plugin class
            
        Raises:
            PluginLoadException: If class cannot be loaded
        """
        cache_key = f"{plugin_metadata.name}:{plugin_metadata.type.value}"
        
        # Check cache first
        if cache_key in self._class_cache:
            return self._class_cache[cache_key]
        
        try:
            # Determine class name and module path
            suffix = "ServiceManager" if plugin_metadata.type in [
                PluginType.SERVICE, PluginType.IUT, PluginType.TESTER
            ] else ""
            class_name = f"{plugin_metadata.name.title()}{suffix}"
            
            module_path = self._get_module_path(plugin_metadata)
            
            # Import module and get class
            module = importlib.import_module(module_path)
            plugin_class = getattr(module, class_name)
            
            # Validate class implements expected interface
            self._validate_plugin_class(plugin_class, plugin_metadata.type)
            
            # Cache the class
            self._class_cache[cache_key] = plugin_class
            
            self.logger.debug(
                "Loaded plugin class: %s from %s",
                class_name,
                module_path
            )
            
            return plugin_class
            
        except (ImportError, AttributeError, ModuleNotFoundError) as e:
            error = (
                f"Failed to load plugin class for '{plugin_metadata.name}': "
                f"module={module_path}, class={class_name}, error={str(e)}"
            )
            raise PluginLoadException(error, plugin_metadata.name, plugin_metadata.type.value) from e
    
    def _get_module_path(self, plugin_metadata: PluginMetadata) -> str:
        """
        Get module import path for plugin.
        
        Args:
            plugin_metadata: Plugin metadata
            
        Returns:
            Module import path
        """
        # Start from the plugin path
        plugin_path = plugin_metadata.path
        
        # Find the relative path from panther root
        current = plugin_path
        path_parts = []
        
        while current.name != "panther" and current.parent != current:
            path_parts.append(current.name)
            current = current.parent
        
        if current.name != "panther":
            # Fallback - construct from known structure
            if plugin_metadata.type in [PluginType.SERVICE, PluginType.IUT, PluginType.TESTER]:
                if plugin_metadata.protocol:
                    path_parts = [
                        "panther", "plugins", "services",
                        plugin_metadata.type.value,
                        plugin_metadata.protocol,
                        plugin_metadata.name,
                        plugin_metadata.name
                    ]
                else:
                    path_parts = [
                        "panther", "plugins", "services",
                        plugin_metadata.name,
                        plugin_metadata.name
                    ]
            elif plugin_metadata.type in [PluginType.NETWORK_ENVIRONMENT, PluginType.EXECUTION_ENVIRONMENT]:
                path_parts = [
                    "panther", "plugins", "environments",
                    plugin_metadata.type.value,
                    plugin_metadata.name,
                    plugin_metadata.name
                ]
            else:
                path_parts = [
                    "panther", "plugins",
                    plugin_metadata.name,
                    plugin_metadata.name
                ]
            
            return ".".join(path_parts)
        
        # Reverse and construct module path
        path_parts.reverse()
        path_parts.append(plugin_metadata.name)  # Add module file name
        
        return ".".join(["panther"] + path_parts)
    
    def _validate_plugin_class(self, plugin_class: Type, plugin_type: PluginType):
        """
        Validate that plugin class implements expected interface.
        
        Args:
            plugin_class: Plugin class to validate
            plugin_type: Expected plugin type
            
        Raises:
            PluginLoadException: If validation fails
        """
        expected_interface = self._interface_mapping.get(plugin_type)
        if not expected_interface:
            return  # No specific interface requirement
        
        # Check if class implements expected methods
        # This is a simplified check - could be enhanced with proper interface validation
        required_methods = self._get_required_methods(plugin_type)
        
        for method_name in required_methods:
            if not hasattr(plugin_class, method_name):
                error = (
                    f"Plugin class {plugin_class.__name__} does not implement "
                    f"required method '{method_name}' for interface {expected_interface}"
                )
                raise PluginLoadException(error, plugin_class.__name__, plugin_type.value)
    
    def _get_required_methods(self, plugin_type: PluginType) -> List[str]:
        """
        Get required methods for plugin type.
        
        Args:
            plugin_type: Plugin type
            
        Returns:
            List of required method names
        """
        if plugin_type in [PluginType.SERVICE, PluginType.IUT, PluginType.TESTER]:
            return ["generate_run_command", "_do_prepare"]
        elif plugin_type in [PluginType.NETWORK_ENVIRONMENT, PluginType.EXECUTION_ENVIRONMENT]:
            return ["prepare", "deploy", "run", "teardown"]
        elif plugin_type == PluginType.OBSERVER:
            return ["handle_event"]
        else:
            return []
    
    def _handle_plugin_error(self, error_message: str, severity: ErrorSeverity):
        """
        Handle plugin loading errors.
        
        Args:
            error_message: Error description
            severity: Error severity
        """
        self.logger.error("Plugin error (%s): %s", severity.value, error_message)
        
        if self.fast_fail_handler:
            # Create a proper exception with the error message
            from panther.core.exceptions.fast_fail import PantherException, ErrorCategory
            error = PantherException(error_message, severity, ErrorCategory.PLUGIN_LOAD)
            self.fast_fail_handler.handle_error(error)
    
    def clear_cache(self):
        """Clear the plugin class cache."""
        self.logger.info("Clearing plugin class cache")
        self._class_cache.clear()
    
    def get_cached_classes(self) -> Dict[str, Type]:
        """
        Get currently cached plugin classes.
        
        Returns:
            Dictionary of cached classes
        """
        return self._class_cache.copy()
    
    def preload_plugins(self, plugin_names: Optional[List[str]] = None):
        """
        Preload plugin classes into cache.
        
        Args:
            plugin_names: Optional list of plugin names to preload.
                         If None, preloads all discovered plugins.
        """
        if plugin_names is None:
            plugins = self.plugin_manager.discover_plugins()
            plugin_names = list(plugins.keys())
        
        self.logger.info("Preloading %d plugin classes", len(plugin_names))
        
        for plugin_name in plugin_names:
            try:
                plugin_metadata = self.plugin_manager.get_plugin(plugin_name)
                if plugin_metadata:
                    self._load_plugin_class(plugin_metadata)
            except Exception as e:
                self.logger.warning(f"Failed to preload plugin '{plugin_name}': {e}")
        
        self.logger.info("Preloaded %d plugin classes", len(self._class_cache))