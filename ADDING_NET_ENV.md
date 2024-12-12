
# Adding a New Network Environment

This guide provides a step-by-step tutorial on adding a new network environment to the PANTHER framework.

---

## 1. Overview

A network environment defines the network conditions under which experiments run, such as latency, bandwidth limits, or multi-container setups. Adding a new network environment involves:

- Implementing network-specific logic.
- Defining configuration schemas.
- Integrating with the framework's network environment plugin system.

---

## 2. Directory Structure

Below is an example structure for adding a network environment:

```
plugins/
└── environments/
    └── network_environment/
        └── my_network_environment/
            ├── __init__.py
            ├── config_schema.py
            ├── my_network_environment.py
            ├── Dockerfile
            ├── templates/
                └── network_config.jinja
```

---

## 3. Step-by-Step Tutorial

### Step 1: Define Configuration Schema

Create a `config_schema.py` file to define the schema for the network environment. Example:

```python
class MyNetworkEnvironmentConfig(NetworkEnvironmentConfig):
    def validate(self, config):
        # Custom validation logic for the network
        ...
```

- **Purpose**: Validates network parameters like latency and bandwidth.

---

### Step 2: Implement Network Environment Logic

Create a Python file (e.g., `my_network_environment.py`) to define the logic for the network environment.

```python
class MyNetworkEnvironment(NetworkEnvironmentInterface):
    def __init__(self, config):
        self.config = config

    def setup(self):
        # Prepare the network environment
        ...

    def execute(self, commands):
        # Execute commands in the network
        ...

    def teardown(self):
        # Cleanup the network environment
        ...
```

- **Key Methods**:
  - `setup`: Initializes the network environment.
  - `execute`: Executes commands with the defined network parameters.
  - `teardown`: Cleans up the network resources.

---

### Step 3: Add Templates

Use Jinja2 templates to dynamically define network configurations.

#### Example: `network_config.jinja`

```jinja
# Network Configuration Template
latency={{ latency }}
bandwidth={{ bandwidth }}
```

- **Purpose**: Allows dynamic configuration generation.

---

### Step 4: Define Dockerfile

Create a `Dockerfile` to define the network environment.

```dockerfile
FROM ubuntu:20.04
RUN apt-get update && apt-get install -y networking-tool
COPY . /app
WORKDIR /app
CMD ["./setup_network"]
```

- **Purpose**: Containerizes the network environment.

---

### Step 5: Integrate with the Plugin System

Add the network environment to the framework by registering it in `plugin_loader`.

```python
plugin_loader.register("my_network_environment", MyNetworkEnvironment)
```

---

## Contribution

To contribute a new network environment:
1. Follow this tutorial to implement the network environment.
2. Add unit tests for the network logic.
3. Submit a pull request with your implementation.

---
