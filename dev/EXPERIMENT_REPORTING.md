# Experiment Reporting System

PANTHER's experiment reporting system automatically generates comprehensive reports after each experiment execution. These reports provide immediate insights into experiment results, test statuses, and failure analysis to streamline troubleshooting and result tracking.

## Overview

The reporting system consists of two main components:

1. **StatusCollector**: Aggregates experiment data from logs and test outputs
2. **ExperimentReporter**: Generates reports in multiple formats (JSON, Markdown)

Reports are automatically generated during the experiment cleanup phase, ensuring you always have a summary of your experiment results.

## Report Types

### JSON Report (`experiment_summary.json`)

A machine-readable format designed for:
- CI/CD pipeline integration
- Automated result processing
- Historical data analysis
- Programmatic experiment validation

**Structure:**
```json
{
  "experiment_id": "2025-06-16_12-28-36",
  "status": "failed",
  "start_time": "2025-06-16T12:28:36",
  "end_time": "2025-06-16T12:28:36",
  "duration_seconds": 0,
  "configuration_file": "experiment_config.yaml",
  "tests": {
    "total": 3,
    "passed": 1,
    "failed": 2,
    "skipped": 0,
    "success_rate": 33.3,
    "results": [...]
  },
  "fast_fail": {
    "enabled": true,
    "triggered": true,
    "reason": "Docker build failure",
    "error_category": "docker_build_failures"
  },
  "resources": {
    "peak_memory_mb": 1024.5,
    "disk_usage_mb": 512.3,
    "docker_images_created": 4,
    "total_log_size_mb": 15.2
  },
  "report_metadata": {
    "generated_at": "2025-06-16T12:55:03",
    "panther_version": "1.2.0",
    "report_format_version": "1.0"
  }
}
```

### Markdown Report (`EXPERIMENT_REPORT.md`)

A human-readable format featuring:
- Visual status indicators (✅ ❌ ⏰)
- Organized sections for quick navigation
- Direct links to relevant log files
- Failure analysis guidance
- Directory structure overview

**Example sections:**
- **Overview**: Experiment ID, status, timing, configuration
- **Test Results Summary**: Success rates and statistics
- **Individual Test Results**: Detailed per-test information
- **Fast-Fail Analysis**: Termination reasons and triggers
- **Resource Usage**: Memory, disk, and Docker metrics
- **Failure Analysis**: Next steps and investigation guidance

## Report Location

Reports are generated in the experiment output directory:

```
outputs/<experiment_timestamp>/
├── experiment_summary.json       # Machine-readable report
├── EXPERIMENT_REPORT.md          # Human-readable report
├── experiment.log                # Main experiment log
├── experiment_config.yaml        # Configuration used
└── <test_name>/                  # Individual test directories
    ├── test.log
    ├── stdout.log
    ├── stderr.log
    └── ...
```

## Using Reports

### Quick Status Check

```bash
# View human-readable summary
cat outputs/*/EXPERIMENT_REPORT.md | head -20

# Check success rate across experiments
jq '.tests.success_rate' outputs/*/experiment_summary.json

# Find all failed experiments
grep -l '"status": "failed"' outputs/*/experiment_summary.json
```

### CI/CD Integration

```python
#!/usr/bin/env python3
import json
import sys
from pathlib import Path

# Load latest experiment report
latest_experiment = sorted(Path("outputs").iterdir())[-1]
report_path = latest_experiment / "experiment_summary.json"

with open(report_path) as f:
    summary = json.load(f)

# Check experiment status
if summary["status"] != "completed":
    print(f"Experiment failed: {summary['status']}")
    sys.exit(1)

# Validate success rate
if summary["tests"]["success_rate"] < 90.0:
    print(f"Low success rate: {summary['tests']['success_rate']}%")
    print(f"Failed tests: {summary['tests']['failed']}")
    sys.exit(1)

print(f"All tests passed! Success rate: {summary['tests']['success_rate']}%")
```

### Failure Investigation

1. **Identify failed tests**:
   ```bash
   jq '.tests.results[] | select(.status == "failed")' experiment_summary.json
   ```

2. **Check fast-fail triggers**:
   ```bash
   jq '.fast_fail | select(.triggered == true)' experiment_summary.json
   ```

3. **Analyze resource usage**:
   ```bash
   jq '.resources' experiment_summary.json
   ```

## Manual Report Generation

While reports are generated automatically, you can also generate them manually:

