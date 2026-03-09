"""Service configuration models."""

from enum import Enum
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from ..base import BaseConfig
from ..validators import implementation_type_validator, protocol_role_validator
from .global_config import ServiceDockerOverrideConfig


class Parameter(BaseModel):
    """Configuration parameter."""

    value: Optional[str] = None
    description: Optional[str] = None


class VersionBase(BaseModel):
    """Base version configuration."""

    version: str = ""
    commit: str = ""
    dependencies: List[Dict[str, str]] = Field(default_factory=list)


class ImplementationType(str, Enum):
    """Implementation type enumeration."""

    IUT = "iut"
    TESTERS = "testers"


class ProtocolRole(str, Enum):
    """Protocol role enumeration."""

    SERVER = "server"
    CLIENT = "client"
    PEER = "peer"


class NetworkConfig(BaseConfig):
    """Network configuration for services."""

    interface: str = Field("eth0", description="Network interface")
    port: int = Field(4443, description="Network port")
    host: str = Field("localhost", description="Host address")
    bind_address: Optional[str] = Field(None, description="Bind address")
    mtu: Optional[int] = Field(None, description="Maximum transmission unit")

    @field_validator("port", mode="before")
    @classmethod
    def validate_port(cls, v):
        """Convert string/float to integer for port."""
        from ..components.field_coercion import validate_integer_field

        return validate_integer_field(v, "port")

    @field_validator("mtu", mode="before")
    @classmethod
    def validate_mtu(cls, v):
        """Convert string/float to integer for MTU."""
        if v is None:
            return v
        from ..components.field_coercion import validate_integer_field

        return validate_integer_field(v, "mtu")


class ProtocolConfig(BaseConfig):
    ## TODO check which verson is used in the protocol config
    """Protocol configuration."""

    name: str = Field(..., description="Protocol name (e.g., quic, http)")
    version: Optional[str] = Field(None, description="Protocol version")
    role: ProtocolRole = Field(..., description="Protocol role")
    target: Optional[str] = Field(None, description="Target service name (for clients)")

    # Allow extra fields for protocol-specific parameters

    @field_validator("role", mode="before")
    @classmethod
    def validate_role(cls, v):
        """Convert string to ProtocolRole enum."""
        return protocol_role_validator(cls, v)

    @model_validator(mode="before")
    @classmethod
    def validate_target(cls, values):
        """Validate target is set for clients."""
        if isinstance(values, dict):
            role = values.get("role")
            target = values.get("target")
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


class ImplementationConfig(BaseConfig):
    """Implementation configuration."""

    name: str = Field(..., description="Implementation name")
    type: ImplementationType = Field(..., description="Implementation type")
    version: Optional[str] = Field(None, description="Implementation version")
    version_config: Optional[Dict[str, Any]] = Field(
        None, description="Version configuration object with parameters"
    )
    shadow_compatible: bool = Field(
        False, description="Compatible with Shadow simulator"
    )
    gperf_compatible: bool = Field(False, description="Compatible with gperf profiling")

    # Allow extra fields for implementation-specific parameters
    # For example, panther_ivy might have a 'test' field

    @field_validator("type", mode="before")
    @classmethod
    def validate_type(cls, v):
        """Convert string to ImplementationType enum."""
        return implementation_type_validator(cls, v)

    # extra="allow" inherited from BaseConfig handles plugin-specific fields


