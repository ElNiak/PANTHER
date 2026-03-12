"""Config Command.

Configuration management and validation with enhanced user experience.
"""

from pathlib import Path
from typing import Any, Dict, List

import click
from termcolor import colored

from panther.cli.core.base import (
    error_message,
    featured_example,
    handle_errors,
    info_message,
    pass_context_and_setup_logging,
    success_message,
)
from panther.config import ConfigurationManager


def _explain_validation_error(error: Exception) -> str:
    """Return a human-readable explanation of a validation error."""
    msg = str(error)
    lines = [f"  Validation error: {msg}"]
    # Pydantic errors often contain nested details
    if hasattr(error, "errors"):
        for err in error.errors():
            loc = " -> ".join(str(l) for l in err.get("loc", []))
            lines.append(f"  - {loc}: {err.get('msg', '')}")
    return "\n".join(lines)


def _suggest_fixes(config_data: Any, error: Exception) -> List[str]:
    """Return a list of suggested fixes for a validation error."""
    suggestions = []
    msg = str(error).lower()
    if "required" in msg:
        suggestions.append("Add missing required fields to the configuration")
    if "type" in msg or "invalid" in msg:
        suggestions.append("Check that field values have the correct type")
    if "yaml" in msg or "syntax" in msg:
        suggestions.append("Check YAML indentation and syntax")
    if not suggestions:
        suggestions.append("Check configuration syntax and field values")
        suggestions.append(
            "Run: panther config schema --format text  (to see expected fields)"
        )
    return suggestions


def _render_schema_text(schema: Dict[str, Any], indent: int = 0) -> None:
    """Render a JSON schema dict as a human-readable property table."""
    prefix = "  " * indent
    properties = schema.get("properties", {})
    required_fields = set(schema.get("required", []))
    defs = schema.get("$defs", schema.get("definitions", {}))

    if not properties and indent == 0:
        click.echo(f"{prefix}(empty schema)")
        return

    for name, prop in properties.items():
        # Resolve $ref if present
        if "$ref" in prop:
            ref_name = prop["$ref"].rsplit("/", 1)[-1]
            prop = defs.get(ref_name, prop)

        field_type = prop.get("type", "object")
        # Handle anyOf / oneOf (Pydantic Optional fields)
        if "anyOf" in prop:
            types = []
            for option in prop["anyOf"]:
                if "$ref" in option:
                    types.append(option["$ref"].rsplit("/", 1)[-1])
                elif option.get("type") == "null":
                    continue
                else:
                    types.append(option.get("type", "any"))
            field_type = " | ".join(types) if types else field_type
        if "allOf" in prop:
            refs = [o["$ref"].rsplit("/", 1)[-1] for o in prop["allOf"] if "$ref" in o]
            field_type = refs[0] if refs else field_type

        description = prop.get("description", "")
        default = prop.get("default", "")
        req_marker = " (required)" if name in required_fields else ""

        default_str = f"  [default: {default}]" if default != "" else ""
        desc_str = f"  - {description}" if description else ""

        click.echo(f"{prefix}  {name}: {field_type}{req_marker}{default_str}{desc_str}")

        # Recurse into nested object properties
        nested_props = prop.get("properties")
        if nested_props:
            _render_schema_text(prop, indent=indent + 1)


@featured_example("panther config validate --config config.yaml")
@click.group()
def config():
    r"""Configuration management and validation.

    Powerful tools for managing PANTHER configuration files including
    validation, template generation, schema inspection, and interactive design.

    \b
    Key Features:
    🔍 Configuration validation with detailed error reporting
    📋 Schema inspection and documentation
    🎯 Template generation for common scenarios
    🎨 Interactive configuration designer
    ⚡ Fast syntax checking and validation

    \b
    Common Workflows:
      # Validate existing configuration
      panther config validate --config experiment.yaml

      # Generate a basic template
      panther config generate --template basic --output my-config.yaml

      # Interactive configuration design
      panther config design --output new-experiment.yaml

      # View configuration schema
      panther config schema --format text

    Use 'panther config COMMAND --help' for detailed information on each command.
    """
    pass


