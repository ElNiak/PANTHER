# PANTHER Quickstart Tutorial

Get started with PANTHER network protocol testing in 15 minutes. This tutorial walks you through setting up your first experiment, running tests, and understanding the results.

## Prerequisites

Before starting, ensure you have:

```bash
# System requirements
python >= 3.9
docker >= 20.10
docker-compose >= 2.0

# Verify installations
python --version
docker --version
docker-compose --version
```

## Installation

### 1. Install PANTHER

```bash
# Clone the repository
git clone <panther-repository-url>
cd PANTHER

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate.bat  # Windows

# Install PANTHER with dependencies
pip install -e ".[dev]"

# Verify installation
panther --version
```

### 2. Verify Docker Setup

```bash
# Test Docker functionality
docker run hello-world

# Test Docker Compose
docker-compose --version
```

## Your First Experiment

### 1. Create Basic Configuration

Create a simple experiment configuration:

```bash
# Create experiment directory
mkdir my_first_experiment
cd my_first_experiment

# Create global configuration
cat > global_config.yaml << 'EOF'
# Global PANTHER Configuration
paths:
  output_dir: "./outputs"
  plugin_dir: "panther/plugins"

logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  enable_colors: true

execution:
  timeout: 60
  retry_attempts: 1

progress:
  enable_progress_bar: true
  show_test_status: true
  use_emojis: true

fast_fail:
  enabled: true

plugins:
  cache_ttl: 3600
  discovery_timeout: 30
EOF

# Create experiment configuration
cat > experiment_config.yaml << 'EOF'
# PANTHER Experiment Configuration
name: "my_first_experiment"
description: "First PANTHER experiment - QUIC client-server test"

tests:
  - name: "QUIC_Basic_Test"
    description: "Basic QUIC client-server communication test"

    protocol:
      name: "quic"
      port: 4433
      server_address: "server"
      timeout: 30

    environment:
      name: "docker_compose"
      plugin_name: "docker_compose"
      plugin_type: "network"
      parameters:
        network_name: "quic_test_network"
        cleanup_on_exit: true

    services:
      - name: "quic_server"
        plugin_name: "quiche"
        plugin_type: "iut"
        role: "server"
        build_args:
          PROTOCOL: "quic"
        environment:
          SERVER_PORT: "4433"

      - name: "quic_client"
        plugin_name: "quiche"
        plugin_type: "iut"
        role: "client"
        build_args:
          PROTOCOL: "quic"
        environment:
          SERVER_ADDRESS: "server"
          SERVER_PORT: "4433"

    execution:
      timeout: 45
      retry_attempts: 1

    assertions:
      - type: "output_contains"
        target: "client"
        pattern: "connection established"
      - type: "exit_code"
        target: "server"
        expected: 0
      - type: "exit_code"
        target: "client"
        expected: 0
EOF
```

### 2. Validate Configuration

Before running tests, validate your configuration:

```bash
# Validate configuration files
panther config validate --global-config global_config.yaml --experiment-config experiment_config.yaml

# Check plugin availability
panther plugins list --type protocol
panther plugins list --type service
panther plugins list --type environment

# Verify QUIC plugin availability
panther plugins info quiche
```

### 3. Run Your First Test

```bash
# Run the experiment
panther run --global-config global_config.yaml --experiment-config experiment_config.yaml

# Or run with verbose output for learning
panther run --global-config global_config.yaml --experiment-config experiment_config.yaml --verbose

# Or run in dry-run mode first (recommended)
panther run --global-config global_config.yaml --experiment-config experiment_config.yaml --dry-run
```

**Expected Output:**
```
🧪 Starting: QUIC_Basic_Test
📋 Building service images...
🐳 Building quic_server (quiche plugin)
🐳 Building quic_client (quiche plugin)
🌐 Setting up network environment (docker_compose)
🚀 Starting services...
▶️  Running test execution...
✅ Completed: QUIC_Basic_Test

Experiment Summary:
- Total Tests: 1
- Successful: 1
- Failed: 0
- Duration: 45.2s
```

### 4. Examine Results