class ServiceConfig(BaseConfig):
    """Service configuration."""

    VERSION_CLASS: ClassVar[Optional[type]] = None

    implementation: ImplementationConfig = Field(
        ..., description="Implementation configuration"
    )
    protocol: ProtocolConfig = Field(..., description="Protocol configuration")
    network: Optional[NetworkConfig] = Field(None, description="Network configuration")
    environment: Dict[str, str] = Field(
        default_factory=dict, description="Environment variables"
    )
    timeout: int = Field(60, description="Service timeout in seconds")
    ports: List[str] = Field(
        default_factory=list, description="Port mappings (host:container)"
    )
    volumes: List[str] = Field(default_factory=list, description="Volume mounts")
    generate_new_certificates: bool = Field(
        False, description="Generate new certificates"
    )
    command_override: Optional[str] = Field(
        None, description="Override service command"
    )
    working_directory: Optional[str] = Field(None, description="Working directory")
    depends_on: List[str] = Field(
        default_factory=list, description="Service dependencies"
    )
    restart_policy: str = Field("no", description="Restart policy")

    docker: Optional[ServiceDockerOverrideConfig] = Field(
        None,
        description="Per-service Docker build overrides (inherits from global if absent)",
    )

    # Service build/docker fields
    docker_image: Optional[str] = Field(None, description="Docker image name")
    build_from_source: bool = Field(True, description="Build from source")
    source_repository: Optional[str] = Field(None, description="Source repository URL")

    # Allow extra fields for service-specific parameters

    @classmethod
    def load_version(
        cls,
        version_configs_dir: Optional[str] = None,
        version: Optional[str] = None,
        protocol_version_override: Optional[str] = None,
    ):
        """Generic version loading using VERSION_CLASS.

        Subclasses set ``VERSION_CLASS`` to their VersionBase subclass.
        Default ``version_configs_dir`` is ``version_configs/`` next to the
        subclass's ``config_schema.py``.

        Args:
            version_configs_dir: Directory containing version YAML files.
            version: Specific version to load (e.g. ``'rfc9000'``).
            protocol_version_override: Protocol version from experiment config.

        Returns:
            VERSION_CLASS instance, or ``None`` if VERSION_CLASS is not set.
        """
        import logging
        import os
        from pathlib import Path

        if cls.VERSION_CLASS is None:
            return None

        import yaml

        from ..utils.merge import deep_merge

        # Determine directory
        if version_configs_dir is None:
            import inspect

            src_file = inspect.getfile(cls)
            version_configs_dir = str(
                Path(os.path.dirname(src_file)) / "version_configs"
            )

        effective_version = protocol_version_override or version

        if effective_version:
            version_path = os.path.join(
                version_configs_dir, f"{effective_version}.yaml"
            )
            if not os.path.exists(version_path):
                raise FileNotFoundError(
                    f"Version config file not found: {version_path}"
                )
            with open(version_path) as f:
                raw_dict = yaml.safe_load(f) or {}
        else:
            # Load first YAML found (sorted for determinism)
            if not os.path.exists(version_configs_dir):
                logging.warning(
                    "Version configs directory %s not found, using defaults",
                    version_configs_dir,
                )
                return cls.VERSION_CLASS()
            version_files = sorted(
                f for f in os.listdir(version_configs_dir) if f.endswith(".yaml")
            )
            if not version_files:
                logging.warning(
                    "No version files found in %s, using defaults",
                    version_configs_dir,
                )
                return cls.VERSION_CLASS()
            version_path = os.path.join(version_configs_dir, version_files[0])
            with open(version_path) as f:
                raw_dict = yaml.safe_load(f) or {}

        # Merge with defaults using pure dict merge
        default_dict = cls.VERSION_CLASS().model_dump()
        merged = deep_merge(default_dict, raw_dict)
        return cls.VERSION_CLASS(**merged)

    @classmethod
    def create_with_protocol_context(cls, protocol=None):
        """Create config instance with optional protocol context.

        If ``VERSION_CLASS`` is set and *protocol* carries a version, the
        matching version config is loaded automatically.

        Args:
            protocol: Optional protocol configuration for context-aware creation

        Returns:
            Configuration instance
        """
        if (
            cls.VERSION_CLASS is not None
            and protocol
            and getattr(protocol, "version", None)
        ):
            try:
                version_config = cls.load_version(
                    protocol_version_override=protocol.version
                )
                return cls(version=version_config)
            except (FileNotFoundError, ValueError) as e:
                raise ValueError(
                    f"Could not load protocol version {protocol.version}: {e}"
                ) from e
        return cls()

    @field_validator("timeout", mode="before")
    @classmethod
    def validate_timeout(cls, v):
        """Convert string/float to integer and validate timeout is positive."""
        from ..components.field_coercion import validate_integer_field

        # First convert to integer
        timeout_val = validate_integer_field(v, "timeout")
        # Then validate it's positive
        if timeout_val <= 0:
            raise ValueError("Timeout must be positive")
        return timeout_val

    @field_validator("ports")
    @classmethod
    def validate_ports(cls, v):
        """Validate port mappings format with flexible type conversion."""
        for port_mapping in v:
            if ":" not in port_mapping:
                raise ValueError(f"Invalid port mapping format: {port_mapping}")

            parts = port_mapping.split(":")
            if len(parts) != 2:
                raise ValueError(
                    f"Port mapping must be host:container format: {port_mapping}"
                )

            try:
                # Use universal validator to handle decimal strings
                from ..components.field_coercion import validate_integer_field

                host_port = validate_integer_field(
                    parts[0], f"host_port in {port_mapping}"
                )
                container_port = validate_integer_field(
                    parts[1], f"container_port in {port_mapping}"
                )

                if not (1 <= host_port <= 65535):
                    raise ValueError(f"Invalid host port: {host_port}")
                if not (1 <= container_port <= 65535):
                    raise ValueError(f"Invalid container port: {container_port}")
            except ValueError as e:
                raise ValueError(f"Invalid port numbers in {port_mapping}: {e}") from e

        return v

    def get_host_port(self) -> Optional[int]:
        """Get the first host port mapping.

        Returns:
            Host port number or None
        """
        return int(self.ports[0].split(":")[0]) if self.ports else None

    def get_container_port(self) -> Optional[int]:
        """Get the first container port mapping.

        Returns:
            Container port number or None
        """
        return int(self.ports[0].split(":")[1]) if self.ports else None

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
            if default_port_mapping := self.protocol.get_default_port_mapping():
                self.ports = [default_port_mapping]

    def get_protocol_default_port(self) -> Optional[str]:
        """Get default port mapping from the protocol configuration."""
        return self.protocol.get_default_port_mapping() if self.protocol else None
