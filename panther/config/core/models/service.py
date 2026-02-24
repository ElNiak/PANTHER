"""Service configuration models."""

import contextlib
import logging
from enum import Enum
from typing import Any, Dict, List, Optional, Type, TypeVar

from pydantic import BaseModel, Field, field_validator, model_validator

from ..validators import implementation_type_validator, protocol_role_validator
from .base_model import BaseUnifiedModel
from .global_config import ServiceDockerOverrideConfig
from .plugin import BasePluginConfig


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

    @field_validator("port", mode="before")
    @classmethod
    def validate_port(cls, v):
        """Convert string/float to integer for port."""
        from ..components.universal_validators import validate_integer_field

        return validate_integer_field(v, "port")

    @field_validator("mtu", mode="before")
    @classmethod
    def validate_mtu(cls, v):
        """Convert string/float to integer for MTU."""
        if v is None:
            return v
        from ..components.universal_validators import validate_integer_field

        return validate_integer_field(v, "mtu")


class ProtocolConfig(BaseUnifiedModel):
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


class ImplementationConfig(BaseUnifiedModel):
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

    def __init__(self, **data):
        """Initialize with support for extra fields."""
        # Extract known fields
        known_fields = {"name", "type", "version"}
        base_data = {k: v for k, v in data.items() if k in known_fields}
        extra_data = {k: v for k, v in data.items() if k not in known_fields}

        # Initialize base model
        super().__init__(**base_data)

        # Add extra fields as attributes
        for key, value in extra_data.items():
            setattr(self, key, value)


T = TypeVar("T", bound=BasePluginConfig)


