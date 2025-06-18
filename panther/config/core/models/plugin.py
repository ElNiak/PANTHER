"""Plugin configuration models."""

from typing import Any, Dict, Optional

from pydantic import Field

from .base_model import BaseUnifiedModel


class BasePluginConfig(BaseUnifiedModel):
    """Base configuration for all plugins.
    
    This class provides common configuration fields and functionality
    that all plugin configurations should inherit from.
    """
    
    # Common fields for all plugins
    enabled: bool = Field(True, description="Whether the plugin is enabled")
    version: Optional[str] = Field(None, description="Plugin version")
    priority: int = Field(100, description="Plugin execution priority")
    
    # Allow extra fields for plugin-specific configuration
    # (inherited from BaseUnifiedModel Config)
    
    def validate_plugin_specific(self) -> None:
        """Override this method to add plugin-specific validation."""
        pass
    
    def get_plugin_type(self) -> str:
        """Get the plugin type based on class name.
        
        Returns:
            Plugin type string
        """
        class_name = self.__class__.__name__
        if class_name.endswith('Config'):
            return class_name[:-6].lower()
        return class_name.lower()
    
    def to_dict(self, **kwargs) -> Dict[str, Any]:
        """Convert to dictionary with plugin-specific handling.
        
        Returns:
            Dictionary representation
        """
        data = super().to_dict(**kwargs)
        # Include extra fields but exclude Pydantic internals
        excluded_keys = {'omega_config', 'model_fields', 'model_config', 'model_fields_set', '__dict__', '__weakref__'}
        for key in self.__dict__:
            if (key not in data and 
                not key.startswith('_') and 
                key not in excluded_keys and
                not hasattr(getattr(self, key), '__func__')):  # Exclude methods
                try:
                    value = getattr(self, key)
                    # Only include serializable values
                    if value is not None:
                        data[key] = value
                except AttributeError:
                    pass
        return data


class ExecutionEnvironmentPluginConfig(BasePluginConfig):
    """Base configuration for execution environment plugins."""
    
    # Common fields for execution environments
    output_format: str = Field("json", description="Output format for results")
    collect_metrics: bool = Field(True, description="Whether to collect metrics")
    
    def get_plugin_type(self) -> str:
        """Return execution environment plugin type."""
        return "execution_environment"


class NetworkEnvironmentPluginConfig(BasePluginConfig):
    """Base configuration for network environment plugins."""
    
    # Common fields for network environments
    network_name: str = Field("panther_network", description="Network name")
    subnet: Optional[str] = Field(None, description="Network subnet")
    enable_ipv6: bool = Field(False, description="Enable IPv6 support")
    
    def get_plugin_type(self) -> str:
        """Return network environment plugin type."""
        return "network_environment"


class ServicePluginConfig(BasePluginConfig):
    """Base configuration for service plugins (IUT and testers)."""
    
    # Common fields for services
    docker_image: Optional[str] = Field(None, description="Docker image name")
    build_from_source: bool = Field(True, description="Build from source")
    source_repository: Optional[str] = Field(None, description="Source repository URL")
    
    def get_plugin_type(self) -> str:
        """Return service plugin type."""
        return "service"


class ProtocolPluginConfig(BasePluginConfig):
    """Base configuration for protocol plugins."""
    
    # Common fields for protocols
    protocol_version: str = Field(..., description="Protocol version")
    default_port: int = Field(..., description="Default port number")
    supports_tls: bool = Field(True, description="Whether protocol supports TLS")
    
    def get_plugin_type(self) -> str:
        """Return protocol plugin type."""
        return "protocol"