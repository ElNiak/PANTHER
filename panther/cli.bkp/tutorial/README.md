# PANTHER CLI Tutorial

*Part of the Diátaxis documentation framework - this document provides **step-by-step learning** for new PANTHER CLI users.*

## Getting Started with PANTHER CLI

This tutorial guides you through your first PANTHER experiment, from installation to results analysis. By the end, you'll understand core CLI concepts and be ready to design your own protocol tests.

### Prerequisites

- Python 3.8+ installed
- Basic familiarity with command-line interfaces
- Understanding of network protocols (helpful but not required)

### What You'll Learn

1. **Basic CLI Navigation**: Essential commands and help system
2. **Configuration Management**: Creating and validating experiment configurations
3. **Plugin Discovery**: Finding and understanding available plugins
4. **Running Experiments**: Executing your first protocol test
5. **Results Analysis**: Interpreting experiment outputs

## Step 1: Installation and Setup

### Install PANTHER CLI

```bash
# Install PANTHER with CLI support
pip install panther-framework[cli]

# Verify installation
panther --version
panther --help
```

**Expected Output:**
```
PANTHER - Protocol Analysis and Testing for Heterogeneous Execution and Research

Available commands:
  run        Execute PANTHER experiments
  config     Configuration management and validation
  plugins    Plugin management and discovery
  create     Create new plugins and resources
  tutorial   Interactive tutorials and learning
  ...
```

### Enable Bash Completion (Optional)

```bash
# Add to your .bashrc or .zshrc
eval "$(register-python-argcomplete panther)"

# Test completion
panther <TAB><TAB>
```

This enables tab completion for commands and options, making the CLI much more discoverable.

## Step 2: Explore Available Plugins

Before creating experiments, let's see what protocols and tools are available.

### List All Plugins

```bash
panther plugins list
```

**Expected Output:**
```
Available Plugins:
┌──────────────┬─────────┬──────────────┬─────────────────────────────────┐
│ Name         │ Version │ Type         │ Description                     │
├──────────────┼─────────┼──────────────┼─────────────────────────────────┤
│ picoquic     │ 1.1.0   │ iut          │ QUIC implementation by Picotls  │
│ quiche       │ 0.15.0  │ iut          │ QUIC implementation by Cloudflare│
│ http3_tester │ 2.1.0   │ tester       │ HTTP/3 protocol testing suite  │
│ network_sim  │ 1.0.0   │ environment  │ Network simulation environment  │
└──────────────┴─────────┴──────────────┴─────────────────────────────────┘
```

### Get Detailed Plugin Information

```bash
# Learn about a specific plugin
panther plugins info picoquic

# See what parameters it accepts
panther plugins params picoquic
```

**Key Insight:** PANTHER uses plugins for protocol implementations, testing tools, and environments. Understanding available plugins is essential for designing experiments.

## Step 3: Create Your First Configuration

Instead of writing YAML from scratch, let's use the interactive configuration designer.

### Interactive Configuration Design

```bash
panther config design --output my_first_experiment.yaml
```

This starts an interactive wizard that guides you through creating a valid configuration:

```
🔧 PANTHER Configuration Designer
==================================

📋 Experiment Information
Name [my_experiment]: my_first_quic_test
Description: My first QUIC protocol test

🌐 Protocol Selection
Available protocols: [quic, http3, coap, mqtt]
Select protocol: quic

🏗️  Implementation Selection
Available QUIC implementations: [picoquic, quiche, aioquic]
Select implementation: picoquic

📊 Test Configuration
Test type [basic]: connection_test
Duration [30s]: 10s
Connections [1]: 1

✅ Configuration created: my_first_experiment.yaml
```

### Validate Your Configuration

```bash
panther config validate --config my_first_experiment.yaml
```

**Expected Output:**
```
🔍 Validating configuration...
✅ Configuration is valid
📋 Summary:
  - Experiment: my_first_quic_test
  - Protocol: QUIC
  - Implementation: picoquic
  - Tests: 1 test case
  - Duration: 10 seconds
```

## Step 4: Understanding the Generated Configuration

Let's examine what the wizard created:

```bash
cat my_first_experiment.yaml
```

