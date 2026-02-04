# PANTHER Tester Services Tutorial: Formal Verification and Protocol Testing

## Overview

This tutorial provides hands-on experience with PANTHER's tester services, focusing on formal verification using the Panther Ivy framework. You'll learn to set up, configure, and execute formal verification tests for network protocols.

## Prerequisites

- Python 3.10+
- Docker 27.x+ with Docker Compose
- Basic understanding of formal verification concepts
- Familiarity with QUIC protocol (for examples)
- 30 minutes for complete tutorial

## Installation and Setup

### Install PANTHER with Tester Support

```bash
# Clone with submodules (required for Ivy)
git clone --recursive https://github.com/ElNiak/PANTHER.git
cd PANTHER

# Install with tester dependencies
pip install -e ".[testers]"

# Verify Ivy integration
python -c "from panther.plugins.services.testers.panther_ivy import PantherIvyServiceManager; print('Ivy tester available')"
```

### Docker Environment Setup

```bash
# Build Ivy container
docker-compose -f docker/docker-compose.ivy.yml build

# Verify container
docker run --rm panther/ivy:latest ivy_check --version
```

## Tutorial Structure

This tutorial covers:

1. **Basic Formal Verification** — Simple QUIC handshake verification
2. **Advanced Configuration** — Custom build modes and optimization
3. **Output Analysis** — Understanding verification results
4. **Custom Test Development** — Creating new formal verification tests
5. **Integration Patterns** — Combining with other PANTHER services

## Section 1: Basic Formal Verification

### Create Basic Configuration

Create `ivy_tutorial_config.yaml`:

```yaml
# Global PANTHER configuration
global:
  paths:
    output_dir: "./ivy_tutorial_outputs"
    plugin_dir: "./plugins"
  logging:
    level: "INFO"
    format: "structured"
  docker:
    enabled: true
    build_timeout: 600  # Ivy compilation can take time

# Experiment configuration for formal verification
experiment:
  name: "QUIC_Formal_Verification_Tutorial"
  protocol: "quic"

  # Network environment for testing
  network_environment:
    type: "docker_compose"
    network_name: "ivy_verification_network"
    subnet: "192.168.20.0/24"

  # Basic execution environment
  execution_environment:
    type: "basic"
    timeout: 300  # Allow time for formal verification

  # Test cases using Ivy formal verification
  test_cases:
    - name: "QUIC_Server_Handshake_Verification"
      implementation: "panther_ivy"
      scenario: "formal_verification"
      protocol:
        name: "quic"
        role: "server"
      plugin_config:
        test: "quic_server_test_connect"
        build_mode: ""  # Standard build for basic verification
        log_level_binary: "INFO"
        optimization_level: "O0"
        iterations_per_test: 1
        timeout: 240

    - name: "QUIC_Client_Handshake_Verification"
      implementation: "panther_ivy"
      scenario: "formal_verification"
      protocol:
        name: "quic"
        role: "client"
      plugin_config:
        test: "quic_client_test_connect"
        build_mode: ""
        log_level_binary: "INFO"
        optimization_level: "O0"
        iterations_per_test: 1
        timeout: 240
```

### Run Basic Formal Verification

```bash
# Execute formal verification
panther run --config ivy_tutorial_config.yaml

# Expected output:
# [INFO] Initializing experiment: QUIC_Formal_Verification_Tutorial
# [INFO] Loading formal verification plugin: panther_ivy
# [INFO] Compiling Ivy test: quic_server_test_connect
# [INFO] Running formal verification...
# [INFO] Verification completed successfully
# [INFO] Results available in: ./ivy_tutorial_outputs/
```

### Examine Verification Results

```bash
# Navigate to results
cd ivy_tutorial_outputs/QUIC_Formal_Verification_Tutorial_*/

# View experiment summary
cat experiment_summary.json

# Check individual verification results
ls test_results/
cat test_results/QUIC_Server_Handshake_Verification/test_result.json
```

#### Sample Verification Result