@config.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    required=True,
    help="Path to configuration file to validate",
)
@click.option(
    "--strict", is_flag=True, help="Enable strict validation mode with enhanced checks"
)
@click.option(
    "--show-schema",
    is_flag=True,
    help="Show configuration schema information and summary",
)
@click.option(
    "--explain", is_flag=True, help="Show detailed explanations for validation errors"
)
@click.option(
    "--format",
    type=click.Choice(["text", "json", "yaml"]),
    default="text",
    help="Output format for validation results (default: text)",
)
@handle_errors
@pass_context_and_setup_logging
def validate(ctx, config, strict, show_schema, explain, format):
    r"""Validate configuration file syntax and structure.

    Performs comprehensive validation of PANTHER configuration files
    including YAML syntax, schema compliance, and logical consistency.

    \b
    Validation Checks:
    🔍 YAML syntax validation
    📋 Schema structure validation
    🔗 Service dependency validation
    ⚙️  Implementation compatibility
    🐋 Docker configuration validation

    \b
    Examples:
      # Basic validation
      panther config validate --config experiment.yaml

      # Strict validation with explanations
      panther config validate --config test.yaml --strict --explain

      # Show schema summary
      panther config validate --config config.yaml --show-schema

      # JSON format output
      panther config validate --config exp.yaml --format json

    \b
    Exit Codes:
      0  Configuration is valid
      1  Validation errors found
      2  File not found or access error
    """
    verbose = ctx.obj.get("verbose", False)

    if verbose:
        info_message(f"Validating configuration: {config}")

    # Enhanced validation display
    click.echo(colored("🔍 PANTHER Configuration Validation", "blue", attrs=["bold"]))
    click.echo(f"📄 File: {config}")
    if strict:
        click.echo(f"⚡ Mode: {colored('STRICT VALIDATION', 'yellow', attrs=['bold'])}")
    click.echo()

    try:
        import yaml

        from panther.core.utils.logger_factory import LoggerFactory

        click.echo(colored("📋 Running validation checks:", "blue"))

        # YAML syntax validation (basic check first)
        config_path = Path(config)
        if not config_path.exists():
            error_message(f"Configuration file not found: {config_path}")
            raise click.Abort()

        with click.progressbar(range(4), label="Validating configuration") as bar:
            try:
                with open(config_path, "r") as f:
                    config_data = yaml.safe_load(f)
                click.echo("  ✅ YAML syntax is valid")
                bar.update(1)
            except yaml.YAMLError as e:
                click.echo(f"  ❌ YAML syntax error: {e}")
                if explain:
                    click.echo(f"\n{_explain_validation_error(e)}")
                raise click.Abort()

            # Initialize LoggerFactory with colors if specified in config
            if config_data and "logging" in config_data:
                logging_config = config_data["logging"]
                LoggerFactory.initialize(
                    {
                        "level": logging_config.get("level", "INFO"),
                        "format": logging_config.get(
                            "format",
                            "%(asctime)s [%(levelname)s] - %(module)s - %(message)s",
                        ),
                        "enable_colors": logging_config.get("enable_colors", True),
                    }
                )
            bar.update(1)

            try:
                config_loader = ConfigurationManager(
                    experiment_file=str(config_path),
                    debug_override=ctx.obj.get("debug", False),
                )

                # Load and validate configuration (like legacy CLI)
                experiment_config = config_loader.load_and_validate_experiment_config()
                click.echo("  ✅ Configuration schema is valid")
                bar.update(1)

                # Show configuration summary (like legacy CLI)
                if experiment_config and hasattr(experiment_config, "tests"):
                    test_count = (
                        len(experiment_config.tests) if experiment_config.tests else 0
                    )
                    click.echo(f"  ✅ Found {test_count} test(s) in configuration")

                    if show_schema:
                        click.echo("\n📖 Configuration Summary:")
                        if experiment_config.tests:
                            for i, test in enumerate(experiment_config.tests, 1):
                                click.echo(f"  Test {i}: {test.name}")
                                if hasattr(test, "services") and test.services:
                                    service_count = len(test.services)
                                    click.echo(f"    Services: {service_count}")
                bar.update(1)

            except Exception as e:
                click.echo(f"  ❌ Configuration validation failed: {e}")

                if explain:
                    click.echo(f"\n{_explain_validation_error(e)}")

                    suggestions = _suggest_fixes(config_data, e)
                    if suggestions:
                        click.echo("\n💡 Suggestions:")
                        for suggestion in suggestions:
                            click.echo(f"   {suggestion}")

                if ctx.obj.get("debug", False):
                    import traceback

                    click.echo(traceback.format_exc(), err=True)
                raise click.Abort()

        if explain:
            click.echo("\n📋 Detailed Validation Report:")
            click.echo("   All validation checks passed")

        success_message("Configuration validation completed successfully")

    except Exception as e:
        error_message(f"Validation error: {e}")
        if ctx.obj.get("debug", False):
            import traceback

            click.echo(traceback.format_exc(), err=True)
        raise click.Abort()