class ServiceConfig(BaseUnifiedModel):
    """Service configuration."""

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

    plugin_config: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Plugin-specific configuration"
    )

    def get_plugin_config(self, config_class: Type[T], validate: bool = True) -> T:
        """Get typed plugin configuration with defaults.

        This method creates an instance of the plugin config class, using values
        from plugin_config where available and defaults from the class where not.

        For nested Pydantic models, it handles type conversion intelligently.

        Args:
            config_class: The plugin configuration class
            validate: Whether to validate using PluginConfigResolver (if available)

        Returns:
            Typed plugin configuration instance
        """
        # For plugin configs that have complex nested defaults, we need to be careful
        # Handle special cases where we need to pass protocol context
        default_instance = config_class()
        # Use protocol-aware factory method if available
        if hasattr(config_class, "create_with_protocol_context"):
            logging.debug(
                "Using protocol-aware factory method for plugin config: %s",
                config_class.__name__,
            )
            default_instance = config_class.create_with_protocol_context(
                self.protocol if hasattr(self, "protocol") else None
            )
        else:
            logging.debug(
                "Using standard instantiation for plugin config: %s",
                config_class.__name__,
            )
            # Fallback to standard instantiation
            default_instance = config_class()

        # Get default values (handle both Pydantic v1 and v2)
        try:
            default_dict = default_instance.model_dump()
        except AttributeError:
            default_dict = default_instance.dict()

        # Deep merge plugin_config values over defaults with type awareness
        merged_config = self._deep_merge_with_type_conversion(
            default_dict, self.plugin_config, config_class
        )

        # Create final instance with merged values
        instance = config_class(**merged_config)

        # Optional validation with PluginConfigResolver
        if validate and self.implementation:
            try:
                from panther.plugins.core.plugin_config_resolver import (
                    get_plugin_config_resolver,
                )

                resolver = get_plugin_config_resolver()

                # Try to find the expected config class
                # Handle both enum and string types for implementation.type
                service_type = (
                    self.implementation.type.value
                    if isinstance(self.implementation.type, ImplementationType)
                    else self.implementation.type
                ).lower()

                expected_class = resolver.resolve_service_config_class(
                    service_type=service_type,
                    protocol=self.protocol.name if self.protocol else "",
                    name=self.implementation.name,
                )

                if expected_class and expected_class != config_class:
                    # Log warning but don't fail
                    logging.warning(
                        f"Plugin config class mismatch: expected {expected_class.__name__}, "
                        f"got {config_class.__name__}"
                    )
            except Exception as e:
                # Validation is optional, so we just log and continue
                logging.debug(f"Could not validate plugin config with resolver: {e}")

        return instance

    def _deep_merge_configs(
        self, defaults: Dict[str, Any], overrides: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Deep merge configuration dictionaries, preserving structure.

        Args:
            defaults: Default configuration with full structure
            overrides: Override values that may have simplified structure

        Returns:
            Merged configuration
        """
        result = defaults.copy()

        for key, value in overrides.items():
            if key in result:
                if isinstance(result[key], dict) and isinstance(value, dict):
                    # Recursive merge for nested dicts
                    result[key] = self._deep_merge_configs(result[key], value)
                else:
                    # Direct override
                    result[key] = value
            else:
                # New key not in defaults
                result[key] = value

        return result

    def _deep_merge_with_type_conversion(
        self,
        defaults: Dict[str, Any],
        overrides: Dict[str, Any],
        config_class: Type[Any],
    ) -> Dict[str, Any]:
        """Deep merge with intelligent type conversion based on schema.

        This method inspects the Pydantic model's field types to determine
        how to convert simplified YAML values to the expected types.

        Args:
            defaults: Default configuration with full structure
            overrides: Override values that may have simplified structure
            config_class: The Pydantic model class for type information

        Returns:
            Merged configuration with proper types
        """
        result = defaults.copy()

        # Get field information from the Pydantic model
        try:
            # Pydantic v2
            fields = config_class.model_fields
        except AttributeError:
            # Pydantic v1
            fields = config_class.__fields__

        for key, value in overrides.items():
            if key in result:
                # Get field info to understand expected type
                field_info = fields.get(key) if fields else None

                if isinstance(result[key], dict) and not isinstance(value, dict):
                    # The default is a dict but override is a simple value
                    # Check if this is a Pydantic model field that expects a specific format
                    if field_info and self._is_pydantic_model_field(field_info):
                        # Keep the default structure, just update the relevant field
                        # For example, Parameter objects have 'value' and 'description'
                        if "value" in result[key]:
                            result[key]["value"] = str(value)
                    else:
                        # Simple override
                        result[key] = value
                elif isinstance(result[key], dict):
                    # Both are dicts - recursive merge
                    # Try to get the nested model class if this is a Pydantic field
                    nested_class = (
                        self._get_nested_model_class(field_info) if field_info else None
                    )
                    if nested_class:
                        result[key] = self._deep_merge_with_type_conversion(
                            result[key], value, nested_class
                        )
                    else:
                        result[key] = self._deep_merge_configs(result[key], value)
                else:
                    # Direct override
                    result[key] = value
            else:
                # New key not in defaults
                result[key] = value

        return result

    def _is_pydantic_model_field(self, field_info) -> bool:
        """Check if a field is a Pydantic model field.

        Args:
            field_info: Field information from Pydantic model

        Returns:
            True if the field is a Pydantic model
        """
        with contextlib.suppress(Exception):
            if field_type := getattr(field_info, "annotation", None) or getattr(
                field_info, "type_", None
            ):
                # Check if it's a Pydantic BaseModel subclass
                return isinstance(field_type, type) and issubclass(
                    field_type, BaseModel
                )
        return False

    def _get_nested_model_class(self, field_info) -> Optional[Type[Any]]:
        """Get the nested model class from field info.

        Args:
            field_info: Field information from Pydantic model

        Returns:
            Nested model class or None
        """
        with contextlib.suppress(Exception):
            field_type = getattr(field_info, "annotation", None) or getattr(
                field_info, "type_", None
            )
            if (
                field_type
                and isinstance(field_type, type)
                and issubclass(field_type, BaseModel)
            ):
                return field_type
        return None

    # Allow extra fields for service-specific parameters

    @field_validator("timeout", mode="before")
    @classmethod
    def validate_timeout(cls, v):
        """Convert string/float to integer and validate timeout is positive."""
        from ..components.universal_validators import validate_integer_field

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
                from ..components.universal_validators import validate_integer_field

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