```json
{
  "test_id": "QUIC_Server_Handshake_Verification",
  "success": true,
  "verification_results": {
    "properties_verified": [
      "connection_establishment",
      "state_consistency",
      "protocol_compliance"
    ],
    "invariants_checked": 47,
    "properties_passed": 12,
    "verification_time": 45.6,
    "memory_usage": "2.3 GB"
  },
  "ivy_analysis": {
    "compilation_successful": true,
    "solver_iterations": 150,
    "counterexamples_found": 0,
    "warnings": []
  },
  "artifacts": {
    "ivy_log": "ivy_quic_server_test_connect.log",
    "compilation_output": "compilation_output.log",
    "verification_trace": "verification_trace.txt"
  }
}
```

## Section 2: Advanced Configuration and Build Modes

### Performance-Optimized Configuration

Create `ivy_performance_config.yaml`:

```yaml
experiment:
  name: "QUIC_Performance_Verification"
  protocol: "quic"

  # Use performance-optimized settings
  test_cases:
    - name: "QUIC_High_Performance_Verification"
      implementation: "panther_ivy"
      scenario: "performance_verification"
      protocol:
        name: "quic"
        role: "server"
      plugin_config:
        test: "quic_server_test_performance"
        build_mode: "rel-lto"           # Release with Link Time Optimization
        optimization_level: "O3"        # Maximum optimization
        log_level_binary: "INFO"        # Reduced logging for performance
        iterations_per_test: 5          # Multiple iterations for statistics
        internal_iterations_per_test: 500
        timeout: 600
        use_system_models: false        # Use protocol-specific models
```

### Debug-Enabled Configuration

Create `ivy_debug_config.yaml`:

```yaml
experiment:
  name: "QUIC_Debug_Verification"
  protocol: "quic"

  test_cases:
    - name: "QUIC_Debug_Verification"
      implementation: "panther_ivy"
      scenario: "debug_verification"
      protocol:
        name: "quic"
        role: "server"
      plugin_config:
        test: "quic_server_test_debug"
        build_mode: "debug-asan"        # Debug with AddressSanitizer
        optimization_level: "O0"        # No optimization for debugging
        log_level_binary: "DEBUG"       # Maximum logging detail
        log_level_events: "DEBUG"       # Detailed event logging
        iterations_per_test: 1
        get_tests_stats: true           # Collect detailed statistics
        timeout: 900                    # Longer timeout for debug builds
```

### Execute Advanced Configurations

```bash
# Run performance verification
panther run --config ivy_performance_config.yaml

# Run debug verification
panther run --config ivy_debug_config.yaml

# Compare results
diff -u ivy_tutorial_outputs/QUIC_Performance_Verification_*/experiment_summary.json \
        ivy_tutorial_outputs/QUIC_Debug_Verification_*/experiment_summary.json
```

## Section 3: Programmatic API Usage

### Basic Programmatic Verification

Create `tutorial_programmatic.py`:

