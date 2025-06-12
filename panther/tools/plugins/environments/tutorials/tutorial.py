#!/usr/bin/env python3
"""
Interactive Environment Plugin Tutorial for PANTHER

This tutorial guides you through creating environment plugins for PANTHER,
including both network and execution environment types.

Author: PANTHER Development Team
License: MIT
"""

import os
import sys
from pathlib import Path
from typing import Any


class EnvironmentPluginTutorial:
    """Interactive tutorial for creating PANTHER environment plugins."""

    def __init__(self):
        self.tutorial_dir = Path(__file__).parent
        self.plugins_dir = self.tutorial_dir.parent.parent

    def run(self):
        """Run the interactive tutorial."""
        self.display_header()

        # Tutorial menu
        while True:
            choice = self.display_menu()

            if choice == "1":
                self.network_environment_tutorial()
            elif choice == "2":
                self.execution_environment_tutorial()
            elif choice == "3":
                self.integration_tutorial()
            elif choice == "4":
                self.show_examples()
            elif choice == "5":
                print("\n✅ Tutorial completed! Happy coding!")
                break
            else:
                print("❌ Invalid choice. Please try again.")

    def display_header(self):
        """Display tutorial header."""
        print("=" * 80)
        print("🌐 PANTHER Environment Plugin Development Tutorial")
        print("=" * 80)
        print()
        print("Welcome to the interactive environment plugin tutorial!")
        print("This tutorial will guide you through creating:")
        print("• Network Environment Plugins (docker_compose, shadow_ns, etc.)")
        print("• Execution Environment Plugins (memcheck, strace, profiling, etc.)")
        print("• Integration patterns and best practices")
        print()

    def display_menu(self):
        """Display main menu and get user choice."""
        print("\n" + "─" * 60)
        print("📋 TUTORIAL MENU")
        print("─" * 60)
        print("1. 🌐 Network Environment Plugin Tutorial")
        print("2. ⚙️  Execution Environment Plugin Tutorial")
        print("3. 🔗 Integration & Best Practices")
        print("4. 📚 Show Real Examples")
        print("5. 🚪 Exit Tutorial")
        print("─" * 60)

        return input("\nSelect option (1-5): ").strip()

    def network_environment_tutorial(self):
        """Tutorial for network environment plugins."""
        print("\n" + "🌐" * 30)
        print("NETWORK ENVIRONMENT PLUGIN TUTORIAL")
        print("🌐" * 30)

        # Get plugin details
        plugin_name = self.get_input(
            "Enter network environment plugin name",
            "my_network_env",
            "Plugin name (e.g., 'kubernetes', 'mininet', 'custom_docker')",
        )

        plugin_description = self.get_input(
            "Enter plugin description",
            "Custom network environment for testing",
            "Brief description of the environment",
        )

        # Network configuration
        print("\n🔧 Network Configuration:")
        supports_containers = self.get_yes_no("Does this environment support containers?", True)
        supports_scaling = self.get_yes_no("Does this environment support scaling?", False)
        requires_root = self.get_yes_no("Does this environment require root privileges?", False)

        # Generate the plugin
        plugin_dir = self.tutorial_dir / f"{plugin_name}_generated"
        self.create_network_environment_plugin(
            plugin_dir,
            plugin_name,
            plugin_description,
            supports_containers,
            supports_scaling,
            requires_root,
        )

        print(f"\n✅ Network environment plugin '{plugin_name}' generated!")
        print(f"📁 Location: {plugin_dir}")
        self.show_next_steps(plugin_dir)

    def execution_environment_tutorial(self):
        """Tutorial for execution environment plugins."""
        print("\n" + "⚙️" * 30)
        print("EXECUTION ENVIRONMENT PLUGIN TUTORIAL")
        print("⚙️" * 30)

        # Get plugin details
        plugin_name = self.get_input(
            "Enter execution environment plugin name",
            "my_exec_env",
            "Plugin name (e.g., 'custom_profiler', 'security_scanner', 'monitor')",
        )

        plugin_description = self.get_input(
            "Enter plugin description",
            "Custom execution environment for analysis",
            "Brief description of the execution environment",
        )

        # Tool configuration
        print("\n🔧 Tool Configuration:")
        tool_command = self.get_input(
            "Enter the main tool command",
            "my_tool",
            "Command to run (e.g., 'valgrind', 'perf', 'strace')",
        )

        generates_reports = self.get_yes_no("Does this tool generate report files?", True)
        requires_symbols = self.get_yes_no("Does this tool require debug symbols?", False)
        is_profiler = self.get_yes_no("Is this a performance profiling tool?", False)

        # Generate the plugin
        plugin_dir = self.tutorial_dir / f"{plugin_name}_generated"
        self.create_execution_environment_plugin(
            plugin_dir,
            plugin_name,
            plugin_description,
            tool_command,
            generates_reports,
            requires_symbols,
            is_profiler,
        )

        print(f"\n✅ Execution environment plugin '{plugin_name}' generated!")
        print(f"📁 Location: {plugin_dir}")
        self.show_next_steps(plugin_dir)

    def create_network_environment_plugin(
        self,
        plugin_dir: Path,
        name: str,
        description: str,
        supports_containers: bool,
        supports_scaling: bool,
        requires_root: bool,
    ):
        """Generate a complete network environment plugin."""
        plugin_dir.mkdir(exist_ok=True)

        # Main implementation
        implementation_content = f'''"""
{description}

This network environment plugin provides custom networking capabilities
for PANTHER testing scenarios.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
import subprocess
import json

from panther.plugins.environments.network_environment.network_environment_interface import INetworkEnvironment
from panther.plugins.environments.config_schema import EnvironmentConfig


class {name.title().replace("_", "")}NetworkEnvironment(INetworkEnvironment):
    """
    {description}

    Features:
    - Container support: {supports_containers}
    - Scaling support: {supports_scaling}
    - Root required: {requires_root}
    """

    def __init__(self, config: EnvironmentConfig, output_dir: Path, **kwargs):
        super().__init__(config, output_dir, **kwargs)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.network_name = f"panther_{name}_{{config.name}}"
        self.containers: List[str] = []

    def setup(self) -> None:
        """Set up the network environment."""
        self.logger.info(f"Setting up {name} network environment")

        try:
            # Create network infrastructure
            self._create_network()

            # Configure network policies
            self._configure_network_policies()

            # Setup monitoring if needed
            self._setup_monitoring()

            self.logger.info("Network environment setup completed successfully")

        except Exception as e:
            self.logger.error(f"Failed to setup network environment: {{e}}")
            raise

    def teardown(self) -> None:
        """Clean up the network environment."""
        self.logger.info(f"Tearing down {name} network environment")

        try:
            # Stop all containers
            for container in self.containers:
                self._stop_container(container)

            # Remove network
            self._remove_network()

            # Cleanup monitoring
            self._cleanup_monitoring()

            self.logger.info("Network environment teardown completed")

        except Exception as e:
            self.logger.error(f"Failed to teardown network environment: {{e}}")

    def deploy_service(self, service_name: str, service_config: Dict[str, Any]) -> Dict[str, Any]:
        """Deploy a service in the network environment."""
        self.logger.info(f"Deploying service {{service_name}}")

        container_config = {{
            "name": f"{{self.network_name}}_{{service_name}}",
            "image": service_config.get("image", "ubuntu:latest"),
            "network": self.network_name,
            "environment": service_config.get("environment", {{}}),
            "ports": service_config.get("ports", []),
            "volumes": service_config.get("volumes", [])
        }}

        # Deploy container
        container_id = self._deploy_container(container_config)
        self.containers.append(container_id)

        # Get network information
        network_info = self._get_container_network_info(container_id)

        return {{
            "container_id": container_id,
            "ip_address": network_info.get("ip_address"),
            "hostname": network_info.get("hostname"),
            "network_name": self.network_name,
            "ports": network_info.get("ports", [])
        }}

    def get_network_info(self) -> Dict[str, Any]:
        """Get network environment information."""
        return {{
            "network_name": self.network_name,
            "network_type": "{name}",
            "containers": len(self.containers),
            "supports_containers": {supports_containers},
            "supports_scaling": {supports_scaling},
            "requires_root": {requires_root},
            "status": "active" if self.containers else "inactive"
        }}

    def _create_network(self) -> None:
        """Create the network infrastructure."""
        # Implementation depends on specific network type
        self.logger.debug(f"Creating network: {{self.network_name}}")

        # Example: Create custom network
        # cmd = ["docker", "network", "create", "--driver", "bridge", self.network_name]
        # subprocess.run(cmd, check=True, capture_output=True)

    def _configure_network_policies(self) -> None:
        """Configure network policies and rules."""
        self.logger.debug("Configuring network policies")

        # Add network configuration here
        # - Firewall rules
        # - Traffic shaping
        # - Isolation policies

    def _setup_monitoring(self) -> None:
        """Setup network monitoring."""
        if self.config.monitoring_enabled:
            self.logger.debug("Setting up network monitoring")
            # Setup packet capture, metrics collection, etc.

    def _stop_container(self, container_id: str) -> None:
        """Stop a container."""
        # Implementation for stopping containers
        pass

    def _remove_network(self) -> None:
        """Remove the network."""
        # Implementation for network cleanup
        pass

    def _cleanup_monitoring(self) -> None:
        """Cleanup monitoring resources."""
        # Implementation for monitoring cleanup
        pass

    def _deploy_container(self, config: Dict[str, Any]) -> str:
        """Deploy a container with the given configuration."""
        # Implementation for container deployment
        return f"container_{{config['name']}}"

    def _get_container_network_info(self, container_id: str) -> Dict[str, Any]:
        """Get network information for a container."""
        # Implementation for getting container network info
        return {{
            "ip_address": "192.168.1.100",
            "hostname": f"{name}-host",
            "ports": []
        }}
'''

        (plugin_dir / "__init__.py").write_text(
            f"from .{name} import {name.title().replace('_', '')}NetworkEnvironment"
        )
        (plugin_dir / f"{name}.py").write_text(implementation_content)

        # Configuration schema
        config_schema = f'''"""
Configuration schema for {name} network environment plugin.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

from panther.plugins.environments.config_schema import EnvironmentConfig


@dataclass
class {name.title().replace("_", "")}Config(EnvironmentConfig):
    """Configuration for {name} network environment."""

    # Network settings
    network_driver: str = "bridge"
    subnet: Optional[str] = None
    gateway: Optional[str] = None

    # Container settings
    default_image: str = "ubuntu:latest"
    container_limits: Dict[str, Any] = field(default_factory=lambda: {{
        "memory": "512m",
        "cpu": "1.0"
    }})

    # Environment-specific settings
    {"requires_root: bool = True" if requires_root else "requires_root: bool = False"}
    {"supports_scaling: bool = True" if supports_scaling else "supports_scaling: bool = False"}

    # Monitoring settings
    monitoring_enabled: bool = False
    capture_packets: bool = False
    metrics_interval: int = 30

    # Custom settings for {name}
    custom_options: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        """Validate the configuration."""
        super().validate()

        if self.subnet and not self._is_valid_subnet(self.subnet):
            raise ValueError(f"Invalid subnet format: {{self.subnet}}")

        if self.container_limits.get("memory"):
            memory = self.container_limits["memory"]
            if not isinstance(memory, str) or not memory.endswith(('m', 'g', 'M', 'G')):
                raise ValueError(f"Invalid memory format: {{memory}}")

    def _is_valid_subnet(self, subnet: str) -> bool:
        """Validate subnet format."""
        # Basic subnet validation
        try:
            import ipaddress
            ipaddress.IPv4Network(subnet, strict=False)
            return True
        except (ValueError, ipaddress.AddressValueError):
            return False
'''

        (plugin_dir / "config_schema.py").write_text(config_schema)

        # Default configuration
        default_config = f"""# Default configuration for {name} network environment
name: "{name}"
type: "network_environment"
plugin_class: "{name.title().replace("_", "")}NetworkEnvironment"

# Network configuration
network_driver: "bridge"
subnet: null
gateway: null

# Container defaults
default_image: "ubuntu:latest"
container_limits:
  memory: "512m"
  cpu: "1.0"

# Plugin-specific settings
requires_root: {str(requires_root).lower()}
supports_scaling: {str(supports_scaling).lower()}

# Monitoring
monitoring_enabled: false
capture_packets: false
metrics_interval: 30

# Custom options
custom_options: {{}}
"""

        (plugin_dir / "config.yaml").write_text(default_config)

        # Dockerfile
        dockerfile_content = f"""FROM ubuntu:22.04

# Install dependencies for {name}
RUN apt-get update && apt-get install -y \\
    python3 \\
    python3-pip \\
    iproute2 \\
    iptables \\
    {"docker.io" if supports_containers else ""} \\
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /tmp/
RUN pip3 install -r /tmp/requirements.txt

# Copy plugin files
COPY . /plugin/
WORKDIR /plugin

# Set execution permissions
{"RUN chmod +x /plugin/setup.sh" if requires_root else ""}

ENTRYPOINT ["python3", "-m", "{name}"]
"""

        (plugin_dir / "Dockerfile").write_text(dockerfile_content)

        # Requirements
        requirements = """panther-framework>=0.1.0
pyyaml>=6.0
"""

        (plugin_dir / "requirements.txt").write_text(requirements)

        # README
        self._create_environment_readme(
            plugin_dir,
            name,
            description,
            "network",
            {
                "supports_containers": supports_containers,
                "supports_scaling": supports_scaling,
                "requires_root": requires_root,
            },
        )

    def create_execution_environment_plugin(
        self,
        plugin_dir: Path,
        name: str,
        description: str,
        tool_command: str,
        generates_reports: bool,
        requires_symbols: bool,
        is_profiler: bool,
    ):
        """Generate a complete execution environment plugin."""
        plugin_dir.mkdir(exist_ok=True)

        # Build conditional code sections
        symbol_setup = ""
        if requires_symbols:
            symbol_setup = """
            # Setup symbol resolution
            if self.config.debug_symbols:
                self._setup_symbol_resolution()"""

        reports_generation = ""
        if generates_reports:
            reports_generation = """
            # Generate reports
            self._generate_reports(result)"""

        reports_finalization = ""
        if generates_reports:
            reports_finalization = """
            # Finalize reports
            self._finalize_reports()"""

        profiling_metrics = ""
        reports_summaries = ""
        if is_profiler:
            profiling_metrics = """
        # Add profiling metrics
        if hasattr(self, '_profiling_metrics'):
            results['profiling_metrics'] = self._profiling_metrics"""

        if generates_reports:
            reports_summaries = """
        # Add report summaries
        if hasattr(self, '_report_summaries'):
            results['report_summaries'] = self._report_summaries"""

        # Additional methods for specific features
        additional_methods = ""

        if generates_reports:
            additional_methods += '''
    def _generate_reports(self, result: subprocess.CompletedProcess) -> None:
        """Generate analysis reports."""
        self.logger.debug('Generating analysis reports')

        # Parse tool output and generate structured reports
        report_data = {
            'timestamp': time.time(),
            'exit_code': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'tool': self.tool_command
        }

        # Save JSON report
        report_file = self.reports_dir / 'analysis_report.json'
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2)

    def _finalize_reports(self) -> None:
        """Finalize all generated reports."""
        self.logger.info('Finalizing reports')
        # Aggregate reports, create summaries, etc.
        pass'''

        if requires_symbols:
            additional_methods += '''
    def _setup_symbol_resolution(self) -> None:
        """Setup debug symbol resolution."""
        self.logger.debug('Setting up debug symbol resolution')
        # Configure symbol paths, debug info, etc.
        if hasattr(self.config, 'debug_symbols_path') and self.config.debug_symbols_path:
            import os
            env = os.environ.copy()
            env['DEBUG_SYMBOLS_PATH'] = self.config.debug_symbols_path
        pass'''

        if is_profiler:
            additional_methods += '''
    def _configure_profiling(self) -> None:
        """Configure profiling options."""
        self.logger.debug('Configuring profiling settings')
        # Setup profiling-specific configuration
        self._profiling_metrics = {}
        pass'''

        # Main implementation
        implementation_content = f'''"""
{description}

This execution environment plugin provides {tool_command}-based analysis
for PANTHER testing scenarios.
"""

import logging
import subprocess
import shutil
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
import json
import time

from panther.plugins.environments.execution_environment.execution_environment_interface import IExecutionEnvironment
from panther.plugins.environments.config_schema import EnvironmentConfig


class {name.title().replace("_", "")}ExecutionEnvironment(IExecutionEnvironment):
    """
    {description}

    Tool: {tool_command}
    Features:
    - Report generation: {generates_reports}
    - Debug symbols: {requires_symbols}
    - Profiling: {is_profiler}
    """

    def __init__(self, config: EnvironmentConfig, output_dir: Path, **kwargs):
        super().__init__(config, output_dir, **kwargs)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.tool_command = "{tool_command}"
        self.reports_dir = output_dir / "reports" / "{name}"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def setup(self) -> None:
        """Set up the execution environment."""
        self.logger.info(f"Setting up {name} execution environment")

        try:
            # Check tool availability
            if not self._check_tool_availability():
                raise RuntimeError(f"Tool {{self.tool_command}} not available")

            # Setup output directories
            self._setup_output_directories()

            # Configure tool settings
            self._configure_tool(){symbol_setup}

            self.logger.info("Execution environment setup completed")

        except Exception as e:
            self.logger.error(f"Failed to setup execution environment: {{e}}")
            raise

    def execute_with_environment(self, command: List[str], **kwargs) -> subprocess.CompletedProcess:
        """Execute a command with the execution environment."""
        self.logger.info(f"Executing command with {name}: {{' '.join(command)}}")

        # Build the execution command
        execution_cmd = self._build_execution_command(command)

        # Set environment variables
        env = self._get_environment_variables()

        try:
            # Execute the command
            start_time = time.time()
            result = subprocess.run(
                execution_cmd,
                env=env,
                capture_output=True,
                text=True,
                **kwargs
            )
            execution_time = time.time() - start_time

            # Process results
            self._process_execution_results(result, execution_time){reports_generation}

            self.logger.info(f"Command execution completed in {{execution_time:.2f}}s")
            return result

        except Exception as e:
            self.logger.error(f"Command execution failed: {{e}}")
            raise

    def teardown(self) -> None:
        """Clean up the execution environment."""
        self.logger.info(f"Tearing down {name} execution environment")

        try:{reports_finalization}

            # Cleanup temporary files
            self._cleanup_temp_files()

            # Archive results
            self._archive_results()

            self.logger.info("Execution environment teardown completed")

        except Exception as e:
            self.logger.error(f"Failed to teardown execution environment: {{e}}")

    def get_results(self) -> Dict[str, Any]:
        """Get execution results and metrics."""
        results = {{
            "tool": self.tool_command,
            "environment": "{name}",
            "reports_directory": str(self.reports_dir),
            "generates_reports": {generates_reports},
            "requires_symbols": {requires_symbols},
            "is_profiler": {is_profiler},
        }}{profiling_metrics}{reports_summaries}

        return results

    def _check_tool_availability(self) -> bool:
        """Check if the tool is available on the system."""
        return shutil.which(self.tool_command) is not None

    def _setup_output_directories(self) -> None:
        """Setup output directories for reports and logs."""
        directories = ["logs", "tmp"]
        {"if True:" if generates_reports else ""}
        {"    directories.extend(['reports', 'profiles'])" if generates_reports else ""}

        for directory in directories:
            (self.reports_dir / directory).mkdir(exist_ok=True)

    def _configure_tool(self) -> None:
        """Configure tool-specific settings."""
        self.logger.debug(f"Configuring {{self.tool_command}} settings")

        # Tool-specific configuration
        {"# Configure profiling options" if is_profiler else ""}
        {"if hasattr(self.config, 'profiling_options'):" if is_profiler else ""}
        {"    self._configure_profiling()" if is_profiler else ""}

    def _build_execution_command(self, command: List[str]) -> List[str]:
        """Build the complete execution command with tool wrapper."""
        base_cmd = [self.tool_command]

        # Add tool-specific options
        {"# Add profiling options" if is_profiler else ""}
        {"if True:" if is_profiler else ""}
        {"    base_cmd.extend(['--profile', '--output', str(self.reports_dir / 'profile.out')])" if is_profiler else ""}

        {"# Add report output options" if generates_reports else ""}
        {"if True:" if generates_reports else ""}
        {"    base_cmd.extend(['--report', str(self.reports_dir / 'report.txt')])" if generates_reports else ""}

        # Add the actual command
        base_cmd.extend(command)

        return base_cmd

    def _get_environment_variables(self) -> Dict[str, str]:
        """Get environment variables for execution."""
        env = os.environ.copy()

        # Add tool-specific environment variables
        env.update({{
            f"{name.upper()}_OUTPUT_DIR": str(self.reports_dir),
            f"{name.upper()}_LOG_LEVEL": self.config.log_level or "INFO"
        }})

        {"# Add debug symbol paths" if requires_symbols else ""}
        {"if self.config.debug_symbols:" if requires_symbols else ""}
        {"    env['DEBUG_SYMBOLS_PATH'] = getattr(self.config, 'debug_symbols_path', '')" if requires_symbols else ""}

        return env

    def _process_execution_results(self, result: subprocess.CompletedProcess,
                                 execution_time: float) -> None:
        """Process the execution results."""
        # Log execution metrics
        self.logger.debug(f"Execution time: {{execution_time:.2f}}s")
        self.logger.debug(f"Return code: {{result.returncode}}")

        {"# Store profiling metrics" if is_profiler else ""}
        {"if True:" if is_profiler else ""}
        {"    self._profiling_metrics = {" if is_profiler else ""}
        {"        'execution_time': execution_time," if is_profiler else ""}
        {"        'return_code': result.returncode," if is_profiler else ""}
        {"        'stdout_lines': len(result.stdout.splitlines())" if is_profiler else ""}
        {"    }" if is_profiler else ""}

        # Save logs
        (self.reports_dir / "logs" / "stdout.log").write_text(result.stdout)
        (self.reports_dir / "logs" / "stderr.log").write_text(result.stderr)

    def _cleanup_temp_files(self) -> None:
        """Cleanup temporary files."""
        temp_dir = self.reports_dir / "tmp"
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    def _archive_results(self) -> None:
        """Archive execution results."""
        # Implementation for result archiving
        pass{additional_methods}
'''

        (plugin_dir / "__init__.py").write_text(
            f"from .{name} import {name.title().replace('_', '')}ExecutionEnvironment"
        )
        (plugin_dir / f"{name}.py").write_text(implementation_content)

        # Configuration schema
        config_schema = f'''"""
Configuration schema for {name} execution environment plugin.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

from panther.plugins.environments.config_schema import EnvironmentConfig


@dataclass
class {name.title().replace("_", "")}Config(EnvironmentConfig):
    """Configuration for {name} execution environment."""

    # Tool configuration
    tool_command: str = "{tool_command}"
    tool_options: List[str] = field(default_factory=list)

    # Output configuration
    output_format: str = "text"
    {"generate_reports: bool = True" if generates_reports else "generate_reports: bool = False"}

    # Debugging configuration
    {"debug_symbols: bool = True" if requires_symbols else "debug_symbols: bool = False"}
    {"debug_symbols_path: Optional[str] = None" if requires_symbols else ""}

    # Profiling configuration (if applicable)
    {"profiling_mode: str = 'standard'" if is_profiler else ""}
    {"profiling_frequency: int = 100" if is_profiler else ""}
    {"profile_memory: bool = True" if is_profiler else ""}
    {"profile_cpu: bool = True" if is_profiler else ""}

    # Analysis options
    detailed_analysis: bool = False
    include_system_calls: bool = True
    filter_noise: bool = True

    # Custom options
    custom_options: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        """Validate the configuration."""
        super().validate()

        if not self.tool_command:
            raise ValueError("tool_command is required")

        {"if self.debug_symbols and not self.debug_symbols_path:" if requires_symbols else ""}
        {"    raise ValueError('debug_symbols_path required when debug_symbols is enabled')" if requires_symbols else ""}

        {"if self.profiling_frequency <= 0:" if is_profiler else ""}
        {"    raise ValueError('profiling_frequency must be positive')" if is_profiler else ""}
'''

        (plugin_dir / "config_schema.py").write_text(config_schema)

        # Default configuration
        default_config = f"""# Default configuration for {name} execution environment
name: "{name}"
type: "execution_environment"
plugin_class: "{name.title().replace("_", "")}ExecutionEnvironment"

# Tool settings
tool_command: "{tool_command}"
tool_options: []

# Output settings
output_format: "text"
generate_reports: {str(generates_reports).lower()}

# Debug settings
{"debug_symbols: true" if requires_symbols else "debug_symbols: false"}
{"debug_symbols_path: null" if requires_symbols else ""}

# Analysis settings
detailed_analysis: false
include_system_calls: true
filter_noise: true

{"# Profiling settings (if applicable)" if is_profiler else ""}
{"profiling_mode: 'standard'" if is_profiler else ""}
{"profiling_frequency: 100" if is_profiler else ""}
{"profile_memory: true" if is_profiler else ""}
{"profile_cpu: true" if is_profiler else ""}

# Custom options
custom_options: {{}}
"""

        (plugin_dir / "config.yaml").write_text(default_config)

        # Dockerfile
        dockerfile_content = f"""FROM ubuntu:22.04

# Install {tool_command} and dependencies
RUN apt-get update && apt-get install -y \\
    python3 \\
    python3-pip \\
    {tool_command} \\
    {"binutils" if requires_symbols else ""} \\
    {"gdb" if requires_symbols else ""} \\
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /tmp/
RUN pip3 install -r /tmp/requirements.txt

# Copy plugin files
COPY . /plugin/
WORKDIR /plugin

ENTRYPOINT ["python3", "-m", "{name}"]
"""

        (plugin_dir / "Dockerfile").write_text(dockerfile_content)

        # Requirements
        requirements = """panther-framework>=0.1.0
pyyaml>=6.0
"""

        (plugin_dir / "requirements.txt").write_text(requirements)

        # README
        self._create_environment_readme(
            plugin_dir,
            name,
            description,
            "execution",
            {
                "tool_command": tool_command,
                "generates_reports": generates_reports,
                "requires_symbols": requires_symbols,
                "is_profiler": is_profiler,
            },
        )

    def _create_environment_readme(
        self,
        plugin_dir: Path,
        name: str,
        description: str,
        env_type: str,
        features: dict[str, Any],
    ):
        """Create a comprehensive README for the environment plugin."""

        readme_content = f"""# {name.title().replace("_", " ")} Environment Plugin

{description}

## Overview

This is a **{env_type} environment plugin** for the PANTHER testing framework. It provides specialized execution capabilities for testing and analysis scenarios.

## Features

"""

        if env_type == "network":
            readme_content += f"""- **Container Support**: {features["supports_containers"]}
- **Scaling Support**: {features["supports_scaling"]}
- **Root Privileges**: {features["requires_root"]}
- **Network Isolation**: Custom network environments
- **Service Deployment**: Automated container deployment
- **Monitoring**: Network traffic analysis and monitoring
"""
        else:  # execution
            readme_content += f"""- **Tool**: {features["tool_command"]}
- **Report Generation**: {features["generates_reports"]}
- **Debug Symbols**: {features["requires_symbols"]}
- **Profiling**: {features["is_profiler"]}
- **Analysis**: Detailed execution analysis
- **Integration**: Seamless PANTHER integration
"""

        readme_content += """
## Installation

### Prerequisites

"""

        if env_type == "network":
            readme_content += """- Docker Engine
- Python 3.8+
- Network administration privileges (if required)
"""
        else:
            readme_content += f"""- {features["tool_command"]} tool
- Python 3.8+
{"- Debug symbols and GDB (for symbol resolution)" if features.get("requires_symbols") else ""}
"""

        readme_content += f"""
### Setup

1. **Install the plugin**:
   ```bash
   # Copy to PANTHER plugins directory
   cp -r {name} $PANTHER_HOME/plugins/environments/{env_type}_environment/
   ```

2. **Install dependencies**:
   ```bash
   cd $PANTHER_HOME/plugins/environments/{env_type}_environment/{name}
   pip install -r requirements.txt
   ```

3. **Build Docker image** (if needed):
   ```bash
   docker build -t panther-{name} .
   ```

## Configuration

### Basic Configuration

```yaml
# config.yaml
name: "{name}"
type: "{env_type}_environment"
plugin_class: "{name.title().replace("_", "")}{"Network" if env_type == "network" else "Execution"}Environment"

"""

        if env_type == "network":
            readme_content += """# Network settings
network_driver: "bridge"
subnet: "192.168.100.0/24"
gateway: "192.168.100.1"

# Container settings
default_image: "ubuntu:latest"
container_limits:
  memory: "512m"
  cpu: "1.0"

# Monitoring
monitoring_enabled: true
capture_packets: false
"""
        else:
            readme_content += f"""# Tool settings
tool_command: "{features["tool_command"]}"
tool_options: []

# Output settings
output_format: "text"
generate_reports: {str(features["generates_reports"]).lower()}

# Analysis settings
detailed_analysis: true
include_system_calls: true
filter_noise: false
"""

        readme_content += """```

### Advanced Configuration

"""

        if env_type == "network":
            readme_content += """```yaml
# Advanced network configuration
custom_options:
  isolation_level: "strict"
  traffic_shaping:
    enabled: true
    bandwidth: "100Mbps"
    latency: "10ms"

  firewall_rules:
    - "ACCEPT tcp port 80"
    - "ACCEPT tcp port 443"
    - "DROP all"

  scaling:
    auto_scale: true
    min_instances: 1
    max_instances: 10
    scale_metric: "cpu_usage"
```
"""
        else:
            readme_content += f"""```yaml
# Advanced execution configuration
custom_options:
  {"profiling:" if features.get("is_profiler") else ""}
  {"  detailed_profiling: true" if features.get("is_profiler") else ""}
  {"  profile_duration: 30" if features.get("is_profiler") else ""}
  {"  sampling_rate: 1000" if features.get("is_profiler") else ""}

  {"debugging:" if features.get("requires_symbols") else ""}
  {"  symbol_resolution: true" if features.get("requires_symbols") else ""}
  {"  debug_info_path: '/usr/lib/debug'" if features.get("requires_symbols") else ""}

  {"reporting:" if features.get("generates_reports") else ""}
  {"  detailed_reports: true" if features.get("generates_reports") else ""}
  {"  report_formats: ['html', 'json', 'xml']" if features.get("generates_reports") else ""}
  {"  include_graphs: true" if features.get("generates_reports") else ""}
```
"""

        readme_content += f"""
## Usage Examples

### Basic Usage

```python
from panther.plugins.environments.{env_type}_environment.{name} import {name.title().replace("_", "")}{"Network" if env_type == "network" else "Execution"}Environment
from panther.plugins.environments.config_schema import EnvironmentConfig

# Create configuration
config = EnvironmentConfig(
    name="{name}",
    type="{env_type}_environment"
)

# Initialize environment
env = {name.title().replace("_", "")}{"Network" if env_type == "network" else "Execution"}Environment(config, output_dir)

# Setup environment
env.setup()

try:
    """

        if env_type == "network":
            readme_content += """# Deploy services
    service_info = env.deploy_service("test_service", {
        "image": "nginx:latest",
        "ports": ["80:80"],
        "environment": {"ENV": "test"}
    })

    # Get network information
    network_info = env.get_network_info()
    print(f"Service deployed at: {service_info['ip_address']}")
"""
        else:
            readme_content += """# Execute with environment
    result = env.execute_with_environment([
        "your_test_command",
        "--option", "value"
    ])

    # Get results
    results = env.get_results()
    print(f"Execution completed: {results}")
"""

        readme_content += (
            '''
finally:
    # Cleanup
    env.teardown()
```

### Integration with PANTHER

```yaml
# experiment.yaml
test_cases:
  - name: "test_with_custom_environment"
    environment:
      type: "'''
            + env_type
            + '''_environment"
      plugin: "'''
            + name
            + """"
      config:
        # Environment-specific configuration
"""
        )

        if env_type == "network":
            readme_content += """        network_driver: "bridge"
        monitoring_enabled: true
"""
        else:
            readme_content += f"""        tool_command: "{features["tool_command"]}"
        generate_reports: true
"""

        readme_content += """
    services:
      - name: "test_service"
        # Service configuration
```

## Output and Reports

"""

        if env_type == "network":
            readme_content += """### Network Information

The plugin provides detailed network information:

```json
{
  "network_name": "panther_my_network_env_test",
  "network_type": "my_network_env",
  "containers": 3,
  "supports_containers": true,
  "supports_scaling": true,
  "requires_root": false,
  "status": "active"
}
```

### Service Deployment Results

```json
{
  "container_id": "container_abc123",
  "ip_address": "192.168.100.10",
  "hostname": "test-service-host",
  "network_name": "panther_network",
  "ports": ["80:8080", "443:8443"]
}
```
"""
        else:
            readme_content += f"""### Execution Results

The plugin provides comprehensive execution results:

```json
{{
  "tool": "{features["tool_command"]}",
  "environment": "{name}",
  "reports_directory": "/path/to/reports",
  "generates_reports": {str(features["generates_reports"]).lower()},
  "requires_symbols": {str(features.get("requires_symbols", False)).lower()},
  "is_profiler": {str(features.get("is_profiler", False)).lower()}
}}
```

{"### Analysis Reports" if features.get("generates_reports") else ""}

{"Generated reports include:" if features.get("generates_reports") else ""}
{"- **Summary Report**: Overview of analysis results" if features.get("generates_reports") else ""}
{"- **Detailed Analysis**: In-depth analysis data" if features.get("generates_reports") else ""}
{"- **Logs**: Complete execution logs" if features.get("generates_reports") else ""}
{"- **Metrics**: Performance and execution metrics" if features.get("generates_reports") else ""}

{"### Profiling Data" if features.get("is_profiler") else ""}

{"For profiling tools, additional data is available:" if features.get("is_profiler") else ""}
{"- **CPU Profiles**: Detailed CPU usage analysis" if features.get("is_profiler") else ""}
{"- **Memory Profiles**: Memory allocation and usage" if features.get("is_profiler") else ""}
{"- **Performance Metrics**: Timing and performance data" if features.get("is_profiler") else ""}
"""

        readme_content += f"""
## Troubleshooting

### Common Issues

1. **Plugin Not Found**:
   ```bash
   # Verify plugin location
   ls $PANTHER_HOME/plugins/environments/{env_type}_environment/{name}/

   # Check plugin registration
   panther list-plugins --type {env_type}_environment
   ```

"""

        if env_type == "network":
            readme_content += """2. **Network Creation Failed**:
   ```bash
   # Check Docker daemon
   docker version

   # Verify network permissions
   docker network ls

   # Check for port conflicts
   netstat -tulpn | grep <port>
   ```

3. **Container Deployment Issues**:
   ```bash
   # Check image availability
   docker images | grep <image_name>

   # Verify container logs
   docker logs <container_id>

   # Check network connectivity
   docker network inspect <network_name>
   ```
"""
        else:
            readme_content += f"""2. **Tool Not Available**:
   ```bash
   # Check tool installation
   which {features["tool_command"]}
   {features["tool_command"]} --version

   # Install if missing
   sudo apt-get install {features["tool_command"]}
   ```

3. **Execution Failures**:
   ```bash
   # Check permissions
   ls -la /path/to/executable

   # Verify dependencies
   ldd /path/to/executable

   # Check logs
   cat $PANTHER_OUTPUT/reports/{name}/logs/stderr.log
   ```

{"4. **Symbol Resolution Issues**:" if features.get("requires_symbols") else ""}
{"   ```bash" if features.get("requires_symbols") else ""}
{"   # Install debug symbols" if features.get("requires_symbols") else ""}
{"   sudo apt-get install libc6-dbg" if features.get("requires_symbols") else ""}
{"   " if features.get("requires_symbols") else ""}
{"   # Verify symbol path" if features.get("requires_symbols") else ""}
{"   ls /usr/lib/debug/" if features.get("requires_symbols") else ""}
{"   ```" if features.get("requires_symbols") else ""}
"""

        readme_content += """
### Debug Mode

Enable debug logging for detailed troubleshooting:

```yaml
# config.yaml
log_level: "DEBUG"
debug_mode: true
```

```bash
# Run with debug output
PANTHER_LOG_LEVEL=DEBUG panther run experiment.yaml
```

## Development

### Extending the Plugin

"""

        if env_type == "network":
            readme_content += f"""To extend the {name} network environment:

1. **Add new network features**:
   ```python
   def setup_custom_routing(self):
       # Implementation for custom routing
       pass
   ```

2. **Implement load balancing**:
   ```python
   def setup_load_balancer(self, services):
       # Implementation for load balancing
       pass
   ```

3. **Add monitoring capabilities**:
   ```python
   def setup_network_monitoring(self):
       # Implementation for network monitoring
       pass
   ```
"""
        else:
            readme_content += f"""To extend the {name} execution environment:

1. **Add custom analysis**:
   ```python
   def custom_analysis(self, execution_data):
       # Implementation for custom analysis
       pass
   ```

2. **Implement new report formats**:
   ```python
   def generate_custom_report(self, data, format_type):
       # Implementation for custom reports
       pass
   ```

3. **Add integration with other tools**:
   ```python
   def integrate_with_tool(self, tool_name, options):
       # Implementation for tool integration
       pass
   ```
"""

        readme_content += f"""
### Testing

Run the plugin tests:

```bash
cd $PANTHER_HOME/plugins/environments/{env_type}_environment/{name}

# Unit tests
python -m pytest tests/

# Integration tests
python -m pytest tests/integration/

# Validation tests
panther validate-plugin --plugin {name}
```

## Contributing

1. **Fork the repository**
2. **Create a feature branch**
3. **Make your changes**
4. **Add tests**
5. **Submit a pull request**

## License

This plugin is licensed under the MIT License. See LICENSE for details.

## Support

For support and questions:

- **Documentation**: [PANTHER Documentation](../../../README.md)
- **Issues**: [GitHub Issues](https://github.com/panther-project/panther/issues)
- **Community**: [PANTHER Community](https://github.com/panther-project/panther/discussions)

---

*Generated by PANTHER Environment Plugin Tutorial*
"""

        (plugin_dir / "README.md").write_text(readme_content)

    def integration_tutorial(self):
        """Tutorial for integration patterns and best practices."""
        print("\n" + "🔗" * 30)
        print("INTEGRATION & BEST PRACTICES TUTORIAL")
        print("🔗" * 30)

        topics = [
            "1. Multi-Environment Integration",
            "2. Plugin Communication Patterns",
            "3. Configuration Management",
            "4. Error Handling & Recovery",
            "5. Performance Optimization",
            "6. Testing Strategies",
            "7. Documentation Standards",
        ]

        print("\n📋 Available Integration Topics:")
        for topic in topics:
            print(f"   {topic}")

        print("\n💡 Integration Best Practices:")
        print("   • Design plugins to be composable and reusable")
        print("   • Use consistent configuration schemas")
        print("   • Implement proper error handling and cleanup")
        print("   • Follow PANTHER naming conventions")
        print("   • Document all public interfaces")
        print("   • Include comprehensive tests")
        print("   • Optimize for performance and resource usage")

        # Create integration example
        integration_dir = self.tutorial_dir / "integration_example"
        integration_dir.mkdir(exist_ok=True)

        # Multi-environment example
        multi_env_example = '''"""
Multi-Environment Integration Example

This example demonstrates how to use multiple environment plugins
together in a single PANTHER experiment.
"""

# experiment_config.yaml
experiment:
  name: "multi_environment_test"
  description: "Testing with multiple environments"

  environments:
    # Network environment for service deployment
    - name: "test_network"
      type: "network_environment"
      plugin: "docker_compose"
      config:
        network_name: "test_net"
        subnet: "192.168.50.0/24"

    # Execution environment for analysis
    - name: "profiling_env"
      type: "execution_environment"
      plugin: "gperf_cpu"
      config:
        profiling_frequency: 1000
        detailed_analysis: true

  test_cases:
    - name: "integrated_test"
      # Use network environment for deployment
      network_environment: "test_network"
      # Use execution environment for analysis
      execution_environment: "profiling_env"

      services:
        - name: "quic_server"
          image: "quic-server:latest"
          environment_config:
            network: "test_network"

        - name: "quic_client"
          image: "quic-client:latest"
          environment_config:
            network: "test_network"
            execution_env: "profiling_env"

# Python integration code
from panther.core.experiment_manager import ExperimentManager
from panther.config.config_loader import ConfigLoader

def run_multi_environment_test():
    """Run a test with multiple environments."""

    # Load configuration
    config = ConfigLoader.load_experiment_config("experiment_config.yaml")

    # Create experiment manager
    experiment = ExperimentManager(config)

    try:
        # Setup all environments
        experiment.setup_environments()

        # Run test cases
        results = experiment.run_test_cases()

        # Collect results from all environments
        network_results = experiment.get_environment_results("test_network")
        profiling_results = experiment.get_environment_results("profiling_env")

        # Combine and analyze results
        combined_results = {
            "network_metrics": network_results,
            "performance_metrics": profiling_results,
            "test_results": results
        }

        return combined_results

    finally:
        # Cleanup all environments
        experiment.teardown_environments()

if __name__ == "__main__":
    results = run_multi_environment_test()
    print(f"Integration test completed: {results}")
'''

        (integration_dir / "multi_environment_example.py").write_text(multi_env_example)

        # Plugin communication example
        communication_example = '''"""
Plugin Communication Pattern Example

Demonstrates how environment plugins can communicate and share data.
"""

from typing import Dict, Any
from panther.core.observer.management.event_manager import EventManager
from panther.plugins.environments.environment_interface import IEnvironmentPlugin

class CommunicatingEnvironment(IEnvironmentPlugin):
    """Example environment plugin that communicates with other plugins."""

    def __init__(self, config, output_dir, event_manager: EventManager = None):
        super().__init__(config, output_dir)
        self.event_manager = event_manager or EventManager()
        self.shared_data = {}

        # Subscribe to events from other plugins
        self.event_manager.subscribe("network.service_deployed", self._on_service_deployed)
        self.event_manager.subscribe("execution.analysis_complete", self._on_analysis_complete)

    def setup(self):
        """Setup with event broadcasting."""
        super().setup()

        # Broadcast setup complete
        self.event_manager.publish("environment.setup_complete", {
            "plugin": self.__class__.__name__,
            "capabilities": self.get_capabilities()
        })

    def share_data(self, key: str, data: Any):
        """Share data with other plugins."""
        self.shared_data[key] = data

        # Broadcast data update
        self.event_manager.publish("environment.data_shared", {
            "plugin": self.__class__.__name__,
            "key": key,
            "data": data
        })

    def get_shared_data(self, key: str) -> Any:
        """Get data shared by other plugins."""
        return self.shared_data.get(key)

    def _on_service_deployed(self, event_data: Dict[str, Any]):
        """Handle service deployment events."""
        service_info = event_data.get("service_info", {})

        # Store service information for later use
        self.share_data(f"service_{service_info.get('name')}", service_info)

        # React to deployment
        self._configure_for_service(service_info)

    def _on_analysis_complete(self, event_data: Dict[str, Any]):
        """Handle analysis completion events."""
        analysis_results = event_data.get("results", {})

        # Store analysis results
        self.share_data("latest_analysis", analysis_results)

        # Trigger follow-up actions
        self._process_analysis_results(analysis_results)

    def _configure_for_service(self, service_info: Dict[str, Any]):
        """Configure environment based on deployed services."""
        # Implementation for service-specific configuration
        pass

    def _process_analysis_results(self, results: Dict[str, Any]):
        """Process analysis results from other plugins."""
        # Implementation for result processing
        pass

    def get_capabilities(self) -> Dict[str, Any]:
        """Get plugin capabilities for sharing."""
        return {
            "supports_communication": True,
            "data_sharing": True,
            "event_handling": True
        }

# Usage example
def demonstrate_plugin_communication():
    """Demonstrate inter-plugin communication."""

    event_manager = EventManager()

    # Create multiple environments with shared event manager
    network_env = CommunicatingEnvironment(network_config, output_dir, event_manager)
    exec_env = CommunicatingEnvironment(exec_config, output_dir, event_manager)

    # Setup environments (they will communicate during setup)
    network_env.setup()
    exec_env.setup()

    # Simulate service deployment
    event_manager.publish("network.service_deployed", {
        "service_info": {
            "name": "test_service",
            "ip": "192.168.1.100",
            "ports": [80, 443]
        }
    })

    # Simulate analysis completion
    event_manager.publish("execution.analysis_complete", {
        "results": {
            "cpu_usage": 85.3,
            "memory_usage": 512,
            "network_connections": 42
        }
    })

    # Access shared data
    service_data = exec_env.get_shared_data("service_test_service")
    analysis_data = network_env.get_shared_data("latest_analysis")

    print(f"Shared service data: {service_data}")
    print(f"Shared analysis data: {analysis_data}")
'''

        (integration_dir / "communication_example.py").write_text(communication_example)

        print(f"\n✅ Integration examples created at: {integration_dir}")
        print("\n📖 Review the examples to understand:")
        print("   • Multi-environment coordination")
        print("   • Inter-plugin communication patterns")
        print("   • Event-driven architecture")
        print("   • Data sharing mechanisms")

    def show_examples(self):
        """Show real examples from the codebase."""
        print("\n" + "📚" * 30)
        print("REAL PLUGIN EXAMPLES")
        print("📚" * 30)

        examples = [
            {
                "name": "Docker Compose Network Environment",
                "path": "plugins/environments/network_environment/docker_compose/",
                "description": "Production network environment using Docker Compose",
            },
            {
                "name": "Memcheck Execution Environment",
                "path": "plugins/environments/execution_environment/memcheck/",
                "description": "Memory analysis using Valgrind Memcheck",
            },
            {
                "name": "Shadow Network Simulator",
                "path": "plugins/environments/network_environment/shadow_ns/",
                "description": "Large-scale network simulation environment",
            },
            {
                "name": "QUIC Protocol Plugin",
                "path": "plugins/protocols/client_server/quic/",
                "description": "QUIC protocol implementation and testing",
            },
        ]

        print("\n🔍 Available Real Examples:")
        for i, example in enumerate(examples, 1):
            print(f"\n{i}. **{example['name']}**")
            print(f"   📁 Path: {example['path']}")
            print(f"   📄 Description: {example['description']}")

        print("\n💡 To explore these examples:")
        print("   1. Navigate to the plugin directory")
        print("   2. Read the README.md file")
        print("   3. Examine the implementation files")
        print("   4. Study the configuration schemas")
        print("   5. Review the Docker integration")

        # Show directory structure
        print("\n📂 Plugin Directory Structure:")
        print("   plugins/")
        print("   ├── environments/")
        print("   │   ├── network_environment/")
        print("   │   │   ├── docker_compose/")
        print("   │   │   ├── localhost_single_container/")
        print("   │   │   └── shadow_ns/")
        print("   │   └── execution_environment/")
        print("   │       ├── memcheck/")
        print("   │       ├── strace/")
        print("   │       ├── gperf_cpu/")
        print("   │       └── helgrind/")
        print("   ├── protocols/")
        print("   │   ├── client_server/")
        print("   │   │   ├── quic/")
        print("   │   │   ├── http/")
        print("   │   │   └── minip/")
        print("   │   └── peer_to_peer/")
        print("   │       └── bittorrent/")
        print("   └── services/")
        print("       ├── iut/")
        print("       │   └── quic/")
        print("       │       ├── aioquic/")
        print("       │       ├── lsquic/")
        print("       │       ├── quinn/")
        print("       │       └── quic_go/")
        print("       └── testers/")
        print("           └── panther_ivy/")

    def get_input(self, prompt: str, default: str, help_text: str = "") -> str:
        """Get user input with default value and help."""
        if help_text:
            print(f"\n💭 {help_text}")

        response = input(f"{prompt} [{default}]: ").strip()
        return response if response else default

    def get_yes_no(self, prompt: str, default: bool = True) -> bool:
        """Get yes/no input from user."""
        default_str = "Y/n" if default else "y/N"
        response = input(f"{prompt} [{default_str}]: ").strip().lower()

        if not response:
            return default

        return response in ["y", "yes", "true", "1"]

    def show_next_steps(self, plugin_dir: Path):
        """Show next steps after plugin generation."""
        print("\n📋 Next Steps:")
        print("1. **Review Generated Files**:")
        print(f"   cd {plugin_dir}")
        print("   ls -la")

        print("\n2. **Customize Implementation**:")
        print("   • Edit the main plugin file")
        print("   • Modify configuration schema")
        print("   • Update Dockerfile if needed")

        print("\n3. **Test the Plugin**:")
        print("   panther validate-plugin --plugin-dir .")
        print("   python -m pytest tests/")

        print("\n4. **Integration Testing**:")
        print("   • Create a test experiment configuration")
        print("   • Run with PANTHER framework")
        print("   • Verify functionality")

        print("\n5. **Documentation**:")
        print("   • Review and update README.md")
        print("   • Add usage examples")
        print("   • Document configuration options")

    def create_new_plugin(self, plugin_name):
        """
        Creates a new environment plugin with the specified name

        Args:
            plugin_name: The name of the plugin to create
        """
        print(f"Creating new environment plugin: {plugin_name}")

        # Set plugin attributes
        plugin_type = "environments"

        # Create the plugin directory in the appropriate location
        base_dir = self.plugins_dir
        plugin_dir = base_dir / plugin_type / plugin_name

        if plugin_dir.exists():
            print(f"❌ Plugin already exists at {plugin_dir}")
            return False

        # Create the plugin directory
        plugin_dir.mkdir(parents=True, exist_ok=True)

        # Copy template files
        template_dir = self.tutorial_dir / "template"
        if not template_dir.exists():
            print(f"❌ Template directory not found: {template_dir}")
            return False

        os.system(f"cp -r {template_dir}/* {plugin_dir}/")

        print(f"✅ Created new environment plugin: {plugin_name}")
        print(f"Plugin location: {plugin_dir}")

        # Show next steps
        self.show_next_steps(plugin_dir)
        return True


if __name__ == "__main__":
    import argparse

    # Set up argument parsing
    parser = argparse.ArgumentParser(description="PANTHER Environment Plugin Tutorial")
    parser.add_argument(
        "--create",
        metavar="NAME",
        help="Create a new environment plugin with the specified name",
    )
    args = parser.parse_args()

    tutorial = EnvironmentPluginTutorial()

    if args and hasattr(args, "create") and args.create:
        sys.exit(0 if tutorial.create_new_plugin(args.create) else 1)
    else:
        tutorial.run()
