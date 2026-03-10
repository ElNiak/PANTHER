#!/usr/bin/env python3
"""Interactive service plugin tutorial for creating PANTHER service plugins."""
import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


class ServicePluginTutorial:
    """Interactive tutorial for creating PANTHER service plugins."""

    def __init__(self):
        """Initialize ServicePluginTutorial."""
        self.tutorial_dir = Path(__file__).parent
        self.plugin_name = None
        self.plugin_type = None
        self.plugin_dir = None

    def welcome(self):
        """Display the tutorial welcome message."""
        print("=" * 60)
        print("🚀 PANTHER Service Plugin Development Tutorial")
        print("=" * 60)
        print("\nThis interactive tutorial will guide you through:")
        print("• Understanding service plugin architecture")
        print("• Creating plugin structure and configuration")
        print("• Implementing core plugin functionality")
        print("• Adding testing and documentation")
        print("• Integration with PANTHER framework")
        print("\nLet's get started!\n")

    def create_new_plugin(self, plugin_name):
        """Creates a new service plugin with the specified name.

        Args:
            plugin_name: The name of the plugin to create
        """
        print(f"Creating new service plugin: {plugin_name}")

        # Set plugin attributes
        self.plugin_name = plugin_name
        self.plugin_type = "service"

        # Create the plugin directory in the appropriate location
        base_dir = self.tutorial_dir.parent.parent / "services"
        self.plugin_dir = base_dir / plugin_name

        if self.plugin_dir.exists():
            print(f"❌ Plugin already exists at {self.plugin_dir}")
            return False

        # Create the plugin directory and required files
        return self.create_plugin_structure()

    def choose_plugin_type(self):
        """Prompt the user to select a plugin type."""
        print("📋 Step 1: Choose Your Plugin Type")
        print("-" * 40)
        print("Service plugins can be:")
        print("1. Top-level service plugin (contains both IUT and Tester)")
        print("2. IUT (Implementation Under Test) subplugin")
        print("3. Tester (Testing/Validation Tool) subplugin")

        while True:
            choice = input("\nSelect plugin type (1, 2, or 3): ").strip()
            if choice == "1":
                self.plugin_type = "service"
                print("✅ You selected: Top-level Service Plugin")
                break
            elif choice == "2":
                self.plugin_type = "iut"
                print("✅ You selected: IUT Plugin")
                break
            elif choice == "3":
                self.plugin_type = "tester"
                print("✅ You selected: Tester Plugin")
                break
            else:
                print("❌ Invalid choice. Please enter 1, 2, or 3.")

    def get_plugin_details(self):
        """Prompt the user to enter plugin configuration details."""
        print("\n📝 Step 2: Plugin Configuration")
        print("-" * 40)

        while True:
            name = input("Enter plugin name (lowercase, no spaces): ").strip()
            if name and name.isalnum() and name.islower():
                self.plugin_name = name
                break
            else:
                print("❌ Plugin name must be lowercase alphanumeric")

        print(f"✅ Plugin name: {self.plugin_name}")

    def create_plugin_structure(self):
        """Create the plugin directory structure and required files."""
        print("\n🏗️  Step 3: Creating Plugin Structure")
        print("-" * 40)

        # Create plugin directory structure
        plugin_dir = (
            self.tutorial_dir / "generated" / self.plugin_type / self.plugin_name
        )
        plugin_dir.mkdir(parents=True, exist_ok=True)

        # Create files
        files_to_create = [
            "__init__.py",
            f"{self.plugin_name}.py",
            "config_schema.py",
            "Dockerfile",
            "README.md",
            "version_configs/default.yaml",
        ]

        for file_name in files_to_create:
            file_path = plugin_dir / file_name
            file_path.parent.mkdir(exist_ok=True)

            if not file_path.exists():
                self.create_file_content(file_path, file_name)
                print(f"✅ Created: {file_path.relative_to(self.tutorial_dir)}")

        self.plugin_dir = plugin_dir

    def create_file_content(self, file_path, file_name):
        """Generate appropriate content for each file."""
        if file_name == "__init__.py":
            content = f'"""PANTHER {self.plugin_type} plugin: {self.plugin_name}"""\n'

        elif file_name == f"{self.plugin_name}.py":
            content = self.generate_main_plugin_file()

        elif file_name == "config_schema.py":
            content = self.generate_config_schema()

        elif file_name == "Dockerfile":
            content = self.generate_dockerfile()

        elif file_name == "README.md":
            content = self.generate_readme()

        elif file_name == "default.yaml":
            content = self.generate_version_config()

        else:
            content = f"# {file_name} for {self.plugin_name}\n"

        file_path.write_text(content)

    def generate_main_plugin_file(self):
        """Generate the main plugin module source code."""
        class_name = f"{self.plugin_name.title()}ServiceManager"
        config_class = f"{self.plugin_name.title()}Config"

        if self.plugin_type == "iut":
            base_class = "IImplementationManager"
            import_path = "panther.plugins.services.iut.implementation_interface"
        else:
            base_class = "ITesterManager"
            import_path = "panther.plugins.services.testers.tester_interface"

        return f'''"""
{self.plugin_name.title()} Service Manager

This module provides the service manager for the {self.plugin_name} {self.plugin_type} plugin.
"""

import subprocess
import os
import traceback
from pathlib import Path

from panther.plugins.services.{self.plugin_type}.{self.plugin_name}.config_schema import {config_class}
# PluginManager functionality now integrated into PluginManager
from {import_path} import {base_class}
from panther.config.core.models import ProtocolConfig, ProtocolRole

class {class_name}({base_class}):
    """

from typing import ListVersion-specific configuration for {self.plugin_name}"""
    Service manager for {self.plugin_name} {self.plugin_type}.

    This class handles the lifecycle of the {self.plugin_name} service including:
    - Service initialization and configuration
    - Command generation for different phases
    - Integration with PANTHER framework
    """

    def __init__(
        self,
        service_config_to_test: {config_class},
        service_type: str,
        protocol: ProtocolConfig,
        implementation_name: str):
        super().__init__(
            service_config_to_test, service_type, protocol, implementation_name
        )
        self.logger.debug(f"Initializing {{self.__class__.__name__}} for '{{implementation_name}}'")
        # Use summarizer for concise config logging
        from panther.core.utils import log_omega_config_summary
        log_omega_config_summary(self.logger, "Configuration", self.service_config_to_test)
        self.initialize_commands()

    def get_service_name(self) -> str:
        """Return the service name"""
        return self.service_name

    def generate_pre_compile_commands(self):
        """Generate commands to run before compilation"""
        self.logger.debug("Generating pre-compile commands")
        # Add your pre-compilation steps here
        return []

    def generate_compile_commands(self):
        """Generate compilation commands"""
        self.logger.debug("Generating compile commands")
        # Add your compilation steps here
        compile_commands = [
            "echo 'Compiling {self.plugin_name}...'",
            "# Add actual compilation commands here"
        ]
        return compile_commands

    def generate_pre_run_commands(self):
        """Generate commands to run before service execution"""
        self.logger.debug("Generating pre-run commands")
        # Add your pre-run setup here
        return []

    def generate_run_command(self):
        """Generate the main service execution command"""
        self.logger.debug("Generating run command")

        # Example command generation based on role
        if self.protocol.role == ProtocolRole.CLIENT:
            command = f"./{{self.plugin_name}}_client --server {{self.protocol.server_host}} --port {{self.protocol.port}}"
        else:
            command = f"./{{self.plugin_name}}_server --port {{self.protocol.port}}"

        self.logger.debug(f"Generated run command: {{command}}")
        return command

    def generate_post_run_commands(self):
        """Generate commands to run after service execution"""
        self.logger.debug("Generating post-run commands")
        # Add cleanup or post-processing steps here
        return []

    def prepare(self, plugin_manager: Optional[PluginManager] = None):
        """Prepare the service for execution"""
        self.logger.debug("Preparing service for execution")
        # Add any preparation logic here
        pass

    def generate_deployment_commands(self) -> str:
        """Generate deployment commands for the service"""
        self.logger.debug("Generating deployment commands")
        return "echo 'Deploying {self.plugin_name} service...'"
'''

    def generate_config_schema(self):
        """Generate the configuration schema source code."""
        config_class = f"{self.plugin_name.title()}Config"
        version_class = f"{self.plugin_name.title()}Version"

        return f'''"""
Configuration schema for {self.plugin_name} plugin.

This module defines the configuration structure and validation
for the {self.plugin_name} {self.plugin_type} plugin.
"""

from dataclasses import dataclass, field
import logging
import os
from pathlib import Path

from omegaconf import OmegaConf

from panther.plugins.services.{self.plugin_type}.config_schema import ImplementationConfig, VersionBase
from panther.plugins.services.{self.plugin_type}.config_schema import ImplementationType

@dataclass
class {version_class}(VersionBase):
    """

    version: str = ""
    commit: str = ""
    dependencies: List[Dict[str, str]] = field(default_factory=list)
    client: Optional[Dict] = field(default_factory=dict)
    server: Optional[Dict] = field(default_factory=dict)

@dataclass
class {config_class}(ImplementationConfig):
    """
    Configuration class for {self.plugin_name} implementation.

    Attributes:
        name: Implementation name
        type: Plugin type designation
        custom_param: Example custom parameter
        version: Version configuration loaded from YAML files
    """

    name: str = "{self.plugin_name}"
    type: ImplementationType = ImplementationType.{self.plugin_type}

    # Custom configuration parameters
    custom_param: str = "default_value"
    enable_feature: bool = True
    timeout: int = 30

    # Version configuration (loaded dynamically)
    version: {version_class} = field(
        default_factory=lambda: {config_class}.load_versions_from_files()
    )

    @staticmethod
    def load_versions_from_files(
        version_configs_dir: str = f"{{Path(os.path.dirname(__file__))}}/version_configs/") -> {version_class}:
        """Load version configurations dynamically from YAML files."""
        logging.debug(f"Loading {self.plugin_name} versions from {{version_configs_dir}}")

        for version_file in os.listdir(version_configs_dir):
            if version_file.endswith(".yaml"):
                version_path = os.path.join(version_configs_dir, version_file)
                try:
                    config = OmegaConf.load(version_path)
                    return {version_class}(**config)
                except Exception as e:
                    logging.warning(f"Failed to load version config {{version_file}}: {{e}}")

        # Return default version if no config files found
        return {version_class}()
'''

    def generate_dockerfile(self):
        """Generate a Dockerfile for the plugin."""
        return f"""# Dockerfile for {self.plugin_name} {self.plugin_type} plugin

FROM --platform=linux/amd64 panther_base_service:latest

ENV DEBIAN_FRONTEND=noninteractive

# Define build arguments for version-specific configurations
ARG VERSION=main
ARG DEPENDENCIES="[]"
ENV VERSION=${{VERSION}}
ENV DEPENDENCIES=${{DEPENDENCIES}}

# Install plugin-specific dependencies
RUN apt-get update && apt-get install -y \\
    # Add your dependencies here
    # build-essential \\
    # git \\
    # cmake \\
    && rm -rf /var/lib/apt/lists/*

USER ${{USER_N}}

# Set working directory
WORKDIR /opt/{self.plugin_name}

# Copy plugin files
COPY . .

# Build the plugin
RUN echo "Building {self.plugin_name}..." && \\
    # Add your build commands here
    echo "Build completed"

# Set the entrypoint
ENTRYPOINT ["./entrypoint.sh"]
"""

    def generate_readme(self):
        """Generate a README for the plugin."""
        return f"""# {self.plugin_name.title()} Plugin

> **Plugin Type**: Service ({self.plugin_type.upper()})
> **Verified Source Location**: `plugins/services/{self.plugin_type}/{self.plugin_name}/`

## Purpose and Overview

The {self.plugin_name.title()} plugin provides [describe the plugin's purpose and functionality].

This {self.plugin_type} plugin is valuable for:
- **Feature 1**: Description of first key feature
- **Feature 2**: Description of second key feature
- **Feature 3**: Description of third key feature

## Requirements and Dependencies

### System Requirements
- **Operating System**: Linux (Ubuntu 20.04+ recommended)
- **Runtime**: Python 3.8+
- **Memory**: 512MB minimum

### Python Dependencies
```bash
# Core dependencies
omegaconf>=2.0
dataclasses-json
```

## Configuration Options

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | String | `"{self.plugin_name}"` | Plugin identifier |
| `type` | ImplementationType | `{self.plugin_type}` | Plugin type |
| `custom_param` | String | `"default_value"` | Example parameter |
| `enable_feature` | Boolean | `true` | Enable special feature |
| `timeout` | Integer | `30` | Operation timeout in seconds |

## Usage Examples

### Basic Configuration

```yaml
services:
  - name: "{self.plugin_name}_service"
    type: "{self.plugin_type}"
    implementation: "{self.plugin_name}"
    config:
      custom_param: "example_value"
      enable_feature: true
      timeout: 60
```

### Advanced Configuration

```yaml
services:
  - name: "{self.plugin_name}_advanced"
    type: "{self.plugin_type}"
    implementation: "{self.plugin_name}"
    config:
      custom_param: "advanced_value"
      enable_feature: true
      timeout: 120
      version:
        version: "latest"
        client:
          feature_x: true
        server:
          feature_y: true
```

## Integration with Testing Framework

This plugin integrates with PANTHER's testing infrastructure through:
- **Service Management**: Automatic lifecycle management
- **Configuration Validation**: Schema-based configuration validation
- **Logging Integration**: Structured logging with PANTHER framework
- **Resource Management**: Automatic resource cleanup

## Development

### Building from Source

```bash
# Clone and build
git clone [repository_url]
cd {self.plugin_name}
docker build -t panther_{self.plugin_name} .
```

### Testing

```bash
# Run plugin tests
python -m pytest tests/

# Integration testing
panther test --plugin {self.plugin_name}
```

## Related Documentation

- [Plugin Development Guide](../../__init__.py) (module docstring)
- [PANTHER Plugin System](../../README.md)
- [Configuration Schema Documentation](../config_schema.py)

---

*This plugin was generated using the PANTHER Plugin Development Tutorial.*
"""

    def generate_version_config(self):
        """Generate a default version configuration YAML."""
        return f"""# Default version configuration for {self.plugin_name}

version: "main"
commit: ""
dependencies: []

client:
  default_port: 8080
  max_connections: 100

server:
  bind_address: "0.0.0.0"
  port: 8080
  threads: 4
"""

    def demonstrate_integration(self):
        """Demonstrate plugin integration with a test configuration."""
        print("\n🔗 Step 4: Testing Plugin Integration")
        print("-" * 40)

        # Create a simple test configuration
        test_config = f"""# Test configuration for {self.plugin_name}
tests:
  - name: "{self.plugin_name}_test"
    services:
      - name: "{self.plugin_name}_service"
        type: "{self.plugin_type}"
        implementation: "{self.plugin_name}"
        config:
          custom_param: "test_value"
          enable_feature: true
"""

        config_file = self.plugin_dir / "test_config.yaml"
        config_file.write_text(test_config)
        print(
            f"✅ Created test configuration: {config_file.relative_to(self.tutorial_dir)}"
        )

        # Show how to validate the plugin
        print("\n📋 Plugin Validation Steps:")
        print("1. Validate configuration schema")
        print("2. Test plugin loading")
        print("3. Verify service lifecycle")
        print("4. Run integration tests")

    def show_next_steps(self):
        """Display next steps and additional resources."""
        print("\n🎉 Tutorial Complete!")
        print("=" * 60)
        print(f"Your {self.plugin_name} plugin has been created at:")
        print(f"📁 {self.plugin_dir.relative_to(self.tutorial_dir)}")
        print("\n📚 Next Steps:")
        print("1. Customize the plugin implementation")
        print("2. Add your specific business logic")
        print("3. Update configuration parameters")
        print("4. Add comprehensive tests")
        print("5. Document any special requirements")
        print("6. Integrate with your protocol")

        print("\n🔧 Development Commands:")
        print(f"cd {self.plugin_dir}")
        print(f"# Edit {self.plugin_name}.py to add your implementation")
        print("# Update config_schema.py for your configuration needs")
        print("# Modify Dockerfile for your build requirements")

        print("\n📖 Additional Resources:")
        print("• PANTHER Plugin Development Guide")
        print("• Service Plugin Examples")
        print("• Configuration Schema Documentation")
        print("• Testing Framework Integration")

    def run(self, args=None):
        """Run the interactive tutorial."""
        try:
            # Check if we're creating a new plugin directly
            if args and args.create:
                plugin_name = args.create
                return 0 if self.create_new_plugin(plugin_name) else 1

            # Otherwise, run the interactive tutorial
            self.welcome()
            self.choose_plugin_type()
            self.get_plugin_details()
            self.create_plugin_structure()
            self.demonstrate_integration()
            self.show_next_steps()

        except KeyboardInterrupt:
            print("\n\n👋 Tutorial cancelled by user.")
        except Exception as e:
            print(f"\n❌ Tutorial error: {e}")
            return 1

        return 0


if __name__ == "__main__":
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="PANTHER Service Plugin Tutorial")
    parser.add_argument(
        "--create",
        metavar="NAME",
        help="Create a new service plugin with the specified name",
    )
    args = parser.parse_args()

    tutorial = ServicePluginTutorial()
    sys.exit(tutorial.run(args))
