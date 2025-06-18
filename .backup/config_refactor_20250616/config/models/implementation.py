"""Implementation and protocol configuration models."""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import Field, validator

from panther.config.models.base import ConfigModel


class ImplementationType(str, Enum):
    """Types of implementations in the system."""

    IUT = "iut"  # Implementation Under Test
    TESTERS = "testers"  # Implementation used for testing


class ProtocolType(str, Enum):
    """Types of protocols supported."""

    CLIENT_SERVER = "client_server"
    PEER_TO_PEER = "peer_to_peer"


class ProtocolRole(str, Enum):
    """Roles in protocol communication."""

    SERVER = "server"
    CLIENT = "client"
    PEER = "peer"


class ProtocolModel(ConfigModel):
    """Protocol configuration with dynamic version support.
    
    Unlike the old system with hardcoded version enums, this model
    supports dynamic version loading from plugin configurations.
    """

    name: str = Field(..., description="Protocol name (e.g., quic, http, minip)")
    version: Optional[str] = Field(
        None, 
        description="Protocol version (e.g., rfc9000, draft29). Loaded dynamically from plugins."
    )
    role: ProtocolRole = Field(
        ProtocolRole.SERVER, 
        description="Role in the protocol communication"
    )
    target: Optional[str] = Field(
        None, 
        description="Target service name (required for clients)"
    )
    protocol_type: ProtocolType = Field(
        ProtocolType.CLIENT_SERVER,
        description="Type of protocol communication pattern"
    )
    
    # Additional protocol-specific parameters
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Protocol-specific parameters loaded from version configs"
    )

    @validator("target")
    def validate_target(cls, v, values):
        """Validate that clients have a target specified."""
        if values.get("role") == ProtocolRole.CLIENT and not v:
            raise ValueError("Client role requires a target service to be specified")
        if values.get("role") == ProtocolRole.SERVER and v:
            raise ValueError("Server role should not have a target specified")
        return v

    @validator("version")
    def validate_version_format(cls, v):
        """Basic version format validation."""
        if v and not v.replace("_", "").replace("-", "").replace(".", "").isalnum():
            raise ValueError(f"Invalid version format: {v}")
        return v

    def get_default_server_port(self) -> Optional[int]:
        """Get the default server port for this protocol.
        
        This should be overridden by protocol-specific configurations
        or loaded from version configs.
        """
        # Default ports for known protocols
        default_ports = {
            "quic": 4443,
            "http": 80,
            "https": 443,
            "minip": 5000,
        }
        return default_ports.get(self.name.lower())

    def requires_server_port(self) -> bool:
        """Check if this protocol configuration requires a server port."""
        return self.role == ProtocolRole.SERVER

    def get_default_port_mapping(self) -> Optional[str]:
        """Get default port mapping for this protocol configuration."""
        if self.requires_server_port():
            port = self.get_default_server_port()
            if port:
                return f"{port}:{port}"
        return None


class ImplementationModel(ConfigModel):
    """Implementation configuration model.
    
    Represents a specific implementation of a protocol, either as an
    Implementation Under Test (IUT) or a Tester.
    """

    name: str = Field(
        ..., 
        description="Implementation name (e.g., picoquic, aioquic, panther_ivy)"
    )
    type: ImplementationType = Field(
        ImplementationType.IUT,
        description="Type of implementation"
    )
    test: Optional[str] = Field(
        None,
        description="Test name for tester implementations (e.g., quic_client_test_max)"
    )
    shadow_compatible: bool = Field(
        False,
        description="Whether the implementation is compatible with Shadow NS"
    )
    gperf_compatible: bool = Field(
        False,
        description="Whether the implementation is compatible with gperf profiling"
    )
    
    # Version configuration path resolution
    version_config_path: Optional[str] = Field(
        None,
        description="Path to version-specific configuration file"
    )
    
    # Additional implementation-specific parameters
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Implementation-specific parameters"
    )

    @validator("test")
    def validate_test_requirement(cls, v, values):
        """Validate that testers have a test specified."""
        if values.get("type") == ImplementationType.TESTERS and not v:
            raise ValueError("Tester implementations require a test name to be specified")
        if values.get("type") == ImplementationType.IUT and v:
            raise ValueError("IUT implementations should not have a test specified")
        return v

    def get_version_config_path(self, protocol_name: str, protocol_version: str) -> str:
        """Get the path to version configuration file.
        
        For IUT: version_configs/{protocol_version}.yaml
        For testers: version_configs/{protocol_name}/{protocol_version}.yaml
        """
        if self.version_config_path:
            return self.version_config_path
            
        if self.type == ImplementationType.TESTERS:
            return f"version_configs/{protocol_name}/{protocol_version}.yaml"
        else:
            return f"version_configs/{protocol_version}.yaml"

    def is_compatible_with_protocol(self, protocol: ProtocolModel) -> bool:
        """Check if this implementation is compatible with the given protocol.
        
        This method can be extended to include more sophisticated
        compatibility checking based on version configs.
        """
        # Basic compatibility - can be enhanced with version-specific rules
        return True


class ProtocolImplementationCompatibility(ConfigModel):
    """Model for validating protocol-implementation compatibility."""
    
    protocol: ProtocolModel
    implementation: ImplementationModel
    
    @validator("implementation")
    def validate_compatibility(cls, v, values):
        """Validate that the implementation is compatible with the protocol."""
        protocol = values.get("protocol")
        if protocol and not v.is_compatible_with_protocol(protocol):
            raise ValueError(
                f"Implementation {v.name} is not compatible with protocol "
                f"{protocol.name} version {protocol.version}"
            )
        return v