```python
from pathlib import Path
from panther.core.reporting import ExperimentReporter

# Generate reports for a specific experiment
experiment_dir = Path("outputs/2025-06-16_12-28-36")
reporter = ExperimentReporter(experiment_dir)

# Generate all report formats
results = reporter.generate_reports()
print(f"JSON report: {'✅' if results['json'] else '❌'}")
print(f"Markdown report: {'✅' if results['markdown'] else '❌'}")

# Get a quick summary
summary = reporter.generate_quick_summary()
print(summary)
# Output: ❌ 2025-06-16_12-28-36: 0/3 tests passed (0.0%) in 0s
```

## Report Schema

### Test Result Schema

Each test result contains:
- `name`: Test identifier
- `status`: One of `passed`, `failed`, `skipped`, `timeout`, `error`
- `duration`: Execution time in seconds
- `start_time` & `end_time`: ISO format timestamps
- `error_message`: Failure description (if applicable)
- `logs_path`: Relative path to test logs
- `fast_fail_triggered`: Boolean indicating fast-fail activation

### Fast-Fail Information

The fast-fail section includes:
- `enabled`: Global fast-fail setting
- `test_level`: Whether per-test control is enabled
- `triggered`: Whether fast-fail terminated the experiment
- `reason`: Human-readable termination reason
- `error_category`: Category of error that triggered termination
- `termination_time`: When the experiment was terminated

### Resource Usage Metrics

Resource tracking includes:
- `peak_memory_mb`: Maximum memory usage during experiment
- `disk_usage_mb`: Total disk space used
- `docker_images_created`: Number of Docker images built
- `total_log_size_mb`: Combined size of all log files

## Best Practices

### For Development

1. **Review reports immediately** after experiment completion
2. **Use JSON reports** for automated validation in pre-commit hooks
3. **Track success rates** over time to identify flaky tests
4. **Monitor resource usage** to optimize experiment configurations

### For CI/CD

1. **Parse JSON reports** to determine build status
2. **Archive reports** with build artifacts
3. **Set thresholds** for acceptable success rates
4. **Alert on resource usage spikes**

### For Troubleshooting

1. **Start with the Markdown report** for human-friendly overview
2. **Use report paths** to navigate directly to relevant logs
3. **Check fast-fail analysis** to understand early terminations
4. **Compare reports** across runs to identify patterns

## Integration with Other Systems

### Grafana/Prometheus

Export metrics from JSON reports:
```python
# prometheus_exporter.py
from prometheus_client import Gauge, start_http_server
import json
import time

success_rate = Gauge('panther_experiment_success_rate', 'Test success rate')
total_tests = Gauge('panther_experiment_total_tests', 'Total number of tests')
duration = Gauge('panther_experiment_duration_seconds', 'Experiment duration')

def update_metrics(report_path):
    with open(report_path) as f:
        data = json.load(f)
    
    success_rate.set(data['tests']['success_rate'])
    total_tests.set(data['tests']['total'])
    if data.get('duration_seconds'):
        duration.set(data['duration_seconds'])

start_http_server(8000)
while True:
    update_metrics('outputs/latest/experiment_summary.json')
    time.sleep(60)
```

### Slack/Email Notifications

```python
# notify_on_failure.py
import json
import requests

def send_slack_notification(webhook_url, summary):
    if summary['status'] != 'completed':
        message = {
            "text": f"🚨 Experiment {summary['experiment_id']} failed!",
            "attachments": [{
                "color": "danger",
                "fields": [
                    {"title": "Status", "value": summary['status'], "short": True},
                    {"title": "Success Rate", "value": f"{summary['tests']['success_rate']}%", "short": True},
                    {"title": "Failed Tests", "value": summary['tests']['failed'], "short": True},
                    {"title": "Total Tests", "value": summary['tests']['total'], "short": True}
                ]
            }]
        }
        requests.post(webhook_url, json=message)
```

## Extending the Reporting System

The reporting system is designed to be extensible. To add custom report formats or metrics:

1. **Extend StatusCollector** to collect additional metrics
2. **Extend ExperimentReporter** to generate new report formats
3. **Update report templates** in `panther/core/reporting/templates/`

Example custom collector:
```python
from panther.core.reporting import StatusCollector

class CustomStatusCollector(StatusCollector):
    def _extract_custom_metrics(self):
        # Add your custom metric extraction logic
        return {
            "custom_metric": self._parse_custom_logs(),
            "performance_score": self._calculate_performance()
        }
```

## Version History

- **v1.0** (2024-06): Initial release
  - JSON and Markdown report formats
  - Fast-fail integration
  - Resource usage tracking
  - Automatic generation during cleanup

## Future Enhancements

Planned features for upcoming releases:

1. **Test Replay System**: Save and replay failed test configurations
2. **Trend Analysis**: Compare results across multiple experiments
3. **HTML Reports**: Rich interactive reports with charts
4. **Report Aggregation**: Combine multiple experiment reports
5. **Custom Metrics**: Plugin system for domain-specific metrics