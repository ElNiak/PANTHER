"""Configuration validation and schema checking functionality."""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from omegaconf import ValidationError

from panther.config.config_experiment_schema import ExperimentConfig, TestConfig
from panther.config.config_global_schema import GlobalConfig
from panther.core.exceptions.error_handler_mixin import ErrorHandlerMixin


class ValidationResult:
    """Container for validation results."""

    def __init__(self, is_valid: bool = True):
        """Initialize validation result.

        Args:
            is_valid: Whether validation passed
        """
        self.is_valid = is_valid
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.field_errors: Dict[str, List[str]] = {}

    def add_error(self, message: str, field: Optional[str] = None) -> None:
        """Add a validation error.

        Args:
            message: Error message
            field: Optional field name where error occurred
        """
        self.is_valid = False
        self.errors.append(message)

        if field:
            if field not in self.field_errors:
                self.field_errors[field] = []
            self.field_errors[field].append(message)

    def add_warning(self, message: str) -> None:
        """Add a validation warning.

        Args:
            message: Warning message
        """
        self.warnings.append(message)

    def get_summary(self) -> str:
        """Get a summary of validation results.

        Returns:
            Human-readable summary string
        """
        if self.is_valid:
            summary = "Validation passed"
            if self.warnings:
                summary += f" with {len(self.warnings)} warnings"
        else:
            summary = f"Validation failed with {len(self.errors)} errors"
            if self.warnings:
                summary += f" and {len(self.warnings)} warnings"

        return summary

    def get_detailed_report(self) -> str:
        """Get a detailed validation report.

        Returns:
            Detailed report string
        """
        lines = [self.get_summary()]

        if self.errors:
            lines.append("\nErrors:")
            for error in self.errors:
                lines.append(f"  - {error}")

        if self.warnings:
            lines.append("\nWarnings:")
            for warning in self.warnings:
                lines.append(f"  - {warning}")

        if self.field_errors:
            lines.append("\nField-specific errors:")
            for field, field_errors in self.field_errors.items():
                lines.append(f"  {field}:")
                for error in field_errors:
                    lines.append(f"    - {error}")

        return "\n".join(lines)


