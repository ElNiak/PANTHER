"""Experiment Reporting System for PANTHER Protocol Testing.

Multi-format reporting pipeline: data collection via StatusCollector,
transformation, and output via ExperimentReporter.

Core Components:
    StatusCollector: Aggregates test results, resource metrics, fast-fail
        analysis, and experiment metadata from execution outputs.
    ExperimentReporter: Generates reports in JSON (machine-readable),
        Markdown (human-readable), and text (fallback) formats using
        Jinja2 templates with graceful degradation.

Reports cover test outcomes, resource usage, fast-fail analysis,
timing breakdowns, and configuration metadata.
"""

from .experiment_reporter import ExperimentReporter
from .result_serialization import (
    save_experiment_result,
    save_implementation_logs,
    save_test_result,
)
from .sequence_trace import SequenceOff, SequenceOn
from .status_collector import StatusCollector

__all__ = [
    "ExperimentReporter",
    "StatusCollector",
    "save_experiment_result",
    "save_test_result",
    "save_implementation_logs",
    "SequenceOn",
    "SequenceOff",
]
