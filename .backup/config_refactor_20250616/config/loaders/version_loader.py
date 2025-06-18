"""Version configuration loader for dynamic protocol version management."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Type, Union

import yaml
from omegaconf import DictConfig, OmegaConf

from panther.config.loaders.base_loader import (
    AbstractConfigLoader,
    ConfigurationLoadingError,
    FileBasedLoaderMixin,
)
from panther.config.models.base import ConfigModel
from panther.config.models.implementation import ImplementationType


class VersionConfigModel(ConfigModel):
    """Model for version-specific configuration."""
    
    version: str
    commit: Optional[str] = None
    dependencies: List[Dict[str, str]] = []
    parameters: Dict[str, Any] = {}
    build_args: Dict[str, str] = {}
    environment: Dict[str, str] = {}
    
    # Protocol-specific settings
    protocol_features: List[str] = []
    compatibility_notes: Optional[str] = None


class VersionRegistry:
    """Registry for managing protocol versions across implementations."""
    
    def __init__(self):
        self._versions: Dict[str, Dict[str, VersionConfigModel]] = {}
        self._protocol_versions: Dict[str, Set[str]] = {}
        self._registry_logger = logging.getLogger(__name__)
    
    def register_version(
        self, 
        protocol: str, 
        version: str, 
        config: VersionConfigModel,
        implementation: Optional[str] = None
    ) -> None:
        """Register a version configuration.
        
        Args:
            protocol: Protocol name (e.g., 'quic', 'http')
            version: Version identifier (e.g., 'rfc9000', 'draft29')
            config: Version configuration
            implementation: Optional implementation name
        """
        if protocol not in self._versions:
            self._versions[protocol] = {}
            self._protocol_versions[protocol] = set()
        
        key = f"{implementation}:{version}" if implementation else version
        self._versions[protocol][key] = config
        self._protocol_versions[protocol].add(version)
        
        self._registry_logger.debug(f"Registered version {version} for protocol {protocol}")
    
    def get_version(
        self, 
        protocol: str, 
        version: str, 
        implementation: Optional[str] = None
    ) -> Optional[VersionConfigModel]:
        """Get version configuration.
        
        Args:
            protocol: Protocol name
            version: Version identifier
            implementation: Optional implementation name
            
        Returns:
            Version configuration if found, None otherwise
        """
        if protocol not in self._versions:
            return None
        
        # Try implementation-specific first, then generic
        keys_to_try = []
        if implementation:
            keys_to_try.append(f"{implementation}:{version}")
        keys_to_try.append(version)
        
        for key in keys_to_try:
            if key in self._versions[protocol]:
                return self._versions[protocol][key]
        
        return None
    
    def get_available_versions(self, protocol: str) -> List[str]:
        """Get all available versions for a protocol.
        
        Args:
            protocol: Protocol name
            
        Returns:
            List of available version identifiers
        """
        return sorted(list(self._protocol_versions.get(protocol, set())))
    
    def get_supported_protocols(self) -> List[str]:
        """Get all supported protocols.
        
        Returns:
            List of protocol names
        """
        return sorted(list(self._protocol_versions.keys()))
    
    def clear(self) -> None:
        """Clear the registry."""
        self._versions.clear()
        self._protocol_versions.clear()


# Global version registry instance
version_registry = VersionRegistry()


class VersionConfigLoader(AbstractConfigLoader, FileBasedLoaderMixin):
    """Loader for version-specific configurations.
    
    Replaces the hardcoded version loading in service_manager_docker_mixin.py
    with a flexible, dynamic system.
    """
    
    def __init__(self, plugin_dir: Optional[Union[str, Path]] = None, enable_cache: bool = True):
        super().__init__(enable_cache=enable_cache)
        self.plugin_dir = Path(plugin_dir) if plugin_dir else self._get_default_plugin_dir()
        self.supported_extensions = [".yaml", ".yml"]
        self.registry = version_registry
        self._discovered_paths: Set[Path] = set()
    
    def _get_default_plugin_dir(self) -> Path:
        """Get the default plugin directory."""
        return Path(__file__).parent.parent.parent / "plugins"
    
    def load(self, source: Union[str, Path, Dict[str, Any]]) -> Dict[str, Any]:
        """Load version configuration from file or dict.
        
        Args:
            source: Path to version config file or dict
            
        Returns:
            Configuration dictionary
        """
        if isinstance(source, dict):
            return source
        
        file_path = self.validate_file_exists(source)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            if not isinstance(config, dict):
                raise ConfigurationLoadingError(
                    f"Version config must be a dictionary, got {type(config)}",
                    source=str(file_path)
                )
            
            return config
            
        except yaml.YAMLError as e:
            raise ConfigurationLoadingError(
                f"YAML parsing error in {file_path}: {e}",
                source=str(file_path),
                line=getattr(e, 'problem_mark', {}).get('line')
            )
        except Exception as e:
            raise ConfigurationLoadingError(
                f"Failed to load version config from {file_path}: {e}",
                source=str(file_path)
            )
    
    def validate(self, config: Dict[str, Any]) -> bool:
        """Validate version configuration structure."""
        required_fields = ['version']
        
        for field in required_fields:
            if field not in config:
                raise ConfigurationLoadingError(
                    f"Missing required field '{field}' in version configuration"
                )
        
        return True
    
    def get_schema(self) -> Type[ConfigModel]:
        """Get the schema for version configurations."""
        return VersionConfigModel
    
    def get_version_config_path(
        self, 
        implementation_name: str, 
        implementation_type: ImplementationType,
        protocol_name: str, 
        protocol_version: str
    ) -> Path:
        """Get the path to version configuration file.
        
        This replaces the hardcoded path logic from service_manager_docker_mixin.py.
        
        Args:
            implementation_name: Name of the implementation
            implementation_type: Type of implementation (IUT or TESTERS)
            protocol_name: Protocol name
            protocol_version: Protocol version
            
        Returns:
            Path to version configuration file
        """
        if implementation_type == ImplementationType.TESTERS:
            # For testers: plugins/services/testers/{impl}/version_configs/{protocol}/{version}.yaml
            return (
                self.plugin_dir / "services" / "testers" / implementation_name / 
                "version_configs" / protocol_name / f"{protocol_version}.yaml"
            )
        else:
            # For IUT: plugins/services/iut/{protocol}/{impl}/version_configs/{version}.yaml
            return (
                self.plugin_dir / "services" / "iut" / protocol_name / implementation_name /
                "version_configs" / f"{protocol_version}.yaml"
            )
    
    def load_version_config(
        self, 
        implementation_name: str,
        implementation_type: ImplementationType,
        protocol_name: str, 
        protocol_version: str
    ) -> Optional[VersionConfigModel]:
        """Load version configuration for specific implementation.
        
        Args:
            implementation_name: Implementation name
            implementation_type: Implementation type
            protocol_name: Protocol name
            protocol_version: Protocol version
            
        Returns:
            Version configuration or None if not found
        """
        # Check registry first
        existing = self.registry.get_version(
            protocol_name, 
            protocol_version, 
            implementation_name
        )
        if existing:
            return existing
        
        # Load from file
        config_path = self.get_version_config_path(
            implementation_name, implementation_type, protocol_name, protocol_version
        )
        
        if not config_path.exists():
            self._loader_logger.debug(f"Version config not found: {config_path}")
            return None
        
        try:
            config_model = self.load_and_validate(config_path)
            
            # Register in the registry
            self.registry.register_version(
                protocol_name, 
                protocol_version, 
                config_model, 
                implementation_name
            )
            
            return config_model
            
        except Exception as e:
            self._loader_logger.warning(f"Failed to load version config from {config_path}: {e}")
            return None
    
    def discover_versions(
        self, 
        protocol_name: Optional[str] = None,
        implementation_name: Optional[str] = None
    ) -> Dict[str, List[str]]:
        """Discover available versions by scanning plugin directories.
        
        Args:
            protocol_name: Optional protocol filter
            implementation_name: Optional implementation filter
            
        Returns:
            Dictionary mapping protocols to available versions
        """
        discovered = {}
        
        # Scan IUT directories
        iut_base = self.plugin_dir / "services" / "iut"
        if iut_base.exists():
            for protocol_dir in iut_base.iterdir():
                if not protocol_dir.is_dir():
                    continue
                
                if protocol_name and protocol_dir.name != protocol_name:
                    continue
                
                protocol = protocol_dir.name
                versions = set()
                
                for impl_dir in protocol_dir.iterdir():
                    if not impl_dir.is_dir():
                        continue
                    
                    if implementation_name and impl_dir.name != implementation_name:
                        continue
                    
                    version_configs_dir = impl_dir / "version_configs"
                    if version_configs_dir.exists():
                        for version_file in version_configs_dir.glob("*.yaml"):
                            version = version_file.stem
                            versions.add(version)
                            self._discovered_paths.add(version_file)
                
                if protocol not in discovered:
                    discovered[protocol] = set()
                discovered[protocol].update(versions)
        
        # Scan tester directories
        testers_base = self.plugin_dir / "services" / "testers"
        if testers_base.exists():
            for impl_dir in testers_base.iterdir():
                if not impl_dir.is_dir():
                    continue
                
                if implementation_name and impl_dir.name != implementation_name:
                    continue
                
                version_configs_dir = impl_dir / "version_configs"
                if version_configs_dir.exists():
                    for protocol_dir in version_configs_dir.iterdir():
                        if not protocol_dir.is_dir():
                            continue
                        
                        if protocol_name and protocol_dir.name != protocol_name:
                            continue
                        
                        protocol = protocol_dir.name
                        if protocol not in discovered:
                            discovered[protocol] = set()
                        
                        for version_file in protocol_dir.glob("*.yaml"):
                            version = version_file.stem
                            discovered[protocol].add(version)
                            self._discovered_paths.add(version_file)
                    
                    # Convert sets to sorted lists
                    for protocol in discovered:
                        if isinstance(discovered[protocol], set):
                            discovered[protocol] = sorted(list(discovered[protocol]))
        
        return discovered
    
    def preload_all_versions(self) -> None:
        """Preload all discoverable version configurations into the registry."""
        discovered = self.discover_versions()
        
        for protocol, versions in discovered.items():
            for version in versions:
                # Try to load from all implementations
                for path in self._discovered_paths:
                    if version in str(path) and protocol in str(path):
                        try:
                            config_model = self.load_and_validate(path)
                            
                            # Extract implementation name from path
                            path_parts = path.parts
                            if "testers" in path_parts:
                                impl_idx = path_parts.index("testers") + 1
                            else:
                                impl_idx = path_parts.index("iut") + 2
                            
                            if impl_idx < len(path_parts):
                                implementation = path_parts[impl_idx]
                                self.registry.register_version(
                                    protocol, version, config_model, implementation
                                )
                        except Exception as e:
                            self._loader_logger.warning(f"Failed to preload {path}: {e}")
    
    def get_available_versions_for_protocol(self, protocol: str) -> List[str]:
        """Get available versions for a specific protocol.
        
        Args:
            protocol: Protocol name
            
        Returns:
            List of available versions
        """
        # Discover if not already done
        if protocol not in self.registry.get_supported_protocols():
            self.discover_versions(protocol_name=protocol)
        
        return self.registry.get_available_versions(protocol)
    
    def supports_source_type(self, source: Union[str, Path, Dict[str, Any]]) -> bool:
        """Check if this loader supports the source type."""
        if isinstance(source, dict):
            return True
        
        if isinstance(source, (str, Path)):
            return self.supports_file(source)
        
        return False