```python
#!/usr/bin/env python3
"""
Programmatic formal verification tutorial using PANTHER Ivy integration.
"""

from pathlib import Path
from panther.core.experiment_manager import ExperimentManager
from panther.config.core.manager import ConfigManager
from panther.plugins.services.testers.panther_ivy import PantherIvyServiceManager
from panther.config.core.models import ProtocolConfig
from panther.config.core.models.service import ServiceConfig

def run_basic_verification():
    """Execute basic formal verification programmatically."""

    print("🔍 Starting PANTHER Ivy Formal Verification Tutorial")

    # Load configuration
    config_manager = ConfigManager()
    global_config = config_manager.load_global_config("ivy_tutorial_config.yaml")
    experiment_config = config_manager.load_experiment_config("ivy_tutorial_config.yaml")

    # Create experiment manager
    manager = ExperimentManager(
        global_config=global_config,
        experiment_name="Programmatic_Ivy_Verification"
    )

    try:
        # Initialize and run verification
        print("📋 Initializing formal verification experiment...")
        manager.initialize_experiments(experiment_config)

        print("🚀 Running formal verification tests...")
        results = manager.run_tests()

        # Display results
        print("\n📊 Verification Results Summary:")
        print(f"   Total tests: {results['total_tests']}")
        print(f"   Successful verifications: {results['passed']}")
        print(f"   Failed verifications: {results['failed']}")
        print(f"   Overall success rate: {results['success_rate']:.2%}")

        # Show individual test results
        print("\n🔬 Individual Verification Results:")
        for test_name, test_result in results['test_results'].items():
            status_icon = "✅" if test_result['status'] == 'PASS' else "❌"
            print(f"   {status_icon} {test_name}: {test_result['status']}")

            if 'verification_results' in test_result:
                verification = test_result['verification_results']
                print(f"      Properties verified: {len(verification.get('properties_verified', []))}")
                print(f"      Verification time: {verification.get('verification_time', 0):.1f}s")

        return results

    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return None

    finally:
        # Cleanup resources
        print("🧹 Cleaning up resources...")
        manager.cleanup()

def run_custom_verification():
    """Execute custom verification with specific configuration."""

    print("\n🛠️  Running Custom Ivy Verification")

    # Create custom protocol configuration
    protocol = ProtocolConfig(name="quic", role="server")

    # Create custom service configuration
    service_config = ServiceConfig(
        name="custom_ivy_verification",
        implementation="panther_ivy",
        plugin_config={
            "test": "quic_server_test_custom",
            "build_mode": "debug-asan",
            "optimization_level": "O1",
            "log_level_binary": "DEBUG",
            "iterations_per_test": 3,
            "timeout": 180,
            "use_system_models": False
        }
    )

    # Initialize Ivy tester directly
    tester = PantherIvyServiceManager(
        service_config_to_test=service_config,
        service_type="TESTERS",
        protocol=protocol,
        implementation_name="panther_ivy"
    )

    try:
        print("🔧 Preparing Ivy verification environment...")
        success = tester.prepare()
        if not success:
            print("❌ Failed to prepare verification environment")
            return None

        print("🧪 Executing formal verification...")
        results = tester.run_tests()

        # Analyze results
        print("\n📈 Custom Verification Analysis:")
        if results['success']:
            print("   ✅ Verification completed successfully")
            analysis = results.get('analysis', {})
            if 'properties_verified' in analysis:
                print(f"   📋 Properties verified: {len(analysis['properties_verified'])}")
            if 'verification_time' in analysis:
                print(f"   ⏱️  Verification time: {analysis['verification_time']:.2f}s")
        else:
            print("   ❌ Verification failed")
            for error in results.get('errors', []):
                print(f"      Error: {error}")

        return results

    except Exception as e:
        print(f"❌ Custom verification failed: {e}")
        return None

if __name__ == "__main__":
    # Run basic verification
    basic_results = run_basic_verification()

    # Run custom verification
    custom_results = run_custom_verification()

    # Summary
    print("\n🎯 Tutorial Summary:")
    if basic_results and basic_results.get('success_rate', 0) > 0:
        print("   ✅ Basic verification tutorial completed successfully")
    else:
        print("   ❌ Basic verification tutorial had issues")

    if custom_results and custom_results.get('success'):
        print("   ✅ Custom verification tutorial completed successfully")
    else:
        print("   ❌ Custom verification tutorial had issues")

    print("\n📚 Next steps:")
    print("   1. Explore different build modes (debug-asan, rel-lto, release-static-pgo)")
    print("   2. Create custom Ivy test specifications")
    print("   3. Integrate with CI/CD pipelines")
    print("   4. Scale to multi-protocol verification campaigns")
```

### Run Programmatic Tutorial

```bash
# Execute programmatic tutorial
python tutorial_programmatic.py

# Expected output shows verification progress and results
```

## Section 4: Custom Test Development

### Understanding Ivy Test Structure

Ivy tests follow a specific structure for formal verification:

```ivy
# Example: custom_quic_test.ivy
#lang ivy1.7

# Import QUIC protocol model
include quic_protocol
include quic_connection

# Define test-specific state
object test_state = {
    var connection_established : bool
    var handshake_completed : bool

    after init {
        connection_established := false;
        handshake_completed := false;
    }
}

# Define properties to verify
property connection_consistency =
    globally (test_state.connection_established -> test_state.handshake_completed)

property handshake_progress =
    eventually test_state.handshake_completed

# Define test actions
action client_connect = {
    require ~test_state.connection_established;
    # Implementation for connection logic
    test_state.connection_established := true;
}

action complete_handshake = {
    require test_state.connection_established;
    # Implementation for handshake completion
    test_state.handshake_completed := true;
}

# Export test for PANTHER integration
export client_connect
export complete_handshake
```

