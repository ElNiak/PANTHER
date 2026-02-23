# PANTHER Metrics System

**Comprehensive performance monitoring and data collection for experiment analysis**

The PANTHER metrics system provides detailed performance monitoring, resource tracking, and experiment analysis capabilities. It collects timing data, system resources, success/failure rates, and custom metrics throughout the experiment lifecycle.

!!! info "Metrics Integration"
    The metrics system is fully integrated with PANTHER's event-driven architecture and observer pattern. All metrics are collected automatically during experiment execution and can be exported in multiple formats for analysis.

## Overview

The metrics system captures data across the entire experiment workflow:

- **Timing Metrics** - Execution times for each phase and component
- **Resource Metrics** - CPU, memory, disk, and network usage (requires psutil)
- **Status Metrics** - Success/failure tracking and error reporting
- **Custom Metrics** - User-defined measurements and counters
- **Artifact Metrics** - File sizes, packet captures, and output data

## System Components

### MetricsCollector (`metrics_collector.py`)

Central collection engine that gathers metrics throughout experiment execution:

```python
from panther.core.metrics.metrics_collector import MetricsCollector, Metric
from panther.core.metrics.enums import MetricType, Phase

# Initialize collector
collector = MetricsCollector()

# Record timing metric
collector.record_timing("test_execution", 45.2, 
                       phase=Phase.TEST_EXECUTION,
                       test_case="QUIC_handshake")

# Record resource usage  
collector.record_resource("cpu_usage", 85.5,
                         component="picoquic_server")

# Record status
collector.record_status("test_result", "success",
                       metadata={"packets_sent": 1024})
```

#### Metric Types

| Type | Purpose | Examples |
|------|---------|----------|
| `TIMING` | Execution durations | Test runtime, plugin loading time |
| `COUNTER` | Incrementing values | Packet count, error count |
| `GAUGE` | Point-in-time measurements | CPU usage, memory usage |
| `HISTOGRAM` | Distribution data | Response time distributions |
| `STATUS` | Success/failure tracking | Test outcomes, service states |
| `RESOURCE` | System resource usage | CPU, memory, disk, network |
| `ARTIFACT` | Output file information | Log sizes, packet capture files |
| `ERROR` | Error tracking and analysis | Exception details, failure causes |

#### Execution Phases

Metrics are categorized by experiment phase:

| Phase | Description | Typical Metrics |
|-------|-------------|-----------------|
| `CONFIG_LOADING` | Configuration file parsing | Parse time, file size |
| `CONFIG_VALIDATION` | Configuration validation | Validation time, error count |
| `EXPERIMENT_INITIALIZATION` | Experiment setup | Plugin loading time, memory usage |
| `TEST_CASE_INITIALIZATION` | Individual test setup | Service creation time |
| `ENVIRONMENT_SETUP` | Network/execution environment | Container build time, image size |
| `SERVICE_DEPLOYMENT` | Service deployment | Deployment time, startup time |
| `TEST_EXECUTION` | Main test execution | Test duration, throughput |
| `STEP_EXECUTION` | Individual test steps | Step timing, resource usage |
| `ASSERTION_VALIDATION` | Result validation | Validation time, assertion count |
| `ENVIRONMENT_TEARDOWN` | Environment cleanup | Teardown time, resource cleanup |
| `EXPERIMENT_CLEANUP` | Final cleanup | Total experiment time |

### MetricsExporter (`metrics_exporter.py`)

Handles exporting collected metrics to various formats:

```python
from panther.core.metrics.metrics_exporter import MetricsExporter

# Initialize exporter
exporter = MetricsExporter(metrics_collector)

# Export to JSON
exporter.export_json("outputs/metrics/experiment_metrics.json")

# Export to CSV
exporter.export_csv("outputs/metrics/")

# Export summary report
exporter.export_summary("outputs/metrics/summary.txt")

# Export for dashboards
exporter.export_dashboard_format("outputs/metrics/dashboard.json")
```

#### Export Formats

- **JSON** - Complete metrics data with metadata
- **CSV** - Tabular data for spreadsheet analysis  
- **Summary** - Human-readable performance report
- **Dashboard** - Formatted for monitoring dashboards

### MetricsReporter (`metrics_reporter.py`)

Generates analysis reports and performance summaries:

```python
from panther.core.metrics.metrics_reporter import MetricsReporter

reporter = MetricsReporter(metrics_collector)

# Generate performance analysis
performance_report = reporter.generate_performance_analysis()

# Generate resource utilization report  
resource_report = reporter.generate_resource_analysis()

# Generate test success summary
success_report = reporter.generate_success_analysis()
```

### ResourceMonitor (`resource_monitor.py`)

Real-time system resource monitoring (requires psutil):

```python
from panther.core.metrics.resource_monitor import ResourceMonitor

# Start monitoring
monitor = ResourceMonitor(metrics_collector, interval=5.0)
monitor.start_monitoring()

# Monitor specific process
monitor.monitor_process("picoquic_server", pid=1234)

# Stop monitoring
monitor.stop_monitoring()
```

#### Monitored Resources

- **CPU Usage** - Per-core and total CPU utilization
- **Memory** - RAM usage, swap usage, memory limits
- **Disk I/O** - Read/write rates, disk usage
- **Network** - Bandwidth utilization, packet rates
- **Process** - Per-process resource consumption

## Integration with PANTHER Components

### Event System Integration

Metrics collection is integrated with PANTHER's event system:

