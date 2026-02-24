# PANTHER Tester Plugins

**Formal Verification and Protocol Testing Services**

Tester plugins in PANTHER provide sophisticated testing and validation capabilities for protocol implementations. These services generate test traffic, perform conformance verification, and validate protocol behavior using formal methods, specification-based testing, and comprehensive test suites.

<!-- src: /panther/plugins/services/testers/ -->

## Tester Categories

### Formal Verification Testers

Testing tools that use formal methods and mathematical verification to validate protocol implementations against their specifications.

| Tester | Purpose | Technology | Documentation |
|---------|---------|------------|---------------|
| **Panther Ivy** | Specification-based testing and formal verification | Microsoft Ivy framework | [Documentation](panther_ivy/README.md) |

## Quick Start

### Using a Tester Plugin

```python
# filepath: example_tester_usage.py
from panther.plugins.plugin_loader import PluginLoader

# Load the Panther Ivy tester plugin
loader = PluginLoader()
ivy_tester = loader.load_plugin('services', 'testers', 'panther_ivy')

# Configure the tester
config = {
    "protocol": "quic",
    "specification": "/specs/quic_spec.ivy",
    "target_implementation": "picoquic",
    "test_scenarios": ["handshake", "data_transfer", "connection_migration"],
    "output_format": "junit"
}

# Initialize and run tests
ivy_tester.initialize(config)
results = ivy_tester.run_tests()
```

### Running Formal Verification

```python
# filepath: example_formal_verification.py
from panther.plugins.services.testers.panther_ivy import PantherIvyTester

# Set up formal verification testing
tester = PantherIvyTester()
tester.configure({
    "verification_mode": "compositional",
    "protocol_model": "/models/quic_transport.ivy",
    "implementation_config": {
        "type": "picoquic",
        "role": "server",
        "port": 4433
    },
    "test_generation": {
        "depth": 10,
        "coverage_target": 0.95,
        "property_checks": ["safety", "liveness"]
    }
})

# Execute verification
verification_results = tester.verify_implementation()
```

## Tester Architecture

### Base Tester Interface

All tester plugins inherit from the base `ITester` interface:

```python
# filepath: /panther/plugins/services/testers/tester_interface.py
from abc import ABC, abstractmethod
from typing import Dict, List, Any

class ITester(ABC):
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.test_results = []

    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the tester with configuration"""
        pass

    @abstractmethod
    def run_tests(self) -> Dict[str, Any]:
        """Execute the test suite"""
        pass

    @abstractmethod
    def generate_report(self) -> str:
        """Generate test report"""
        pass
```

### Test Result Management

Standardized test result format across all testers:

```python
# Test result structure
test_result = {
    "test_id": "quic_handshake_001",
    "test_name": "QUIC Initial Handshake",
    "status": "PASS|FAIL|SKIP",
    "duration": 1.234,  # seconds
    "properties_verified": ["connection_establishment", "crypto_negotiation"],
    "violations": [],  # List of property violations if any
    "metrics": {
        "packets_sent": 42,
        "packets_received": 38,
        "rtt_ms": 15.6
    },
    "artifacts": {
        "pcap_file": "/results/trace.pcap",
        "log_file": "/results/test.log",
        "qlog_file": "/results/trace.qlog"
    }
}
```

## Testing Methodologies

### Specification-Based Testing

- **Model-Driven Testing**: Generate tests from formal protocol models
- **Property Verification**: Validate safety and liveness properties
- **State Space Exploration**: Systematic exploration of protocol states
- **Invariant Checking**: Continuous verification of protocol invariants

### Conformance Testing

- **RFC Compliance**: Verification against protocol specifications
- **Edge Case Testing**: Boundary condition and error scenario testing
- **Regression Testing**: Automated testing for implementation changes
- **Compatibility Testing**: Cross-implementation interoperability

### Performance Testing

- **Load Testing**: High-volume traffic generation
- **Stress Testing**: Resource exhaustion and recovery
- **Endurance Testing**: Long-term operation validation
- **Scalability Testing**: Multi-connection and multi-stream scenarios

## Configuration Patterns

### Basic Tester Configuration

```yaml
testers:
  ivy_formal_verification:
    type: "panther_ivy"
    protocol: "quic"
    specification_file: "/specs/quic_rfc9000.ivy"
    test_scenarios:
      - "initial_handshake"
      - "key_exchange"
      - "data_transfer"
      - "connection_migration"
    verification_depth: 15
    property_checks:
      - "no_packet_loss_without_network_drop"
      - "ordered_stream_delivery"
      - "connection_state_consistency"
```

### Multi-Implementation Testing

```yaml
testers:
  interoperability:
    type: "cross_implementation"
    implementations:
      - name: "picoquic"
        role: "server"
        config: {port: 4433}
      - name: "quic_go"
        role: "client"
        config: {server_addr: "picoquic:4433"}
    test_matrix:
      - scenario: "basic_handshake"
        variations: ["ipv4", "ipv6"]
      - scenario: "version_negotiation"
        versions: ["draft-29", "v1"]
```

### Performance Testing Configuration

```yaml
testers:
  load_generator:
    type: "performance"
    target:
      implementation: "lsquic"
      endpoint: "server:4433"
    load_profile:
      concurrent_connections: 1000
      requests_per_connection: 100
      ramp_up_time: "30s"
      test_duration: "5m"
    metrics:
      - "connection_setup_time"
      - "request_response_latency"
      - "throughput_mbps"
      - "cpu_utilization"
```

## Test Automation

### Continuous Integration

