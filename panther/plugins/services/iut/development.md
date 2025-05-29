# Adding an Implementation Under Test (IUT) to PANTHER

This guide walks through the process of creating a new Implementation Under Test (IUT) plugin for the PANTHER framework.

## Overview

IUT plugins represent implementations of protocols that need to be tested within the PANTHER framework. These plugins provide the necessary interface between the PANTHER system and the actual protocol implementation being tested.

## Implementation Steps

### 1. Create the Plugin Directory Structure

Create the following directory structure for your IUT plugin:

```
panther/plugins/services/iut/protocol_name/your_iut_name/
├── __init__.py
├── your_iut_name.py
├── config_schema.py
├── Dockerfile
└── README.md
```

Where:

- `protocol_name`: The name of the protocol this IUT implements (e.g., quic, http)
- `your_iut_name`: The name of your specific implementation (e.g., picoquic, nginx)

### 2. Define the Configuration Schema

Create a configuration schema in `config_schema.py` that defines the parameters your IUT accepts:

```python
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from panther.plugins.services.iut.config_schema import IUTConfig


@dataclass
class YourIUTConfig(IUTConfig):
    """Configuration for YourIUT implementation."""
    binary_path: str = "/usr/local/bin/your_binary"  # Path to the binary
    extra_args: List[str] = field(default_factory=list)  # Extra command line arguments
    environment_vars: Dict[str, str] = field(default_factory=dict)  # Environment variables
    config_file_template: Optional[str] = None  # Optional config file template
    custom_parameter: str = "default_value"  # Add your custom parameters here
```

### 3. Implement the IUT Class

Create your main plugin implementation in `your_iut_name.py`:

```python
from panther.plugins.services.iut.iut_interface import IIUT
from panther.core.observer.event_manager import EventManager
from panther.plugins.services.config_schema import ServiceConfig


class YourIUT(IIUT):
    """
    YourIUT is a class that manages the YourIUT implementation of the protocol.
    """

    def __init__(
        self,
        service_config: ServiceConfig,
        output_dir: str,
        service_type: str,
        service_sub_type: str,
        event_manager: EventManager,
    ):
        super().__init__(service_config, output_dir, service_type, service_sub_type, event_manager)

    def setup_service(self):
        """Set up the service for execution."""
        self.logger.info(f"Setting up {self.__class__.__name__}")

        # Build command based on role (client/server)
        if self.service_config.protocol.role == "server":
            self.setup_server()
        elif self.service_config.protocol.role == "client":
            self.setup_client()
        else:
            self.logger.error(f"Unknown role: {self.service_config.protocol.role}")
            return False

        return True

    def setup_server(self):
        """Set up the server configuration."""
        # Configure server-specific settings
        self.run_cmd = {
            "run_cmd": {
                "command": self.service_config.implementation.binary_path,
                "args": [
                    "-p", str(self.service_config.ports[0].split(":")[0]),
                    # Add other arguments
                ] + self.service_config.implementation.extra_args,
                "command_env": {
                    # Add environment variables
                    **self.service_config.implementation.environment_vars
                }
            },
            "pre_run_cmds": [
                # Add any commands to run before starting the service
            ],
            "post_run_cmds": [
                # Add any commands to run after the service completes
            ]
        }

    def setup_client(self):
        """Set up the client configuration."""
        # Get target server information
        target_server = self.get_target_server()

        # Configure client-specific settings
        self.run_cmd = {
            "run_cmd": {
                "command": self.service_config.implementation.binary_path,
                "args": [
                    "-s", target_server,
                    # Add other arguments
                ] + self.service_config.implementation.extra_args,
                "command_env": {
                    # Add environment variables
                    **self.service_config.implementation.environment_vars
                }
            },
            "pre_run_cmds": [
                # Add any commands to run before starting the service
            ],
            "post_run_cmds": [
                # Add any commands to run after the service completes
            ]
        }

    def get_target_server(self):
        """Get the target server address from configuration."""
        if not self.service_config.protocol.target:
            self.logger.error("No target server specified")
            return "localhost"
        return self.service_config.protocol.target
```

### 4. Create a Dockerfile

Create a Dockerfile that builds the environment for your IUT:

```Dockerfile
# Use an appropriate base image
FROM ubuntu:22.04

# Install dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    cmake \
    # Add any other dependencies your IUT needs
    && rm -rf /var/lib/apt/lists/*

# Clone and build your implementation
RUN git clone https://github.com/example/your-implementation.git /src && \
    cd /src && \
    cmake . && \
    make && \
    make install

# Set working directory
WORKDIR /app

# Set entrypoint (optional)
ENTRYPOINT ["/usr/local/bin/your_binary"]
```

### 5. Create the Plugin Documentation

Create a comprehensive README.md file following the PANTHER documentation template:

```markdown
# Your IUT Name

> **Plugin Type**: Service (IUT)

> **Verified Source Location**: `plugins/services/iut/protocol_name/your_iut_name/`

## Purpose and Overview

Describe your IUT's purpose, the protocol it implements, and its key features.

## Requirements and Dependencies

List all dependencies required by this IUT.

## Configuration Options

Document all configuration parameters.

## Usage Examples

Provide examples of how to use your IUT in PANTHER experiments.

## Extension Points

Document how your IUT can be extended.

## Testing and Verification

Explain how to test your IUT.

## Troubleshooting

Document common issues and solutions.
```

### 6. Register the Plugin

Make sure your plugin can be discovered by PANTHER by updating the `__init__.py` file:

```python
from panther.plugins.services.iut.protocol_name.your_iut_name.your_iut_name import YourIUT

__all__ = ["YourIUT"]
```

## Testing Your IUT

1. Create a test configuration file:

```yaml
tests:
  - name: "Test with Your IUT"
    network_environment:
      type: "docker_compose"
    services:
      server:
        name: "your_server"
        implementation:
          name: "your_iut_name"
          type: "iut"
          binary_path: "/usr/local/bin/your_binary"
          extra_args: ["--debug"]
        protocol:
          name: "protocol_name"
          version: "1.0"
          role: "server"
        ports:
          - "8080:8080"
      client:
        name: "your_client"
        implementation:
          name: "your_iut_name"
          type: "iut"
        protocol:
          name: "protocol_name"
          version: "1.0"
          role: "client"
          target: "your_server"
```

2. Run PANTHER with your test configuration:

```bash
python -m panther -c path/to/your/test/config.yaml
```

3. Debug any issues and refine your implementation.

## Best Practices

1. **Protocol Conformance**: Ensure your IUT correctly implements the protocol specification
2. **Proper Configuration**: Make configuration options flexible but with sensible defaults
3. **Logging**: Use the logger provided by the base class for consistent logging
4. **Client/Server Roles**: Clearly handle different roles (client/server) in your implementation
5. **Documentation**: Keep your README.md updated with accurate information and usage examples

## Example Implementation

For reference, you can examine existing IUT plugins:

- Picoquic (QUIC): `plugins/services/iut/quic/picoquic/`
- HTTP Implementation: `plugins/services/iut/http/`