### Create Custom Test Configuration

Create `custom_test_config.yaml`:

```yaml
experiment:
  name: "Custom_QUIC_Test_Verification"
  protocol: "quic"

  test_cases:
    - name: "Custom_QUIC_Connection_Test"
      implementation: "panther_ivy"
      scenario: "custom_verification"
      protocol:
        name: "quic"
        role: "client"
      plugin_config:
        test: "custom_quic_test"        # Your custom test name
        build_mode: ""
        optimization_level: "O1"
        iterations_per_test: 2
        internal_iterations_per_test: 200
        timeout: 300
        # Custom environment variables for your test
        environment:
          CUSTOM_TEST_PARAM: "value"
          VERIFICATION_DEPTH: "15"
```

### Implement Custom Test Handler

Create `custom_verification.py`:

```python
#!/usr/bin/env python3
"""
Custom Ivy verification implementation example.
"""

from typing import Dict, Any
from panther.plugins.services.testers.panther_ivy import PantherIvyServiceManager

class CustomIvyVerification:
    """Custom verification workflow implementation."""

    def __init__(self, config_file: str):
        self.config_file = config_file
        self.results = {}

    def setup_custom_test(self):
        """Set up custom test environment."""
        # Copy custom Ivy test files
        # Set up custom protocol models
        # Configure verification parameters
        print("🔧 Setting up custom Ivy test environment")

    def run_verification(self) -> Dict[str, Any]:
        """Execute custom verification workflow."""
        try:
            # Load configuration
            from panther.config.core.manager import ConfigManager
            config_manager = ConfigManager()
            global_config = config_manager.load_global_config(self.config_file)
            experiment_config = config_manager.load_experiment_config(self.config_file)

            # Initialize experiment
            from panther.core.experiment_manager import ExperimentManager
            manager = ExperimentManager(
                global_config=global_config,
                experiment_name="Custom_Verification"
            )

            # Set up custom test
            self.setup_custom_test()

            # Execute verification
            print("🚀 Running custom formal verification...")
            manager.initialize_experiments(experiment_config)
            results = manager.run_tests()

            # Post-process results
            processed_results = self.process_verification_results(results)

            manager.cleanup()
            return processed_results

        except Exception as e:
            print(f"❌ Custom verification failed: {e}")
            return {"success": False, "error": str(e)}

    def process_verification_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Process and enhance verification results."""
        processed = {
            "success": results.get('success_rate', 0) > 0,
            "total_tests": results.get('total_tests', 0),
            "verification_summary": {},
            "custom_metrics": {}
        }

        # Extract custom metrics
        for test_name, test_result in results.get('test_results', {}).items():
            if 'verification_results' in test_result:
                verification = test_result['verification_results']
                processed['verification_summary'][test_name] = {
                    "properties_verified": len(verification.get('properties_verified', [])),
                    "verification_time": verification.get('verification_time', 0),
                    "solver_iterations": verification.get('solver_iterations', 0)
                }

        return processed

# Usage example
if __name__ == "__main__":
    verifier = CustomIvyVerification("custom_test_config.yaml")
    results = verifier.run_verification()

    print("\n📊 Custom Verification Results:")
    print(f"   Success: {results['success']}")
    print(f"   Total tests: {results['total_tests']}")

    for test_name, summary in results.get('verification_summary', {}).items():
        print(f"   {test_name}:")
        print(f"     Properties verified: {summary['properties_verified']}")
        print(f"     Verification time: {summary['verification_time']:.2f}s")
```

## Section 5: Output Analysis and Debugging

### Understanding Ivy Output Patterns

Ivy generates several types of output files:

```bash
# Navigate to test results
cd ivy_tutorial_outputs/*/test_results/QUIC_Server_Handshake_Verification/

# Core output files
ls -la
# ivy_quic_server_test_connect.log    # Main Ivy execution log
# stdout.log                          # Standard output
# stderr.log                          # Error output
# compilation_status.txt              # Compilation results
# test_results.json                   # Structured results
```

