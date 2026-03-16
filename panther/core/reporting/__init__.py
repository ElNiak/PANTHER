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

from .artifact_browser import ArtifactBrowser
from .experiment_reporter import ExperimentReporter
from .failure_patterns import BUILTIN_PATTERNS, FailurePattern
from .log_query_engine import LogFilter, LogQueryEngine
from .result_serialization import (
    save_experiment_result,
    save_implementation_logs,
    save_test_result,
)
from .root_cause_analyzer import RootCause, RootCauseAnalyzer
from .sequence_trace import SequenceOff, SequenceOn
from .status_collector import StatusCollector
from .timeline_renderer import TimelineRenderer

__all__ = [
    "ArtifactBrowser",
    "BUILTIN_PATTERNS",
    "ExperimentReporter",
    "FailurePattern",
    "LogFilter",
    "LogQueryEngine",
    "RootCause",
    "RootCauseAnalyzer",
    "StatusCollector",
    "TimelineRenderer",
    "save_experiment_result",
    "save_test_result",
    "save_implementation_logs",
    "SequenceOn",
    "SequenceOff",
]
