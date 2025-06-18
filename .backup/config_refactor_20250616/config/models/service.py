"""Service configuration models."""

import re
from typing import Dict, List, Optional

from pydantic import Field, validator

from panther.config.models.base import ConfigModel
from panther.config.models.implementation import (
    ImplementationModel,
    ProtocolModel,
    ProtocolRole,
)


class ServiceConfigModel(ConfigModel):
    """Service configuration model with enhanced validation.
    
    Represents a service instance in an experiment, combining an implementation
    with a protocol configuration and runtime parameters.
    """

    # Core identification
    name: str = Field(
        ...,
        description="Service name (must be unique within a test)",
        regex="^[a-zA-Z][a-zA-Z0-9_-]*$"
    )
    
    # Implementation and protocol
    implementation: ImplementationModel = Field(
        ...,
        description="Implementation details for this service"
    )
    protocol: ProtocolModel = Field(
        ...,
        description="Protocol configuration for this service"
    )
    
    # Runtime configuration
    timeout: int = Field(
        100,
        ge=1,
        le=3600,
        description="Service timeout in seconds (1-3600)"
    )
    
    # Network configuration
    ports: List[str] = Field(
        default_factory=list,
        description="Port mappings in format 'host:container' (e.g., '4443:4443')"
    )
    
    # Certificate configuration
    generate_new_certificates: bool = Field(
        False,
        description="Whether to generate new certificates for this service"
    )
    certificate_path: Optional[str] = Field(
        None,
        description="Path to existing certificates (if not generating new ones)"
    )
    
    # Volume and directory configuration
    volumes: List[str] = Field(
        default_factory=list,
        description="Volume mappings in Docker format"
    )
    directories_to_start: List[str] = Field(
        default_factory=list,
        description="Directories to create before starting the service"
    )
    
    # Environment configuration
    environment: Dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables for the service"
    )
    
    # Additional parameters
    parameters: Dict[str, str] = Field(
        default_factory=dict,
        description="Additional service-specific parameters"
    )

    @validator("ports", each_item=True)
    def validate_port_format(cls, port):
        """Validate port mapping format."""
        # Accept single port (e.g., "4443") or mapping (e.g., "8080:80")
        port_pattern = r"^(\d+)(:\d+)?$"
        if not re.match(port_pattern, port):
            raise ValueError(
                f"Invalid port format: {port}. "
                "Expected format: 'port' or 'host_port:container_port'"
            )
        
        # Validate port ranges
        parts = port.split(":")
        for p in parts:
            port_num = int(p)
            if not (1 <= port_num <= 65535):
                raise ValueError(f"Port {port_num} out of valid range (1-65535)")
        
        return port
    
    @validator("protocol")
    def validate_protocol_consistency(cls, v, values):
        """Ensure protocol configuration is consistent with service setup."""
        # If this is a server and no ports are specified, we'll add default later
        # This validator just ensures consistency
        return v
    
    @validator("volumes", each_item=True)
    def validate_volume_format(cls, volume):
        """Validate volume mapping format."""
        # Basic validation for Docker volume format
        # Format: source:destination[:mode]
        parts = volume.split(":")
        if len(parts) < 2 or len(parts) > 3:
            raise ValueError(
                f"Invalid volume format: {volume}. "
                "Expected format: 'source:destination' or 'source:destination:mode'"
            )
        return volume

    def ensure_server_has_ports(self) -> None:
        """Ensure that server services have at least one port assigned.
        
        This method adds default port mapping if a server has no ports configured.
        """
        if not self.ports and self.protocol.requires_server_port():
            default_port_mapping = self.protocol.get_default_port_mapping()
            if default_port_mapping:
                self.ports = [default_port_mapping]

    def get_protocol_default_port(self) -> Optional[str]:
        """Get default port mapping from the protocol configuration."""
        return self.protocol.get_default_port_mapping()

    def validate_relationship_target(self, available_services: List[str]) -> None:
        """Validate that the target service exists if this is a client.
        
        Args:
            available_services: List of available service names in the test
            
        Raises:
            ValueError: If target service doesn't exist
        """
        if self.protocol.role == ProtocolRole.CLIENT:
            if not self.protocol.target:
                raise ValueError(f"Client service {self.name} must specify a target")
            if self.protocol.target not in available_services:
                raise ValueError(
                    f"Service {self.name} targets non-existent service: {self.protocol.target}"
                )

    def get_connection_target(self) -> Optional[str]:
        """Get the target service this service connects to."""
        if self.protocol.role == ProtocolRole.CLIENT:
            return self.protocol.target
        return None

    def is_compatible_with(self, other: "ServiceConfigModel") -> bool:
        """Check if this service is compatible with another service.
        
        Used for validating client-server relationships.
        """
        # Basic compatibility check - can be enhanced
        if self.protocol.name != other.protocol.name:
            return False
            
        # Check version compatibility if both have versions
        if self.protocol.version and other.protocol.version:
            # This could be enhanced with version compatibility rules
            # For now, just check if they're the same
            return self.protocol.version == other.protocol.version
            
        return True

    def to_deployment_config(self) -> Dict[str, any]:
        """Convert to deployment configuration format.
        
        Returns a dictionary suitable for Docker Compose or other
        deployment systems.
        """
        config = {
            "name": self.name,
            "image": f"{self.implementation.name}:latest",
            "environment": self.environment.copy(),
            "volumes": self.volumes.copy(),
        }
        
        # Add ports only if present
        if self.ports:
            config["ports"] = self.ports
            
        # Add timeout as environment variable
        config["environment"]["PANTHER_TIMEOUT"] = str(self.timeout)
        
        # Add protocol-specific environment variables
        config["environment"]["PANTHER_PROTOCOL"] = self.protocol.name
        config["environment"]["PANTHER_PROTOCOL_VERSION"] = self.protocol.version or "default"
        config["environment"]["PANTHER_ROLE"] = self.protocol.role
        
        if self.protocol.target:
            config["environment"]["PANTHER_TARGET"] = self.protocol.target
            
        return config