```bash
# Navigate to output directory
ls outputs/

# Examine experiment results
ls outputs/$(ls outputs/ | tail -1)/

# View experiment log
cat outputs/$(ls outputs/ | tail -1)/experiment.log

# View test-specific results
cat outputs/$(ls outputs/ | tail -1)/QUIC_Basic_Test/test.log
```

## Understanding the Results

### Output Structure

PANTHER organizes results in a structured format:

```
outputs/
└── 2025-07-05_14-30-25_my_first_experiment/
    ├── experiment_config.yaml          # Complete experiment configuration
    ├── experiment.log                   # Main experiment log
    ├── experiment_events.log           # Event timeline
    ├── metrics_observer.log            # Performance metrics
    ├── QUIC_Basic_Test/                # Test-specific results
    │   ├── test_config.yaml            # Test configuration
    │   ├── test.log                     # Test execution log
    │   ├── storage_observer.log        # Detailed events
    │   └── error_events.jsonl          # Error events (if any)
    └── event_debug.log                 # Debug event information
```

### Key Result Files

**experiment.log** - Main experiment execution log:
```
2025-07-05 14:30:25,123 - panther.core.experiment_manager - INFO - ExperimentManager initialized
2025-07-05 14:30:25,234 - panther.core.experiment_manager - INFO - Initializing test case: QUIC_Basic_Test
2025-07-05 14:30:26,345 - panther.core.experiment_manager - INFO - Starting test execution
2025-07-05 14:30:45,567 - panther.core.experiment_manager - INFO - Test completed successfully
```

**test.log** - Detailed test execution:
```
2025-07-05 14:30:26,400 - panther.core.test_cases.test_case_impl - INFO - Building service images
2025-07-05 14:30:30,500 - panther.core.test_cases.test_case_impl - INFO - Starting services
2025-07-05 14:30:35,600 - panther.core.test_cases.test_case_impl - INFO - Executing test commands
2025-07-05 14:30:42,700 - panther.core.test_cases.test_case_impl - INFO - Validating assertions
2025-07-05 14:30:43,800 - panther.core.test_cases.test_case_impl - INFO - Test passed
```

**experiment_events.log** - Event timeline:
```json
{"timestamp": "2025-07-05T14:30:25.123Z", "event": "experiment.initialized", "data": {"test_count": 1}}
{"timestamp": "2025-07-05T14:30:26.234Z", "event": "test.created", "data": {"test_name": "QUIC_Basic_Test"}}
{"timestamp": "2025-07-05T14:30:45.567Z", "event": "test.completed", "data": {"status": "success"}}
```

### Success Indicators

Your experiment succeeded if you see:
- ✅ "Completed" status for your test
- Exit codes of 0 for all services
- All assertions passed
- No error events in `error_events.jsonl`

## Next Steps

### 1. Try Different Protocols

Modify your experiment to test different protocols:

```yaml
# MinIP Protocol Test
protocol:
  name: "minip"
  port: 8080
  server_address: "server"

services:
  - name: "minip_server"
    plugin_name: "minip"
    plugin_type: "iut"
    role: "server"
  - name: "minip_client"
    plugin_name: "minip"
    plugin_type: "iut"
    role: "client"
```

### 2. Add Multiple Tests

Extend your experiment with multiple test cases:

```yaml
tests:
  - name: "QUIC_Basic_Test"
    # ... existing test configuration

  - name: "QUIC_Performance_Test"
    description: "QUIC performance measurement"
    protocol:
      name: "quic"
      port: 4434
      # ... performance-specific configuration

  - name: "MinIP_Compatibility_Test"
    description: "MinIP protocol compatibility"
    protocol:
      name: "minip"
      # ... MinIP configuration
```

### 3. Explore Different Environments

Try different execution environments:

```yaml
# Network simulation environment
environment:
  name: "shadow_ns"
  plugin_name: "shadow_ns"
  plugin_type: "network"
  parameters:
    simulation_time: "60s"
    bandwidth: "100Mbps"
    latency: "10ms"

# Performance profiling environment
environment:
  name: "gperf_cpu"
  plugin_name: "gperf_cpu"
  plugin_type: "execution"
  parameters:
    profile_frequency: 1000
    output_format: "text"
```

