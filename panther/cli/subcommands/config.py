"""
Config Command - Configuration management and validation
"""

import json
import logging
import sys
from argparse import ArgumentParser, _SubParsersAction
from pathlib import Path
from typing import Any

from ..base import BaseCommand


class ConfigCommand(BaseCommand):
    """Handle configuration management commands."""

    @classmethod
    def register_parser(cls, subparsers: _SubParsersAction) -> ArgumentParser:
        """Register the config subcommand parser."""
        parser = subparsers.add_parser(
            "config",
            help="Configuration management and validation",
            description="Validate, analyze, and manage PANTHER configuration files",
        )

        subcommands = parser.add_subparsers(
            dest="config_action", help="Configuration actions", metavar="ACTION"
        )

        # Validate subcommand
        validate_parser = subcommands.add_parser(
            "validate",
            help="Validate configuration file",
            description="Validate experiment configuration file syntax and structure",
        )
        validate_parser.add_argument(
            "--config",
            type=str,
            required=True,
            help="Path to configuration file to validate",
        )
        validate_parser.add_argument(
            "--strict", action="store_true", help="Enable strict validation mode"
        )
        validate_parser.add_argument(
            "--show-schema",
            action="store_true",
            help="Show configuration schema information",
        )
        validate_parser.add_argument(
            "--explain",
            action="store_true",
            help="Show detailed explanations for validation errors",
        )

        # Schema subcommand
        schema_parser = subcommands.add_parser(
            "schema",
            help="Show configuration schema",
            description="Display the configuration schema and documentation",
        )
        schema_parser.add_argument(
            "--format",
            choices=["json", "yaml", "text"],
            default="text",
            help="Output format for schema (default: text)",
        )

        # Generate subcommand
        generate_parser = subcommands.add_parser(
            "generate",
            help="Generate configuration templates",
            description="Generate configuration file templates for common scenarios",
        )
        generate_parser.add_argument(
            "--template",
            choices=["minimal", "basic", "advanced", "performance", "security"],
            default="basic",
            help="Configuration template type (default: basic)",
        )
        generate_parser.add_argument(
            "--output", type=str, help="Output file path (default: stdout)"
        )

        # Design subcommand - Interactive configuration designer
        design_parser = subcommands.add_parser(
            "design",
            help="Interactive configuration designer",
            description="Create experiment configurations interactively with guided prompts",
        )
        design_parser.add_argument(
            "--output",
            type=str,
            required=True,
            help="Output file path for the generated configuration",
        )
        design_parser.add_argument(
            "--from",
            dest="from_file",
            type=str,
            help="Start from an existing configuration file",
        )
        design_parser.add_argument(
            "--quick",
            action="store_true",
            help="Quick mode - use more defaults and skip optional configurations",
        )

        return parser

    @classmethod
    def handle(cls, args: Any) -> int:
        """Handle the config command execution."""
        if not hasattr(args, "config_action") or args.config_action is None:
            logging.info(
                "❌ No config action specified. Use 'panther config --help' for options."
            )
            return 1

        if args.config_action == "validate":
            return cls._handle_validate(args)
        elif args.config_action == "schema":
            return cls._handle_schema(args)
        elif args.config_action == "generate":
            return cls._handle_generate(args)
        elif args.config_action == "design":
            return cls._handle_design(args)
        else:
            logging.info(f"❌ Unknown config action: {args.config_action}")
            return 1

    @classmethod
    def _handle_validate(cls, args: Any) -> int:
        """Handle configuration validation."""
        try:
            import yaml
            from omegaconf import OmegaConf

            from ...config.config_manager_enhanced import ConfigLoader
            from ...core.utils.logger_factory import LoggerFactory

            config_path = Path(args.config)
            if not config_path.exists():
                logging.info(f"❌ Configuration file not found: {config_path}")
                return 1

            logging.info(f"🔍 Validating configuration: {config_path}")

            # Basic YAML syntax check
            try:
                with open(config_path, "r") as f:
                    config_data = yaml.safe_load(f)
                logging.info("✅ YAML syntax is valid")
            except yaml.YAMLError as e:
                logging.info(f"❌ YAML syntax error: {e}")
                return 1

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

            # Schema validation using ConfigLoader
            try:
                config_loader = ConfigLoader(
                    experiment_file=str(config_path),
                    debug_override=hasattr(args, "debug") and args.debug,
                )

                # Load and validate configuration
                experiment_config = config_loader.load_and_validate_experiment_config()
                logging.info("✅ Configuration schema is valid")

                # Show configuration summary
                if experiment_config and hasattr(experiment_config, "tests"):
                    test_count = (
                        len(experiment_config.tests) if experiment_config.tests else 0
                    )
                    logging.info(f"📋 Found {test_count} test(s) in configuration")

                    if args.show_schema:
                        logging.info("\n📖 Configuration Summary:")
                        if experiment_config.tests:
                            for i, test in enumerate(experiment_config.tests, 1):
                                logging.info(f"  Test {i}: {test.name}")
                                if hasattr(test, "services") and test.services:
                                    service_count = len(test.services)
                                    logging.info(f"    Services: {service_count}")

            except Exception as e:
                logging.info(f"❌ Configuration validation failed: {e}")

                # Enhanced error explanation if requested
                if hasattr(args, "explain") and args.explain:
                    from ...cli.interactive.validation_helper import ValidationHelper

                    logging.info("\n" + ValidationHelper.explain_validation_error(e))

                    # Try to provide specific suggestions
                    suggestions = ValidationHelper.suggest_fixes(config_data, e)
                    if suggestions:
                        logging.info("\n💡 Suggestions:")
                        for suggestion in suggestions:
                            logging.info(f"   {suggestion}")

                if hasattr(args, "debug") and args.debug:
                    import traceback

                    traceback.print_exc()
                return 1

            # Additional validation with explanation if requested
            if hasattr(args, "explain") and args.explain:
                from ...cli.interactive.validation_helper import ValidationHelper

                valid, explanations = ValidationHelper.validate_with_explanation(
                    config_path
                )

                logging.info("\n📋 Detailed Validation Report:")
                for explanation in explanations:
                    logging.info(f"   {explanation}")

                if not valid:
                    return 1

            logging.info("✅ Configuration is valid and ready to use")
            return 0

        except Exception as e:
            logging.info(f"❌ Error during validation: {e}")
            return 1

    @classmethod
    def _handle_schema(cls, args: Any) -> int:
        """Handle schema display."""
        try:
            from ...config.core.models import ExperimentConfig, GlobalConfig

            logging.info("📖 PANTHER Configuration Schema")
            logging.info("=" * 40)

            if args.format == "text":
                logging.info(
                    """
Main Configuration Sections:
  - logging: Logging configuration (level, format, etc.)
  - observers: Observer configurations (logger, metrics, storage, etc.)
  - paths: Directory paths (output_dir, log_dir, plugin_dir)
  - docker: Docker configuration (build_docker_image, etc.)
  - tests: List of test configurations

Test Configuration:
  - name: Test name (required)
  - description: Test description
  - network_environment: Network environment configuration
  - execution_environment: Execution environment configuration (optional)
  - services: Service configurations
  - steps: Test execution steps

Service Configuration:
  - implementation: Implementation details (name, type)
  - protocol: Protocol configuration (name, version, role)
  - timeout: Service timeout
  - ports: Port mappings (for Docker)
  - generate_new_certificates: Certificate generation flag

For complete schema details, see the configuration documentation.
"""
                )
            elif args.format == "json":
                # This would ideally generate JSON schema
                logging.info('{"message": "JSON schema export not yet implemented"}')
            elif args.format == "yaml":
                # This would ideally generate YAML schema
                logging.info("# YAML schema export not yet implemented")

            return 0

        except Exception as e:
            logging.info(f"❌ Error displaying schema: {e}")
            return 1

    @classmethod
    def _handle_generate(cls, args: Any) -> int:
        """Handle configuration template generation."""
        try:
            templates = {
                "minimal": cls._get_minimal_template(),
                "basic": cls._get_basic_template(),
                "advanced": cls._get_advanced_template(),
                "performance": cls._get_performance_template(),
                "security": cls._get_security_template(),
            }

            template_content = templates.get(args.template)
            if not template_content:
                logging.info(f"❌ Unknown template: {args.template}")
                return 1

            if args.output:
                output_path = Path(args.output)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "w") as f:
                    f.write(template_content)
                logging.info(f"✅ Template generated: {output_path}")
            else:
                logging.info(template_content)

            return 0

        except Exception as e:
            logging.info(f"❌ Error generating template: {e}")
            return 1

    @classmethod
    def _get_minimal_template(cls) -> str:
        """Get minimal configuration template."""
        return """# Minimal PANTHER Configuration
logging:
  level: INFO
  enable_colors: true

progress:
  enable_progress_bar: true
  show_test_status: true
  redirect_logging: false  # Preserve colored logging

observers:
  logger:
    enabled: true

paths:
  output_dir: "outputs"

docker:
  build_docker_image: false

tests:
  - name: "Basic Test"
    description: "Minimal test configuration"
    network_environment:
      type: docker_compose
    iterations: 1
    execution_environment: []
    debug_environment: []
    services:
      server:
        name: "server"
        implementation:
          name: picoquic
          type: iut
        protocol:
          name: quic
          version: rfc9000
          role: server
        timeout: 60
      client:
        name: "client"
        implementation:
          name: picoquic
          type: iut
        protocol:
          name: quic
          version: rfc9000
          role: client
          target: server
        timeout: 60
    steps:
      wait: 30
"""

    @classmethod
    def _get_basic_template(cls) -> str:
        """Get basic configuration template."""
        return """# Basic PANTHER Configuration
logging:
  level: INFO
  format: "%(asctime)s [%(levelname)s] - %(module)s - %(message)s"
  enable_colors: true

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
  build_docker_image: false

tests:
  - name: "QUIC Basic Test"
    description: "Basic QUIC connectivity test"
    network_environment:
      type: docker_compose
    iterations: 1
    execution_environment: []
    debug_environment: []
    services:
      server:
        name: "server"
        implementation:
          name: picoquic
          type: iut
        protocol:
          name: quic
          version: rfc9000
          role: server
        timeout: 100
        ports:
          - "4443:4443"
        generate_new_certificates: true
      client:
        name: "client"
        implementation:
          name: picoquic
          type: iut
        protocol:
          name: quic
          version: rfc9000
          role: client
          target: server
        timeout: 100
        generate_new_certificates: true
    steps:
      wait: 60
"""

    @classmethod
    def _get_advanced_template(cls) -> str:
        """Get advanced configuration template."""
        return """# Advanced PANTHER Configuration
logging:
  level: DEBUG
  format: "%(asctime)s [%(levelname)s] - %(module)s:%(lineno)d - %(message)s"
  enable_colors: true

observers:
  logger:
    enabled: true
    log_level: "DEBUG"
    enable_colors: true
    correlation_tracking: true
  metrics:
    enabled: true
    collect_system_metrics: true
    publish_interval: 30
  storage:
    enabled: true
    enable_compression: true
    retention_days: 30
  experiment:
    enabled: true
    priority: 115
    track_timing: true
    track_steps: true

paths:
  output_dir: "outputs"
  log_dir: "outputs/logs"
  plugin_dir: "panther/plugins"

docker:
  build_docker_image: true

tests:
  - name: "QUIC Multi-Implementation Test"
    description: "Test multiple QUIC implementations"
    network_environment:
      type: docker_compose
    iterations: 1
    execution_environment:
      - type: strace
      - type: gperf_cpu
    debug_environment: []
    services:
      picoquic_server:
        name: "picoquic_server"
        implementation:
          name: picoquic
          type: iut
        protocol:
          name: quic
          version: rfc9000
          role: server
        timeout: 120
        ports:
          - "4443:4443"
        generate_new_certificates: true
      aioquic_client:
        name: "aioquic_client"
        implementation:
          name: aioquic
          type: iut
        protocol:
          name: quic
          version: rfc9000
          role: client
          target: picoquic_server
        timeout: 120
        generate_new_certificates: true
    steps:
      wait: 90
"""

    @classmethod
    def _get_performance_template(cls) -> str:
        """Get performance testing configuration template."""
        return """# Performance Testing PANTHER Configuration
logging:
  level: INFO

observers:
  logger:
    enabled: true
  metrics:
    enabled: true
    collect_system_metrics: true
    publish_interval: 10
  storage:
    enabled: true

paths:
  output_dir: "outputs"

docker:
  build_docker_image: false

tests:
  - name: "QUIC Performance Test"
    description: "Performance analysis with profiling"
    network_environment:
      type: docker_compose
    iterations: 1
    execution_environment:
      - type: gperf_cpu
      - type: gperf_heap
    debug_environment: []
    services:
      server:
        name: "server"
        implementation:
          name: picoquic
          type: iut
        protocol:
          name: quic
          version: rfc9000
          role: server
        timeout: 300
        ports:
          - "4443:4443"
        generate_new_certificates: true
      client:
        name: "client"
        implementation:
          name: picoquic
          type: iut
        protocol:
          name: quic
          version: rfc9000
          role: client
          target: server
        timeout: 300
        generate_new_certificates: true
    steps:
      wait: 240
"""

    @classmethod
    def _get_security_template(cls) -> str:
        """Get security testing configuration template."""
        return """# Security Testing PANTHER Configuration
logging:
  level: DEBUG

observers:
  logger:
    enabled: true
    log_level: "DEBUG"
  storage:
    enabled: true

paths:
  output_dir: "outputs"

docker:
  build_docker_image: true

tests:
  - name: "QUIC Security Test with Ivy"
    description: "Formal security testing using Ivy"
    network_environment:
      type: docker_compose
    iterations: 1
    execution_environment: []
    debug_environment: []
    services:
      ivy_tester:
        name: "ivy_tester"
        implementation:
          name: panther_ivy
          type: testers
          test: quic_client_test_max
        protocol:
          name: quic
          version: rfc9000
          role: server
        timeout: 200
        ports:
          - "4443:4443"
          - "4987:4987"
      implementation_under_test:
        name: "implementation_under_test"
        implementation:
          name: picoquic
          type: iut
        protocol:
          name: quic
          version: rfc9000
          role: client
          target: ivy_tester
        timeout: 180
    steps:
      wait: 150
"""

    @classmethod
    def _handle_design(cls, args: Any) -> int:
        """Handle interactive configuration design."""
        try:
            from ...cli.interactive.experiment_designer import ExperimentDesigner

            designer = ExperimentDesigner(
                output_path=args.output,
                from_file=args.from_file if hasattr(args, "from_file") else None,
                quick_mode=args.quick if hasattr(args, "quick") else False,
            )

            logging.info("🎨 Welcome to PANTHER Interactive Configuration Designer!")
            logging.info("=" * 60)

            # Run the interactive designer
            success = designer.run()

            if success:
                logging.info(f"\n✅ Configuration successfully created: {args.output}")
                logging.info(
                    "📋 You can validate it with: panther config validate --config {} --explain".format(
                        args.output
                    )
                )
                return 0
            else:
                logging.info("\n❌ Configuration design cancelled or failed")
                return 1

        except KeyboardInterrupt:
            logging.info("\n⚠️  Design session cancelled by user")
            return 130
        except Exception as e:
            logging.info(f"❌ Error during configuration design: {e}")
            if hasattr(args, "debug") and args.debug:
                import traceback

                traceback.print_exc()
            return 1