### Analyze Verification Logs

Create `analyze_results.py`:

```python
#!/usr/bin/env python3
"""
Ivy verification result analysis tool.
"""

import json
import re
from pathlib import Path
from typing import Dict, Any, List

class IvyResultAnalyzer:
    """Analyzer for Ivy formal verification results."""

    def __init__(self, results_directory: str):
        self.results_dir = Path(results_directory)
        self.analysis = {}

    def analyze_verification_log(self, log_file: Path) -> Dict[str, Any]:
        """Analyze main Ivy verification log."""
        if not log_file.exists():
            return {"error": "Log file not found"}

        content = log_file.read_text()
        analysis = {
            "compilation_successful": False,
            "verification_successful": False,
            "properties_checked": [],
            "invariants_verified": [],
            "counterexamples": [],
            "warnings": [],
            "errors": []
        }

        # Check compilation success
        if "compilation successful" in content.lower():
            analysis["compilation_successful"] = True

        # Check verification success
        if "verification successful" in content.lower():
            analysis["verification_successful"] = True

        # Extract properties checked
        property_pattern = r"checking property\s+(\w+)"
        analysis["properties_checked"] = re.findall(property_pattern, content, re.IGNORECASE)

        # Extract invariants
        invariant_pattern = r"invariant\s+(\w+)\s+verified"
        analysis["invariants_verified"] = re.findall(invariant_pattern, content, re.IGNORECASE)

        # Extract counterexamples
        counterexample_pattern = r"counterexample found for\s+(\w+)"
        analysis["counterexamples"] = re.findall(counterexample_pattern, content, re.IGNORECASE)

        # Extract warnings
        warning_pattern = r"warning:\s+(.+)"
        analysis["warnings"] = re.findall(warning_pattern, content, re.IGNORECASE)

        # Extract errors
        error_pattern = r"error:\s+(.+)"
        analysis["errors"] = re.findall(error_pattern, content, re.IGNORECASE)

        return analysis

    def analyze_performance_metrics(self, log_file: Path) -> Dict[str, Any]:
        """Extract performance metrics from verification log."""
        if not log_file.exists():
            return {}

        content = log_file.read_text()
        metrics = {}

        # Extract timing information
        time_pattern = r"verification time:\s+([\d.]+)\s*seconds"
        time_match = re.search(time_pattern, content, re.IGNORECASE)
        if time_match:
            metrics["verification_time"] = float(time_match.group(1))

        # Extract memory usage
        memory_pattern = r"memory usage:\s+([\d.]+)\s*(MB|GB)"
        memory_match = re.search(memory_pattern, content, re.IGNORECASE)
        if memory_match:
            value = float(memory_match.group(1))
            unit = memory_match.group(2).upper()
            metrics["memory_usage_mb"] = value if unit == "MB" else value * 1024

        # Extract solver iterations
        solver_pattern = r"solver iterations:\s+(\d+)"
        solver_match = re.search(solver_pattern, content, re.IGNORECASE)
        if solver_match:
            metrics["solver_iterations"] = int(solver_match.group(1))

        return metrics

    def generate_analysis_report(self) -> Dict[str, Any]:
        """Generate comprehensive analysis report."""
        report = {
            "summary": {},
            "test_results": {},
            "overall_status": "unknown"
        }

        test_dirs = [d for d in self.results_dir.iterdir() if d.is_dir()]

        total_tests = len(test_dirs)
        successful_tests = 0

        for test_dir in test_dirs:
            test_name = test_dir.name

            # Analyze main log
            ivy_log = test_dir / "ivy_*.log"
            ivy_logs = list(test_dir.glob("ivy_*.log"))

            if ivy_logs:
                log_analysis = self.analyze_verification_log(ivy_logs[0])
                performance = self.analyze_performance_metrics(ivy_logs[0])

                report["test_results"][test_name] = {
                    **log_analysis,
                    "performance": performance
                }

                if log_analysis.get("verification_successful", False):
                    successful_tests += 1
            else:
                report["test_results"][test_name] = {"error": "No log files found"}

        # Generate summary
        report["summary"] = {
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "success_rate": successful_tests / total_tests if total_tests > 0 else 0,
            "failed_tests": total_tests - successful_tests
        }

        report["overall_status"] = "success" if successful_tests == total_tests else "partial" if successful_tests > 0 else "failure"

        return report

# Usage example
def analyze_tutorial_results():
    """Analyze tutorial verification results."""
    import glob

    # Find latest results directory
    result_dirs = glob.glob("ivy_tutorial_outputs/QUIC_*_Tutorial_*/test_results")
    if not result_dirs:
        print("❌ No tutorial results found. Run the tutorial first.")
        return

    latest_results = sorted(result_dirs)[-1]
    print(f"📊 Analyzing results from: {latest_results}")

    analyzer = IvyResultAnalyzer(latest_results)
    report = analyzer.generate_analysis_report()

    # Display summary
    print("\n🎯 Verification Analysis Summary:")
    summary = report["summary"]
    print(f"   Total tests: {summary['total_tests']}")
    print(f"   Successful: {summary['successful_tests']}")
    print(f"   Failed: {summary['failed_tests']}")
    print(f"   Success rate: {summary['success_rate']:.2%}")
    print(f"   Overall status: {report['overall_status']}")

    # Display individual test results
    print("\n🔬 Individual Test Analysis:")
    for test_name, result in report["test_results"].items():
        if "error" in result:
            print(f"   ❌ {test_name}: {result['error']}")
        else:
            status = "✅" if result.get("verification_successful") else "❌"
            print(f"   {status} {test_name}:")
            print(f"      Compilation: {'✅' if result.get('compilation_successful') else '❌'}")
            print(f"      Properties checked: {len(result.get('properties_checked', []))}")
            print(f"      Invariants verified: {len(result.get('invariants_verified', []))}")

            if result.get("counterexamples"):
                print(f"      ⚠️  Counterexamples: {len(result['counterexamples'])}")

            performance = result.get("performance", {})
            if "verification_time" in performance:
                print(f"      Verification time: {performance['verification_time']:.2f}s")
            if "memory_usage_mb" in performance:
                print(f"      Memory usage: {performance['memory_usage_mb']:.1f} MB")

    return report

if __name__ == "__main__":
    analyze_tutorial_results()
```

