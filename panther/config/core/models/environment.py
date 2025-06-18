"""Environment configuration models."""

from typing import Any, Dict, List, Optional

from pydantic import Field, validator

from .base_model import BaseUnifiedModel


class EnvironmentConfig(BaseUnifiedModel):
    """Base environment configuration."""
    
    type: str = Field(..., description="Environment type")
    
    # Background monitoring configuration for non-blocking service health checks
    enable_background_monitoring: bool = Field(True, description="Enable background monitoring")
    monitoring_interval_seconds: int = Field(5, description="Monitoring interval in seconds")
    failure_threshold_count: int = Field(3, description="Failure threshold count")
    allow_partial_deployment: bool = Field(False, description="Allow partial deployment")
    critical_services: List[str] = Field(default_factory=list, description="Critical services list")


class NetworkEnvironmentConfig(EnvironmentConfig):
    """Base network environment configuration."""
    
    type: str = Field(..., description="Environment type")
    
    # Allow extra fields for environment-specific parameters


# Network environment configurations have been moved to plugin directories:
# - DockerComposeConfig -> panther/plugins/environments/network_environment/docker_compose/config_schema.py
# - LocalhostSingleContainerConfig -> panther/plugins/environments/network_environment/localhost_single_container/config_schema.py
# - ShadowNsConfig -> panther/plugins/environments/network_environment/shadow_ns/config_schema.py


class ExecutionEnvironmentConfig(EnvironmentConfig):
    """Base execution environment configuration."""
    
    type: str = Field(..., description="Environment type")
    enabled: bool = Field(True, description="Whether this environment is enabled")
    
    # Allow extra fields for environment-specific parameters


# Note: Plugin-specific configurations have been moved to their respective plugin directories
# to support dynamic plugin discovery. Only base classes remain here.
#
# For example:
# - StraceConfig -> panther/plugins/environments/execution_environment/strace/config_schema.py
# - GperfCpuConfig -> panther/plugins/environments/execution_environment/gperf_cpu/config_schema.py
# - etc.
#
# This allows new plugins to be added without modifying core code.