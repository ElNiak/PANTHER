
# Configuration Guide for PANTHER

This guide explains how to configure experiments, services, and plugins in PANTHER. Configuration is managed using YAML files, ensuring flexibility and readability.

---

## Configuration Files

### 1. **Main Configuration File**
- **Path**: `config/experiment_config.yaml`
- **Purpose**: Defines the overall experiment setup, including logging, paths, tests, and Docker options.

### 2. **Plugin-Specific Configurations**
- **Path**: Resides in `plugins/` subdirectories.
- **Purpose**: Defines parameters for specific plugins like implementations, protocols, and environments.

---

## Structure of `experiment_config.yaml`

### Example Configuration:
```yaml
logging:
  level: DEBUG
  format: "%(asctime)s [%(levelname)s] - %(module)s - %(message)s"

paths:
  output_dir: "outputs"
  log_dir: "outputs/logs"
  config_dir: "configs"
  plugin_dir: "plugins"

docker:
  build_docker_image: true

tests:
  - name: "QUIC Server-Client Communication Test"
    description: "Test Picoquic server and client communication over Docker."
    network_environment:
      type: "docker_compose"
    execution_environment:
      - type: "gperf"
    iterations: 1
    services:
      picoquic_server:
        name: "picoquic_server"
        implementation:
          name: "picoquic"
          type: "iut"
        protocol:
          name: "quic"
          version: "rfc9000"
          role: "server"
        ports:
          - "4443:4443"
        generate_new_certificates: true
    steps:
      wait: 100  # seconds to wait during the test
    assertions:
      - type: "service_responsive"
        service: "picoquic_server"
        endpoint: "8080/health"
        expected_status: 200
```

---

## Key Sections

### 1. **Logging**
Configures the verbosity and format of logs.
```yaml
logging:
  level: DEBUG  # Options: DEBUG, INFO, WARNING, ERROR
  format: "%(asctime)s [%(levelname)s] - %(module)s - %(message)s"
```

### 2. **Paths**
Defines directories for output, logs, and plugins.
```yaml
paths:
  output_dir: "outputs"
  log_dir: "outputs/logs"
  config_dir: "configs"
  plugin_dir: "plugins"
```

### 3. **Docker Options**
Controls Docker behavior for test environments.
```yaml
docker:
  build_docker_image: true
```

### 4. **Tests**
Each test case defines:
- **Name**: A unique identifier.
- **Description**: Brief details about the test.
- **Network Environment**: The type of environment (e.g., Docker Compose).
- **Services**: Definitions for each service involved in the test.
- **Steps**: Actions such as waiting or running commands.
- **Assertions**: Validations for test success.

---

## Services Configuration

Each service includes:
- **Name**: A unique identifier.
- **Implementation**: Plugin type and name.
- **Protocol**: Details like name, version, role, and associated target.
- **Ports**: Exposed ports for communication.

### Example:
```yaml
services:
  picoquic_server:
    name: "picoquic_server"
    implementation:
      name: "picoquic"
      type: "iut"
    protocol:
      name: "quic"
      version: "rfc9000"
      role: "server"
    ports:
      - "4443:4443"
    generate_new_certificates: true
```

---

## Writing Custom Configurations

### Adding a New Test Case
1. Copy the structure from an existing test case.
2. Update fields like `name`, `description`, and `services`.

### Adding Custom Steps
1. Define new actions under `steps`:
   ```yaml
   steps:
     - action: "custom_command"
       parameters:
         command: "echo 'Hello, PANTHER!'"
   ```

### Adding Assertions
1. Define conditions to validate test results:
   ```yaml
   assertions:
     - type: "service_responsive"
       service: "my_service"
       endpoint: "5000/health"
       expected_status: 200
   ```

---

## Validation
To validate your configuration, run:
```bash
panther --validate-config --config config/experiment_config.yaml
```

---

## Advanced Configuration: Plugins
For plugin-specific configurations, refer to `plugins/`. Each plugin directory contains a `config.yaml` file with additional parameters.

---

## Troubleshooting
1. **Missing Configuration Keys**:
   - Ensure all required fields are present. Refer to this guide or sample files.
2. **Validation Errors**:
   - Use `panther --validate-config` to debug.
3. **Docker Build Issues**:
   - Verify that `config.yaml` in plugin directories includes valid `Dockerfile` paths.

---

For more advanced configurations or examples, consult the [Plugin Development Guide](PLUGIN_GUIDE.md) or reach out to the development team.