### 4. Add Custom Assertions

Enhance test validation with custom assertions:

```yaml
assertions:
  - type: "output_contains"
    target: "client"
    pattern: "connection established"

  - type: "output_not_contains"
    target: "server"
    pattern: "error|failed|timeout"

  - type: "execution_time"
    target: "client"
    max_duration: 30

  - type: "file_exists"
    target: "server"
    file_path: "/app/server.log"

  - type: "json_field_equals"
    target: "client"
    file_path: "/app/results.json"
    field: "status"
    expected: "success"
```

## Common Issues and Solutions

### Docker Permission Issues

**Problem**: Permission denied when running Docker commands

**Solution**:
```bash
# Add user to docker group (Linux)
sudo usermod -aG docker $USER
# Log out and back in, or run:
newgrp docker

# For Windows/Mac Docker Desktop users:
# Ensure Docker Desktop is running and accessible
```

### Plugin Not Found

**Problem**: "Plugin 'quiche' not found" error

**Solution**:
```bash
# Check available plugins
panther plugins list --type service

# Verify plugin directory
panther config show --paths

# Update plugin configuration if needed
panther plugins refresh
```

### Network Port Conflicts

**Problem**: "Port already in use" error

**Solution**:
```bash
# Check port usage
sudo netstat -tulpn | grep :4433

# Kill conflicting processes
sudo kill $(sudo lsof -t -i:4433)

# Or use different ports in configuration
```

### Container Build Failures

**Problem**: Docker image build fails

**Solution**:
```bash
# Check Docker space
docker system df

# Clean up unused images
docker system prune -a

# Manually build problematic image
cd panther/plugins/services/iut/quiche/
docker build -t quiche:latest .
```

### Configuration Validation Errors

**Problem**: Configuration validation fails

**Solution**:
```bash
# Validate configuration step by step
panther config validate --global-config global_config.yaml
panther config validate --experiment-config experiment_config.yaml

# Check specific section
panther config validate --section protocols

# Show configuration schema
panther config schema --type experiment
```

## Learning Resources

### 1. Interactive Tutorials

```bash
# Start interactive tutorial system
panther tutorial start

# Available tutorials:
panther tutorial list

# Specific tutorial
panther tutorial protocol quic
panther tutorial environment docker_compose
panther tutorial plugin development
```

### 2. Example Experiments

```bash
# Copy example experiments
panther examples copy --target ./examples

# Available examples:
ls examples/
# - basic_quic/
# - multi_protocol/
# - performance_testing/
# - custom_plugins/

# Run example
cd examples/basic_quic/
panther run --global-config global_config.yaml --experiment-config experiment_config.yaml
```

### 3. Plugin Development

```bash
# Create custom plugin
panther plugin create --type protocol --name my_protocol
panther plugin create --type service --name my_service
panther plugin create --type environment --name my_environment

# Plugin development tutorial
panther tutorial plugin development
```

### 4. Advanced Configuration

```bash
# Show all configuration options
panther config schema --all

# Configuration examples
panther config examples --type global
panther config examples --type experiment
panther config examples --type test
```

## What's Next?

Now that you've successfully run your first PANTHER experiment, explore these advanced topics:

1. **[Plugin Development Guide](../plugins/development.md)** - Create custom plugins
2. **[Advanced Configuration](../config/README.md)** - Comprehensive configuration options
3. **Performance Testing** - Optimize experiment performance
4. **CI/CD Integration** - Automate testing workflows
5. **Troubleshooting Guide** - Common issues and solutions

### Community and Support

- **Documentation**: [Full documentation site](https://panther-docs.example.com)
- **Examples**: [Example repository](https://github.com/panther-examples)
- **Issues**: [Report bugs and request features](https://github.com/panther/issues)
- **Discussions**: [Community discussions](https://github.com/panther/discussions)

Welcome to the PANTHER community! Happy testing! 🎉
