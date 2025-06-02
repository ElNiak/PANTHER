# PANTHER Metrics System

The PANTHER metrics system provides comprehensive observability for build processes, test executions, and system performance. It automatically captures both internal metrics (build and test performance) and external metrics (container image sizes, artifact footprints) for every experiment and test session.

## Overview

The metrics system is designed to:

- **Automatically capture metrics** during build and test operations
- **Store data persistently** in a query-friendly JSON Lines format
- **Provide CLI tools** for viewing and analyzing metrics
- **Enable performance regression detection** through historical data
- **Support future integrations** with monitoring systems like Prometheus/Grafana

## Metrics Collected

### Builder Metrics

| Metric | Description | Units |
|--------|-------------|-------|
| `container.build_seconds` | Wall-clock time from build start to ready image | seconds |
| `container.image_mb` | Compressed Docker image size | megabytes |
| `artifact.dist_mb` | Size of the `/dist` folder | megabytes |
| `artifact.wheel_mb` | Size of the built wheel file | megabytes |
| `artifact.build_mb` | Size of the `/build` folder | megabytes |
| `build.wheel_success` | Whether wheel build succeeded (1.0 = success, 0.0 = failure) | boolean |

### Test Metrics

| Metric | Description | Units |
|--------|-------------|-------|
| `pytest.total_seconds` | End-to-end test runtime | seconds |
| `pytest.item_count` | Number of collected test cases | count |
| `pytest.passed` | Number of passed tests | count |
| `pytest.failed` | Number of failed tests | count |
| `pytest.skipped` | Number of skipped tests | count |
| `pytest.errors` | Number of tests with errors | count |
| `pytest.coverage_pct` | Line coverage percentage | percentage |
| `test.suite_success` | Whether test suite passed (1.0 = success, 0.0 = failure) | boolean |

### System Metrics

| Metric | Description | Units |
|--------|-------------|-------|
| `cpu.avg_load` | Average CPU load during operation | percentage |
| `cpu.max_load` | Peak CPU load during operation | percentage |
| `ram.peak_mb` | Peak memory usage during operation | megabytes |
| `ram.avg_mb` | Average memory usage during operation | megabytes |

### Documentation Metrics

| Metric | Description | Units |
|--------|-------------|-------|
| `docs.build_success` | Whether documentation build succeeded | boolean |
| `artifact.docs_mb` | Size of the `/docs` folder | megabytes |
| `artifact.site_mb` | Size of the built documentation site | megabytes |

## Data Storage

Metrics are stored in JSON Lines format at `<project>/.panther-metrics/<date>.jsonl`. Each record contains:

```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "type": "build_wheel",
  "timestamp": "2025-05-30T14:30:45.123456+00:00",
  "git_commit": "abc123def456...",
  "metrics": {
    "container.build_seconds": 12.3,
    "artifact.dist_mb": 2.5,
    "cpu.avg_load": 45.2,
    "ram.peak_mb": 128.7
  },
  "tags": {
    "container.build_seconds": {"stage": "build_wheel"},
    "artifact.dist_mb": {"stage": "build_wheel"}
  },
  "operation": "build_wheel",
  "duration": 12.3,
  "success": true
}
```

## Automatic Integration

### Build Process Integration

The metrics system is automatically integrated into `panther_builder.py`. Every build operation is instrumented:

```python
# Example: Building a wheel automatically records metrics
python panther_builder.py build-wheel
```

This will create a metrics record with:
- Build duration
- Artifact sizes (dist/, wheel file)
- CPU and memory usage during build
- Success/failure status

### Test Integration

Tests automatically record metrics through the pytest plugin. Enable by adding to your `conftest.py`:

```python
pytest_plugins = ["panther.metrics.pytest_plugin"]
```

Running tests with coverage:
```bash
pytest --cov=panther --cov-report=xml
```

This captures:
- Test execution time
- Pass/fail counts
- Coverage percentage
- Resource usage during tests

## CLI Usage

### List Recent Metrics

View recent build and test metrics:

```bash
python -m panther.metrics.cli ls
```

Example output:
```
Run ID                               Type     Timestamp           Key Metrics
--------------------------------------------------------------------------------
550e8400-e29b-41d4-a716-446655440000 build    2025-05-30 14:30:45 build: 12.3s, image: 45.2 MB, dist: 2.5 MB
7b2c8d9e-1f3a-4b5c-9d2e-6f8a1b3c5d7e tests    2025-05-30 14:25:30 duration: 8.7s, tests: 156, passed: 154, failed: 2
```

### Show Detailed Metrics

Get detailed information about a specific run:

```bash
python -m panther.metrics.cli show 550e8400-e29b-41d4-a716-446655440000
```

Example output:
```
Run ID: 550e8400-e29b-41d4-a716-446655440000
Type: build_wheel
Timestamp: 2025-05-30 14:30:45
Git Commit: abc123def456789...

Metrics:
  container.build_seconds: 12.3s
  artifact.dist_mb: 2.5 MB
  artifact.wheel_mb: 1.8 MB
  cpu.avg_load: 45.2%
  ram.peak_mb: 128.7 MB

Additional Data:
  operation: build_wheel
  duration: 12.3
  success: true
```