```yaml
# .github/workflows/protocol-testing.yml
name: Protocol Testing
on: [push, pull_request]

jobs:
  formal_verification:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Ivy Formal Verification
        run: |
          python -m panther.test \
            --tester panther_ivy \
            --protocol quic \
            --implementation picoquic \
            --specification specs/quic_rfc9000.ivy

  conformance_testing:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        implementation: [picoquic, quic_go, quinn, mvfst]
    steps:
      - name: Run Conformance Tests
        run: |
          python -m panther.test \
            --tester conformance \
            --implementation ${{ matrix.implementation }} \
            --test_suite rfc_compliance
```

### Test Orchestration

```python
# filepath: test_orchestration_example.py
from panther.testing.orchestrator import TestOrchestrator

# Define test campaign
campaign = TestOrchestrator()

# Add formal verification phase
campaign.add_phase("formal_verification", {
    "tester": "panther_ivy",
    "implementations": ["picoquic", "quic_go"],
    "protocols": ["quic"],
    "test_depth": 10
})

# Add performance testing phase
campaign.add_phase("performance", {
    "tester": "load_generator",
    "implementations": ["lsquic", "mvfst"],
    "load_profiles": ["light", "moderate", "heavy"]
})

# Execute campaign
results = campaign.execute()
campaign.generate_report(results, format="html")
```

## Development Guidelines

### Creating a New Tester Plugin

1. **Inherit Base Interface**: Extend `ITester` with your specific functionality
2. **Define Test Scenarios**: Create comprehensive test scenario definitions
3. **Implement Configuration**: Support flexible configuration options
4. **Handle Results**: Generate standardized test result formats
5. **Add Documentation**: Document test capabilities and usage patterns

### Tester Plugin Structure

```text
my_tester/
├── __init__.py
├── my_tester.py           # Main tester implementation
├── config_schema.py       # Configuration validation
├── test_scenarios/        # Test scenario definitions
│   ├── basic_tests.py
│   └── advanced_tests.py
├── templates/            # Test templates and generators
├── results/              # Result processing utilities
└── README.md            # Tester documentation
```

### Example Tester Implementation

```python
# filepath: custom_tester_example.py
from panther.plugins.services.testers.tester_interface import ITester
import logging
from typing import Dict, Any, List

class CustomProtocolTester(ITester):
    def __init__(self):
        super().__init__()
        self.test_scenarios = []
        self.target_implementation = None

    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize tester with configuration"""
        self.target_implementation = config.get('implementation')
        self.test_scenarios = config.get('test_scenarios', [])
        self.logger.info(f"Initialized tester for {self.target_implementation}")

    def run_tests(self) -> Dict[str, Any]:
        """Execute test scenarios"""
        results = []

        for scenario in self.test_scenarios:
            self.logger.info(f"Running scenario: {scenario}")
            result = self._execute_scenario(scenario)
            results.append(result)

        return {
            "total_tests": len(results),
            "passed": len([r for r in results if r['status'] == 'PASS']),
            "failed": len([r for r in results if r['status'] == 'FAIL']),
            "results": results
        }

    def _execute_scenario(self, scenario: str) -> Dict[str, Any]:
        """Execute individual test scenario"""
        # Implementation-specific test logic
        pass

    def generate_report(self) -> str:
        """Generate comprehensive test report"""
        # Report generation logic
        pass
```

## Integration Examples

### Web Dashboard Integration

```python
# Flask web interface for test results
from flask import Flask, render_template, jsonify
from panther.plugins.services.testers import get_test_results

app = Flask(__name__)

@app.route('/test-results')
def test_results():
    results = get_test_results()
    return render_template('test_results.html', results=results)

@app.route('/api/test-status')
def test_status():
    return jsonify({
        "status": "running",
        "progress": "75%",
        "current_test": "quic_handshake_verification"
    })
```

### Notification Integration

```python
# Slack notification for test completion
from panther.integrations.slack import SlackNotifier

def notify_test_completion(results):
    notifier = SlackNotifier()
    message = f"""
    🧪 Test Campaign Completed

    **Results Summary:**
    • Total Tests: {results['total_tests']}
    • Passed: {results['passed']} ✅
    • Failed: {results['failed']} ❌
    • Success Rate: {results['success_rate']}%

    View detailed results: {results['report_url']}
    """
    notifier.send_message(message, channel="#testing")
```

## Troubleshooting

### Common Issues

**Test Execution Failures**

- Verify tester plugin configuration and dependencies
- Check target implementation availability and status
- Review test scenario definitions and parameters
- Validate network connectivity and firewall rules

**Performance Issues**

- Monitor resource usage during test execution
- Tune test parallelism and concurrency settings
- Check for memory leaks in long-running tests
- Profile test execution bottlenecks

**Result Analysis Problems**

- Verify result collection and storage mechanisms
- Check log file permissions and disk space
- Review test artifact generation and cleanup
- Validate result format compatibility

### Debug Configuration

```yaml
testers:
  debug_tester:
    type: "panther_ivy"
    debug_mode: true
    log_level: "DEBUG"
    artifact_retention: "all"
    timeout_settings:
      test_timeout: "300s"
      setup_timeout: "60s"
    resource_monitoring:
      cpu_profiling: true
      memory_tracking: true
```

## Related Documentation

- [Service Plugin Overview](../README.md): General service plugin architecture
- [Protocol Plugins](../../protocols/README.md): Protocol-specific testing

## References

- [Microsoft Ivy Framework](https://github.com/microsoft/ivy)
- [Protocol Testing Methodologies](https://tools.ietf.org/html/rfc2544)
- [Formal Verification in Networking](https://doi.org/10.1145/3123939.3123952)
- [QUIC Protocol Testing](https://github.com/quicwg/base-drafts)