**Generated Configuration:**
```yaml
experiment:
  name: my_first_quic_test
  description: My first QUIC protocol test
  protocol: quic

iut:
  name: picoquic
  version: "1.1.0"
  parameters:
    log_level: info

tester:
  name: quic_basic_tester
  parameters:
    test_duration: 10s
    connections: 1
    test_type: connection_test

environment:
  name: local_docker
  parameters:
    network_delay: 0ms
    packet_loss: 0%
    bandwidth: unlimited

output:
  directory: ./results
  formats: [json, csv]
```

**Understanding the Structure:**
- **experiment**: Metadata about your test
- **iut**: Implementation Under Test (what you're testing)
- **tester**: The testing tool that exercises the IUT
- **environment**: The network environment for testing
- **output**: Where and how results are saved

## Step 5: Run Your First Experiment

Now let's execute the experiment:

```bash
panther run --config my_first_experiment.yaml
```

**Expected Output:**
```
🚀 Starting experiment: my_first_quic_test
🔧 Initializing environment...
📦 Setting up picoquic implementation...
🧪 Configuring quic_basic_tester...
▶️  Running test: connection_test
[========================================] 100% Complete
✅ Experiment completed successfully

📊 Results saved to: ./results/my_first_quic_test_20231201_143022/
📋 Summary:
  - Total connections: 1
  - Successful connections: 1
  - Average connection time: 15.3ms
  - Data transferred: 1.2KB
```

### Understanding the Results

```bash
# Navigate to results directory
cd results/my_first_quic_test_20231201_143022/

# Examine the contents
ls -la
```

**Results Structure:**
```
results/my_first_quic_test_20231201_143022/
├── experiment_config.yaml    # Configuration used
├── experiment_log.txt        # Detailed execution log
├── metrics.json             # Machine-readable metrics
├── metrics.csv              # Spreadsheet-friendly metrics
├── iut_logs/               # Implementation logs
└── tester_logs/            # Testing tool logs
```

## Step 6: Analyze Results

### View Metrics Summary

```bash
# Quick metrics overview
panther metrics analyze --experiment my_first_quic_test_20231201_143022

# Or manually inspect
cat metrics.json
```

**Sample Metrics:**
```json
{
  "experiment": {
    "name": "my_first_quic_test",
    "start_time": "2023-12-01T14:30:22Z",
    "duration": 12.5,
    "status": "completed"
  },
  "connection_metrics": {
    "attempted": 1,
    "successful": 1,
    "failed": 0,
    "average_time_ms": 15.3
  },
  "throughput_metrics": {
    "bytes_sent": 1200,
    "bytes_received": 800,
    "duration_seconds": 10.1
  }
}
```

### Key Metrics to Understand

- **Connection Success Rate**: Percentage of successful connections
- **Connection Latency**: Time to establish connections
- **Throughput**: Data transfer rates
- **Error Rates**: Types and frequency of failures

## Step 7: Experiment with Different Configurations

Now that you understand the basics, let's try some variations:

### Test Different Implementations

```bash
# Create configuration with different implementation
panther config design --output quiche_test.yaml
# Select 'quiche' when prompted for implementation

# Run both tests and compare
panther run --config my_first_experiment.yaml
panther run --config quiche_test.yaml
```

### Add Network Conditions

```bash
# Create configuration with network simulation
panther config design --output network_test.yaml
```

When prompted for environment, select network simulation and configure:
- Network delay: 50ms
- Packet loss: 1%
- Bandwidth: 10Mbps

### Parallel Execution

```bash
# Run multiple tests in parallel
panther run --config my_first_experiment.yaml --output-dir results/test1 &
panther run --config quiche_test.yaml --output-dir results/test2 &
panther run --config network_test.yaml --output-dir results/test3 &

# Wait for all to complete
wait
```

## Step 8: Explore Advanced Features

### Configuration Templates

```bash
# See available templates
panther config generate --list

# Generate from template
panther config generate --template performance --output perf_test.yaml

# Customize the generated configuration
panther config design --from perf_test.yaml --output my_perf_test.yaml
```

### Plugin Development

```bash
# Create a custom plugin
panther create plugin tester my_custom_tester

# This creates a plugin template you can customize
ls my_custom_tester/
```

### Validation and Debugging

```bash
# Validate configuration with strict checking
panther config validate --config complex_config.yaml --strict

# Run with debug output
panther run --config test.yaml --debug

# Dry run to see what would happen
panther run --config test.yaml --dry-run
```

## Next Steps

### Explore More Commands

```bash
# Interactive tutorial for advanced features
panther tutorial interactive

# Explore specific protocol tutorials
panther tutorial run http3
panther tutorial run coap

# System administration
panther admin doctor  # Check system health
panther admin clean   # Clean up old results
```

### Learn Plugin Development

```bash
# Create different types of plugins
panther create plugin iut my_protocol_impl
panther create plugin environment my_network_sim
panther create plugin tester my_test_suite
```

### Integration with Workflows

```bash
# JSON output for scripting
panther plugins list --format json

# Exit codes for CI/CD
panther config validate --config $CONFIG_FILE
if [ $? -eq 0 ]; then
    echo "Configuration valid, proceeding with tests"
    panther run --config $CONFIG_FILE
fi
```

## Common Patterns and Best Practices

### Configuration Management

1. **Start with Templates**: Use `panther config generate` for common scenarios
2. **Validate Early**: Always validate configurations before running experiments
3. **Version Control**: Keep configuration files in version control
4. **Naming Conventions**: Use descriptive names for experiments and outputs

### Experiment Design

1. **Start Simple**: Begin with basic tests before adding complexity
2. **Isolate Variables**: Change one thing at a time to understand impact
3. **Baseline Measurements**: Always have a reference configuration
4. **Document Parameters**: Use configuration descriptions to explain choices

### Results Management

1. **Organized Storage**: Use clear directory structures for results
2. **Metadata Preservation**: Keep configuration files with results
3. **Automated Analysis**: Script metric extraction for consistent analysis
4. **Comparison Tools**: Use tools to compare results across experiments

### Development Workflow

1. **Use Debug Mode**: Enable debug logging during development
2. **Dry Runs**: Test configurations without resource allocation
3. **Incremental Testing**: Build complex experiments incrementally
4. **Plugin Development**: Create custom plugins for specialized needs

## Troubleshooting Common Issues

### Configuration Errors

**Problem**: "Plugin not found" error
```bash
❌ Error: Plugin 'my_plugin' not found
```

**Solution**: Check available plugins and spelling
```bash
panther plugins list
panther plugins list --type iut  # Filter by type
```

**Problem**: "Invalid configuration schema"
```bash
❌ Validation error: Missing required field 'experiment.name'
```

**Solution**: Use the configuration designer or check schema
```bash
panther config schema  # Show schema documentation
panther config design --from broken_config.yaml  # Fix interactively
```

### Execution Errors

**Problem**: Docker-related errors
```bash
❌ Error: Cannot connect to Docker daemon
```

**Solution**: Ensure Docker is running
```bash
docker info  # Test Docker connectivity
panther admin doctor  # Check system dependencies
```

**Problem**: Network connectivity issues
```bash
❌ Error: Connection timeout during test
```

**Solution**: Check network configuration and firewall settings
```bash
panther run --config test.yaml --debug  # Enable debug logging
# Check Docker network settings
# Verify firewall allows required ports
```

### Performance Issues

**Problem**: Slow experiment startup
**Solution**: Use local plugins and optimize Docker images
```bash
panther admin clean  # Clean up old containers
panther tools install-slim  # Use optimized images
```

**Problem**: High memory usage
**Solution**: Limit parallel operations and use streaming output
```bash
panther run --config test.yaml --max-workers 2
```

## Conclusion

You've now learned the fundamentals of PANTHER CLI:

✅ **Installation and Setup**: CLI installation and configuration
✅ **Plugin Discovery**: Finding and understanding available tools
✅ **Configuration Design**: Creating valid experiment configurations
✅ **Experiment Execution**: Running tests and understanding results
✅ **Advanced Features**: Templates, validation, and debugging
✅ **Best Practices**: Patterns for effective protocol testing

### What You Can Do Now

- Design and run protocol experiments
- Create custom configurations for specific testing scenarios
- Integrate PANTHER into automated testing workflows
- Explore advanced features like plugin development
- Troubleshoot common issues independently

### Continue Learning

- **[DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)**: Deep dive into CLI development
- **[api_reference.md](api_reference.md)**: Complete API documentation
- **[README.md](README.md)**: Architectural explanations and design decisions
- **Interactive Tutorials**: `panther tutorial interactive` for hands-on learning

---

*This tutorial provides a complete introduction to PANTHER CLI. For specific how-to guides on advanced topics, see the DEVELOPER_GUIDE.md. For conceptual understanding, see the README.md explanation document.*
