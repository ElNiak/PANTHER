"""Service configuration models."""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from pydantic import Field, field_validator, model_validator

from .base_model import BaseUnifiedModel


class Parameter(BaseModel):
    """Configuration parameter."""
    
    value: Optional[str] = None
    description: Optional[str] = None


class VersionBase(BaseModel):
    """Base version configuration."""
    
    version: str
    commit: str
    dependencies: List[Dict[str, str]]


class ImplementationType(str, Enum):
    """Implementation type enumeration."""
    
    IUT = "iut"
    TESTERS = "testers"


class ProtocolRole(str, Enum):
    """Protocol role enumeration."""
    
    SERVER = "server"
    CLIENT = "client"
    PEER = "peer"


class NetworkConfig(BaseUnifiedModel):
    """Network configuration for services."""
    
    interface: str = Field("eth0", description="Network interface")
    port: int = Field(4443, description="Network port")
    host: str = Field("localhost", description="Host address")
    bind_address: Optional[str] = Field(None, description="Bind address")
    mtu: Optional[int] = Field(None, description="Maximum transmission unit")


class ProtocolConfig(BaseUnifiedModel):
    """Protocol configuration."""
    
    name: str = Field(..., description="Protocol name (e.g., quic, http)")
    version: Optional[str] = Field(None, description="Protocol version")
    role: ProtocolRole = Field(..., description="Protocol role")
    target: Optional[str] = Field(None, description="Target service name (for clients)")
    
    # Allow extra fields for protocol-specific parameters
    
    @field_validator('role', mode='before')
    @classmethod
    def validate_role(cls, v):
        """Convert string to ProtocolRole enum."""
        if isinstance(v, str):
            return ProtocolRole(v.lower())
        return v
    
    @model_validator(mode='before')
    @classmethod
    def validate_target(cls, values):
        """Validate target is set for clients."""
        if isinstance(values, dict):
            role = values.get('role')
            target = values.get('target')
            if role == ProtocolRole.CLIENT and not target:
                raise ValueError("Client services must specify a target")
        return values
    
    def get_default_port(self) -> int:
        """Get default port for protocol.
        
        Returns:
            Default port number
        """
        default_ports = {
            "quic": 4443,
            "http": 80,
            "https": 443,
            "minip": 8080,
        }
        return default_ports.get(self.name.lower(), 8080)
    
    def requires_server_port(self) -> bool:
        """Check if protocol requires server port.
        
        Returns:
            True if protocol requires server port
        """
        return self.role == ProtocolRole.SERVER
    
    def get_default_port_mapping(self) -> Optional[str]:
        """Get default port mapping string.
        
        Returns:
            Default port mapping in format "host:container"
        """
        port = self.get_default_port()
        return f"{port}:{port}"


class ImplementationConfig(BaseUnifiedModel):
    """Implementation configuration."""
    
    name: str = Field(..., description="Implementation name")
    type: ImplementationType = Field(..., description="Implementation type")
    version: Optional[str] = Field(None, description="Implementation version")
    shadow_compatible: bool = Field(False, description="Compatible with Shadow simulator")
    gperf_compatible: bool = Field(False, description="Compatible with gperf profiling")
    
    # Allow extra fields for implementation-specific parameters
    # For example, panther_ivy might have a 'test' field
    
    @field_validator('type', mode='before')
    @classmethod
    def validate_type(cls, v):
        """Convert string to ImplementationType enum."""
        if isinstance(v, str):
            return ImplementationType(v.lower())
        return v
    
    def __init__(self, **data):
        """Initialize with support for extra fields."""
        # Extract known fields
        known_fields = {'name', 'type', 'version'}
        base_data = {k: v for k, v in data.items() if k in known_fields}
        extra_data = {k: v for k, v in data.items() if k not in known_fields}
        
        # Initialize base model
        super().__init__(**base_data)
        
        # Add extra fields as attributes
        for key, value in extra_data.items():
            setattr(self, key, value)


