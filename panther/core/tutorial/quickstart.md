# PANTHER Core Tutorial: Network Protocol Testing

This tutorial demonstrates how to use PANTHER's core framework to test network protocols. You'll learn to configure, execute, and analyze protocol experiments step-by-step.

## Prerequisites

- Python 3.10+
- Docker 27.x+
- Basic understanding of network protocols
- 15 minutes for this tutorial

## Installation

```bash
# Install PANTHER
pip install panther-net

# Verify installation
panther --version
```

## Tutorial Overview

This tutorial covers:

1. **Basic Configuration** — Setting up your first experiment
2. **Running Tests** — Executing protocol tests
3. **Analyzing Results** — Understanding experiment outputs
4. **Customization** — Adding custom observers and metrics
5. **Advanced Usage** — Event-driven programming with PANTHER

## Step 1: Basic QUIC Protocol Test

Let's start with a simple QUIC protocol test between client and server implementations.

### Create Configuration File

Create `tutorial_config.yaml`:

```yaml
# Global configuration
global:
  paths:
    output_dir: "./tutorial_outputs"
    plugin_dir: "./plugins"
  logging:
    level: "INFO"
    format: "structured"
  docker:
    enabled: true
    build_timeout: 300

# Experiment configuration
experiment:
  name: "QUIC_Tutorial"
  protocol: "quic"

  # Network environment setup
  network_environment:
    type: "docker_compose"
    network_name: "quic_test_network"
    subnet: "192.168.10.0/24"

  # Execution environment
  execution_environment:
    type: "basic"
    timeout: 60

  # Test cases
  test_cases:
    - name: "QUIC_Basic_Connection"
      implementation: "picoquic"
      scenario: "client_server"
      parameters:
        server_port: 4433
        test_duration: 10
        data_size: "1MB"

    - name: "QUIC_Handshake_Test"
      implementation: "quiche"
      scenario: "handshake_only"
      parameters:
        server_port: 4434
        connection_timeout: 5
```

### Run Your First Experiment

```bash
# Run the experiment
panther run --config tutorial_config.yaml

# Output should show:
# [INFO] Initializing experiment: QUIC_Tutorial
# [INFO] Loading plugins for protocol: quic
# [INFO] Setting up network environment: docker_compose
# [INFO] Executing test case: QUIC_Basic_Connection
# [INFO] Test completed successfully
# [INFO] Experiment completed. Results in: ./tutorial_outputs/
```

## Step 2: Understanding the Output

After running the experiment, examine the generated outputs:

```bash
# Navigate to results directory
cd tutorial_outputs/QUIC_Tutorial_<timestamp>/

# View experiment summary
cat experiment_summary.json

# Check individual test results
ls test_results/
cat test_results/QUIC_Basic_Connection/test_result.json
```

### Sample Output Structure

```text
tutorial_outputs/
└── QUIC_Tutorial_2024-07-05_15-30-45/
    ├── experiment_summary.json      # Overall results
    ├── experiment_config.yaml       # Used configuration
    ├── experiment.log              # Detailed logs
    ├── test_results/               # Individual test results
    │   ├── QUIC_Basic_Connection/
    │   │   ├── test_result.json    # Test outcome
    │   │   ├── server.log         # Server logs
    │   │   ├── client.log         # Client logs
    │   │   └── network_capture.pcap # Packet capture
    │   └── QUIC_Handshake_Test/
    │       └── ...
    └── metrics/                    # Performance metrics
        ├── timing_metrics.json
        ├── resource_usage.json
        └── success_rates.json
```

## Step 3: Programmatic API Usage

You can also use PANTHER programmatically in Python:

```python
# tutorial_script.py
from pathlib import Path
from panther.core.experiment_manager import ExperimentManager
from panther.config.core.manager import ConfigManager

def run_tutorial_experiment():
    """Run QUIC experiment programmatically."""

    # Load configuration
    config_manager = ConfigManager()
    global_config = config_manager.load_global_config("tutorial_config.yaml")
    experiment_config = config_manager.load_experiment_config("tutorial_config.yaml")

    # Create experiment manager
    manager = ExperimentManager(
        global_config=global_config,
        experiment_name="QUIC_Programmatic_Test"
    )

    try:
        # Initialize and run experiment
        manager.initialize_experiments(experiment_config)
        results = manager.run_tests()

        # Print results summary
        print(f"Experiment completed!")
        print(f"Success rate: {results['success_rate']:.2%}")
        print(f"Total tests: {results['total_tests']}")
        print(f"Failed tests: {results['failed_tests']}")

        # Access individual test results
        for test_name, test_result in results['test_results'].items():
            print(f"{test_name}: {test_result['status']}")

    finally:
        # Cleanup resources
        manager.cleanup()

if __name__ == "__main__":
    run_tutorial_experiment()
```

