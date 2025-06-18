"""
Unified Plugin Metadata System

This module provides the single source of truth for plugin metadata
and manifest handling, consolidating all duplicated metadata classes.
"""

import json
import yaml
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


class PluginType(Enum):
    """Enumeration of plugin types."""
    SERVICE = "service"
    IUT = "iut" 
    TESTER = "tester"
    ENVIRONMENT = "environment"
    NETWORK_ENVIRONMENT = "network_environment"
    EXECUTION_ENVIRONMENT = "execution_environment"
    PROTOCOL = "protocol"
    OBSERVER = "observer"


class PluginStatus(Enum):
    """Plugin status enumeration."""
    DISCOVERED = "discovered"
    REGISTERED = "registered"
    LOADED = "loaded"
    ACTIVE = "active"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class PluginDependency:
    """Plugin dependency specification."""
    name: str
    version: Optional[str] = None
    optional: bool = False
    minimum_version: Optional[str] = None


@dataclass
class PluginParameter:
    """Plugin parameter specification."""
    name: str
    type: str
    description: str = ""
    required: bool = False
    default: Any = None
    choices: Optional[List[Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'name': self.name,
            'type': self.type,
            'description': self.description,
            'required': self.required,
            'default': self.default,
            'choices': self.choices
        }


@dataclass
class PluginCapability:
    """Plugin capability specification."""
    name: str
    description: str = ""
    version: str = "1.0.0"


@dataclass 
class PluginMetadata:
    """
    Unified plugin metadata container.
    
    This class consolidates all plugin metadata from the various
    duplicated implementations across the codebase.
    """
    # Core identification
    name: str
    type: PluginType
    path: Path
    
    # Basic metadata  
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    license: str = ""
    
    # Plugin classification
    protocol: Optional[str] = None
    category: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    # Functional specifications
    capabilities: List[PluginCapability] = field(default_factory=list)
    dependencies: List[PluginDependency] = field(default_factory=list)
    parameters: List[PluginParameter] = field(default_factory=list)
    supported_protocols: List[str] = field(default_factory=list)
    
    # Configuration and schema
    config_schema_path: Optional[Path] = None
    config_schema: Optional[Dict[str, Any]] = None
    
    # File system locations
    dockerfile_path: Optional[Path] = None
    manifest_path: Optional[Path] = None
    main_module_path: Optional[Path] = None
    
    # Runtime information
    status: PluginStatus = PluginStatus.DISCOVERED
    last_modified: Optional[float] = None
    checksum: Optional[str] = None
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Post-initialization processing."""
        # Ensure type is PluginType enum
        if isinstance(self.type, str):
            try:
                self.type = PluginType(self.type)
            except ValueError:
                # Handle legacy type names
                type_mapping = {
                    "testers": PluginType.TESTER,
                    "iut": PluginType.IUT,
                    "network_environment": PluginType.NETWORK_ENVIRONMENT,
                    "execution_environment": PluginType.EXECUTION_ENVIRONMENT,
                }
                self.type = type_mapping.get(self.type, PluginType.SERVICE)
        
        # Ensure path is Path object
        if isinstance(self.path, str):
            self.path = Path(self.path)
            
        # Convert string schema path to Path
        if isinstance(self.config_schema_path, str):
            self.config_schema_path = Path(self.config_schema_path)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation.
        
        Returns:
            Dictionary representation of metadata
        """
        return {
            'name': self.name,
            'type': self.type.value,
            'path': str(self.path),
            'version': self.version,
            'description': self.description,
            'author': self.author,
            'license': self.license,
            'protocol': self.protocol,
            'category': self.category,
            'tags': self.tags,
            'capabilities': [
                {'name': cap.name, 'description': cap.description, 'version': cap.version}
                for cap in self.capabilities
            ],
            'dependencies': [
                {
                    'name': dep.name,
                    'version': dep.version,
                    'optional': dep.optional,
                    'minimum_version': dep.minimum_version
                }
                for dep in self.dependencies
            ],
            'parameters': [
                {
                    'name': param.name,
                    'type': param.type,
                    'description': param.description,
                    'required': param.required,
                    'default': param.default,
                    'choices': param.choices
                }
                for param in self.parameters
            ],
            'supported_protocols': self.supported_protocols,
            'config_schema_path': str(self.config_schema_path) if self.config_schema_path else None,
            'dockerfile_path': str(self.dockerfile_path) if self.dockerfile_path else None,
            'manifest_path': str(self.manifest_path) if self.manifest_path else None,
            'main_module_path': str(self.main_module_path) if self.main_module_path else None,
            'status': self.status.value,
            'last_modified': self.last_modified,
            'checksum': self.checksum,
            'has_schema': self.config_schema is not None,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PluginMetadata':
        """Create instance from dictionary.
        
        Args:
            data: Dictionary data
            
        Returns:
            PluginMetadata instance
        """
        # Handle capabilities
        capabilities = []
        if 'capabilities' in data:
            for cap_data in data['capabilities']:
                if isinstance(cap_data, dict):
                    capabilities.append(PluginCapability(
                        name=cap_data.get('name', ''),
                        description=cap_data.get('description', ''),
                        version=cap_data.get('version', '1.0.0')
                    ))
                elif isinstance(cap_data, str):
                    capabilities.append(PluginCapability(name=cap_data))
        
        # Handle dependencies
        dependencies = []
        if 'dependencies' in data:
            for dep_data in data['dependencies']:
                if isinstance(dep_data, dict):
                    dependencies.append(PluginDependency(
                        name=dep_data.get('name', ''),
                        version=dep_data.get('version'),
                        optional=dep_data.get('optional', False),
                        minimum_version=dep_data.get('minimum_version')
                    ))
                elif isinstance(dep_data, str):
                    dependencies.append(PluginDependency(name=dep_data))
        
        # Handle parameters
        parameters = []
        if 'parameters' in data:
            for param_data in data['parameters']:
                if isinstance(param_data, dict):
                    parameters.append(PluginParameter(
                        name=param_data.get('name', ''),
                        type=param_data.get('type', 'str'),
                        description=param_data.get('description', ''),
                        required=param_data.get('required', False),
                        default=param_data.get('default'),
                        choices=param_data.get('choices')
                    ))
        
        # Parse status
        status = PluginStatus.DISCOVERED
        if 'status' in data:
            try:
                status = PluginStatus(data['status'])
            except ValueError:
                pass
        
        return cls(
            name=data.get('name', ''),
            type=data.get('type', PluginType.SERVICE),
            path=Path(data.get('path', '')),
            version=data.get('version', '1.0.0'),
            description=data.get('description', ''),
            author=data.get('author', ''),
            license=data.get('license', ''),
            protocol=data.get('protocol'),
            category=data.get('category'),
            tags=data.get('tags', []),
            capabilities=capabilities,
            dependencies=dependencies,
            parameters=parameters,
            supported_protocols=data.get('supported_protocols', []),
            config_schema_path=Path(data['config_schema_path']) if data.get('config_schema_path') else None,
            config_schema=data.get('config_schema'),
            dockerfile_path=Path(data['dockerfile_path']) if data.get('dockerfile_path') else None,
            manifest_path=Path(data['manifest_path']) if data.get('manifest_path') else None,
            main_module_path=Path(data['main_module_path']) if data.get('main_module_path') else None,
            status=status,
            last_modified=data.get('last_modified'),
            checksum=data.get('checksum'),
            metadata=data.get('metadata', {})
        )
    
    def is_compatible_with(self, protocol: Optional[str] = None, version: Optional[str] = None) -> bool:
        """Check if plugin is compatible with requirements.
        
        Args:
            protocol: Required protocol
            version: Required version
            
        Returns:
            True if compatible
        """
        if protocol and protocol not in self.supported_protocols and protocol != self.protocol:
            return False
            
        if version:
            # Simple version comparison - can be enhanced
            try:
                from packaging import version as pkg_version
                return pkg_version.parse(self.version) >= pkg_version.parse(version)
            except ImportError:
                # Fallback to string comparison
                return self.version >= version
                
        return True
    
    def get_parameter(self, name: str) -> Optional[PluginParameter]:
        """Get parameter by name.
        
        Args:
            name: Parameter name
            
        Returns:
            Parameter specification or None
        """
        for param in self.parameters:
            if param.name == name:
                return param
        return None
    
    def has_capability(self, capability: str) -> bool:
        """Check if plugin has capability.
        
        Args:
            capability: Capability name
            
        Returns:
            True if plugin has capability
        """
        return any(cap.name == capability for cap in self.capabilities)
    
    def validate_dependencies(self, available_plugins: Dict[str, 'PluginMetadata']) -> List[str]:
        """Validate that all dependencies are satisfied.
        
        Args:
            available_plugins: Dictionary of available plugins
            
        Returns:
            List of missing dependencies
        """
        missing = []
        
        for dep in self.dependencies:
            if dep.optional:
                continue
                
            if dep.name not in available_plugins:
                missing.append(dep.name)
                continue
                
            plugin = available_plugins[dep.name]
            
            # Check version requirements
            if dep.minimum_version:
                try:
                    from packaging import version as pkg_version
                    if pkg_version.parse(plugin.version) < pkg_version.parse(dep.minimum_version):
                        missing.append(f"{dep.name} (requires >= {dep.minimum_version}, found {plugin.version})")
                except ImportError:
                    if plugin.version < dep.minimum_version:
                        missing.append(f"{dep.name} (requires >= {dep.minimum_version}, found {plugin.version})")
        
        return missing


# Alias for backward compatibility
PluginManifest = PluginMetadata


class PluginMetadataLoader:
    """Utility class for loading plugin metadata from various sources."""
    
    @staticmethod
    def load_from_manifest(manifest_path: Path) -> Optional[PluginMetadata]:
        """Load metadata from manifest file.
        
        Args:
            manifest_path: Path to manifest file
            
        Returns:
            PluginMetadata instance or None
        """
        if not manifest_path.exists():
            return None
            
        try:
            with open(manifest_path) as f:
                if manifest_path.suffix.lower() in ['.yaml', '.yml']:
                    data = yaml.safe_load(f)
                else:
                    data = json.load(f)
            
            # Set file paths
            data['manifest_path'] = str(manifest_path)
            data['path'] = str(manifest_path.parent)
            
            return PluginMetadata.from_dict(data)
            
        except Exception:
            return None
    
    @staticmethod
    def extract_from_python_module(module_path: Path) -> Dict[str, Any]:
        """Extract metadata from Python module.
        
        Args:
            module_path: Path to Python module
            
        Returns:
            Extracted metadata dictionary
        """
        metadata = {}
        
        try:
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
            
            # Extract author
            if '__author__' in content:
                for line in content.split('\n'):
                    if '__author__' in line and '=' in line:
                        author = line.split('=')[1].strip().strip('"\'')
                        metadata['author'] = author
                        break
            
            # Extract supported protocols from decorators
            if '@register_plugin' in content:
                for line in content.split('\n'):
                    if 'supported_protocols' in line:
                        if '[' in line and ']' in line:
                            start = line.find('[')
                            end = line.find(']') + 1
                            try:
                                protocols = eval(line[start:end])
                                metadata['supported_protocols'] = protocols
                            except:
                                pass
        except Exception:
            pass
        
        return metadata
    
    @staticmethod
    def load_from_directory(plugin_dir: Path, plugin_type: str, protocol: Optional[str] = None) -> Optional[PluginMetadata]:
        """Load metadata from plugin directory.
        
        Args:
            plugin_dir: Plugin directory
            plugin_type: Type of plugin
            protocol: Protocol name
            
        Returns:
            PluginMetadata instance or None
        """
        plugin_name = plugin_dir.name
        
        # Basic info
        data = {
            'name': plugin_name,
            'type': plugin_type,
            'path': str(plugin_dir),
            'protocol': protocol,
        }
        
        # Try to load manifest
        manifest_files = ["manifest.yaml", "manifest.yml", "plugin.yaml", "plugin.yml"]
        for manifest_file in manifest_files:
            manifest_path = plugin_dir / manifest_file
            if manifest_path.exists():
                manifest_metadata = PluginMetadataLoader.load_from_manifest(manifest_path)
                if manifest_metadata:
                    return manifest_metadata
        
        # Try to extract from Python module
        main_module = plugin_dir / f"{plugin_name}.py"
        if main_module.exists():
            data.update(PluginMetadataLoader.extract_from_python_module(main_module))
            data['main_module_path'] = str(main_module)
        
        # Look for config schema
        schema_files = [
            plugin_dir / "config_schema.py",
            plugin_dir / "schema.json",
            plugin_dir / "schema.yaml"
        ]
        
        for schema_file in schema_files:
            if schema_file.exists():
                data['config_schema_path'] = str(schema_file)
                break
        
        # Look for Dockerfile
        dockerfile_path = plugin_dir / "Dockerfile"
        if dockerfile_path.exists():
            data['dockerfile_path'] = str(dockerfile_path)
        
        return PluginMetadata.from_dict(data)