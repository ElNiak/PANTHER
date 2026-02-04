# PANTHER Service Plugins - Quick Start Tutorial

## Overview

This tutorial guides you through creating your first PANTHER service plugin step by step. You'll build a simple QUIC client/server implementation plugin and learn the essential patterns for service management in the PANTHER testing framework.

## Prerequisites

- Python 3.8+ installed
- Docker and Docker Compose
- Basic understanding of QUIC protocol
- PANTHER development environment set up

## Tutorial Goal

Build a functional service plugin for a hypothetical "SimpleQUIC" implementation that can:
- Act as both client and server
- Generate proper Docker deployment configurations
- Handle command generation and execution
- Collect and organize output files
- Integrate with PANTHER's event system

## Step 1: Project Setup

### Create Directory Structure

```bash
# Navigate to the services directory
cd panther/plugins/services/iut/quic/

# Create your implementation directory
mkdir -p simple_quic/templates/
mkdir -p simple_quic/version_configs/quic/

# Create required files
touch simple_quic/__init__.py
touch simple_quic/simple_quic.py
touch simple_quic/config_schema.py
touch simple_quic/README.md
touch simple_quic/Dockerfile
```

Your structure should look like:
```
simple_quic/
├── __init__.py
├── simple_quic.py          # Main service manager
├── config_schema.py        # Configuration validation
├── README.md              # Implementation documentation
├── Dockerfile             # Container build configuration
├── templates/             # Jinja2 templates
│   ├── docker-compose.yml.j2
│   └── entrypoint.sh.j2
└── version_configs/       # Version-specific configurations
    └── quic/
        └── v1.json
```

## Step 2: Define Configuration Schema

Create `config_schema.py`:

```python
"""Configuration schema for SimpleQUIC implementation."""

CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "implementation": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "const": "simple_quic"},
                "version": {"type": "string", "pattern": r"^\d+\.\d+\.\d+$"},
                "build_mode": {
                    "type": "string",
                    "enum": ["debug", "release"],
                    "default": "release"
                },
                "enable_logging": {"type": "boolean", "default": True},
                "log_level": {
                    "type": "string",
                    "enum": ["debug", "info", "warning", "error"],
                    "default": "info"
                }
            },
            "required": ["name", "version"]
        },
        "protocol": {
            "type": "object",
            "properties": {
                "version": {"type": "string", "enum": ["draft-29", "v1"]},
                "role": {"type": "string", "enum": ["client", "server"]},
                "port": {"type": "integer", "minimum": 1024, "maximum": 65535},
                "alpn": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": ["h3", "h3-29"]
                }
            },
            "required": ["version", "role", "port"]
        }
    },
    "required": ["implementation", "protocol"]
}

def validate_simple_quic_config(config):
    """Validate SimpleQUIC configuration."""
    from jsonschema import validate, ValidationError
    try:
        validate(config, CONFIG_SCHEMA)
        return True, []
    except ValidationError as e:
        return False, [str(e)]
```

## Step 3: Implement the Service Manager

Create `simple_quic.py`:

```python
"""SimpleQUIC service manager for PANTHER testing framework."""

import os
from typing import Any, Dict, List, Union, Tuple

from panther.core.command_processor.models import ShellCommand
from panther.plugins.services.base.quic_service_base import BaseQUICServiceManager


class SimpleQUICServiceManager(BaseQUICServiceManager):
    """Service manager for SimpleQUIC QUIC implementation.

    Manages lifecycle, command generation, and configuration for SimpleQUIC
    protocol implementation in both client and server modes.
    """

    def __init__(self, service_config_to_test, service_type, protocol,
                 implementation_name, event_manager=None, test_case=None):
        """Initialize SimpleQUIC service manager.

        Args:
            service_config_to_test: Service configuration object
            service_type: Service type ("IUT")
            protocol: Protocol configuration
            implementation_name: Name of implementation ("simple_quic")
            event_manager: Event manager for notifications
            test_case: Parent test case reference
        """
        super().__init__(
            service_config_to_test=service_config_to_test,
            service_type=service_type,
            protocol=protocol,
            implementation_name=implementation_name,
            event_manager=event_manager,
            test_case=test_case
        )

        # Load version-specific configuration
        self._load_version_config()

    def _load_version_config(self):
        """Load version-specific configuration from version_configs."""
        version_file = os.path.join(
            self.config_versions_dir,
            f"{self.service_protocol.version}.json"
        )

        if os.path.exists(version_file):
            import json
            with open(version_file, 'r') as f:
                self.version_config = json.load(f)
                self.logger.debug(
                    f"Loaded version config for {self.service_protocol.version}"
                )
        else:
            self.logger.warning(f"No version config found for {version_file}")
            self.version_config = {}

    def generate_compile_commands(self) -> List[Union[str, ShellCommand]]:
        """Generate commands to compile SimpleQUIC.

        Returns:
            List of compilation commands
        """
        self.emit_command_generation_started("compile")

        build_mode = self.version_config.get("env", {}).get("BUILD_TYPE", "Release")
        source_dir = self.environments.get("SOURCE_DIR", "/opt/simple_quic")

        commands = [
            ShellCommand(
                f"cd {source_dir}",
                description="Change to source directory",
                is_critical=True
            ),
            ShellCommand(
                "mkdir -p build",
                description="Create build directory",
                is_critical=True
            ),
            ShellCommand(
                f"cd build && cmake -DCMAKE_BUILD_TYPE={build_mode} ..",
                description="Configure build with CMake",
                is_critical=True
            ),
            ShellCommand(
                "cd build && make -j$(nproc)",
                description="Compile SimpleQUIC",
                is_critical=True
            )
        ]

        self.emit_command_generated("compile", f"Generated {len(commands)} compile commands")
        return commands

    def generate_run_command(self) -> Dict[str, Any]:
        """Generate the main execution command for SimpleQUIC.

        Returns:
            Command configuration dictionary
        """
        self.emit_command_generation_started("run")

        # Determine binary name based on role
        if self.is_server():
            binary = "simple_quic_server"
            args = [
                "--listen", f"0.0.0.0:{self.get_port()}",
                "--cert", "/app/certs/cert.pem",
                "--key", "/app/certs/key.pem"
            ]
        else:
            binary = "simple_quic_client"
            args = [
                "--connect", f"{self.get_server_host()}:{self.get_port()}"
            ]

        # Add common arguments
        args.extend([
            "--version", self.service_protocol.version,
            "--qlog-dir", "/app/logs",
            "--log-level", self.environments.get("QUIC_LOG_LEVEL", "info")
        ])

        run_cmd = {
            "working_dir": self.environments.get("SOURCE_DIR", "/opt/simple_quic"),
            "command_binary": binary,
            "command_args": args,
            "timeout": self.service_config_to_test.timeout,
            "environment": self.environments
        }

        self.emit_command_generated("run", f"Generated run command: {binary}")
        return run_cmd

    def generate_deployment_commands(self) -> str:
        """Generate Docker Compose deployment configuration.

        Returns:
            Docker Compose YAML configuration as string
        """
        # Prepare template parameters
        params = {
            "service_name": self.service_name,
            "implementation_name": self.implementation_name,
            "role": self.role,
            "port": self.get_port(),
            "protocol_version": self.service_protocol.version,
            "volumes": self.volumes,
            "log_level": self.environments.get("QUIC_LOG_LEVEL", "info")
        }

        # Prepare structured arguments and environment
        command_args = []
        if self.is_server():
            command_args = [
                "--listen", f"0.0.0.0:{self.get_port()}",
                "--cert", "/app/certs/cert.pem",
                "--key", "/app/certs/key.pem"
            ]
        else:
            command_args = [
                "--connect", f"{self.get_server_host()}:{self.get_port()}"
            ]

        command_args.extend([
            "--version", self.service_protocol.version,
            "--qlog-dir", "/app/logs"
        ])

        env_vars = dict(self.environments)
        env_vars.update({
            "RUST_LOG": self.environments.get("QUIC_LOG_LEVEL", "info"),
            "QLOGDIR": "/app/logs",
            "SSLKEYLOGFILE": "/app/logs/sslkeylogfile.txt"
        })

        return self.render_template_with_structured_args(
            template_name="docker-compose.yml.j2",
            params=params,
            command_args=command_args,
            env_vars=env_vars
        )

    def get_output_patterns(self) -> List[Tuple[str, str]]:
        """Define output patterns for SimpleQUIC.

        Returns:
            List of (output_type, filename_pattern) tuples
        """
        patterns = super().get_output_patterns()  # Get base QUIC patterns

        # Add SimpleQUIC-specific patterns
        patterns.extend([
            ("simple_quic_log", "simple_quic_{service_name}.log"),
            ("connection_log", "connection_*.log"),
            ("performance_metrics", "perf_{service_name}.json"),
            ("error_log", "error_{service_name}.log")
        ])

        return patterns
```

## Conclusion

You've successfully created a complete PANTHER service plugin! Your SimpleQUIC plugin now includes:

✅ **Service Manager**: Full `IServiceManager` implementation
✅ **Configuration**: Schema validation and version management
✅ **Command Generation**: Compile, run, and deployment commands
✅ **Output Management**: Comprehensive pattern definitions
✅ **Event Integration**: Service lifecycle notifications

## Next Steps

1. **Extend Functionality**: Add more protocol features
2. **Performance Optimization**: Implement caching and optimization patterns
3. **Advanced Templates**: Create more sophisticated deployment configurations
4. **Monitoring Integration**: Add custom metrics and monitoring
5. **Multi-Protocol Support**: Extend to support additional protocols

This tutorial covered essential patterns for PANTHER service plugin development. Use this as a foundation for creating production-ready service plugins for real protocol implementations.

---

*For more advanced patterns and examples, see the [Developer Guide](../DEVELOPER_GUIDE.md) and [API Reference](../api_reference.md).*
