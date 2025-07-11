"""
Create Command - Plugin and component creation (Click implementation)
"""

import json
import traceback
from pathlib import Path
from typing import Optional

import click
from termcolor import colored

from panther.cli_click.core.base import (
    error_message,
    handle_errors,
    info_message,
    pass_context_and_setup_logging,
    success_message,
    warning_message,
)


@click.group()
def create():
    """
    Create new plugins and components.

    Powerful plugin and component creation tools for PANTHER development.
    Supports multiple plugin types with intelligent templating and development mode detection.

    \b
    Key Features:
    🔧 Plugin creation with intelligent scaffolding
    📦 Subplugin support for modular development
    📋 Configuration template generation
    🎯 Development and production mode support
    ⚡ Smart dependency detection and setup

    \b
    Plugin Types:
    🔌 Service: IUT implementations (QUIC, HTTP, etc.)
    🌐 Environment: Network and execution environments
    🏗️ Protocol: Protocol-specific testing components

    \b
    Template Types:
    📊 Experiment: Complete experiment configurations
    🔧 Service: Service plugin configurations
    🌍 Environment: Environment plugin configurations

    Examples:
      panther create plugin service my_quic_impl
      panther create subplugin service picoquic my_variant
      panther create template experiment --output config.yaml
    """
    pass


@create.command()
@click.argument(
    "plugin_type", type=click.Choice(["service", "environment", "protocol"])
)
@click.argument("plugin_name")
@click.option(
    "--dev-mode",
    is_flag=True,
    help="Create plugin in development mode (editable install)",
)
@click.option(
    "--production-mode",
    is_flag=True,
    help="Create plugin in production mode (standard install)",
)
@click.option(
    "--with-subplugins",
    is_flag=True,
    help="Create plugin with subplugin support structure",
)
@click.option(
    "--output-dir",
    type=click.Path(exists=False),
    help="Custom output directory for plugin creation",
)
@click.option(
    "--template",
    type=click.Choice(["minimal", "standard", "advanced"]),
    default="standard",
    help="Plugin template complexity level",
)
@click.option(
    "--force", is_flag=True, help="Force creation even if plugin already exists"
)
@pass_context_and_setup_logging
@handle_errors
def plugin(
    ctx,
    plugin_type: str,
    plugin_name: str,
    dev_mode: bool,
    production_mode: bool,
    with_subplugins: bool,
    output_dir: Optional[str],
    template: str,
    force: bool,
):
    """
    Create a new plugin.

    Creates a new plugin with the specified type and name. The plugin will be
    scaffolded with appropriate templates, configuration files, and directory structure.

    \b
    PLUGIN_TYPE: Type of plugin to create
    ├── service     - Implementation Under Test (IUT) services
    ├── environment - Network or execution environments
    └── protocol    - Protocol-specific components

    \b
    PLUGIN_NAME: Name of the plugin to create

    \b
    Development Modes:
    🔧 --dev-mode: Editable installation for active development
    📦 --production-mode: Standard installation for stable plugins
    🤖 Auto-detect: Automatically choose based on environment

    \b
    Template Levels:
    📋 minimal  - Basic structure and essential files
    🏗️ standard - Complete plugin with common patterns
    🚀 advanced - Full-featured with advanced integrations

    Examples:
      # Create a standard QUIC service plugin
      panther create plugin service my_quic_impl

      # Create in development mode with subplugin support
      panther create plugin service advanced_quic --dev-mode --with-subplugins

      # Create advanced environment plugin
      panther create plugin environment k8s_env --template advanced
    """

    info_message(
        f"🔧 Creating {plugin_type} plugin: {colored(plugin_name, 'cyan', attrs=['bold'])}"
    )

    # Validate mode conflicts
    if dev_mode and production_mode:
        error_message("❌ Cannot specify both --dev-mode and --production-mode")
        ctx.exit(1)

    # Determine development mode
    development_mode = None
    if dev_mode:
        development_mode = True
        info_message("🔧 Development mode: Editable installation")
    elif production_mode:
        development_mode = False
        info_message("📦 Production mode: Standard installation")
    else:
        info_message("🤖 Auto-detecting development mode based on environment")

    # Show creation parameters
    if with_subplugins:
        info_message("📦 Subplugin support: Enabled")

    info_message(f"🎯 Template level: {colored(template, 'yellow')}")

    if output_dir:
        info_message(f"📁 Output directory: {colored(output_dir, 'blue')}")

    try:
        # Import plugin creator
        from panther.tools.plugins.plugin_creator import create_plugin

        # Display progress
        with click.progressbar(length=100, label="Creating plugin") as bar:
            bar.update(20)

            # Create the plugin
            success = create_plugin(
                plugin_type,
                plugin_name,
                in_development_mode=development_mode,
                create_subplugins=with_subplugins,
                force_overwrite=force,
                # Additional parameters based on available API
            )

            bar.update(80)

            if success:
                bar.update(100)
                success_message(
                    f"✅ Plugin '{colored(plugin_name, 'green', attrs=['bold'])}' created successfully!"
                )

                # Provide next steps
                info_message("\n📝 Next steps:")
                info_message(
                    f"  1. Navigate to plugin directory: cd panther/plugins/{plugin_type}s/{plugin_name}/"
                )
                info_message(f"  2. Review generated files and customize as needed")
                info_message(f"  3. Run tests: pytest tests/")
                if development_mode:
                    info_message(f"  4. Install in dev mode: pip install -e .")

                return 0
            else:
                bar.update(100)
                error_message(
                    f"❌ Failed to create plugin '{colored(plugin_name, 'red')}'"
                )
                return 1

    except ImportError as e:
        error_message(f"❌ Plugin creator not available: {e}")
        error_message("💡 Make sure PANTHER plugin tools are properly installed")
        return 1
    except Exception as e:
        error_message(f"❌ Error creating plugin: {e}")
        if ctx.obj.get("debug", False):
            error_message("\n🔍 Full traceback:")
            traceback.print_exc()
        return 1