### Run Analysis Tool

```bash
# Analyze tutorial results
python analyze_results.py

# Expected output shows detailed verification analysis
```

## Section 6: Integration with CI/CD

### GitHub Actions Integration

Create `.github/workflows/ivy-verification.yml`:

```yaml
name: Ivy Formal Verification

on:
  push:
    branches: [main, develop]
    paths: ['protocols/**', 'tests/**']
  pull_request:
    branches: [main]
    paths: ['protocols/**', 'tests/**']

jobs:
  formal-verification:
    runs-on: ubuntu-latest
    timeout-minutes: 60

    steps:
    - name: Checkout code
      uses: actions/checkout@v3
      with:
        submodules: recursive

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'

    - name: Install PANTHER with Ivy
      run: |
        pip install -e ".[testers]"

    - name: Run QUIC formal verification
      run: |
        panther run --config configs/ivy_ci_config.yaml

    - name: Analyze verification results
      run: |
        python scripts/analyze_ivy_results.py

    - name: Upload verification artifacts
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: ivy-verification-results
        path: |
          ivy_tutorial_outputs/
          **/*.log
          **/*_results.json
        retention-days: 30

    - name: Generate verification report
      run: |
        python scripts/generate_verification_report.py > verification_report.md

    - name: Comment PR with results
      if: github.event_name == 'pull_request'
      uses: actions/github-script@v6
      with:
        script: |
          const fs = require('fs');
          const report = fs.readFileSync('verification_report.md', 'utf8');
          github.rest.issues.createComment({
            issue_number: context.issue.number,
            owner: context.repo.owner,
            repo: context.repo.repo,
            body: `## 🔍 Formal Verification Results\n\n${report}`
          });
```

### CI Configuration File

Create `configs/ivy_ci_config.yaml`:

```yaml
# CI-optimized configuration for formal verification
global:
  paths:
    output_dir: "./ci_verification_outputs"
  logging:
    level: "INFO"
  docker:
    enabled: true
    build_timeout: 900

