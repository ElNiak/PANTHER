"""Data models for network-aware command resolution.

This module provides Pydantic models for handling network parameter
resolution in the placeholder system.
"""

import re
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class NetworkAttribute(str, Enum):
    """Network attributes that can be resolved for services."""

    IP = "ip"
    HOSTNAME = "hostname"
    PORT = "port"
    SERVICE_NAME = "service_name"


class NetworkFormat(str, Enum):
    """Network format types for attribute resolution."""

    DECIMAL = "decimal"
    DOTTED = "dotted"
    HEX = "hex"
    HOSTNAME = "hostname"
    STRING = "string"
    INTEGER = "integer"


class PlaceholderInfo(BaseModel):
    """Information parsed from a network placeholder."""

    service: str = Field(..., description="Target service name")
    attribute: NetworkAttribute = Field(..., description="Network attribute to resolve")
    format_type: NetworkFormat = Field(
        default=NetworkFormat.STRING, description="Format for the resolved value"
    )
    raw_placeholder: str = Field(..., description="Original placeholder string")

    @field_validator("service")
    @classmethod
    def validate_service_name(cls, v: str) -> str:
        """Validate service name format."""
        if not v or not v.strip():
            raise ValueError("Service name cannot be empty")
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9_-]*$", v):
            raise ValueError(
                "Service name must start with letter and contain only "
                "letters, numbers, underscores, and hyphens"
            )
        return v.strip()


class NetworkServiceInfo(BaseModel):
    """Network information for a service."""

    service_name: str = Field(..., description="Name of the service")
    ip_address: Optional[str] = Field(None, description="IP address of the service")
    hostname: Optional[str] = Field(None, description="Hostname of the service")
    port: Optional[int] = Field(None, description="Port number of the service")
    protocol_role: Optional[str] = Field(
        None, description="Role in protocol (client/server/tester)"
    )
    additional_info: Dict[str, str] = Field(
        default_factory=dict, description="Additional service-specific information"
    )

    @field_validator("ip_address")
    @classmethod
    def validate_ip_address(cls, v: Optional[str]) -> Optional[str]:
        """Validate IP address format."""
        if v is None:
            return v

        # Basic IPv4 validation
        if not re.match(r"^(\d{1,3}\.){3}\d{1,3}$", v):
            raise ValueError(f"Invalid IPv4 address format: {v}")

        # Check each octet is 0-255
        octets = v.split(".")
        for octet in octets:
            if not (0 <= int(octet) <= 255):
                raise ValueError(f"Invalid IP address octet: {octet}")

        return v

    @field_validator("port")
    @classmethod
    def validate_port(cls, v: Optional[int]) -> Optional[int]:
        """Validate port number range."""
        if v is not None and not (1 <= v <= 65535):
            raise ValueError(f"Port must be between 1 and 65535, got: {v}")
        return v


class NetworkResolutionResult(BaseModel):
    """Result of network placeholder resolution."""

    original_placeholder: str = Field(..., description="Original placeholder")
    resolved_value: str = Field(..., description="Resolved value")
    service_info: NetworkServiceInfo = Field(
        ..., description="Service information used"
    )
    resolution_method: str = Field(..., description="Method used for resolution")
    environment_type: str = Field(..., description="Network environment type")

    def to_substitution_pair(self) -> tuple[str, str]:
        """Return tuple for string substitution."""
        return (self.original_placeholder, self.resolved_value)


class NetworkResolutionContext(BaseModel):
    """Context for network resolution operations."""

    environment_type: str = Field(..., description="Type of network environment")
    available_services: Dict[str, NetworkServiceInfo] = Field(
        default_factory=dict, description="Available services for resolution"
    )
    resolution_config: Dict[str, str] = Field(
        default_factory=dict,
        description="Environment-specific resolution configuration",
    )
    default_format: NetworkFormat = Field(
        default=NetworkFormat.STRING, description="Default format for resolution"
    )

    def get_service_info(self, service_name: str) -> Optional[NetworkServiceInfo]:
        """Get service information by name."""
        return self.available_services.get(service_name)

    def add_service(self, service_info: NetworkServiceInfo) -> None:
        """Add service information to context."""
        self.available_services[service_info.service_name] = service_info

    def list_service_names(self) -> List[str]:
        """List all available service names."""
        return list(self.available_services.keys())