class ServiceConfig(BaseUnifiedModel):
    """Service configuration."""
    
    implementation: ImplementationConfig = Field(..., description="Implementation configuration")
    protocol: ProtocolConfig = Field(..., description="Protocol configuration")
    network: Optional[NetworkConfig] = Field(None, description="Network configuration")
    environment: Dict[str, str] = Field(default_factory=dict, description="Environment variables")
    timeout: int = Field(60, description="Service timeout in seconds")
    ports: List[str] = Field(default_factory=list, description="Port mappings (host:container)")
    volumes: List[str] = Field(default_factory=list, description="Volume mounts")
    generate_new_certificates: bool = Field(False, description="Generate new certificates")
    command_override: Optional[str] = Field(None, description="Override service command")
    working_directory: Optional[str] = Field(None, description="Working directory")
    depends_on: List[str] = Field(default_factory=list, description="Service dependencies")
    restart_policy: str = Field("no", description="Restart policy")
    
    # Allow extra fields for service-specific parameters
    
    @field_validator('timeout')
    @classmethod
    def validate_timeout(cls, v):
        """Validate timeout is positive."""
        if v <= 0:
            raise ValueError("Timeout must be positive")
        return v
    
    @field_validator('ports')
    @classmethod
    def validate_ports(cls, v):
        """Validate port mappings format."""
        for port_mapping in v:
            if ':' not in port_mapping:
                raise ValueError(f"Invalid port mapping format: {port_mapping}")
            
            parts = port_mapping.split(':')
            if len(parts) != 2:
                raise ValueError(f"Port mapping must be host:container format: {port_mapping}")
            
            try:
                host_port = int(parts[0])
                container_port = int(parts[1])
                
                if not (1 <= host_port <= 65535):
                    raise ValueError(f"Invalid host port: {host_port}")
                if not (1 <= container_port <= 65535):
                    raise ValueError(f"Invalid container port: {container_port}")
            except ValueError as e:
                raise ValueError(f"Invalid port numbers in {port_mapping}: {e}")
        
        return v
    
    def get_host_port(self) -> Optional[int]:
        """Get the first host port mapping.
        
        Returns:
            Host port number or None
        """
        if self.ports:
            return int(self.ports[0].split(':')[0])
        return None
    
    def get_container_port(self) -> Optional[int]:
        """Get the first container port mapping.
        
        Returns:
            Container port number or None
        """
        if self.ports:
            return int(self.ports[0].split(':')[1])
        return None
    
    def add_port_mapping(self, host_port: int, container_port: int) -> None:
        """Add a port mapping.
        
        Args:
            host_port: Host port number
            container_port: Container port number
        """
        self.ports.append(f"{host_port}:{container_port}")
    
    def get_service_name(self) -> str:
        """Get service name for Docker/containers.
        
        Returns:
            Service name
        """
        return f"{self.implementation.name}_{self.protocol.role.value}"
    
    def to_docker_service(self) -> Dict[str, Any]:
        """Convert to Docker Compose service format.
        
        Returns:
            Docker Compose service dictionary
        """
        service = {
            "image": f"panther/{self.implementation.name}:latest",
            "environment": self.environment.copy(),
            "restart": self.restart_policy,
        }
        
        if self.ports:
            service["ports"] = self.ports
        
        if self.volumes:
            service["volumes"] = self.volumes
        
        if self.command_override:
            service["command"] = self.command_override
        
        if self.working_directory:
            service["working_dir"] = self.working_directory
        
        if self.depends_on:
            service["depends_on"] = self.depends_on
        
        return service
    
    def ensure_server_has_ports(self) -> None:
        """Ensure that server services have at least one port assigned."""
        if not self.ports and self.protocol and self.protocol.requires_server_port():
            default_port_mapping = self.protocol.get_default_port_mapping()
            if default_port_mapping:
                self.ports = [default_port_mapping]
    
    def get_protocol_default_port(self) -> Optional[str]:
        """Get default port mapping from the protocol configuration."""
        if self.protocol:
            return self.protocol.get_default_port_mapping()
        return None