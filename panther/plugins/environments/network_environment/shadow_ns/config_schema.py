from typing import List, Optional, Union

from pydantic import BaseModel, Field, validator

from panther.config.core.models.plugin import NetworkEnvironmentPluginConfig
from panther.config.core.validators import shadow_time_validator


class GeneralConfig(BaseModel):
    """General configuration for Shadow NS."""

    stop_time: str = Field(
        default="300s",
        description="The total simulation time in seconds -> use experiment duration",
    )

    @validator("stop_time", pre=True)
    def validate_stop_time(cls, v) -> str:
        """Convert integer seconds to string format with 's' suffix."""
        return shadow_time_validator(cls, v)

    unblocked_syscall_latency: bool = Field(
        default=False, description="Add latency for unblocked system calls"
    )


class ExperimentalConfig(BaseModel):
    """Experimental features configuration."""

    strace_logging_mode: str = Field(
        default="standard", description="Options: 'none', 'standard', 'detailed'"
    )


class NetworkNodeConfig(BaseModel):
    """Network node configuration."""

    id: int = Field(..., description="ID of the network node")
    bandwidth_down: str = Field(default="100 Gbit", description="Download bandwidth")
    bandwidth_up: str = Field(default="100 Gbit", description="Upload bandwidth")


class NetworkEdgeConfig(BaseModel):
    """Network edge configuration."""

    source: int = Field(..., description="Source node ID for the edge")
    target: int = Field(..., description="Target node ID for the edge")
    latency: int = Field(default=10, description="Latency of the edge in milliseconds")
    jitter: int = Field(default=10, description="Jitter of the edge in milliseconds")
    packet_loss: float = Field(default=0.0, description="Packet loss rate")


class NetworkGraphConfig(BaseModel):
    """Network graph configuration."""

    type: str = Field(default="gml", description="Options: '1_gbit_switch', 'gml'")
    nodes: List[NetworkNodeConfig] = Field(
        default_factory=list, description="List of network nodes"
    )
    edges: List[NetworkEdgeConfig] = Field(
        default_factory=list, description="List of network edges"
    )


class NetworkConfig(BaseModel):
    """Network configuration."""

    # TODO: Add support for multiple network nodes
    latency: int = Field(
        default=10, description="Latency of the network in milliseconds"
    )
    jitter: int = Field(default=10, description="Jitter of the network in milliseconds")
    packet_loss: float = Field(default=0.0, description="Packet loss rate")
    # graph: NetworkGraphConfig = Field(default_factory=NetworkGraphConfig)


class HostOptionDefaultsConfig(BaseModel):
    """Host option defaults configuration."""

    pcap_enabled: bool = Field(
        default=True, description="Enable PCAP capture for all hosts"
    )


class HostConfig(BaseModel):
    """Host configuration."""

    network_node_id: int = Field(default=0, description="Network node ID")
    ip_addr: str = Field(default="11.0.0.1", description="IP address")
    start_time: str = Field(default="1s", description="Start time of the process")


class HostsConfig(BaseModel):
    """Hosts configuration."""

    server: HostConfig = Field(
        default_factory=HostConfig, description="Server configuration"
    )
    client: HostConfig = Field(
        default_factory=lambda: HostConfig(ip_addr="11.0.0.2", start_time="5s"),
        description="Client configuration",
    )


class ShadowNSConfig(NetworkEnvironmentPluginConfig):
    """Configuration for Shadow NS network environment."""

    type: str = Field(default="shadow_ns", description="Network environment type")
    incompatibility: List[str] = Field(
        default_factory=lambda: ["strace", "gperf"],
        description="Incompatibilities with execution environments",
    )
    general: GeneralConfig = Field(
        default_factory=GeneralConfig, description="General configuration"
    )
    experimental: ExperimentalConfig = Field(
        default_factory=ExperimentalConfig, description="Experimental features"
    )
    network: NetworkConfig = Field(
        default_factory=NetworkConfig, description="Network configuration"
    )
    host_option_defaults: HostOptionDefaultsConfig = Field(
        default_factory=HostOptionDefaultsConfig, description="Default host options"
    )
    hosts: HostsConfig = Field(
        default_factory=HostsConfig, description="Hosts configuration"
    )