### Export Metrics

Export metrics to JSON for external analysis:

```bash
# Export all metrics
python -m panther.metrics.cli export > metrics.json

# Export specific date
python -m panther.metrics.cli export --date 2025-05-30 > today.json

# Export to file
python -m panther.metrics.cli export --output metrics.json --limit 100
```

## Programmatic Usage

### Recording Custom Metrics

```python
from panther.metrics import record, flush

# Record individual metrics
record("custom.processing_time", 5.2, {"component": "parser"})
record("custom.items_processed", 1000, {"batch": "daily"})

# Flush to storage
run_id = flush("custom_operation", {
    "config_hash": "abc123",
    "extra_info": "batch processing"
})
```

### Using Resource Sampling

```python
from panther.metrics import ResourceSampler

sampler = ResourceSampler(interval=1.0)  # Sample every second
sampler.start()

# ... do some work ...

metrics = sampler.stop()
# metrics = {
#     "cpu.avg_load": 42.3,
#     "cpu.max_load": 78.1,
#     "ram.peak_mb": 256.4,
#     "ram.avg_mb": 180.2
# }
```

### Custom Storage

```python
from panther.metrics import MetricsCollector
from pathlib import Path

# Use custom storage location
collector = MetricsCollector(Path("/custom/metrics/path"))
collector.record("my.metric", 42.0)
run_id = collector.flush("my_operation")
```

## Performance Impact

The metrics system is designed to have minimal performance impact:

- **Resource sampling**: ~0.1% CPU overhead with 1-second intervals
- **Storage I/O**: Asynchronous JSON Lines writes, ~1ms per record
- **Memory usage**: <10MB for typical collection periods
- **Build overhead**: <100ms additional time per build operation

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PANTHER_METRICS_DISABLED` | Disable metrics collection entirely | `false` |
| `PANTHER_METRICS_PATH` | Custom metrics storage path | `.panther-metrics/` |
| `PANTHER_METRICS_SAMPLE_INTERVAL` | Resource sampling interval (seconds) | `1.0` |

### Disabling Metrics

To disable metrics collection:

```bash
export PANTHER_METRICS_DISABLED=true
python panther_builder.py package
```

Or in code:
```python
import os
os.environ['PANTHER_METRICS_DISABLED'] = 'true'
```

## Future Enhancements

### Planned Features

1. **StatsD Integration**: Emit metrics to StatsD for real-time monitoring
   ```python
   # Future: Automatic StatsD emission
   export PANTHER_METRICS_STATSD_HOST=localhost:8125
   ```

2. **Cloud Storage**: Auto-upload metrics to S3/GCS
   ```python
   # Future: Cloud backup
   export PANTHER_METRICS_S3_BUCKET=my-metrics-bucket
   ```

3. **Regression Detection**: Automatic performance regression alerts
   ```python
   # Future: CI integration
   python -m panther.metrics.regression-check --threshold 20%
   ```

4. **Grafana Dashboards**: Pre-built dashboards for metrics visualization

5. **Database Backend**: Optional SQLite/PostgreSQL storage for complex queries

### Integration Examples

#### CI/CD Pipeline

```yaml
# .github/workflows/ci.yml
- name: Run tests with metrics
  run: |
    python panther_builder.py package-test
    python -m panther.metrics.cli export --output metrics.json

- name: Upload metrics artifact
  uses: actions/upload-artifact@v3
  with:
    name: metrics
    path: metrics.json
```

#### Performance Monitoring

```python
# Future: Prometheus integration
from panther.metrics.exporters import PrometheusExporter

exporter = PrometheusExporter()
exporter.push_to_gateway("http://prometheus:9091")
```

## Troubleshooting

### Common Issues

1. **Permission errors**: Ensure write access to `.panther-metrics/` directory
2. **Missing psutil**: Install with `pip install psutil` for resource monitoring
3. **Large metrics files**: Use `--limit` flag when viewing metrics
4. **Clock synchronization**: Ensure system time is accurate for timestamp consistency

### Debug Mode

Enable verbose metrics logging:

```python
import logging
logging.getLogger('panther.metrics').setLevel(logging.DEBUG)
```

### Metrics Not Appearing

1. Check if metrics are disabled: `echo $PANTHER_METRICS_DISABLED`
2. Verify storage path exists: `ls -la .panther-metrics/`
3. Check for import errors: `python -c "import panther.metrics; print('OK')"`

## Best Practices

1. **Regular cleanup**: Archive old metrics files periodically
2. **Backup important runs**: Export critical metrics before cleanup
3. **Tag consistently**: Use consistent tag naming for easier analysis
4. **Monitor overhead**: Check resource usage impact in production
5. **Correlate with git**: Use commit hashes to track performance over time

The metrics system provides the foundation for data-driven development and performance optimization in PANTHER, enabling teams to track progress and identify regressions automatically.