@config.command()
@click.option(
    "--format",
    type=click.Choice(["json", "yaml", "text"]),
    default="text",
    help="Output format for schema (default: text)",
)
@click.option(
    "--section", help="Show specific schema section (e.g., tests, services, docker)"
)
@click.option(
    "--examples", is_flag=True, help="Include configuration examples in output"
)
@handle_errors
def schema(format, section, examples):
    r"""Display configuration schema and documentation.

    Shows the complete PANTHER configuration schema with detailed
    documentation for all sections and configuration options.

    \b
    Schema Sections:
    📝 Global configuration (logging, observers, paths)
    🧪 Test configuration (name, description, iterations)
    🌐 Network environment configuration
    🔧 Service configuration (implementations, protocols)
    🐋 Docker configuration (images, user mapping)

    \b
    Examples:
      # Show complete schema
      panther config schema

      # JSON schema format
      panther config schema --format json

      # Specific section only
      panther config schema --section services

      # Include examples
      panther config schema --examples
    """
    import json

    import yaml as pyyaml

    from panther.config.core.models import ExperimentConfig, GlobalConfig

    click.echo(colored("📖 PANTHER Configuration Schema", "blue", attrs=["bold"]))
    click.echo("=" * 50)
    click.echo()

    # Build the full schema from Pydantic models
    experiment_schema = ExperimentConfig.model_json_schema()
    global_schema = GlobalConfig.model_json_schema()

    # Combine into a single top-level schema
    full_schema = {
        "title": "PANTHER Configuration",
        "type": "object",
        "properties": {},
        "$defs": {},
    }
    # Add global config properties (logging, docker, paths, etc.)
    for key, prop in global_schema.get("properties", {}).items():
        full_schema["properties"][key] = prop
    # Add experiment config properties (tests, metadata)
    for key, prop in experiment_schema.get("properties", {}).items():
        full_schema["properties"][key] = prop
    # Merge $defs from both schemas
    for defs_key in ("$defs", "definitions"):
        full_schema.setdefault("$defs", {}).update(global_schema.get(defs_key, {}))
        full_schema["$defs"].update(experiment_schema.get(defs_key, {}))

    # Filter to section if requested
    schema_to_show = full_schema
    if section:
        if section in full_schema["properties"]:
            schema_to_show = {
                "title": f"PANTHER Configuration - {section}",
                "type": "object",
                "properties": {section: full_schema["properties"][section]},
                "$defs": full_schema.get("$defs", {}),
            }
        else:
            available = ", ".join(sorted(full_schema["properties"].keys()))
            error_message(f"Unknown section '{section}'. Available: {available}")
            raise click.Abort()

    if format == "json":
        click.echo(json.dumps(schema_to_show, indent=2))
    elif format == "yaml":
        click.echo("# PANTHER Configuration Schema (YAML)")
        click.echo(
            pyyaml.dump(schema_to_show, default_flow_style=False, sort_keys=False)
        )
    else:  # text
        _render_schema_text(schema_to_show)

    if examples:
        click.echo(
            colored("\n💡 Example Configuration (from model defaults):", "yellow")
        )
        try:
            from panther.config.core.models import TestConfig

            example_config = {
                "logging": {"level": "INFO", "enable_colors": True},
                "tests": [
                    {
                        "name": "Example Test",
                        "description": "Generated from model defaults",
                        "network_environment": {"type": "docker_compose"},
                        "services": {
                            "server": {
                                "implementation": {"name": "picoquic", "type": "iut"},
                                "protocol": {"name": "quic", "role": "server"},
                            }
                        },
                    }
                ],
            }
            click.echo(
                pyyaml.dump(example_config, default_flow_style=False, sort_keys=False)
            )
        except Exception as e:
            click.echo(f"  (Could not generate example: {e})")