@create.command()
@click.argument(
    "plugin_type", type=click.Choice(["service", "environment", "protocol"])
)
@click.argument("plugin_name")
@click.argument("subplugin_name")
@click.option("--dev-mode", is_flag=True, help="Create subplugin in development mode")
@click.option(
    "--production-mode", is_flag=True, help="Create subplugin in production mode"
)
@click.option(
    "--template",
    type=click.Choice(["minimal", "standard", "advanced"]),
    default="standard",
    help="Subplugin template complexity level",
)
@click.option(
    "--force", is_flag=True, help="Force creation even if subplugin already exists"
)
@pass_context_and_setup_logging
@handle_errors
def subplugin(
    ctx,
    plugin_type: str,
    plugin_name: str,
    subplugin_name: str,
    dev_mode: bool,
    production_mode: bool,
    template: str,
    force: bool,
):
    """
    Create a new subplugin.

    Creates a new subplugin for an existing parent plugin. Subplugins allow
    modular extension of existing plugins with specialized functionality.

    \b
    PLUGIN_TYPE: Type of parent plugin
    PLUGIN_NAME: Name of the existing parent plugin
    SUBPLUGIN_NAME: Name of the subplugin to create

    \b
    Subplugin Benefits:
    🧩 Modular architecture for complex plugins
    🔄 Inherit base functionality from parent
    ⚡ Specialized implementations for specific use cases
    🏗️ Organized code structure for maintainability

    Examples:
      # Create a subplugin for picoquic with custom features
      panther create subplugin service picoquic custom_crypto

      # Create advanced Docker Compose variant
      panther create subplugin environment docker_compose k8s_hybrid --template advanced
    """

    info_message(
        f"🔧 Creating subplugin '{colored(subplugin_name, 'cyan', attrs=['bold'])}' "
        f"for {plugin_type} plugin '{colored(plugin_name, 'yellow')}'"
    )

    # Validate mode conflicts
    if dev_mode and production_mode:
        error_message("❌ Cannot specify both --dev-mode and --production-mode")
        ctx.exit(1)

    # Determine development mode
    development_mode = None
    if dev_mode:
        development_mode = True
        info_message("🔧 Development mode: Editable installation")
    elif production_mode:
        development_mode = False
        info_message("📦 Production mode: Standard installation")
    else:
        info_message("🤖 Auto-detecting development mode based on environment")

    info_message(f"🎯 Template level: {colored(template, 'yellow')}")

    try:
        # Import subplugin creator
        from panther.tools.plugins.plugin_creator import create_subplugin

        # Display progress
        with click.progressbar(length=100, label="Creating subplugin") as bar:
            bar.update(20)

            # Create the subplugin
            success = create_subplugin(
                plugin_type,
                plugin_name,
                subplugin_name,
                in_development_mode=development_mode,
                force_overwrite=force,
            )

            bar.update(80)

            if success:
                bar.update(100)
                success_message(
                    f"✅ Subplugin '{colored(subplugin_name, 'green', attrs=['bold'])}' created successfully!"
                )

                # Provide next steps
                info_message("\n📝 Next steps:")
                info_message(
                    f"  1. Navigate to subplugin directory: cd panther/plugins/{plugin_type}s/{plugin_name}/{subplugin_name}/"
                )
                info_message(f"  2. Customize subplugin implementation")
                info_message(f"  3. Update parent plugin to register subplugin")
                info_message(f"  4. Test integration with parent plugin")

                return 0
            else:
                bar.update(100)
                error_message(
                    f"❌ Failed to create subplugin '{colored(subplugin_name, 'red')}'"
                )
                return 1

    except ImportError as e:
        error_message(f"❌ Subplugin creator not available: {e}")
        return 1
    except Exception as e:
        error_message(f"❌ Error creating subplugin: {e}")
        if ctx.obj.get("debug", False):
            error_message("\n🔍 Full traceback:")
            traceback.print_exc()
        return 1


