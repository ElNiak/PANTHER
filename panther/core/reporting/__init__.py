"""
Comprehensive Experiment Reporting System for PANTHER Protocol Testing

This module provides a sophisticated multi-format reporting system that generates detailed
experiment analysis reports for protocol testing workflows. It aggregates data from multiple
sources and produces human-readable and machine-parseable reports with rich metadata.

## Architecture Overview

The reporting system implements a layered data collection and transformation pipeline:

```mermaid
graph TD
    A[Experiment Execution] --> B[StatusCollector]
    B --> C[Data Aggregation]
    C --> D[ExperimentReporter]
    D --> E[Multi-Format Output]

    E --> F[JSON Report]
    E --> G[Markdown Report]
    E --> H[Text Summary]

    B --> I[Test Results]
    B --> J[Resource Metrics]
    B --> K[Fast-Fail Analysis]
    B --> L[Timing Data]
```

## Core Components

### 1. **StatusCollector**
Central data aggregation engine that gathers experiment data from multiple sources:
- **Test Execution Results**: Individual test outcomes, timing, and error details
- **Resource Usage Metrics**: Memory consumption, disk usage, Docker image statistics
- **Fast-Fail Analysis**: Failure categorization and early termination reasoning
- **Experiment Metadata**: Configuration, timing, and version information

### 2. **ExperimentReporter**
Multi-format report generation engine with template-driven rendering:
- **JSON Reports**: Machine-readable data for programmatic analysis and CI/CD integration
- **Markdown Reports**: Human-readable reports with rich formatting, emojis, and structured sections
- **Text Summaries**: Minimal fallback format for constrained environments or template failures
- **Template System**: Jinja2-based templating with graceful degradation to basic formatting

## Report Content Architecture

Generated reports include comprehensive experiment analysis:

```
Experiment Report Structure:
├── Executive Summary
│   ├── Overall status and success rate
│   ├── Total duration and timing breakdown
│   └── Configuration and environment info
├── Test Results Analysis
│   ├── Individual test outcomes with timing
│   ├── Passed/failed/skipped categorization
│   └── Error messages and stack traces
├── Fast-Fail Analysis
│   ├── Fast-fail configuration and triggers
│   ├── Error categorization and reasoning
│   └── Early termination impact analysis
├── Resource Usage Metrics
│   ├── Peak memory consumption tracking
│   ├── Disk usage and log size statistics
│   ├── Docker image creation counts
│   └── Network and I/O utilization
└── Metadata and References
    ├── PANTHER version and configuration
    ├── Report generation timestamps
    └── Log file locations and references
```

## Key Features

- **Multi-Format Support**: JSON (machine-readable), Markdown (human-readable), Text (fallback)
- **Template-Driven Rendering**: Jinja2 templates with graceful degradation to basic formatting
- **Comprehensive Analysis**: Test outcomes, resource usage, fast-fail analysis, and metadata
- **Error Recovery**: Progressive fallback strategies ensure report availability
- **Rich Formatting**: Status emojis, duration formatting, percentage calculations
- **Protocol-Aware Context**: QUIC, HTTP, TCP, and MINIP specific analysis patterns

## Performance Characteristics

- **Report Generation**: ~100-500ms depending on experiment size and template complexity
- **Memory Usage**: O(n) where n is number of test cases and log entries
- **Template Rendering**: ~10-50ms for Jinja2, ~5-10ms for basic formatting
- **Error Resilience**: Multiple format attempts with progressive fallback strategies

## Usage Examples

```python
from panther.core.reporting import ExperimentReporter, StatusCollector

# Generate comprehensive reports
reporter = ExperimentReporter(experiment_dir, "quic_interop_test")
results = reporter.generate_reports()

# Quick status summary for logging
summary = reporter.generate_quick_summary()
logger.info(summary)

# Manual data collection and analysis
collector = StatusCollector(experiment_dir)
experiment_data = collector.collect_experiment_summary()
```

This reporting system enables detailed post-experiment analysis, automated CI/CD reporting,
and comprehensive debugging support for complex protocol testing scenarios.
"""

from .experiment_reporter import ExperimentReporter
from .status_collector import StatusCollector

__all__ = ["ExperimentReporter", "StatusCollector"]
