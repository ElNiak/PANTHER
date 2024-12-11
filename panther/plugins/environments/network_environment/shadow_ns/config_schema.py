from dataclasses import dataclass, field
from typing import List, Optional

from panther.config.config_experiment_schema import NetworkEnvironmentConfig


@dataclass
class GeneralConfig:
    stop_time: str = "300s"  # The total simulation time in seconds -> use experiment duration
    model_unblocked_syscall_latency: bool = False  # Add latency for unblocked system calls


@dataclass
class ExperimentalConfig:
    strace_logging_mode: str = "standard"  # Options: 'none', 'standard', 'detailed'


@dataclass
class NetworkNodeConfig:
    id: int  # ID of the network node
    bandwidth_down: str = "100 Gbit"  # Download bandwidth
    bandwidth_up: str = "100 Gbit"  # Upload bandwidth


@dataclass
class NetworkEdgeConfig:
    source: int  # Source node ID for the edge
    target: int  # Target node ID for the edge
    latency: int = 10  # Latency of the edge in milliseconds
    jitter: int = 10  # Jitter of the edge in milliseconds
    packet_loss: float = 0.0  # Packet loss rate


@dataclass
class NetworkGraphConfig:
    type: str = "gml"  # Options: '1_gbit_switch', 'gml'
    nodes: List[NetworkNodeConfig] = field(default_factory=list)
    edges: List[NetworkEdgeConfig] = field(default_factory=list)


@dataclass
class NetworkConfig:
    # TODO: Add support for multiple network nodes
    latency: int = 10  # Latency of the network in milliseconds
    jitter: int = 10  # Jitter of the network in milliseconds
    packet_loss: float = 0.0  # Packet loss rate
    # graph: NetworkGraphConfig = field(default_factory=NetworkGraphConfig)


@dataclass
class HostOptionDefaultsConfig:
    pcap_enabled: bool = True  # Enable PCAP capture for all hosts


@dataclass
class HostConfig:
    network_node_id: int = 0  # Network node ID
    ip_addr: str = "11.0.0.1"  # IP address
    start_time: str = "1s"  # Start time of the process


@dataclass
class HostsConfig:
    server: HostConfig = field(default_factory=HostConfig)  # Server configuration
    client: HostConfig = field(default_factory=lambda: HostConfig(ip_addr="11.0.0.2", start_time="5s"))  # Client configuration


@dataclass
class ShadowNsConfig(NetworkEnvironmentConfig):
    type: str = "shadow_ns"
    incompatibility: List[str] = field(default_factory=lambda: ["strace", "gperf"] , metadata={"omegaconf_ignore": True})  # Incompatibilities
    general: GeneralConfig = field(default_factory=GeneralConfig)  # General configuration
    experimental: ExperimentalConfig = field(default_factory=ExperimentalConfig)  # Experimental features
    network: NetworkConfig = field(default_factory=NetworkConfig)  # Network configuration
    host_option_defaults: HostOptionDefaultsConfig = field(default_factory=HostOptionDefaultsConfig)  # Default host options
    hosts: HostsConfig = field(default_factory=HostsConfig)  # Hosts configuration