Run the script:

```bash
python tutorial_script.py
```

## Step 4: Adding Custom Observers

PANTHER uses the Observer pattern for extensibility. Let's add a custom observer to collect custom metrics:

```python
# custom_observer.py
from panther.core.observer.base import Observer
from panther.core.events.test import TestEvent
from panther.core.events.experiment import ExperimentEvent

class TutorialMetricsObserver(Observer):
    """Custom observer for tutorial-specific metrics."""

    def __init__(self):
        self.test_durations = {}
        self.connection_attempts = 0
        self.successful_handshakes = 0

    def handle_event(self, event):
        """Handle incoming events and collect metrics."""

        if isinstance(event, TestEvent):
            self._handle_test_event(event)
        elif isinstance(event, ExperimentEvent):
            self._handle_experiment_event(event)

    def _handle_test_event(self, event: TestEvent):
        """Process test-specific events."""
        if event.action == "started":
            self.connection_attempts += 1
            print(f"🚀 Test started: {event.test_case_id}")

        elif event.action == "completed":
            if event.status == "success":
                self.successful_handshakes += 1
                print(f"✅ Test completed: {event.test_case_id}")
            else:
                print(f"❌ Test failed: {event.test_case_id}")

            # Record duration if available
            if event.duration_ms:
                self.test_durations[event.test_case_id] = event.duration_ms

    def _handle_experiment_event(self, event: ExperimentEvent):
        """Process experiment-level events."""
        if event.phase == "completed":
            self._print_summary()

    def _print_summary(self):
        """Print collected metrics summary."""
        print("\n📊 Tutorial Metrics Summary:")
        print(f"   Connection attempts: {self.connection_attempts}")
        print(f"   Successful handshakes: {self.successful_handshakes}")

        if self.test_durations:
            avg_duration = sum(self.test_durations.values()) / len(self.test_durations)
            print(f"   Average test duration: {avg_duration:.2f}ms")

        success_rate = (self.successful_handshakes / self.connection_attempts) if self.connection_attempts > 0 else 0
        print(f"   Success rate: {success_rate:.2%}")
```

### Using the Custom Observer

```python
# tutorial_with_observer.py
from panther.core.experiment_manager import ExperimentManager
from panther.config.core.manager import ConfigManager
from custom_observer import TutorialMetricsObserver

def run_experiment_with_observer():
    """Run experiment with custom observer."""

    # Load configuration
    config_manager = ConfigManager()
    global_config = config_manager.load_global_config("tutorial_config.yaml")
    experiment_config = config_manager.load_experiment_config("tutorial_config.yaml")

    # Create experiment manager
    manager = ExperimentManager(global_config=global_config)

    # Add custom observer
    custom_observer = TutorialMetricsObserver()
    manager.add_observer(custom_observer)

    # Run experiment
    manager.initialize_experiments(experiment_config)
    manager.run_tests()
    manager.cleanup()

if __name__ == "__main__":
    run_experiment_with_observer()
```

## Step 5: Event-Driven Programming

PANTHER's event system allows you to build reactive applications. Here's an advanced example:

```python
# event_driven_tutorial.py
from panther.core.experiment_manager import ExperimentManager
from panther.core.events.service import ServiceEvent
from panther.core.events.environment import EnvironmentEvent

class ReactiveExperimentController:
    """Reactive controller that responds to experiment events."""

    def __init__(self, manager: ExperimentManager):
        self.manager = manager
        self.setup_event_handlers()

    def setup_event_handlers(self):
        """Subscribe to relevant events."""
        # Subscribe to service events
        self.manager.event_manager.subscribe(
            "service.started",
            self.on_service_started
        )

        self.manager.event_manager.subscribe(
            "service.failed",
            self.on_service_failed
        )

        # Subscribe to environment events
        self.manager.event_manager.subscribe(
            "environment.network_ready",
            self.on_network_ready
        )

    def on_service_started(self, event: ServiceEvent):
        """React to service startup."""
        print(f"🔧 Service {event.service_name} started (container: {event.container_id})")

        # Example: Enable monitoring for this service
        self.enable_service_monitoring(event.service_name)

    def on_service_failed(self, event: ServiceEvent):
        """React to service failure."""
        print(f"🚨 Service {event.service_name} failed (exit code: {event.exit_code})")

        # Example: Trigger automatic recovery
        self.attempt_service_recovery(event.service_name)

    def on_network_ready(self, event: EnvironmentEvent):
        """React to network environment being ready."""
        print(f"🌐 Network environment ready: {event.environment_name}")

        # Example: Run network connectivity tests
        self.validate_network_connectivity()

    def enable_service_monitoring(self, service_name: str):
        """Enable monitoring for a specific service."""
        print(f"   📈 Enabling monitoring for {service_name}")
        # Implementation would add specific monitoring

    def attempt_service_recovery(self, service_name: str):
        """Attempt to recover a failed service."""
        print(f"   🔄 Attempting recovery for {service_name}")
        # Implementation would restart or reconfigure service

    def validate_network_connectivity(self):
        """Validate network connectivity."""
        print(f"   🔍 Validating network connectivity")
        # Implementation would ping between containers

def run_reactive_experiment():
    """Run experiment with reactive event handling."""
    config_manager = ConfigManager()
    global_config = config_manager.load_global_config("tutorial_config.yaml")
    experiment_config = config_manager.load_experiment_config("tutorial_config.yaml")

    # Create experiment manager
    manager = ExperimentManager(global_config=global_config)

    # Create reactive controller
    controller = ReactiveExperimentController(manager)

    # Run experiment - controller will react to events automatically
    manager.initialize_experiments(experiment_config)
    manager.run_tests()
    manager.cleanup()

if __name__ == "__main__":
    run_reactive_experiment()
```

