"""ApiModels — Pydantic models for webapp-specific API responses.

Contains lightweight Pydantic models used exclusively by the PANTHER
(Protocol ANalysis and Testing Harness for Extensible Research) web
dashboard layer.  These models have **no equivalent in the core library**;
for plugin data use ``PluginMetadata`` from
``panther.plugins.core.structures.plugin_metadata``, and for experiment
results use ``ExperimentSummary`` from
``panther.core.reporting.status_collector``.

Only models that exist solely to serve the webapp's API or internal
services belong in this module.
"""

from typing import Optional

from pydantic import BaseModel


class ConfigValidationResult(BaseModel):
    """Result of a configuration validation check.

    Returned by the config service when the user clicks "Validate" in
    the config builder page.

    Attributes:
        valid: ``True`` if the configuration passed all Pydantic and
            custom validators; ``False`` otherwise.
        error: Human-readable error message when ``valid`` is ``False``.
            ``None`` when the configuration is valid.
    """

    valid: bool
    error: Optional[str] = None


class DashboardStats(BaseModel):
    """Aggregate summary statistics displayed on the main dashboard.

    Populated by the dashboard page from the plugin manager and
    experiment service at page-load time.

    Attributes:
        plugin_count: Total number of discovered plugins (IUT + tester +
            protocol + environment).
        experiment_count: Number of completed experiment runs found in
            the output directory.
        config_loaded: Filename of the currently loaded configuration
            file, or ``None`` if no config has been loaded yet.
    """

    plugin_count: int = 0
    experiment_count: int = 0
    config_loaded: Optional[str] = None