```python
# Metrics are automatically collected when events fire
event_manager.emit_event("test_started", {
    "test_name": "QUIC_handshake",
    "timestamp": time.time()
})
# -> Automatically records timing metric

event_manager.emit_event("test_completed", {
    "test_name": "QUIC_handshake", 
    "success": True,
    "duration": 45.2
})
# -> Records completion metric and success status
```

### Observer Pattern

The MetricsObserver automatically collects metrics from all events:

```python
from panther.core.observer.impl.metrics_observer import MetricsObserver

# Observer is automatically registered and collects metrics
observer_manager.register(MetricsObserver(metrics_collector))
```

### Configuration

Enable metrics collection in experiment configuration:

```yaml
observers:
  metrics:
    enabled: true
    collect_system_metrics: true  # Requires psutil
    publish_interval: 30         # Seconds between resource samples
    log_level: INFO
    
# Metrics are automatically saved to output directory
paths:
  output_dir: "outputs"         # Metrics saved to outputs/metrics/
```

## Usage Examples

### Basic Metrics Collection

```python
# Enable metrics in experiment config
config = {
    "observers": {
        "metrics": {
            "enabled": True,
            "collect_system_metrics": True
        }
    }
}

# Run experiment - metrics collected automatically
experiment_manager = ExperimentManager(config)
experiment_manager.run_tests()

# Metrics automatically exported to outputs/metrics/
```

### Custom Metrics in Plugins

```python
class CustomServiceManager(BaseQUICServiceManager):
    
    def generate_run_command(self, **kwargs):
        start_time = time.time()
        
        # Your custom logic here
        command = super().generate_run_command(**kwargs)
        
        # Record custom metric
        if hasattr(self, 'metrics_collector'):
            duration = time.time() - start_time
            self.metrics_collector.record_timing(
                "command_generation", 
                duration,
                component=self.get_implementation_name(),
                metadata={"command_length": len(command)}
            )
        
        return command
```

### Resource Monitoring for Long Tests

```yaml
tests:
  - name: "Long Performance Test"
    network_environment:
      type: docker_compose
    execution_environment:
      - type: gperf_cpu
    services:
      server:
        implementation: {name: picoquic, type: iut}
        protocol: {name: quic, version: rfc9000, role: server}
        timeout: 300  # 5 minutes
    steps:
      wait: 240
      
# Resource monitoring runs automatically during test
# Results saved to outputs/metrics/resource_monitoring.csv
```

## Output Structure

Metrics are automatically saved to the experiment output directory:

```text
outputs/
   2025-XX-XX_experiment_run/
       metrics/
          metrics_complete.json       # All collected metrics
          timing_metrics.csv          # Timing data only
          resource_metrics.csv        # Resource usage data
          status_metrics.csv          # Success/failure tracking
          performance_summary.txt     # Human-readable summary
          resource_monitoring.csv     # Real-time resource data
       experiment.log
```

## Performance Analysis

The metrics system enables comprehensive performance analysis:

### Timing Analysis

```bash
# View experiment timing breakdown
cat outputs/metrics/performance_summary.txt

# Analyze timing data
python -c "
import pandas as pd
df = pd.read_csv('outputs/metrics/timing_metrics.csv')
print(df.groupby('phase')['value'].agg(['mean', 'max', 'std']))
"
```

### Resource Analysis

```bash
# Monitor resource usage trends
python -c "
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv('outputs/metrics/resource_metrics.csv')
cpu_data = df[df['name'] == 'cpu_usage']
plt.plot(cpu_data['timestamp'], cpu_data['value'])
plt.title('CPU Usage Over Time')
plt.savefig('cpu_usage.png')
"
```

### Success Rate Analysis

```bash
# Calculate test success rates
python -c "
import pandas as pd
df = pd.read_csv('outputs/metrics/status_metrics.csv')
success_rate = len(df[df['value'] == 'success']) / len(df) * 100
print(f'Test Success Rate: {success_rate:.1f}%')
"
```

## Best Practices

1. **Enable for Performance Testing** - Always enable metrics for performance analysis
2. **Monitor Long Tests** - Use resource monitoring for tests >30 seconds
3. **Custom Metrics** - Add custom metrics for implementation-specific measurements
4. **Regular Analysis** - Review performance trends across experiment runs
5. **Resource Limits** - Monitor resource usage to prevent system overload

## Troubleshooting

### Common Issues

**High Memory Usage**
```bash
# Check if resource monitoring is using too much memory
# Increase publish_interval to reduce sampling frequency
observers:
  metrics:
    publish_interval: 60  # Sample every 60 seconds instead of 30
```

**Missing psutil**
```bash
# Install psutil for resource monitoring
pip install psutil

# Or disable system metrics collection
observers:
  metrics:
    collect_system_metrics: false
```

**Large Export Files**
```bash
# Filter metrics by phase or component when exporting
python -c "
import json
with open('outputs/metrics/metrics_complete.json') as f:
    data = json.load(f)
    
# Filter to test execution only
test_metrics = [m for m in data if m['phase'] == 'test_execution']
with open('test_only_metrics.json', 'w') as f:
    json.dump(test_metrics, f, indent=2)
"
```

## Integration with Analysis Tools

The metrics system exports data compatible with:

- **Pandas/NumPy** - CSV exports for data analysis
- **Grafana/Prometheus** - Dashboard format exports  
- **Excel/Sheets** - CSV exports for spreadsheet analysis
- **R/MATLAB** - JSON exports for statistical analysis
- **Custom Tools** - Structured JSON format for any analysis tool

This comprehensive metrics system enables deep performance analysis and optimization of protocol implementations tested with PANTHER.