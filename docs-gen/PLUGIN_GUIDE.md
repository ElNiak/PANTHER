
# Plugin Development Guide for PANTHER

This guide provides step-by-step instructions for developing and integrating plugins into PANTHER. Plugins extend the functionality of PANTHER by implementing new protocols, environments, or service behaviors.

---

## Plugin Types

### 1. **Protocol Plugins**
- Define the behavior of network protocols (e.g., QUIC).
- Path: `plugins/services/{protocol_name}/`.

### 2. **Environment Plugins**
- Manage the test environment (e.g., Docker Compose, Shadow).
- Path: `plugins/environments/{environment_type}/`.

### 3. **Service Plugins**
- Implement the logic for individual services.
- Path: `plugins/services/{service_type}/{service_name}/`.

---

## Plugin Structure

### Required Files
Each plugin must include:
1. **`config_schema.py`**:
   - Defines the configuration schema for the plugin.
   - Example:
     ```python
     from dataclasses import dataclass

     @dataclass
     class MyPluginConfig:
         param1: str
         param2: int
     ```
2. **`implementation.py`**:
   - Implements the plugin's main functionality.
   - Example:
     ```python
     from plugins.plugin_interface import IPlugin

     class MyPlugin(IPlugin):
         def execute(self):
             print("Executing MyPlugin")
     ```
3. **`config.yaml`**:
   - Provides default or example configurations for the plugin.

### Optional Files
- **`Dockerfile`**: For environment plugins requiring Docker integration.
- **`README.md`**: Documentation specific to the plugin.

---

## Developing a Plugin

### Step 1: Create the Directory
1. Navigate to the appropriate plugin type directory (e.g., `plugins/services/`).
2. Create a new folder for your plugin:
   ```bash
   mkdir -p plugins/services/my_service
   ```

### Step 2: Define the Configuration Schema
1. Create `config_schema.py`:
   ```python
   from dataclasses import dataclass

   @dataclass
   class MyServiceConfig:
       name: str
       version: str
       param1: int
   ```

2. Ensure the schema includes all necessary parameters for your plugin.

### Step 3: Implement Plugin Logic
1. Create `implementation.py`:
   ```python
   from plugins.plugin_interface import IPlugin

   class MyService(IPlugin):
       def __init__(self, config):
           self.config = config

       def execute(self):
           print(f"Executing service: {self.config.name}")
   ```

2. Implement required methods or extend base functionality from `IPlugin`.

### Step 4: Add Default Configuration
1. Create `config.yaml`:
   ```yaml
   my_service:
     name: "ExampleService"
     version: "1.0"
     param1: 42
   ```

2. Include any Docker-related configurations if applicable.

### Step 5: (Optional) Add Docker Integration
1. Create a `Dockerfile` in the plugin's directory:
   ```dockerfile
   FROM python:3.9-slim
   COPY . /app
   WORKDIR /app
   RUN pip install -r requirements.txt
   CMD ["python", "main.py"]
   ```

---

## Validating and Registering Plugins

### Validation
Run the following command to validate your plugin configuration:
```bash
python panther_cli.py validate-config --plugin my_plugin_name
```

### Registration
PANTHER automatically discovers plugins placed in the appropriate directory. Ensure the plugin directory is correctly structured.

---

## Examples

### Protocol Plugin: QUIC
1. **Directory**: `plugins/services/quic/`
2. **Schema** (`config_schema.py`):
   ```python
   from dataclasses import dataclass

   @dataclass
   class QuicConfig:
       role: str  # Options: client, server
       version: str  # QUIC protocol version
   ```
3. **Implementation** (`implementation.py`):
   ```python
   from plugins.plugin_interface import IPlugin

   class Quic(IPlugin):
       def execute(self):
           print("Running QUIC implementation")
   ```

### Environment Plugin: Docker Compose
1. **Directory**: `plugins/environments/docker_compose/`
2. **Schema**:
   ```python
   from dataclasses import dataclass

   @dataclass
   class DockerComposeConfig:
       version: str
       services: dict
   ```
3. **Dockerfile**:
   ```dockerfile
   FROM docker/compose:latest
   ```

---

## Troubleshooting

### Common Issues
1. **Plugin Not Found**:
   - Verify the directory and file structure.
   - Ensure the plugin is placed in the correct type directory.

2. **Validation Errors**:
   - Check `config_schema.py` for missing or incorrect parameters.
   - Use `python panther_cli.py validate-config` for debugging.

3. **Docker Build Fails**:
   - Confirm the `Dockerfile` path in `config.yaml` is correct.
   - Check logs for build-specific errors.

---

## Best Practices
- **Modular Design**: Keep your plugin logic decoupled from the core system.
- **Comprehensive Testing**: Write unit tests for your plugin’s functionality.
- **Documentation**: Include a `README.md` in the plugin directory to guide users.

---

For additional support, refer to the [Main README](README.md) or contact the development team.