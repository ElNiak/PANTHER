"""PANTHER webapp models --- Pydantic models for API responses and display aggregates.

This package contains data models that exist *only* in the webapp
layer.  They represent UI-specific concerns (dashboard statistics,
validation results) that have no counterpart in the PANTHER core.

Relationship to core models
---------------------------
PANTHER's core already provides rich data structures for plugin
metadata (``panther.plugins.core.structures.plugin_metadata.PluginMetadata``),
experiment results (``panther.core.reporting.status_collector.ExperimentSummary``),
and configuration (``panther.config.core.models``).  Pages and
services use those core types directly whenever possible.  Models
defined here fill gaps where the core does not provide a suitable
data transfer object:

- ``ConfigValidationResult`` -- a simple valid/error pair returned by
  ``ConfigService`` after validating a user-edited config.
- ``DashboardStats`` -- an aggregate of counts (plugins, experiments,
  loaded config path) for the dashboard summary row.

When adding new models, check first whether an existing core type
already carries the data you need.

See Also:
--------
panther.webapp.services : Services that produce and consume these models.
panther.config.core.models : Core configuration Pydantic models.
"""
