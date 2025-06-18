import json
import os
from typing import Any, Dict, List, Optional, Tuple

"""
Plugin Discovery Module

This module handles plugin catalog management, registration, validation,
and discovery operations for the PANTHER framework.
"""

from pathlib import Path

import yaml

from panther.core.utils.logging_mixin import LoggerMixin
from panther.plugins.plugin_catalog import PluginCatalog
from panther.plugins.plugin_manifest import PluginRegistration


class PluginMetadata:
    """Enhanced plugin metadata container."""
    
    def __init__(self, **kwargs):
        """Initialize plugin metadata.
        
        Args:
            **kwargs: Metadata fields
        """
        self.name = kwargs.get('name', '')
        self.type = kwargs.get('type', '')
        self.path = kwargs.get('path', '')
        self.protocol = kwargs.get('protocol')
        self.version = kwargs.get('version', '1.0.0')
        self.description = kwargs.get('description', '')
        self.author = kwargs.get('author', '')
        self.capabilities = kwargs.get('capabilities', [])
        self.dependencies = kwargs.get('dependencies', [])
        self.parameters = kwargs.get('parameters', {})
        self.supported_protocols = kwargs.get('supported_protocols', [])
        self.config_schema = kwargs.get('config_schema')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary.
        
        Returns:
            Dictionary representation
        """
        return {
            'name': self.name,
            'type': self.type,
            'path': self.path,
            'protocol': self.protocol,
            'version': self.version,
            'description': self.description,
            'author': self.author,
            'capabilities': self.capabilities,
            'dependencies': self.dependencies,
            'parameters': self.parameters,
            'supported_protocols': self.supported_protocols,
            'has_schema': self.config_schema is not None
        }


class PluginDiscovery(LoggerMixin):
    """

    Handles plugin discovery, catalog management, and registration.

    This class provides functionality for:
    - Plugin catalog management
    - Plugin registration and validation
    - Directory scanning and plugin discovery
    """

    def __init__(self, plugin_directories: Optional[List[str]] = None):
        """
        Initialize the plugin discovery system.

        Args:
            plugin_directories: Directories to scan for plugins
        """
        super().__init__()

        # Plugin catalog for discovery and validation
        self.plugin_directories = plugin_directories or []
        self.plugin_catalog = PluginCatalog(self.plugin_directories)

        # Plugin registrations and dockerfiles tracking
        self.registrations: Dict[str, PluginRegistration] = {}
        self.dockerfiles: Dict[str, Path] = {}
        
        # Enhanced caches
        self._plugin_metadata_cache: Optional[Dict[str, PluginMetadata]] = None
        self._version_cache: Dict[str, List[str]] = {}
        self._schema_cache: Dict[str, Dict[str, Any]] = {}

        # Automatically discover plugins on initialization
        self._discover_plugins()

    def _discover_plugins(self):
        """Discover available plugins using the catalog."""
        # Add default plugin directories if not specified
        if not self.plugin_directories:
            base_path = Path(__file__).parent
            self.plugin_directories = [
                str(base_path / "services"),
                str(base_path / "environments"),
                str(base_path / "protocols"),
            ]
            # Update the catalog with the directories
            self.plugin_catalog = PluginCatalog(self.plugin_directories)

        # Scan for plugins
        plugins = self.plugin_catalog.scan_plugins(use_cache=False)

        # Register Dockerfiles from discovered plugins
        for plugin_id, manifest in plugins.items():  # pylint: disable=unused-variable
            plugin_path = Path(manifest.file_path) if manifest.file_path else None
            if plugin_path:
                dockerfile_path = plugin_path / "Dockerfile"
                if dockerfile_path.exists():
                    self.dockerfiles[manifest.name] = dockerfile_path
                    self.logger.debug(
                        "Registered Dockerfile for plugin '%s' at '%s'",
                        manifest.name,
                        dockerfile_path,
                    )

        self.logger.info("Discovered %d plugins", len(self.plugin_catalog.catalog))

    def discover_all_plugins(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Discover all available plugins with enhanced metadata.
        
        Args:
            force_refresh: Force re-discovery
            
        Returns:
            List of plugin information dictionaries
        """
        if self._plugin_metadata_cache is not None and not force_refresh:
            return [plugin.to_dict() for plugin in self._plugin_metadata_cache.values()]
        
        self.logger.info("Discovering plugins with enhanced metadata...")
        plugins = []
        self._plugin_metadata_cache = {}
        
        # Get base plugin directories
        if not self.plugin_directories:
            base_path = Path(__file__).parent
            plugin_dir = base_path
        else:
            # Find the plugin root
            plugin_dir = Path(self.plugin_directories[0]).parent if self.plugin_directories else Path(__file__).parent
        
        # Discover service plugins
        services_dir = plugin_dir / "services"
        if services_dir.exists():
            plugins.extend(self._discover_service_plugins(services_dir))
        
        # Discover environment plugins
        environments_dir = plugin_dir / "environments"
        if environments_dir.exists():
            plugins.extend(self._discover_environment_plugins(environments_dir))
        
        # Build cache
        for plugin in plugins:
            metadata = PluginMetadata(**plugin)
            self._plugin_metadata_cache[plugin['name']] = metadata
        
        self.logger.info(f"Discovered {len(plugins)} plugins with enhanced metadata")
        return plugins
    
    def get_plugin_by_name(self, name: str) -> Optional[PluginMetadata]:
        """Get plugin metadata by name.
        
        Args:
            name: Plugin name
            
        Returns:
            Plugin metadata or None
        """
        if self._plugin_metadata_cache is None:
            self.discover_all_plugins()
        
        return self._plugin_metadata_cache.get(name)
    
    def _discover_service_plugins(self, services_dir: Path) -> List[Dict[str, Any]]:
        """Discover service plugins.
        
        Args:
            services_dir: Services directory
            
        Returns:
            List of service plugin info
        """
        plugins = []
        
        # Check IUT and testers
        for service_type in ["iut", "testers"]:
            type_dir = services_dir / service_type
            if not type_dir.exists():
                continue
            
            # For IUT/testers, we have protocol subdirectories
            for protocol_dir in type_dir.iterdir():
                if not protocol_dir.is_dir() or protocol_dir.name.startswith('_'):
                    continue
                
                protocol_name = protocol_dir.name
                
                # Find implementations
                for impl_dir in protocol_dir.iterdir():
                    if not impl_dir.is_dir() or impl_dir.name.startswith('_'):
                        continue
                    
                    plugin_info = self._extract_plugin_info(
                        impl_dir,
                        plugin_type=service_type,
                        protocol=protocol_name
                    )
                    if plugin_info:
                        plugins.append(plugin_info)
        
        return plugins
    
    def _discover_environment_plugins(self, environments_dir: Path) -> List[Dict[str, Any]]:
        """Discover environment plugins.
        
        Args:
            environments_dir: Environments directory
            
        Returns:
            List of environment plugin info
        """
        plugins = []
        
        # Check network and execution environments
        for env_type in ["network_environment", "execution_environment"]:
            type_dir = environments_dir / env_type
            if not type_dir.exists():
                continue
            
            # Find environment implementations
            for impl_dir in type_dir.iterdir():
                if not impl_dir.is_dir() or impl_dir.name.startswith('_'):
                    continue
                
                plugin_info = self._extract_plugin_info(
                    impl_dir,
                    plugin_type=env_type
                )
                if plugin_info:
                    plugins.append(plugin_info)
        
        return plugins
    
    def _extract_plugin_info(
        self,
        plugin_dir: Path,
        plugin_type: str,
        protocol: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Extract plugin information from directory.
        
        Args:
            plugin_dir: Plugin directory
            plugin_type: Type of plugin
            protocol: Protocol name (for service plugins)
            
        Returns:
            Plugin information dictionary or None
        """
        plugin_name = plugin_dir.name
        
        # Basic info
        info = {
            'name': plugin_name,
            'type': plugin_type,
            'path': str(plugin_dir),
            'protocol': protocol,
        }
        
        # Try to load manifest
        manifest_path = plugin_dir / "manifest.yaml"
        if manifest_path.exists():
            try:
                with open(manifest_path) as f:
                    manifest = yaml.safe_load(f)
                    info.update(manifest)
            except Exception as e:
                self.logger.warning(f"Failed to load manifest for {plugin_name}: {e}")
        
        # Try to extract from Python module
        main_module = plugin_dir / f"{plugin_name}.py"
        if main_module.exists():
            info.update(self._extract_from_python_module(main_module))
        
        # Look for config schema
        schema_files = [
            plugin_dir / "config_schema.py",
            plugin_dir / "schema.json",
            plugin_dir / "schema.yaml"
        ]
        
        for schema_file in schema_files:
            if schema_file.exists():
                info['config_schema'] = str(schema_file)
                break
        
        return info
    
    def _extract_from_python_module(self, module_path: Path) -> Dict[str, Any]:
        """Extract metadata from Python module.
        
        Args:
            module_path: Path to Python module
            
        Returns:
            Extracted metadata
        """
        metadata = {}
        
        try:
            # Read the module content
            with open(module_path) as f:
                content = f.read()
            
            # Extract docstring
            if '"""' in content:
                start = content.find('"""') + 3
                end = content.find('"""', start)
                if end > start:
                    metadata['description'] = content[start:end].strip()
            
            # Extract version
            if '__version__' in content:
                for line in content.split('\n'):
                    if '__version__' in line and '=' in line:
                        version = line.split('=')[1].strip().strip('"\'')
                        metadata['version'] = version
                        break
            
            # Extract supported protocols from decorators
            if '@register_plugin' in content:
                for line in content.split('\n'):
                    if 'supported_protocols' in line:
                        # Simple extraction
                        if '[' in line and ']' in line:
                            start = line.find('[')
                            end = line.find(']') + 1
                            try:
                                protocols = eval(line[start:end])
                                metadata['supported_protocols'] = protocols
                            except:
                                pass
        except Exception as e:
            self.logger.debug(f"Failed to extract from {module_path}: {e}")
        
        return metadata

    def validate_experiment_plugins(
        self, experiment_config: Any
    ) -> Tuple[bool, List[str]]:
        """
        Validate that all plugins required by an experiment are available.

        Args:
            experiment_config: Experiment configuration

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        required_plugins = set()

        # Extract required plugins from experiment config
        for test in experiment_config.tests:
            # Check network environment
            if hasattr(test, "network_environment"):
                # Handle both dict and dataclass objects
                if hasattr(test.network_environment, "type"):
                    env_type = test.network_environment.type
                elif isinstance(test.network_environment, dict):
                    env_type = test.network_environment.get("type")
                else:
                    env_type = None

                if env_type:
                    required_plugins.add(f"environment:{env_type}")

            # Check execution environments
            if hasattr(test, "execution_environment") and test.execution_environment:
                for exec_env in test.execution_environment:
                    if hasattr(exec_env, "type"):
                        required_plugins.add(f"environment:{exec_env.type}")

            # Check services
            if hasattr(test, "services"):
                for (
                    service_name,
                    service_config,
                ) in test.services.items():  # pylint: disable=unused-variable
                    if hasattr(service_config, "implementation"):
                        impl = service_config.implementation
                        # Convert service type to plugin type format
                        if impl.type.lower() == "testers":
                            plugin_type = "tester"
                        elif impl.type.lower() == "iut":
                            plugin_type = "iut"
                        else:
                            plugin_type = impl.type.lower()
                        required_plugins.add(f"{plugin_type}:{impl.name}")

        # Validate each required plugin
        for plugin_id in required_plugins:
            if not self.is_plugin_available(plugin_id):
                errors.append(f"Required plugin not available: {plugin_id}")

        return len(errors) == 0, errors

    def get_plugin_info(self, plugin_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific plugin.

        Args:
            plugin_id: The plugin identifier

        Returns:
            Plugin information dictionary or None if not found
        """
        return self.plugin_catalog.get_plugin_info(plugin_id)

    def list_available_plugins(self) -> Dict[str, List[str]]:
        """
        Get a list of all available plugins organized by type.

        Returns:
            Dictionary mapping plugin types to lists of plugin names
        """
        try:
            all_plugins = self.plugin_catalog.catalog

            # Organize plugins by type
            plugins_by_type = {}
            for (
                plugin_id,
                manifest,
            ) in all_plugins.items():  # pylint: disable=unused-variable
                # Handle different attribute access patterns
                if hasattr(manifest, "plugin_type") and manifest.plugin_type:
                    plugin_type = (
                        manifest.plugin_type.value
                        if hasattr(manifest.plugin_type, "value")
                        else str(manifest.plugin_type)
                    )
                elif hasattr(manifest, "type"):
                    plugin_type = (
                        manifest.type.value
                        if hasattr(manifest.type, "value")
                        else str(manifest.type)
                    )
                else:
                    plugin_type = "unknown"

                if plugin_type not in plugins_by_type:
                    plugins_by_type[plugin_type] = []
                plugins_by_type[plugin_type].append(manifest.name)

            return plugins_by_type

        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error("Error listing available plugins: %s", e)
            return {}

    def get_plugin_status(self, plugin_id: str) -> Dict[str, Any]:
        """
        Get the current status of a plugin.

        Args:
            plugin_id: The plugin identifier

        Returns:
            Plugin status information
        """
        try:
            plugin_info = self.get_plugin_info(plugin_id)

            if plugin_info is None:
                return {
                    "status": "not_found",
                    "available": False,
                    "message": f"Plugin {plugin_id} not found",
                }

            # Check if plugin is properly registered
            is_registered = plugin_id in self.registrations

            return {
                "status": "available" if is_registered else "discovered",
                "available": True,
                "registered": is_registered,
                "info": plugin_info,
            }

        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error("Error getting plugin status for %s: %s", plugin_id, e)
            return {
                "status": "error",
                "available": False,
                "message": f"Error getting status: {str(e)}",
            }

    def is_plugin_available(self, plugin_id: str) -> bool:
        """
        Check if a plugin is available.

        Args:
            plugin_id: The plugin identifier

        Returns:
            True if plugin is available, False otherwise
        """
        return plugin_id in self.plugin_catalog.catalog

    def refresh_catalog(self):
        """
        Refresh the plugin catalog by re-scanning directories.
        """
        try:
            self.logger.info("Refreshing plugin catalog")
            self.plugin_catalog.refresh()
            self._discover_plugins()
            self.logger.info("Plugin catalog refreshed successfully")

        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error("Error refreshing plugin catalog: %s", e)

    def get_implementations_for_protocol(self, protocol: str) -> List[str]:
        """
        Get all available implementations for a specific protocol.

        Args:
            protocol: The protocol name (e.g., 'quic')

        Returns:
            List of implementation names
        """
        try:
            implementations = []
            all_plugins = self.plugin_catalog.catalog

            for (
                plugin_id,
                manifest,
            ) in all_plugins.items():  # pylint: disable=unused-variable
                # Check if this is a service plugin that supports the protocol
                manifest_type = None
                if hasattr(manifest, "plugin_type") and manifest.plugin_type:
                    manifest_type = (
                        manifest.plugin_type.value
                        if hasattr(manifest.plugin_type, "value")
                        else str(manifest.plugin_type)
                    )
                elif hasattr(manifest, "type"):
                    manifest_type = manifest.type

                if manifest_type == "service" and protocol in getattr(
                    manifest, "supported_protocols", []
                ):
                    implementations.append(manifest.name)

            self.logger.debug(
                "Found %d implementations for protocol %s",
                len(implementations),
                protocol,
            )
            return implementations

        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error(
                "Error getting implementations for protocol %s: %s", protocol, e
            )
            return []

    def get_testers(self) -> List[str]:
        """
        Get all available tester plugins.

        Returns:
            List of tester plugin names
        """
        try:
            testers = []
            all_plugins = self.plugin_catalog.catalog

            for (
                plugin_id,
                manifest,
            ) in all_plugins.items():  # pylint: disable=unused-variable
                # Check if this is a tester plugin
                if (
                    hasattr(manifest, "categories") and "tester" in manifest.categories
                ) or "tester" in plugin_id:
                    testers.append(manifest.name)

            self.logger.debug("Found %d tester plugins", len(testers))
            return testers

        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error("Error getting tester plugins: %s", e)
            return []

    def get_plugin_manifest(self, plugin_name: str, plugin_type: Optional[str] = None):
        """
        Get the manifest information for a plugin.

        Args:
            plugin_name: Name of the plugin
            plugin_type: Optional plugin type for filtering

        Returns:
            Plugin manifest or None if not found
        """
        try:
            # Search through catalog
            for (
                plugin_id,
                manifest,
            ) in self.plugin_catalog.catalog.items():  # pylint: disable=unused-variable
                manifest_type = None
                if hasattr(manifest, "plugin_type") and manifest.plugin_type:
                    manifest_type = (
                        manifest.plugin_type.value
                        if hasattr(manifest.plugin_type, "value")
                        else str(manifest.plugin_type)
                    )
                elif hasattr(manifest, "type"):
                    manifest_type = manifest.type

                if manifest.name == plugin_name and (
                    plugin_type is None or manifest_type == plugin_type
                ):
                    return manifest

            return None

        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error(
                "Error getting plugin manifest for %s: %s", plugin_name, e
            )
            return None

    def validate_plugin_dependencies(self, plugin_name: str) -> Tuple[bool, List[str]]:
        """
        Validate that all dependencies for a plugin are available.

        Args:
            plugin_name: Name of the plugin to validate

        Returns:
            Tuple of (dependencies_satisfied, missing_dependencies)
        """
        try:
            manifest = self.get_plugin_manifest(plugin_name)

            if manifest is None:
                return False, [f"Plugin {plugin_name} not found"]

            dependencies = getattr(manifest, "dependencies", [])
            missing_dependencies = []

            for dependency in dependencies:
                if not self.is_plugin_available(dependency):
                    missing_dependencies.append(dependency)

            dependencies_satisfied = len(missing_dependencies) == 0

            self.logger.debug(
                "Plugin %s dependency validation: %s (missing: %s)",
                plugin_name,
                "passed" if dependencies_satisfied else "failed",
                missing_dependencies,
            )

            return dependencies_satisfied, missing_dependencies

        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error(
                "Error validating dependencies for %s: %s", plugin_name, e
            )
            return False, [f"Validation error: {str(e)}"]

    def get_plugin_version(self, plugin_name: str) -> Optional[str]:
        """
        Get the version of a specific plugin.

        Args:
            plugin_name: Name of the plugin

        Returns:
            Plugin version string or None if not found
        """
        try:
            manifest = self.get_plugin_manifest(plugin_name)
            return getattr(manifest, "version", None) if manifest else None

        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error("Error getting version for plugin %s: %s", plugin_name, e)
            return None

    def get_dockerfiles(self) -> Dict[str, Path]:
        """
        Get all discovered Dockerfiles mapped by plugin name.

        Returns:
            Dictionary mapping plugin names to Dockerfile paths
        """
        return self.dockerfiles.copy()

    # Version Discovery Methods
    def discover_protocol_versions(self, protocol: Optional[str] = None) -> Dict[str, List[str]]:
        """Discover available versions for protocols.
        
        Args:
            protocol: Optional protocol to filter by
            
        Returns:
            Dictionary mapping protocol names to version lists
        """
        cache_key = protocol or "all"
        
        if cache_key in self._version_cache:
            return {protocol: self._version_cache[cache_key]} if protocol else self._version_cache
        
        self.logger.info(f"Discovering versions for protocol: {protocol or 'all'}")
        
        versions = {}
        
        # Get base plugin directories
        if not self.plugin_directories:
            base_path = Path(__file__).parent
            plugin_dir = base_path
        else:
            plugin_dir = Path(self.plugin_directories[0]).parent if self.plugin_directories else Path(__file__).parent
        
        # Check protocol directories
        protocols_dir = plugin_dir / "protocols"
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
        
        # Also check service implementations
        services_dir = plugin_dir / "services"
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
        """Discover version files in a directory.
        
        Args:
            directory: Directory to search
            
        Returns:
            List of discovered versions
        """
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

    # Schema Discovery Methods
    def discover_all_schemas(self) -> Dict[str, Dict[str, Any]]:
        """Discover all plugin schemas.
        
        Returns:
            Dictionary mapping plugin names to schema info
        """
        if self._schema_cache:
            return self._schema_cache
        
        self.logger.info("Discovering plugin schemas...")
        
        # Use enhanced plugin discovery to find plugins
        plugins = self.discover_all_plugins()
        
        for plugin_info in plugins:
            plugin_name = plugin_info['name']
            schema_path = plugin_info.get('config_schema')
            
            if schema_path:
                schema_info = self._load_schema(Path(schema_path))
                if schema_info:
                    self._schema_cache[plugin_name] = {
                        'schema': schema_info,
                        'path': schema_path,
                        'type': plugin_info['type'],
                        'protocol': plugin_info.get('protocol')
                    }
        
        self.logger.info(f"Discovered {len(self._schema_cache)} schemas")
        return self._schema_cache
    
    def get_schema_for_plugin(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """Get schema for a specific plugin.
        
        Args:
            plugin_name: Plugin name
            
        Returns:
            Schema information or None
        """
        if not self._schema_cache:
            self.discover_all_schemas()
        
        return self._schema_cache.get(plugin_name)
    
    def _load_schema(self, schema_path: Path) -> Optional[Dict[str, Any]]:
        """Load schema from file.
        
        Args:
            schema_path: Path to schema file
            
        Returns:
            Schema dictionary or None
        """
        if not schema_path.exists():
            return None
        
        try:
            if schema_path.suffix == '.json':
                with open(schema_path) as f:
                    return json.load(f)
            elif schema_path.suffix in ['.yaml', '.yml']:
                with open(schema_path) as f:
                    return yaml.safe_load(f)
            elif schema_path.suffix == '.py':
                # For Python schema files, we'd need to extract the schema
                # This is more complex and would require importing the module
                return {'type': 'python_schema', 'path': str(schema_path)}
        except Exception as e:
            self.logger.warning(f"Failed to load schema from {schema_path}: {e}")
        
        return None
