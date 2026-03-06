"""Webapp-specific Pydantic models.

For plugin data, use PluginMetadata from panther.plugins.core.structures.plugin_metadata.
For experiment results, use ExperimentSummary from panther.core.reporting.status_collector.
Only models with NO core equivalent belong here.
"""

from typing import Optional

from pydantic import BaseModel


class ConfigValidationResult(BaseModel):
    """Result of config validation — webapp API response."""

    valid: bool
    error: Optional[str] = None


class DashboardStats(BaseModel):
    """Dashboard summary statistics — webapp-specific aggregate."""

    plugin_count: int = 0
    experiment_count: int = 0
    config_loaded: Optional[str] = None
