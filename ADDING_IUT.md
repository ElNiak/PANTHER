
# Adding a New Implementation Under Test (IUT)

This guide provides a step-by-step tutorial on adding a new Implementation Under Test (IUT) to the PANTHER framework, using `PingPong` as an example.

---

## 1. Overview

An Implementation Under Test (IUT) represents a specific implementation of a protocol or service to be tested within the PANTHER framework. Adding a new IUT involves:

- Defining configuration files.
- Implementing the service logic.
- Integrating the IUT with the framework's plugin system.

---

## 2. Directory Structure

Below is the structure for the `PingPong` IUT:

```
plugins/
└── services/
    └── iut/
        └── minip/
            └── ping_pong/
                ├── __init__.py
                ├── config_schema.py
                ├── ping_pong.py
                ├── Dockerfile
                ├── templates/
                    ├── client_command.jinja
                    └── server_command.jinja
                └── version_configs/
                    ├── functional.yaml
                    ├── random.yaml
                    ├── flaky.yaml
                    ├── fail.yaml
                    └── vulnerable.yaml
```

---

## 3. Step-by-Step Tutorial

### Step 1: Define Configuration Schema

Create a `config_schema.py` file to define the schema for the IUT. For example, the `PingPong` schema includes:

```python
class PingPongConfig(ImplementationConfig):
    def load_versions_from_files(self, version_dir):
        # Load specific versions from YAML files
        ...
```

- **Purpose**: Ensures the IUT accepts valid configurations.
- **Example**: Load versions from YAML files in the `version_configs` directory.

---

### Step 2: Implement the IUT Logic

Create a Python file (e.g., `ping_pong.py`) that defines the service logic. For `PingPong`:

```python
class PingPongServiceManager(IImplementationManager):
    def __init__(self, service_config_to_test, service_type, plugin_loader):
        # Initialize the manager with configuration, type, and plugins

    def generate_pre_compile_commands(self):
        # Return commands to run before compilation

    def generate_compile_commands(self):
        # Return commands to run compilation

    def generate_post_compile_commands(self):
        # Return commands to execute after compilation

    def generate_pre_run_commands(self):
        # Return commands to run before the service starts

    def generate_run_command(self):
        # Return the main command to run the service

    def generate_post_run_commands(self):
        # Return commands to execute after the service runs

    def prepare(self, plugin_loader):
        # Prepare the service manager for execution
```

- **Key Methods**:
  - `generate_pre_compile_commands`: Sets up the environment before compilation.
  - `generate_compile_commands`: Compiles the IUT.
  - `generate_post_compile_commands`: Cleans up after compilation.
  - `generate_pre_run_commands`: Prepares the service before execution.
  - `generate_run_command`: Generates the command to run the IUT.
  - `generate_post_run_commands`: Cleans up after execution.
  - `prepare`: Prepares the service using the `plugin_loader`.

---

### Step 3: Add Templates

Use Jinja2 templates to define commands or configurations dynamically.

#### Example: Client Command Template

```jinja
# client_command.jinja
run --client --host {{ host }} --port {{ port }} --timeout {{ timeout }}
```

#### Example: Server Command Template

```jinja
# server_command.jinja
run --server --host {{ host }} --port {{ port }}
```

- **Purpose**: Enables flexibility in defining runtime commands.

---

### Step 4: Define Dockerfile

Create a `Dockerfile` to build the IUT environment.

```dockerfile
FROM ubuntu:20.04
RUN apt-get update && apt-get install -y build-essential
COPY . /app
WORKDIR /app
RUN make
CMD ["./ping_pong"]
```

- **Purpose**: Provides a containerized environment for the IUT.

---

### Step 5: Add Version Configurations

Define versions in the `version_configs` folder:

#### Example: `functional.yaml`

```yaml
name: functional
description: Fully functional version of PingPong
config:
  timeout: 300
  retries: 3
```

#### Example: `vulnerable.yaml`

```yaml
name: vulnerable
description: Version with known vulnerabilities
config:
  timeout: 100
  retries: 1
```

- **Purpose**: Allows testing against multiple versions with varying characteristics.

---

### Step 6: Test Your IUT

1. Add unit tests for your IUT logic.
2. Run integration tests to validate the behavior of your IUT with other framework components.

---

## 4. Tips and Best Practices

- **Follow Naming Conventions**:
  - Ensure consistent naming for templates, configuration files, and version YAML files.

- **Document Your Code**:
  - Add docstrings to all classes and methods for clarity.

- **Use Modular Design**:
  - Keep templates, Dockerfiles, and configurations separate for easier maintenance.

---

## Contribution

To contribute a new IUT:
1. Follow this tutorial to create your IUT.
2. Submit a pull request with your code, configurations, and tests.