## Step 6: Advanced Configuration

For more complex scenarios, PANTHER supports advanced configuration patterns:

```yaml
# advanced_tutorial_config.yaml
experiment:
  name: "Advanced_QUIC_Testing"
  protocol: "quic"

  # Advanced network configuration
  network_environment:
    type: "docker_compose"
    advanced_options:
      dns_config:
        - "8.8.8.8"
        - "1.1.1.1"
      port_mapping:
        enable_random_ports: true
        port_range: "5000-6000"
      network_conditions:
        latency: "50ms"
        bandwidth: "10Mbps"
        packet_loss: "0.1%"

  # Performance monitoring
  execution_environment:
    type: "profiling"
    profilers:
      - "cpu"
      - "memory"
      - "network"
    sampling_interval: 1000  # ms

  # Multiple test scenarios
  test_cases:
    # Test different QUIC implementations
    - name: "Picoquic_Performance"
      implementation: "picoquic"
      scenario: "throughput_test"
      parameters:
        data_size: "10MB"
        concurrent_connections: 5

    - name: "Quiche_Reliability"
      implementation: "quiche"
      scenario: "stress_test"
      parameters:
        connection_count: 100
        rapid_connects: true

    # Version-specific testing
    - name: "QUIC_v1_Compatibility"
      implementation: "aioquic"
      scenario: "version_negotiation"
      parameters:
        quic_versions: ["1", "draft-29"]

  # Advanced observers
  observers:
    - type: "metrics_collector"
      config:
        export_formats: ["json", "prometheus"]

    - type: "packet_analyzer"
      config:
        capture_filter: "port 443"
        analysis_types: ["handshake", "data_transfer"]
```

## Step 7: Validation and Testing

Verify your configuration before running experiments:

```bash
# Validate configuration syntax
panther config validate --config tutorial_config.yaml

# Check plugin availability
panther plugins list --protocol quic

# Dry run (validate without execution)
panther run --config tutorial_config.yaml --dry-run

# Run with verbose logging
panther run --config tutorial_config.yaml --log-level DEBUG
```

## Common Issues and Solutions

### Issue: Docker Permission Errors

```bash
# Solution: Add user to docker group
sudo usermod -aG docker $USER
# Then logout and login again
```

### Issue: Port Conflicts

```yaml
# Solution: Use random port allocation
network_environment:
  advanced_options:
    port_mapping:
      enable_random_ports: true
```

### Issue: Plugin Not Found

```bash
# Solution: Check plugin discovery paths
panther plugins discover --path ./custom_plugins/
```

## Next Steps

After completing this tutorial, explore:

1. **Custom Plugin Development** — Create protocol-specific plugins
2. **Advanced Network Environments** — Use Shadow NS for deterministic testing
3. **Integration Testing** — Combine PANTHER with CI/CD pipelines
4. **Performance Analysis** — Deep-dive into metrics and profiling
5. **Formal Verification** — Use Ivy integration for protocol verification

## Related Documentation

- [Core Module API Reference](../api_reference.md) — Complete API documentation
- [Configuration Guide](../../config/README.md) — Advanced configuration options
- [Plugin Development](../../plugins/development.md) — Creating custom plugins
- [Network Environments](../../plugins/environments/network_environment/README.md) — Network setup options

---

**Congratulations!** You've completed the PANTHER core tutorial. You now understand how to configure experiments, run tests programmatically, add custom observers, and use event-driven programming patterns.

For questions or support, visit our [GitHub repository](https://github.com/ElNiak/PANTHER) or [documentation site](https://elniak.github.io/PANTHER/).
