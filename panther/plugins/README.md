
# Plugins Module

## Overview
The `plugins` module is a key component of the PANTHER framework, enabling modular and extensible functionality for environments, protocols, and services. It allows dynamic loading and management of plugins to adapt to various testing scenarios and requirements.

## Contents

### 1. Plugin Interface and Management
- **`plugin_interface.py`**:
  - Defines the base interface that all plugins must implement, ensuring consistency across different plugin types.
- **`plugin_loader.py`**:
  - Dynamically loads plugins at runtime based on configuration and system requirements.
- **`plugin_manager.py`**:
  - Manages the lifecycle of plugins, ensuring correct initialization, execution, and cleanup.

### 2. Environments
- **`environments`** (submodule):
  - Provides plugins for creating and managing execution and network environments.
  - Key folders:
    - **`execution_environment`**:
      - Includes plugins like `gperf_cpu`, `gperf_heap`, and `strace` for performance profiling and tracing.
    - **`network_environment`**:
      - Contains plugins such as `docker_compose` for multi-container setups and `shadow_ns` for network simulations.

### 3. Protocols
- **`protocols`** (submodule):
  - Implements plugins for different communication protocols, including client-server and peer-to-peer architectures.
  - Key folders:
    - **`quic`**: Provides configurations for the QUIC protocol, including support for multiple versions (e.g., RFC9000, Draft29).
    - **`http`**: Implements HTTP-based protocol testing logic.

### 4. Services
- **`services`** (submodule):
  - Implements plugins for auxiliary services required during testing.
  - Key folders:
    - **`iut`** (Implementation Under Test):
      - Contains specific implementations like `ping_pong` and `quic/picoquic` for protocol validation.
    - **Testers**: Defines the interface for testing components.

### 5. Templates
- Many plugins use Jinja2 templates for generating dynamic configurations (e.g., Dockerfiles, commands, or networking configurations).

## Usage
1. **Dynamic Plugin Loading**:
   - Use `plugin_loader` to dynamically load available plugins at runtime.
   - Extend the functionality by placing new plugins in the appropriate folder and implementing the `plugin_interface`.

2. **Environment Setup**:
   - Configure execution or network environments using plugins like `docker_compose` or `shadow_ns`.

3. **Protocol Testing**:
   - Use protocol plugins to test and validate specific versions and configurations of protocols like QUIC or HTTP.

4. **Service Validation**:
   - Utilize service plugins (e.g., `iut`) to validate the behavior of implementations under test.

## Extensibility
- New plugins can be added by implementing the `plugin_interface` and placing the module in the corresponding folder.
- Use configuration schemas (`config_schema.py`) to define the parameters required by your plugin.

## Key Dependencies
- **Core Module**:
  - The plugins rely on the core module for lifecycle management and integration with the rest of the framework.
- **Docker and Jinja2**:
  - Many plugins depend on Docker for containerized environments and Jinja2 for template generation.

---

## Contribution
To contribute to the `plugins` module:
1. Ensure new plugins follow the `plugin_interface` and integrate seamlessly with the `plugin_loader`.
2. Write unit tests for all new plugins and their configurations.
3. Update the corresponding README to document the new plugin.

