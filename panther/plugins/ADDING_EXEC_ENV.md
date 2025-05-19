
# Adding a New Execution Environment

This guide provides a step-by-step tutorial on adding a new execution environment to the PANTHER framework.

---

## 1. Overview

An execution environment defines the context in which experiments run, such as performance profiling or execution tracing. Adding a new execution environment involves:

- Implementing environment-specific logic.
- Defining configuration schemas.
- Integrating with the framework's environment plugin system.

---

## 2. Directory Structure

Below is an example structure for adding an execution environment:

```
plugins/
└── environments/
    └── execution_environment/
        └── my_environment/
            ├── __init__.py
            ├── config_schema.py
            ├── my_environment.py
            ├── Dockerfile
            ├── templates/
                └── environment_config.jinja
```

---

## 3. Step-by-Step Tutorial

### Step 1: Define Configuration Schema

Create a `config_schema.py` file to define the schema for the environment. Example:

```python
class MyEnvironmentConfig(EnvironmentConfig):
    def validate(self, config):
        # Custom validation logic for the environment
        ...
```

- **Purpose**: Validates configuration parameters for the environment.

---

### Step 2: Implement Environment Logic

Create a Python file (e.g., `my_environment.py`) to define the logic for the environment.

```python
class MyEnvironment(EnvironmentInterface):
    def __init__(self, config):
        self.config = config

    def setup(self):
        # Prepare the environment
        ...

    def execute(self, commands):
        # Execute commands in the environment
        ...

    def teardown(self):
        # Cleanup after execution
        ...
```

- **Key Methods**:
  - `setup`: Initializes the environment.
  - `execute`: Executes commands within the environment.
  - `teardown`: Cleans up resources.

---

### Step 3: Add Templates

Use Jinja2 templates to dynamically define environment-specific configurations.

#### Example: `environment_config.jinja`

```jinja
# Environment Configuration Template
cpu_limit={{ cpu_limit }}
memory_limit={{ memory_limit }}
```

- **Purpose**: Allows dynamic configuration generation.

---

### Step 4: Define Dockerfile

Create a `Dockerfile` to define the execution environment.

```dockerfile
FROM ubuntu:20.04
RUN apt-get update && apt-get install -y profiling-tool
COPY . /app
WORKDIR /app
CMD ["./run_environment"]
```

- **Purpose**: Containerizes the execution environment.

---

### Step 5: Integrate with the Plugin System

Add the environment to the framework by registering it in `plugin_loader`.

```python
plugin_loader.register("my_environment", MyEnvironment)
```

---

## Contribution

To contribute a new execution environment:
1. Follow this tutorial to implement the environment.
2. Add unit tests for the environment logic.
3. Submit a pull request with your implementation.

---