experiment:
  name: "CI_Formal_Verification"
  protocol: "quic"

  execution_environment:
    type: "basic"
    timeout: 1200  # 20 minutes for CI

  test_cases:
    # Essential verification tests for CI
    - name: "QUIC_Core_Properties"
      implementation: "panther_ivy"
      protocol:
        name: "quic"
        role: "server"
      plugin_config:
        test: "quic_core_properties"
        build_mode: "rel-lto"        # Optimized for CI speed
        optimization_level: "O2"
        iterations_per_test: 1       # Single iteration for CI
        internal_iterations_per_test: 100  # Reduced for speed
        timeout: 600

    - name: "QUIC_Safety_Check"
      implementation: "panther_ivy"
      protocol:
        name: "quic"
        role: "client"
      plugin_config:
        test: "quic_safety_properties"
        build_mode: "rel-lto"
        optimization_level: "O2"
        iterations_per_test: 1
        internal_iterations_per_test: 100
        timeout: 600
```

## Troubleshooting Common Issues

### Issue 1: Ivy Compilation Failures

**Symptom**: Compilation errors during test execution

```bash
# Check Ivy installation
docker run --rm panther/ivy:latest ivy_check --version

# Verify protocol models
ls panther/plugins/services/testers/panther_ivy/protocol-testing/quic/

# Check compilation logs
cat ivy_tutorial_outputs/*/test_results/*/compilation_status.txt
```

**Solution**: Ensure Ivy submodules are initialized and dependencies are available

### Issue 2: Verification Timeouts

**Symptom**: Tests timeout before completion

```bash
# Increase timeout in configuration
timeout: 900  # 15 minutes

# Use faster build mode
build_mode: "rel-lto"
optimization_level: "O3"

# Reduce verification depth
internal_iterations_per_test: 100
```

### Issue 3: Memory Issues

**Symptom**: Out of memory errors during verification

```bash
# Monitor memory usage
docker stats

# Use memory-optimized settings
build_mode: "release-static-pgo"
optimization_level: "Os"  # Optimize for size
```

### Issue 4: Container Permission Issues

**Symptom**: Docker permission errors

```bash
# Fix Docker permissions
sudo usermod -aG docker $USER
# Logout and login again

# Use rootless Docker if available
systemctl --user start docker
```

## Next Steps and Advanced Topics

### 1. Custom Protocol Models

- Develop Ivy models for custom protocols
- Integrate with existing PANTHER protocol plugins
- Create protocol-specific verification properties

### 2. Multi-Implementation Testing

- Verify multiple protocol implementations
- Compare verification results across implementations
- Create implementation compatibility matrices

### 3. Performance Benchmarking

- Use verification results for performance analysis
- Create benchmarking suites with formal verification
- Integrate with performance monitoring systems

### 4. Advanced Verification Techniques

- Bounded model checking with Ivy
- Inductive invariant discovery
- Compositional verification for large systems

## Related Documentation

- [Tester Services API Reference](../api_reference.md) — Complete API documentation
- [Developer Guide](../DEVELOPER_GUIDE.md) — Development workflows and debugging
- [Ivy Framework Documentation](https://github.com/microsoft/ivy) — Microsoft Ivy formal verification
- [QUIC Protocol Specification](https://tools.ietf.org/html/rfc9000) — Protocol testing reference

## Summary

This tutorial covered:

✅ **Basic Setup** — Installing and configuring PANTHER with Ivy tester support
✅ **Formal Verification** — Running QUIC protocol formal verification tests
✅ **Advanced Configuration** — Using different build modes and optimization levels
✅ **Programmatic Usage** — API-based verification workflows
✅ **Custom Development** — Creating custom Ivy tests and verification logic
✅ **Result Analysis** — Understanding and analyzing verification outputs
✅ **CI/CD Integration** — Automating formal verification in development workflows

You now have comprehensive knowledge of PANTHER's formal verification capabilities using the Ivy framework. This foundation enables you to create robust, formally verified protocol implementations and integrate verification into your development processes.

For questions or support, visit our [GitHub repository](https://github.com/ElNiak/PANTHER) or [documentation site](https://elniak.github.io/PANTHER/).
