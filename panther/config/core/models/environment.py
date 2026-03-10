"""Environment configuration models."""

from typing import List, Optional

from pydantic import Field

from ..base import BaseConfig


class EnvironmentConfig(BaseConfig):
    """Base environment configuration."""

    type: str = Field(..., description="Environment type")
    enabled: bool = Field(True, description="Whether this environment is enabled")

    # Background monitoring configuration
    enable_background_monitoring: bool = Field(
        True, description="Enable background monitoring"
    )
    monitoring_interval_seconds: int = Field(
        5, description="Monitoring interval in seconds"
    )
    failure_threshold_count: int = Field(1, description="Failure threshold count")
    allow_partial_deployment: bool = Field(
        False, description="Allow partial deployment"
    )
    critical_services: List[str] = Field(
        default_factory=list, description="Critical services list"
    )


class NetworkEnvironmentConfig(EnvironmentConfig):
    """Base network environment configuration."""

    # Fields merged from former NetworkEnvironmentPluginConfig
    network_name: str = Field("panther_network", description="Network name")
    subnet: Optional[str] = Field(None, description="Network subnet")
    enable_ipv6: bool = Field(False, description="Enable IPv6 support")


class ExecutionEnvironmentConfig(EnvironmentConfig):
    """Base execution environment configuration."""

    # Fields merged from former ExecutionEnvironmentPluginConfig
    output_format: str = Field("json", description="Output format for results")
    collect_metrics: bool = Field(True, description="Whether to collect metrics")