@create.command()
@click.argument(
    "template_type", type=click.Choice(["experiment", "service", "environment"])
)
@click.option(
    "--output",
    type=click.Path(),
    help="Output file path (prints to stdout if not specified)",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["yaml", "json"]),
    default="yaml",
    help="Output format for template",
)
@click.option(
    "--minimal",
    is_flag=True,
    help="Generate minimal template with essential fields only",
)
@click.option(
    "--interactive", is_flag=True, help="Interactive template creation with prompts"
)
@pass_context_and_setup_logging
@handle_errors
def template(
    ctx,
    template_type: str,
    output: Optional[str],
    output_format: str,
    minimal: bool,
    interactive: bool,
):
    """
    Create configuration templates.

    Generates configuration file templates for experiments, services, or environments.
    Templates provide starting points with best practices and common configurations.

    \b
    TEMPLATE_TYPE: Type of template to create
    ├── experiment  - Complete experiment configuration
    ├── service     - Service plugin configuration
    └── environment - Environment plugin configuration

    \b
    Template Features:
    📋 Best practice configurations
    💡 Inline documentation and comments
    🎯 Sensible defaults for quick start
    🔧 Customizable for specific needs

    Examples:
      # Generate experiment template to file
      panther create template experiment --output my_experiment.yaml

      # Print minimal service template to stdout
      panther create template service --minimal

      # Interactive experiment creation
      panther create template experiment --interactive
    """

    info_message(f"🔧 Creating {colored(template_type, 'cyan')} template")

    if minimal:
        info_message("📋 Minimal template: Essential fields only")

    if interactive:
        info_message("🤖 Interactive mode: Guided template creation")

    try:
        # Generate template content
        template_content = _generate_template_content(
            template_type, output_format, minimal, interactive
        )

        if output:
            # Write to file
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w") as f:
                f.write(template_content)

            success_message(f"✅ Template created: {colored(str(output_path), 'green')}")

            # Show file info
            file_size = output_path.stat().st_size
            info_message(f"📊 File size: {file_size} bytes")
            info_message(f"📁 Location: {output_path.absolute()}")

        else:
            # Print to stdout
            info_message("📄 Template content:\n")
            click.echo(template_content)

        return 0

    except Exception as e:
        error_message(f"❌ Error creating template: {e}")
        if ctx.obj.get("debug", False):
            error_message("\n🔍 Full traceback:")
            traceback.print_exc()
        return 1


