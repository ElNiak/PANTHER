
# Experiment Execution Guide for PANTHER

This guide explains how to set up, run, and interpret experiments in PANTHER. Learn about the core components, execution flow, and result analysis.

---

## Overview

### **Core Components**

#### **ExperimentManager**
- Orchestrates the setup, execution, and teardown of experiments.
- Key methods:
  - `run_tests`: Executes the test cases.
  - `_initialize_test_cases`: Loads and prepares test cases from configuration.

#### **TestCase**
- Represents an individual test within an experiment.
- Key methods:
  - `deploy_services`: Deploys required services.
  - `execute_steps`: Executes the test steps defined in the configuration.
  - `validate_assertions`: Verifies test outcomes.

---

## Setting Up an Experiment

1. **Prepare Configuration**:
   - Use the provided sample configuration file:
     ```bash
     cp config/experiment_config.yaml.example config/experiment_config.yaml
     ```
   - Update the configuration file to define your test cases, services, and assertions.

2. **Build Docker Images**:
   - Build Docker images for the required services:
     ```bash
     python panther_cli.py build-docker-images
     ```

3. **Validate Configuration**:
   - Ensure the configuration is valid before execution:
     ```bash
     python panther_cli.py validate-config --config config/experiment_config.yaml
     ```

---

## Running an Experiment

1. Execute the experiment:
   ```bash
   python panther_cli.py run-experiment --config config/experiment_config.yaml
   ```

2. Monitor the logs for real-time updates:
   - Logs are stored in the directory defined in the configuration (`outputs/logs`).

3. Results are automatically saved in the `outputs/` directory.

---

## Example Scenario: Testing QUIC

### Configuration
- Test QUIC client-server communication using Picoquic.

**Sample YAML**:
```yaml
tests:
  - name: "QUIC Server-Client Test"
    description: "Testing QUIC communication with Picoquic."
    network_environment:
      type: "docker_compose"
    services:
      quic_server:
        name: "quic_server"
        implementation:
          name: "picoquic"
          type: "iut"
        protocol:
          name: "quic"
          version: "rfc9000"
          role: "server"
        ports:
          - "4443:4443"
    steps:
      wait: 100
    assertions:
      - type: "service_responsive"
        service: "quic_server"
        endpoint: "4443/health"
        expected_status: 200
```

### Execution
1. Build Docker images for Picoquic:
   ```bash
   python panther_cli.py build-docker-images
   ```
2. Run the experiment:
   ```bash
   python panther_cli.py run-experiment --config config/experiment_config.yaml
   ```

---

## Interpreting Results

1. **Output Directory**:
   - Results are saved in the `outputs/` directory.
   - Example: `outputs/results/test_1.json`.

2. **Log Files**:
   - Located in `outputs/logs`.
   - Contain details about test execution and errors.

3. **Success Criteria**:
   - Validate against assertions defined in the configuration.

---

## Troubleshooting

1. **Missing Services**:
   - Ensure all services are defined in the configuration.

2. **Validation Errors**:
   - Run the validation command to debug configuration issues.

3. **Docker Issues**:
   - Verify Docker is running and accessible.

For further assistance, consult the [Main README](README.md) or contact the development team.