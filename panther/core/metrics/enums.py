"""Metrics Enums Module.

This module contains enum definitions for the metrics system to avoid circular imports.
"""

from enum import Enum


class MetricType(Enum):
    """Types of metrics that can be collected."""

    TIMING = "timing"
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    STATUS = "status"
    RESOURCE = "resource"
    ARTIFACT = "artifact"
    ERROR = "error"
    PERFORMANCE = "performance"


class Phase(Enum):
    """Experiment execution phases for metric categorization."""

    CONFIG_LOADING = "config_loading"
    CONFIG_VALIDATION = "config_validation"
    EXPERIMENT_INITIALIZATION = "experiment_initialization"
    TEST_CASE_INITIALIZATION = "test_case_initialization"
    ENVIRONMENT_SETUP = "environment_setup"
    SERVICE_DEPLOYMENT = "service_deployment"
    TEST_EXECUTION = "test_execution"
    STEP_EXECUTION = "step_execution"
    ASSERTION_VALIDATION = "assertion_validation"
    ENVIRONMENT_TEARDOWN = "environment_teardown"
    EXPERIMENT_CLEANUP = "experiment_cleanup"
