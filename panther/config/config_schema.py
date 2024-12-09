from enum import Enum
from omegaconf import MISSING
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Literal, Type




# Base class for all plugins
@dataclass
class PluginBase:
    type: str  # Plugin type (e.g., docker_compose, gperf, iut, testers)
    settings: Dict = field(default_factory=dict)  # Plugin-specific settings


# Logging Configuration
LoggingLevel = Enum("LoggingLevel", ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
@dataclass
class LoggingConfig:
    level: LoggingLevel = LoggingLevel.DEBUG # Limited valid values
    format: str = "%(asctime)s [%(levelname)s] - %(module)s - %(message)s"


# Paths Configuration
@dataclass
class PathsConfig:
    output_dir: str = "outputs"
    log_dir: str = "outputs/logs"
    config_dir: str = "configs"
    plugin_dir: str = "plugins"


# Docker Configuration
@dataclass
class DockerConfig:
    build_docker_image: bool = True
    remove_docker_image: bool = True
    remove_docker_container: bool = True
    remove_docker_network: bool = True
    remove_docker_volume: bool = True


# Protocol Role Configuration
@dataclass
class ProtocolRoleConfig:
    label: Literal["server", "client"]  # Must be either "server" or "client"
    target: Optional[str] = None  # Optional target service (e.g., another service name)


# Protocol Configuration
@dataclass
class ProtocolConfig:
    name: str = MISSING # Protocol name (e.g., QUIC, BGP)

# Implementation Configuration
# IUT: Implementation Under Test
# Tester: Implementation used for testing
ImplementationType = Enum("ImplementationType", ["iut", "testers"])
@dataclass
class ImplementationConfig:
    name: str = MISSING # Implementation name (e.g., picoquic, panther_ivy)
    type: ImplementationType = ImplementationType.iut  # Must be either "iut" or "testers"
  

def protocol_factory(protocol_data: Dict) -> ProtocolConfig:
    """
    Factory function to dynamically resolve and instantiate the correct ProtocolConfig subclass.

    :param protocol_data: A dictionary containing the protocol configuration.
    :return: An instance of the appropriate ProtocolConfig subclass.
    """
    from plugins.services.iut.quic.config_schema import QuicConfig
    # Map protocol names to their corresponding classes
    PROTOCOL_CLASS_MAP: Dict[str, Type[ProtocolConfig]] = {
        "quic": QuicConfig,
    }
    protocol_name = protocol_data.get("name").lower()
    protocol_class = PROTOCOL_CLASS_MAP.get(protocol_name)
    if protocol_class is None:
        raise ValueError(f"Unsupported protocol: {protocol_name}")
    return protocol_class(**protocol_data)

# Service Configuration
@dataclass
class ServiceConfig:
    name: str = MISSING # Service name
    implementation: ImplementationConfig = MISSING  # Implementation details
    protocol: ProtocolConfig             = MISSING  # Protocol configuration
    ports: List[str]                     = field(default_factory=list)  # List of ports
    generate_new_certificates: Optional[bool] = False
    
                
# Step Configuration
@dataclass
class StepConfig:
    wait: int = field(default=60, metadata={"min": 1, "max": 3600})  # Range for wait time
    record_pcap: Optional[bool] = None  # Optional flag for PCAP recording


# Assertion Configuration
AssertionType = Enum("AssertionType", ["service_responsive", "data_integrity"])
@dataclass
class AssertionConfig:
    type: AssertionType  # Supported assertion types
    service: str  # Service name
    endpoint: str  # Endpoint to assert
    expected_status: int  # Expected status code


# Network Environment Configuration
@dataclass
class NetworkEnvironmentConfig(PluginBase):
    type: str = MISSING

# Execution Environment Configuration
@dataclass
class ExecutionEnvironmentConfig(PluginBase):
    type: str = MISSING


# Test Configuration
@dataclass
class TestConfig:
    name: str        = "Undefined test"  # Test name
    description: str = "Undefined test description"  # Test description
    network_environment: NetworkEnvironmentConfig           = MISSING # field(default_factory= NetworkEnvironmentConfig)  # Network environment configuration
    execution_environment: List[ExecutionEnvironmentConfig] = field(default_factory=lambda: [ExecutionEnvironmentConfig])  # Execution environments
    iterations: int = field(default=1, metadata={"min": 1, "max": 1000})  # Range for iterations
    services: Dict[str, ServiceConfig] = field(default_factory=lambda: { "service_name": ServiceConfig })  # Service configurations
    steps:    Optional[StepConfig]     = None  # Steps configuration
    assertions: Optional[List[AssertionConfig]] = None  # Assertions

# Experiment Configuration
@dataclass
class ExperimentConfig:
    logging: LoggingConfig  = field(default_factory=LoggingConfig)
    paths: PathsConfig      = field(default_factory=PathsConfig)
    docker: DockerConfig    = field(default_factory=DockerConfig)
    tests: List[TestConfig] = field(default_factory=lambda: [TestConfig]) # Required list of tests