class ConfigurationValidator(ErrorHandlerMixin):
    """Handles validation of configurations against schemas and business rules."""

    def __init__(self):
        """Initialize configuration validator."""
        super().__init__()
        self.strict_mode = False
        self.custom_validators: Dict[str, callable] = {}

    def set_strict_mode(self, strict: bool) -> None:
        """Set strict validation mode.

        Args:
            strict: Whether to use strict validation
        """
        self.strict_mode = strict
        self.logger.debug(f"Strict validation mode: {strict}")

    def add_custom_validator(self, name: str, validator_func: callable) -> None:
        """Add a custom validation function.

        Args:
            name: Name of the validator
            validator_func: Function that takes (config, result) and validates
        """
        self.custom_validators[name] = validator_func
        self.logger.debug(f"Added custom validator: {name}")

    def validate_experiment_config(
        self, config: Union[Dict[str, Any], ExperimentConfig]
    ) -> ValidationResult:
        """Validate an experiment configuration.

        Args:
            config: Configuration to validate

        Returns:
            ValidationResult with validation status and messages
        """
        result = ValidationResult()

        try:
            # Convert to ExperimentConfig if needed for schema validation
            if isinstance(config, dict):
                try:
                    experiment_config = ExperimentConfig(**config)
                except ValidationError as e:
                    self._handle_pydantic_validation_error(e, result)
                    return result
            else:
                experiment_config = config

            # Perform business logic validation
            self._validate_experiment_business_rules(experiment_config, result)

            # Run custom validators
            for name, validator in self.custom_validators.items():
                try:
                    validator(experiment_config, result)
                except Exception as e:
                    result.add_error(f"Custom validator '{name}' failed: {str(e)}")

            return result

        except Exception as e:
            result.add_error(f"Validation failed with exception: {str(e)}")
            return result

    def validate_global_config(
        self, config: Union[Dict[str, Any], GlobalConfig]
    ) -> ValidationResult:
        """Validate a global configuration.

        Args:
            config: Configuration to validate

        Returns:
            ValidationResult with validation status and messages
        """
        result = ValidationResult()

        try:
            # Convert to GlobalConfig if needed for schema validation
            if isinstance(config, dict):
                try:
                    global_config = GlobalConfig(**config)
                except ValidationError as e:
                    self._handle_pydantic_validation_error(e, result)
                    return result
            else:
                global_config = config

            # Perform business logic validation
            self._validate_global_business_rules(global_config, result)

            return result

        except Exception as e:
            result.add_error(f"Validation failed with exception: {str(e)}")
            return result

    def validate_test_config(
        self, config: Union[Dict[str, Any], TestConfig]
    ) -> ValidationResult:
        """Validate a test configuration.

        Args:
            config: Configuration to validate

        Returns:
            ValidationResult with validation status and messages
        """
        result = ValidationResult()

        try:
            # Convert to TestConfig if needed for schema validation
            if isinstance(config, dict):
                try:
                    test_config = TestConfig(**config)
                except ValidationError as e:
                    self._handle_pydantic_validation_error(e, result)
                    return result
            else:
                test_config = config

            # Perform business logic validation
            self._validate_test_business_rules(test_config, result)

            return result

        except Exception as e:
            result.add_error(f"Validation failed with exception: {str(e)}")
            return result

    def validate_schema_compatibility(
        self, config: Dict[str, Any], schema_version: str
    ) -> ValidationResult:
        """Validate configuration against a specific schema version.

        Args:
            config: Configuration to validate
            schema_version: Target schema version

        Returns:
            ValidationResult with compatibility status
        """
        result = ValidationResult()

        config_version = config.get("version", "unknown")

        if config_version != schema_version:
            if self.strict_mode:
                result.add_error(
                    f"Schema version mismatch: config has '{config_version}', "
                    f"expected '{schema_version}'"
                )
            else:
                result.add_warning(
                    f"Schema version mismatch: config has '{config_version}', "
                    f"expected '{schema_version}'"
                )

        return result

    def _handle_pydantic_validation_error(
        self, error: ValidationError, result: ValidationResult
    ) -> None:
        """Handle OmegaConf validation errors.

        Args:
            error: OmegaConf ValidationError
            result: ValidationResult to populate
        """
        # OmegaConf ValidationError is simpler than Pydantic
        error_message = str(error)
        result.add_error(f"Configuration validation error: {error_message}")

    def _validate_experiment_business_rules(
        self, config: ExperimentConfig, result: ValidationResult
    ) -> None:
        """Validate experiment-specific business rules.

        Args:
            config: ExperimentConfig to validate
            result: ValidationResult to populate
        """
        # Validate test configurations
        if not config.tests:
            result.add_error("At least one test must be defined")
        else:
            for i, test in enumerate(config.tests):
                self._validate_test_business_rules(test, result, test_index=i)

        # Validate paths if specified
        if hasattr(config, "paths"):
            self._validate_paths(config.paths, result)

        # Validate Docker configuration
        if hasattr(config, "docker"):
            self._validate_docker_config(config.docker, result)

    def _validate_global_business_rules(
        self, config: GlobalConfig, result: ValidationResult
    ) -> None:
        """Validate global configuration business rules.

        Args:
            config: GlobalConfig to validate
            result: ValidationResult to populate
        """
        # Validate logging configuration
        if hasattr(config, "logging"):
            self._validate_logging_config(config.logging, result)

        # Validate observer configuration
        if hasattr(config, "observers"):
            self._validate_observer_config(config.observers, result)

    def _validate_test_business_rules(
        self,
        config: TestConfig,
        result: ValidationResult,
        test_index: Optional[int] = None,
    ) -> None:
        """Validate test configuration business rules.

        Args:
            config: TestConfig to validate
            result: ValidationResult to populate
            test_index: Optional test index for error messages
        """
        test_prefix = f"test[{test_index}]" if test_index is not None else "test"

        # Validate test name
        if not self._is_valid_test_name(config.name):
            result.add_error(
                f"{test_prefix}: Invalid test name '{config.name}'. "
                "Test names must be alphanumeric with underscores and hyphens only",
                f"{test_prefix}.name",
            )

        # Validate services
        if not config.services:
            result.add_error(f"{test_prefix}: At least one service must be defined")
        else:
            self._validate_services(config.services, result, test_prefix)

        # Validate network environment
        if config.network_environment:
            self._validate_network_environment(
                config.network_environment, result, test_prefix
            )

        # Validate execution environments
        if config.execution_environment:
            self._validate_execution_environments(
                config.execution_environment, result, test_prefix
            )

        # Validate steps
        if config.steps:
            self._validate_test_steps(config.steps, result, test_prefix)

    def _validate_services(
        self, services: Dict[str, Any], result: ValidationResult, prefix: str
    ) -> None:
        """Validate service configurations.

        Args:
            services: Services configuration
            result: ValidationResult to populate
            prefix: Prefix for error messages
        """
        service_names = set()

        for service_name, service_config in services.items():
            if service_name in service_names:
                result.add_error(f"{prefix}: Duplicate service name '{service_name}'")
            service_names.add(service_name)

            # Validate service implementation
            implementation = service_config.get("implementation", {})
            if not implementation.get("name"):
                result.add_error(
                    f"{prefix}.services.{service_name}: Implementation name is required"
                )

            if not implementation.get("type"):
                result.add_error(
                    f"{prefix}.services.{service_name}: Implementation type is required"
                )

            # Validate protocol configuration
            protocol = service_config.get("protocol", {})
            if not protocol.get("name"):
                result.add_error(
                    f"{prefix}.services.{service_name}: Protocol name is required"
                )

            # Validate timeout
            timeout = service_config.get("timeout")
            if timeout is not None and timeout <= 0:
                result.add_error(
                    f"{prefix}.services.{service_name}: Timeout must be positive"
                )

            # Validate port mappings
            ports = service_config.get("ports", [])
            protocol_config = service_config.get("protocol", {})
            role = protocol_config.get("role", "").lower()

            # Check for mandatory ports based on role
            if role == "server" and not ports:
                # Check if protocol provides default port
                protocol_name = protocol_config.get("name", "").lower()
                default_port = self._get_default_port_for_protocol(protocol_name)
                if default_port:
                    result.add_warning(
                        f"{prefix}.services.{service_name}: No ports specified for server. "
                        f"Consider adding port mapping like '{default_port}:{default_port}' "
                        f"(default for {protocol_name} protocol)"
                    )
                else:
                    result.add_error(
                        f"{prefix}.services.{service_name}: Server services must have at least one port mapping. "
                        f"Protocol '{protocol_name}' does not define a default port."
                    )

            # Validate individual port mappings
            for port in ports:
                if not self._is_valid_port_mapping(port):
                    result.add_error(
                        f"{prefix}.services.{service_name}: Invalid port mapping '{port}'"
                    )

    def _validate_network_environment(
        self, network_env: Dict[str, Any], result: ValidationResult, prefix: str
    ) -> None:
        """Validate network environment configuration.

        Args:
            network_env: Network environment configuration
            result: ValidationResult to populate
            prefix: Prefix for error messages
        """
        env_type = network_env.get("type")
        if not env_type:
            result.add_error(
                f"{prefix}.network_environment: Environment type is required"
            )

        # Validate known environment types
        known_types = ["docker_compose", "localhost_single_container", "shadow_ns"]
        if env_type and env_type not in known_types:
            result.add_warning(
                f"{prefix}.network_environment: Unknown environment type '{env_type}'"
            )

    def _validate_execution_environments(
        self, exec_envs: List[Dict[str, Any]], result: ValidationResult, prefix: str
    ) -> None:
        """Validate execution environment configurations.

        Args:
            exec_envs: List of execution environment configurations
            result: ValidationResult to populate
            prefix: Prefix for error messages
        """
        for i, exec_env in enumerate(exec_envs):
            env_type = exec_env.get("type")
            if not env_type:
                result.add_error(
                    f"{prefix}.execution_environment[{i}]: Environment type is required"
                )

            # Validate known execution environment types
            known_types = ["strace", "gperf_cpu", "gperf_heap", "memcheck", "helgrind"]
            if env_type and env_type not in known_types:
                result.add_warning(
                    f"{prefix}.execution_environment[{i}]: Unknown environment type '{env_type}'"
                )

    def _validate_test_steps(
        self, steps: Dict[str, Any], result: ValidationResult, prefix: str
    ) -> None:
        """Validate test steps configuration.

        Args:
            steps: Steps configuration
            result: ValidationResult to populate
            prefix: Prefix for error messages
        """
        for step_name, step_config in steps.items():
            if isinstance(step_config, (int, float)):
                # Simple wait step
                if step_config <= 0:
                    result.add_error(
                        f"{prefix}.steps.{step_name}: Wait time must be positive"
                    )
            elif isinstance(step_config, dict):
                # Complex step configuration
                step_type = step_config.get("type")
                if step_type == "wait":
                    duration = step_config.get("duration", 0)
                    if duration <= 0:
                        result.add_error(
                            f"{prefix}.steps.{step_name}: Wait duration must be positive"
                        )
                elif step_type == "http_request":
                    url = step_config.get("url")
                    if not url:
                        result.add_error(
                            f"{prefix}.steps.{step_name}: HTTP request URL is required"
                        )
                    elif not self._is_valid_url(url):
                        result.add_error(
                            f"{prefix}.steps.{step_name}: Invalid URL format"
                        )

    def _validate_paths(self, paths: Dict[str, Any], result: ValidationResult) -> None:
        """Validate path configurations.

        Args:
            paths: Paths configuration
            result: ValidationResult to populate
        """
        for path_name, path_value in paths.items():
            if path_value and not Path(path_value).is_absolute():
                result.add_warning(
                    f"paths.{path_name}: Relative path '{path_value}' may cause issues"
                )

    def _validate_docker_config(
        self, docker: Dict[str, Any], result: ValidationResult
    ) -> None:
        """Validate Docker configuration.

        Args:
            docker: Docker configuration
            result: ValidationResult to populate
        """
        build_images = docker.get("build_docker_image")
        if build_images is None:
            result.add_warning(
                "docker.build_docker_image: Not specified, defaulting to False"
            )

    def _validate_logging_config(
        self, logging: Dict[str, Any], result: ValidationResult
    ) -> None:
        """Validate logging configuration.

        Args:
            logging: Logging configuration
            result: ValidationResult to populate
        """
        level = logging.get("level")
        if level:
            valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            if isinstance(level, str) and level.upper() not in valid_levels:
                result.add_error(
                    f"logging.level: Invalid level '{level}'. Must be one of {valid_levels}"
                )

    def _validate_observer_config(
        self, observers: Dict[str, Any], result: ValidationResult
    ) -> None:
        """Validate observer configuration.

        Args:
            observers: Observer configuration
            result: ValidationResult to populate
        """
        for observer_name, observer_config in observers.items():
            if not isinstance(observer_config, dict):
                result.add_error(f"observers.{observer_name}: Must be a dictionary")
                continue

            if "enabled" not in observer_config:
                result.add_warning(
                    f"observers.{observer_name}: 'enabled' field not specified"
                )

    def _is_valid_test_name(self, name: str) -> bool:
        """Check if test name is valid.

        Args:
            name: Test name to validate

        Returns:
            True if valid, False otherwise
        """
        if not name:
            return False

        # Test names should be alphanumeric with underscores and hyphens
        return re.match(r"^[a-zA-Z0-9_-]+$", name) is not None

    def _is_valid_port_mapping(self, port: str) -> bool:
        """Check if port mapping is valid.

        Args:
            port: Port mapping string

        Returns:
            True if valid, False otherwise
        """
        if not isinstance(port, str):
            return False

        # Port mappings should be in format "host_port:container_port"
        if ":" not in port:
            # Single port number
            try:
                port_num = int(port)
                return 1 <= port_num <= 65535
            except ValueError:
                return False

        # Port mapping
        try:
            host_port, container_port = port.split(":", 1)
            host_num = int(host_port)
            container_num = int(container_port)
            return (1 <= host_num <= 65535) and (1 <= container_num <= 65535)
        except ValueError:
            return False

    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid.

        Args:
            url: URL to validate

        Returns:
            True if valid, False otherwise
        """
        import re

        # Basic URL validation
        url_pattern = re.compile(
            r"^https?://"  # http:// or https://
            r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain...
            r"localhost|"  # localhost...
            r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
            r"(?::\d+)?"  # optional port
            r"(?:/?|[/?]\S+)$",
            re.IGNORECASE,
        )

        return url_pattern.match(url) is not None

    def _get_default_port_for_protocol(self, protocol_name: str) -> Optional[str]:
        """Get default port for a protocol.

        Args:
            protocol_name: Name of the protocol

        Returns:
            Default port string or None if unknown protocol
        """
        # First try to load the protocol plugin and get its default port
        try:
            if protocol_name.lower() == "quic":
                from panther.plugins.protocols.client_server.quic.config_schema import (
                    QuicConfig,
                )

                port = QuicConfig.get_default_server_port()
                return str(port) if port else None
        except ImportError:
            self.logger.debug(f"Could not import protocol config for {protocol_name}")

        # Fallback to hardcoded defaults for unknown protocols
        fallback_ports = {
            "http": "80",
            "https": "443",
            "tcp": "8080",
            "udp": "8080",
            "minip": "5000",
        }
        return fallback_ports.get(protocol_name.lower())