def _generate_template_content(
    template_type: str, output_format: str, minimal: bool, interactive: bool
) -> str:
    """Generate template content based on type and options."""

    if template_type == "experiment":
        return _get_experiment_template(output_format, minimal, interactive)
    elif template_type == "service":
        return _get_service_template(output_format, minimal, interactive)
    elif template_type == "environment":
        return _get_environment_template(output_format, minimal, interactive)
    else:
        raise ValueError(f"Unknown template type: {template_type}")


def _get_experiment_template(
    output_format: str, minimal: bool, interactive: bool
) -> str:
    """Generate experiment configuration template."""

    if interactive:
        # Interactive prompts for key values
        experiment_name = click.prompt("Experiment name", default="my_experiment")
        protocol_name = click.prompt("Protocol", default="quic")
        server_impl = click.prompt("Server implementation", default="picoquic")
        client_impl = click.prompt("Client implementation", default="picoquic")
    else:
        experiment_name = "my_experiment"
        protocol_name = "quic"
        server_impl = "picoquic"
        client_impl = "picoquic"

    if minimal:
        template = f"""# PANTHER Experiment Configuration
tests:
  - name: "{experiment_name}"
    network_environment:
      type: docker_compose
    services:
      server:
        implementation:
          name: {server_impl}
          type: iut
        protocol:
          name: {protocol_name}
          role: server
      client:
        implementation:
          name: {client_impl}
          type: iut
        protocol:
          name: {protocol_name}
          role: client
          target: server
"""
    else:
        template = f"""# PANTHER Experiment Configuration Template
# Generated with enhanced Click CLI

logging:
  level: INFO
  format: "%(asctime)s [%(levelname)s] - %(module)s - %(message)s"

observers:
  logger:
    enabled: true
    log_level: "INFO"
    enable_colors: true
  metrics:
    enabled: true
    collect_system_metrics: true
  storage:
    enabled: true
    storage_path: "outputs/storage"

paths:
  output_dir: "outputs"
  log_dir: "outputs/logs"
  plugin_dir: "panther/plugins"

docker:
  force_build_docker_image: false

tests:
  - name: "{experiment_name}"
    description: "Protocol testing experiment"
    network_environment:
      type: docker_compose
    services:
      server:
        implementation:
          name: {server_impl}
          type: iut
        protocol:
          name: {protocol_name}
          version: rfc9000
          role: server
        timeout: 100
      client:
        implementation:
          name: {client_impl}
          type: iut
        protocol:
          name: {protocol_name}
          version: rfc9000
          role: client
          target: server
        timeout: 100
    steps:
      wait: 60
"""

    if output_format == "json":
        import yaml

        data = yaml.safe_load(template)
        return json.dumps(data, indent=2)

    return template


def _get_service_template(output_format: str, minimal: bool, interactive: bool) -> str:
    """Generate service plugin configuration template."""

    if minimal:
        template = """# Service Plugin Configuration
name: my_service
type: iut
"""
    else:
        template = """# Service Plugin Configuration Template
name: my_service
type: iut
description: "Custom service implementation"

# Plugin metadata
metadata:
  version: "1.0.0"
  author: "Your Name"
  license: "MIT"

# Configuration options
config:
  enabled: true
  parameters:
    # Add service-specific parameters here

# Dependencies
dependencies:
  - panther-core
"""

    if output_format == "json":
        import yaml

        data = yaml.safe_load(template)
        return json.dumps(data, indent=2)

    return template


def _get_environment_template(
    output_format: str, minimal: bool, interactive: bool
) -> str:
    """Generate environment plugin configuration template."""

    if minimal:
        template = """# Environment Plugin Configuration
name: my_environment
type: network_environment
"""
    else:
        template = """# Environment Plugin Configuration Template
name: my_environment
type: network_environment
description: "Custom environment setup"

# Plugin metadata
metadata:
  version: "1.0.0"
  author: "Your Name"
  license: "MIT"

# Environment configuration
config:
  enabled: true
  settings:
    # Add environment-specific settings here

# Resource requirements
resources:
  cpu: "1"
  memory: "512Mi"
"""

    if output_format == "json":
        import yaml

        data = yaml.safe_load(template)
        return json.dumps(data, indent=2)

    return template


# Register the command group
if __name__ == "__main__":
    create()