@config.command("list")
@click.option(
    "--directory",
    "-d",
    type=click.Path(exists=True),
    help="Root directory to scan (defaults to experiment-config/)",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format (default: text)",
)
@handle_errors
def list_cmd(directory, output_format):
    r"""List available experiment configurations.

    Recursively scans experiment-config/ (or a custom directory) and displays
    all YAML configuration files with metadata and summaries.

    \b
    Examples:
      # List all configs
      panther config list

      # List configs in a specific directory
      panther config list -d experiment-config/advanced

      # JSON output for scripting
      panther config list --format json
    """
    import json as json_mod

    from panther.core.utils.file_utils import ConfigurationLoader, FileUtils

    if directory is None:
        root = FileUtils.find_project_root() / "experiment-config"
    else:
        root = Path(directory)

    configs = ConfigurationLoader.list_configs_recursive(root)

    if not configs:
        info_message(f"No configuration files found under {root}")
        return

    if output_format == "json":
        # Convert datetime objects for JSON serialization
        for c in configs:
            if hasattr(c.get("modified"), "isoformat"):
                c["modified"] = c["modified"].isoformat()
        click.echo(json_mod.dumps(configs, indent=2))
        return

    click.echo(
        colored(
            f"Found {len(configs)} configuration(s) under {root}",
            "blue",
            attrs=["bold"],
        )
    )
    click.echo()

    for c in configs:
        category = c.get("category", "")
        prefix = f"[{category}] " if category else ""
        click.echo(f"  {prefix}{colored(c['name'], 'cyan')}")

        summary = c.get("summary", {})
        if summary.get("test_count"):
            tests_str = ", ".join(summary.get("test_names", []))
            click.echo(f"    Tests: {summary['test_count']} ({tests_str})")
        if summary.get("protocols"):
            click.echo(f"    Protocols: {', '.join(summary['protocols'])}")
        if summary.get("services"):
            click.echo(f"    Services: {', '.join(summary['services'])}")
        if summary.get("environment"):
            click.echo(f"    Environment: {summary['environment']}")
        click.echo()

    success_message(f"Listed {len(configs)} configuration(s)")


@config.command()
@click.option(
    "--template",
    type=click.Choice(["minimal", "basic", "advanced", "performance", "security"]),
    default="basic",
    help="Configuration template type (default: basic)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output file path (writes to stdout if not specified)",
)
@click.option(
    "--overwrite", is_flag=True, help="Overwrite existing file without confirmation"
)
@handle_errors
def generate(template, output, overwrite):
    r"""Generate configuration templates for common scenarios.

    Creates ready-to-use configuration templates for different testing
    scenarios, saving time and ensuring best practices.

    \b
    Available Templates:
    📝 minimal: Bare minimum configuration for quick testing
    🎯 basic: Standard configuration with common options
    ⚡ advanced: Full-featured configuration with all options
    📊 performance: Optimized for performance testing with profiling
    🔒 security: Security-focused configuration with formal verification

    \b
    Examples:
      # Generate basic template to stdout
      panther config generate --template basic

      # Save minimal template to file
      panther config generate --template minimal --output test.yaml

      # Generate performance template
      panther config generate --template performance --output perf-test.yaml

      # Overwrite existing file
      panther config generate --template advanced -o config.yaml --overwrite

    \b
    Template Features:
    • Minimal: Essential configuration for basic testing
    • Basic: Standard setup with metrics and logging
    • Advanced: Comprehensive configuration with all features
    • Performance: Profiling and resource monitoring enabled
    • Security: Formal verification and security testing setup
    """
    click.echo(
        colored(
            f"📄 Generating {template} configuration template", "blue", attrs=["bold"]
        )
    )

    # Check for file conflicts
    if output:
        output = Path(output)  # Ensure output is a Path object
        if output.exists() and not overwrite:
            if not click.confirm(f"File {output} already exists. Overwrite?"):
                info_message("Generation cancelled")
                return

    template_content = _generate_template_content(template, output)

    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        with open(output, "w") as f:
            f.write(template_content)
        success_message(f"Template generated: {output}")
        info_message(f"Validate with: panther config validate --config {output}")
    else:
        click.echo(template_content)
        success_message("Template generated successfully")


def _generate_template_content(template: str, output: Path) -> str:
    """Generate template content based on template type."""
    base_config = {
        "minimal": """# Minimal PANTHER Configuration Template
logging:
  level: INFO

tests:
  - name: "Basic Test"
    network_environment:
      type: docker_compose
    services:
      server:
        implementation:
          name: picoquic
          type: iut
        protocol:
          name: quic
          role: server
""",
        "basic": """# Basic PANTHER Configuration Template
logging:
  level: INFO
  enable_colors: true

observers:
  logger:
    enabled: true

paths:
  output_dir: "outputs"

tests:
  - name: "Basic Test"
    description: "Standard configuration template"
    network_environment:
      type: docker_compose
    services:
      server:
        implementation:
          name: picoquic
          type: iut
        protocol:
          name: quic
          role: server
      client:
        implementation:
          name: picoquic
          type: iut
        protocol:
          name: quic
          role: client
          target: server
    steps:
      wait: 30
""",
        "advanced": """# Advanced PANTHER Configuration Template
logging:
  level: INFO
  format: "%(asctime)s [%(levelname)s] - %(module)s - %(message)s"
  enable_colors: true

observers:
  logger:
    enabled: true
    log_level: "INFO"
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
  user_mapping:
    enabled: true

tests:
  - name: "Advanced Test"
    description: "Full-featured configuration with all options"
    iterations: 3
    network_environment:
      type: docker_compose
      settings:
        compose_file: "docker-compose.yml"
    services:
      server:
        implementation:
          name: picoquic
          type: iut
        protocol:
          name: quic
          version: rfc9000
          role: server
        timeout: 120
        parameters:
          cert_file: "/certs/server.crt"
          key_file: "/certs/server.key"
      client:
        implementation:
          name: picoquic
          type: iut
        protocol:
          name: quic
          version: rfc9000
          role: client
          target: server
        timeout: 120
        parameters:
          verify_certificate: false
    steps:
      wait: 60
      post_processing:
        enabled: true
""",
        "performance": """# Performance Testing PANTHER Configuration Template
logging:
  level: INFO
  enable_colors: true

observers:
  logger:
    enabled: true
  metrics:
    enabled: true
    collect_system_metrics: true
    metrics_interval: 1
  profiler:
    enabled: true
    profile_type: "cpu"

paths:
  output_dir: "outputs/performance"
  log_dir: "outputs/performance/logs"

tests:
  - name: "Performance Test"
    description: "Optimized for performance testing with profiling"
    iterations: 10
    network_environment:
      type: docker_compose
    services:
      server:
        implementation:
          name: picoquic
          type: iut
        protocol:
          name: quic
          role: server
        timeout: 60
        resources:
          cpu_limit: "2"
          memory_limit: "1G"
      client:
        implementation:
          name: picoquic
          type: iut
        protocol:
          name: quic
          role: client
          target: server
        timeout: 60
        load_testing:
          concurrent_connections: 100
          requests_per_connection: 1000
    steps:
      warmup: 10
      test_duration: 300
      cooldown: 10
""",
        "security": """# Security Testing PANTHER Configuration Template
logging:
  level: DEBUG
  enable_colors: true

observers:
  logger:
    enabled: true
  security_monitor:
    enabled: true
    log_security_events: true
  verification:
    enabled: true
    formal_verification: true

paths:
  output_dir: "outputs/security"
  log_dir: "outputs/security/logs"

security:
  tls_verification: true
  certificate_validation: strict
  vulnerability_scanning: true

tests:
  - name: "Security Test"
    description: "Security-focused configuration with formal verification"
    network_environment:
      type: docker_compose
      security_policies:
        network_isolation: true
        container_hardening: true
    services:
      server:
        implementation:
          name: picoquic
          type: iut
        protocol:
          name: quic
          role: server
        security:
          tls_version: "1.3"
          cipher_suites: ["TLS_AES_256_GCM_SHA384"]
          certificate_verification: true
      client:
        implementation:
          name: picoquic
          type: iut
        protocol:
          name: quic
          role: client
          target: server
        security:
          verify_server_certificate: true
          security_probes: true
    verification:
      formal_verification:
        enabled: true
        properties: ["authentication", "confidentiality", "integrity"]
    steps:
      security_scan: 30
      penetration_test: 60
      verification: 120
""",
    }

    return base_config.get(template, base_config["basic"])


@config.command()
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    required=True,
    help="Output file path for the generated configuration",
)
@click.option(
    "--from-file",
    type=click.Path(exists=True),
    help="Start from an existing configuration file",
)
@click.option(
    "--quick",
    is_flag=True,
    help="Quick mode - use defaults and skip optional configurations",
)
@click.option(
    "--non-interactive", is_flag=True, help="Non-interactive mode for automated usage"
)
@handle_errors
@pass_context_and_setup_logging
def design(ctx, output, from_file, quick, non_interactive):
    r"""Interactive configuration designer.

    Create experiment configurations interactively with guided prompts,
    validation, and real-time feedback. Perfect for users new to PANTHER
    or complex experiment setups.

    \b
    Design Features:
    🎨 Interactive step-by-step configuration
    🔍 Real-time validation and feedback
    💡 Smart suggestions and recommendations
    📋 Template-based starting points
    ✅ Built-in validation and testing

    \b
    Examples:
      # Start fresh interactive design
      panther config design --output my-experiment.yaml

      # Quick mode with defaults
      panther config design --output test.yaml --quick

      # Start from existing configuration
      panther config design --output modified.yaml --from-file existing.yaml

      # Non-interactive for automation
      panther config design --output auto.yaml --non-interactive

    \b
    Design Process:
    1. Choose base template or start from existing config
    2. Configure test parameters (name, description, iterations)
    3. Set up network environment (docker-compose, localhost, etc.)
    4. Define services and implementations
    5. Configure protocols and parameters
    6. Review and validate configuration
    7. Save to output file
    """
    click.echo(
        colored("🎨 PANTHER Interactive Configuration Designer", "blue", attrs=["bold"])
    )
    click.echo("=" * 60)
    click.echo()

    output = Path(output)  # click.Path() returns str, convert to Path

    # Check for file conflicts
    if output.exists():
        if not click.confirm(f"File {output} already exists. Overwrite?"):
            info_message("Design session cancelled")
            return

    if non_interactive:
        info_message("Running in non-interactive mode")

        # Generate a basic configuration automatically
        template_content = """# Auto-generated PANTHER Configuration
logging:
  level: INFO
  enable_colors: true

observers:
  logger:
    enabled: true

paths:
  output_dir: "outputs"

tests:
  - name: "Auto-generated Test"
    description: "Configuration created in non-interactive mode"
    network_environment:
      type: docker_compose
    iterations: 1
    services:
      server:
        implementation:
          name: picoquic
          type: iut
        protocol:
          name: quic
          role: server
        timeout: 60
      client:
        implementation:
          name: picoquic
          type: iut
        protocol:
          name: quic
          role: client
          target: server
        timeout: 60
    steps:
      wait: 30
"""

        output.parent.mkdir(parents=True, exist_ok=True)
        with open(output, "w") as f:
            f.write(template_content)

        success_message(f"Configuration created: {output}")
        info_message(f"Validate with: panther config validate --config {output}")
        return

    try:
        # Load base configuration if starting from an existing file
        base_config = None
        if from_file:
            import yaml

            info_message(f"Starting from existing configuration: {from_file}")
            try:
                with open(from_file, "r") as f:
                    base_config = yaml.safe_load(f)
            except Exception as e:
                error_message(f"Error loading base configuration: {e}")
                raise click.Abort()

        info_message("Starting interactive configuration designer...")

        # Basic interactive prompts
        name = click.prompt("Test name", default="Interactive Test")
        description = click.prompt(
            "Test description", default="Created with interactive designer"
        )

        # Environment selection
        env_choices = ["docker_compose", "localhost", "shadow_ns"]
        env_type = click.prompt(
            "Network environment type",
            type=click.Choice(env_choices),
            default="docker_compose",
        )

        if not quick:
            iterations = click.prompt("Number of iterations", type=int, default=1)
            timeout = click.prompt("Service timeout (seconds)", type=int, default=60)

            # Server implementation selection
            server_impl = click.prompt("Server implementation", default="picoquic")
            client_impl = click.prompt("Client implementation", default="picoquic")

            # Protocol selection
            protocol_choices = ["quic", "http", "tcp"]
            protocol = click.prompt(
                "Protocol", type=click.Choice(protocol_choices), default="quic"
            )
        else:
            iterations = 1
            timeout = 60
            server_impl = "picoquic"
            client_impl = "picoquic"
            protocol = "quic"

        # Generate configuration based on prompts
        config_content = f"""# Interactive PANTHER Configuration
# Created with panther config design

logging:
  level: INFO
  enable_colors: true

observers:
  logger:
    enabled: true
    log_level: INFO

paths:
  output_dir: "outputs"

tests:
  - name: "{name}"
    description: "{description}"
    network_environment:
      type: {env_type}
    iterations: {iterations}
    services:
      server:
        implementation:
          name: {server_impl}
          type: iut
        protocol:
          name: {protocol}
          role: server
        timeout: {timeout}
      client:
        implementation:
          name: {client_impl}
          type: iut
        protocol:
          name: {protocol}
          role: client
          target: server
        timeout: {timeout}
    steps:
      wait: {timeout // 2}
"""

        # Merge with base configuration if provided
        if base_config:
            import yaml

            new_config = yaml.safe_load(config_content)
            # Merge configurations - new config takes precedence
            if "tests" in base_config:
                base_config["tests"].extend(new_config["tests"])
            else:
                base_config["tests"] = new_config["tests"]

            config_content = yaml.dump(base_config, default_flow_style=False)

        # Preview configuration
        if not quick:
            click.echo(colored("\n📋 Preview of generated configuration:", "yellow"))
            preview = (
                config_content[:400] + "..."
                if len(config_content) > 400
                else config_content
            )
            click.echo(preview)

            if not click.confirm("\nSave this configuration?"):
                info_message("Configuration design cancelled")
                return

        # Save configuration
        output.parent.mkdir(parents=True, exist_ok=True)
        with open(output, "w") as f:
            f.write(config_content)

        success_message(f"Configuration successfully created: {output}")
        info_message(f"Validate with: panther config validate --config {output}")

    except KeyboardInterrupt:
        info_message("\nDesign session cancelled by user")
        raise click.Abort()
    except Exception as e:
        error_message(f"Design session failed: {e}")
        if ctx.obj.get("debug", False):
            import traceback

            click.echo(traceback.format_exc(), err=True)
        raise click.Abort()


if __name__ == "__main__":
    config()
