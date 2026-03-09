"""Configuration validators for the unified system."""

import json
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type

from pydantic import ValidationError as PydanticValidationError

from panther.core.utils.logging_mixin import LoggerMixin

from ..base import BaseConfig


class ValidationError:
    """Validation error details."""

    def __init__(self, field: str, message: str, severity: str = "error"):
        """Initialize validation error."""
        self.field = field
        self.message = message
        self.severity = severity

    def __str__(self):
        """Return formatted error string."""
        return f"{self.severity.upper()}: {self.field} - {self.message}"


class ValidationResult:
    """Validation result container."""

    def __init__(self, is_valid: bool = True):
        """Initialize validation result."""
        self.is_valid = is_valid
        self.errors: List[ValidationError] = []
        self.warnings: List[ValidationError] = []

    def add_error(self, field: str, message: str):
        """Add an error to the result."""
        self.errors.append(ValidationError(field, message, "error"))
        self.is_valid = False

    def add_warning(self, field: str, message: str):
        """Add a warning to the result."""
        self.warnings.append(ValidationError(field, message, "warning"))

    def merge(self, other: "ValidationResult"):
        """Merge another validation result into this one."""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        self.is_valid = self.is_valid and other.is_valid


class BaseValidator(LoggerMixin, ABC):
    """Base class for validators."""

    @abstractmethod
    def validate(self, config: Any) -> ValidationResult:
        """Validate configuration.

        Args:
            config: Configuration to validate

        Returns:
            Validation result
        """
        pass


class ConfigValidator(BaseValidator):
    """Main validator that combines Pydantic and business rules validation."""

    def __init__(self):
        """Initialize unified validator."""
        super().__init__()
        self.pydantic_validator = PydanticValidator()
        self.business_validator = BusinessRulesValidator()
        self.compatibility_validator = CompatibilityValidator()

    def validate(self, config: Any) -> ValidationResult:
        """Validate configuration using all validators.

        Args:
            config: Configuration to validate

        Returns:
            Combined validation result
        """
        result = ValidationResult()

        # Run Pydantic validation
        pydantic_result = self.pydantic_validator.validate(config)
        result.merge(pydantic_result)

        # Run business rules validation
        business_result = self.business_validator.validate(config)
        result.merge(business_result)

        # Run compatibility validation
        compat_result = self.compatibility_validator.validate(config)
        result.merge(compat_result)

        return result


class SchemaValidator(BaseValidator):
    """JSON Schema validator."""

    def __init__(self):
        """Initialize schema validator."""
        super().__init__()
        self._schema_cache: Dict[str, Dict[str, Any]] = {}

    def validate(self, config: Any) -> ValidationResult:
        """Validate against JSON schema.

        Args:
            config: Configuration to validate

        Returns:
            Validation result
        """
        result = ValidationResult()

        # Get schema for config type
        schema = self._get_schema(config)
        if not schema:
            result.add_warning("schema", "No schema found for validation")
            return result

        try:
            import jsonschema

            jsonschema.validate(
                config if isinstance(config, dict) else config.to_dict(), schema
            )
        except jsonschema.ValidationError as e:
            result.add_error(e.path[0] if e.path else "root", str(e.message))
        except Exception as e:
            result.add_error("schema", f"Schema validation failed: {e}")

        return result

    def validate_against_schema(
        self, data: Dict[str, Any], schema: Dict[str, Any]
    ) -> ValidationResult:
        """Validate data against a specific schema.

        Args:
            data: Data to validate
            schema: JSON schema

        Returns:
            Validation result
        """
        result = ValidationResult()

        try:
            import jsonschema

            jsonschema.validate(data, schema)
        except jsonschema.ValidationError as e:
            result.add_error(".".join(str(p) for p in e.path), str(e.message))
        except Exception as e:
            result.add_error("schema", f"Schema validation failed: {e}")

        return result

    def _get_schema(self, config: Any) -> Optional[Dict[str, Any]]:
        """Get schema for configuration type.

        Args:
            config: Configuration object

        Returns:
            JSON schema or None
        """
        config_type = (
            config.__class__.__name__
            if hasattr(config, "__class__")
            else type(config).__name__
        )

        # Check cache
        if config_type in self._schema_cache:
            return self._schema_cache[config_type]

        # Generate schema if it's a Pydantic model
        if hasattr(config, "model_json_schema"):
            schema = config.model_json_schema()
            self._schema_cache[config_type] = schema
            return schema

        return None


class PydanticValidator(BaseValidator):
    """Pydantic model validator."""

    def validate(self, config: Any) -> ValidationResult:
        """Validate using Pydantic.

        Args:
            config: Configuration to validate

        Returns:
            Validation result
        """
        result = ValidationResult()

        # If it's already a Pydantic model, validate it
        if isinstance(config, BaseConfig):
            try:
                config.model_validate(config.model_dump())
            except PydanticValidationError as e:
                self.logger.error(
                    f"Pydantic validation failed with {len(e.errors())} error(s)"
                )
                for error in e.errors():
                    field_path = ".".join(str(loc) for loc in error["loc"])
                    error_msg = error["msg"]
                    self.logger.error(
                        f"Validation error at '{field_path}': {error_msg}"
                    )
                    result.add_error(field_path, error_msg)
        elif isinstance(config, dict):
            # Try to infer the model type and validate
            result.add_warning("type", "Cannot validate dict without model type")

        return result


class BusinessRulesValidator(BaseValidator):
    """Business rules validator for domain-specific validation."""

    def validate(self, config: Any) -> ValidationResult:
        """Validate business rules.

        Args:
            config: Configuration to validate

        Returns:
            Validation result
        """
        result = ValidationResult()

        # Get config type
        if hasattr(config, "__class__"):
            config_type = config.__class__.__name__
        else:
            config_type = type(config).__name__

        # Apply specific validators based on type
        if "ServiceConfig" in config_type:
            result.merge(self._validate_service_rules(config))
        elif "TestConfig" in config_type:
            result.merge(self._validate_test_rules(config))
        elif "ExperimentConfig" in config_type:
            result.merge(self._validate_experiment_rules(config))
        elif "GlobalConfig" in config_type:
            result.merge(self._validate_global_rules(config))

        return result

    def validate_experiment(self, config: Any) -> ValidationResult:
        """Validate experiment configuration (interface method for ValidationOperationsMixin).

        Args:
            config: Experiment configuration to validate

        Returns:
            Validation result
        """
        return self._validate_experiment_rules(config)

    def validate_global(self, config: Any) -> ValidationResult:
        """Validate global configuration (interface method for ValidationOperationsMixin).

        Args:
            config: Global configuration to validate

        Returns:
            Validation result
        """
        return self._validate_global_rules(config)

    def validate_service(self, config: Any) -> ValidationResult:
        """Validate service configuration (interface method for ValidationOperationsMixin).

        Args:
            config: Service configuration to validate

        Returns:
            Validation result
        """
        return self._validate_service_rules(config)

    def _validate_service_rules(self, service: Any) -> ValidationResult:
        """Validate service-specific business rules.

        Args:
            service: Service configuration

        Returns:
            Validation result
        """
        result = ValidationResult()

        # Check port mappings for servers
        if hasattr(service, "protocol") and hasattr(service.protocol, "role"):
            if service.protocol.role == "server" and not service.ports:
                result.add_warning(
                    "ports", "Server services should define port mappings"
                )

        # Validate timeout ranges
        if hasattr(service, "timeout"):
            if service.timeout < 10:
                result.add_warning("timeout", "Very short timeout may cause issues")
            elif service.timeout > 3600:
                result.add_warning("timeout", "Very long timeout may waste resources")

        # Check certificate settings
        if hasattr(service, "protocol") and service.protocol.name.lower() in [
            "quic",
            "https",
        ]:
            if not getattr(service, "generate_new_certificates", False):
                result.add_warning(
                    "certificates", "TLS protocols should generate certificates"
                )

        return result

    def _validate_test_rules(self, test: Any) -> ValidationResult:
        """Validate test-specific business rules.

        Args:
            test: Test configuration

        Returns:
            Validation result
        """
        result = ValidationResult()

        # Check timeout vs wait time
        if hasattr(test, "timeout") and hasattr(test, "steps"):
            if test.timeout and test.steps.wait > test.timeout:
                result.add_error(
                    "steps.wait",
                    f"Wait time ({test.steps.wait}s) exceeds test timeout ({test.timeout}s)",
                )

        # Validate service dependencies
        if hasattr(test, "services"):
            services = test.services
            for service_name, service in services.items():
                if hasattr(service.protocol, "target") and service.protocol.target:
                    if service.protocol.target not in services:
                        result.add_error(
                            f"services.{service_name}.protocol.target",
                            f"Target service '{service.protocol.target}' not found",
                        )

        return result

    def _validate_experiment_rules(self, experiment: Any) -> ValidationResult:
        """Validate experiment-specific business rules.

        Args:
            experiment: Experiment configuration

        Returns:
            Validation result
        """
        result = ValidationResult()

        # Check for duplicate test names
        if hasattr(experiment, "tests"):
            test_names = [test.name for test in experiment.tests]
            if len(test_names) != len(set(test_names)):
                result.add_error("tests", "Test names must be unique")

        # Validate within-test port conflicts only (cross-test conflicts are allowed)
        # Different tests run in isolation and can use the same ports

        if hasattr(experiment, "tests"):
            for test in experiment.tests:
                if hasattr(test, "services"):
                    # Check within-test port conflicts only
                    test_ports = {}
                    test_used_ports = set()

                    for service_name, service in test.services.items():
                        if hasattr(service, "ports"):
                            for port_mapping in service.ports:
                                host_port = port_mapping.split(":")[0]
                                test_used_ports.add(int(host_port))

                                if host_port in test_ports:
                                    # Enhanced error message with suggested alternatives
                                    suggested_port = self._suggest_alternative_port(
                                        int(host_port), test_used_ports
                                    )
                                    result.add_error(
                                        f"tests.{test.name}.services.{service_name}.ports",
                                        f"Port {host_port} already used by service {test_ports[host_port]} in the same test. "
                                        f"Suggested alternative: {suggested_port}",
                                    )
                                else:
                                    test_ports[host_port] = service_name

        return result

    def _suggest_alternative_port(self, conflicting_port: int, used_ports: set) -> int:
        """Suggest an alternative port close to the conflicting one.

        Args:
            conflicting_port: The port that has a conflict
            used_ports: Set of all currently used ports

        Returns:
            Suggested alternative port number
        """
        # Try ports in the same range, starting from conflicting_port + 1
        for offset in range(1, 100):
            candidate = conflicting_port + offset
            if candidate not in used_ports and candidate <= 65535:
                return candidate

        # If no nearby port found, try decreasing
        for offset in range(1, conflicting_port - 1024):
            candidate = conflicting_port - offset
            if candidate not in used_ports and candidate >= 1024:
                return candidate

        # Fallback to a high port range
        for candidate in range(50000, 65535):
            if candidate not in used_ports:
                return candidate

        return conflicting_port + 1000  # Last resort

    def _suggest_port_for_service_type(self, service_type: str, used_ports: set) -> int:
        """Suggest a port based on service type and avoid conflicts.

        Args:
            service_type: Type or name of the service
            used_ports: Set of all currently used ports

        Returns:
            Suggested port number appropriate for the service type
        """
        # Service-type-aware port ranges
        service_port_ranges = {
            "ivy_server": (4000, 4999),
            "ivy_client": (7000, 7999),
            "picoquic_server": (6000, 6999),
            "picoquic_client": (5000, 5999),
            "quic": (4400, 4500),
            "http": (8000, 8999),
            "https": (8400, 8500),
        }

        # Determine appropriate range
        port_range = (50000, 59999)  # Default high range
        for service_pattern, range_tuple in service_port_ranges.items():
            if service_pattern.lower() in service_type.lower():
                port_range = range_tuple
                break

        # Find available port in the appropriate range
        start_port, end_port = port_range
        for candidate in range(start_port, end_port + 1):
            if candidate not in used_ports:
                return candidate

        # If service-specific range is full, try general high range
        for candidate in range(50000, 65535):
            if candidate not in used_ports:
                return candidate

        return start_port  # Last resort

    def _validate_global_rules(self, global_config: Any) -> ValidationResult:
        """Validate global configuration rules.

        Args:
            global_config: Global configuration

        Returns:
            Validation result
        """
        result = ValidationResult()

        # Validate log levels
        if hasattr(global_config, "logging") and hasattr(
            global_config.logging, "level"
        ):
            valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            if global_config.logging.level.upper() not in valid_levels:
                result.add_error(
                    "logging.level", f"Invalid log level: {global_config.logging.level}"
                )

        # Validate paths exist
        if hasattr(global_config, "paths"):
            paths = global_config.paths
            if hasattr(paths, "plugin_dir"):
                from pathlib import Path

                if not Path(paths.plugin_dir).exists():
                    result.add_warning(
                        "paths.plugin_dir",
                        f"Plugin directory not found: {paths.plugin_dir}",
                    )

        return result


class CompatibilityValidator(BaseValidator):
    """Validator for checking legacy format compatibility."""

    def validate(self, config: Any) -> ValidationResult:
        """Check for legacy format issues.

        Args:
            config: Configuration to validate

        Returns:
            Validation result
        """
        result = ValidationResult()

        # Check for deprecated fields
        deprecated_fields = {
            "use_docker": "docker.enabled",
            "log_level": "logging.level",
            "output_directory": "paths.output_dir",
        }

        config_dict = config if isinstance(config, dict) else config.to_dict()

        for old_field, new_field in deprecated_fields.items():
            if old_field in config_dict:
                result.add_warning(
                    old_field,
                    f"Deprecated field '{old_field}', use '{new_field}' instead",
                )

        # Check for legacy structure
        if "config" in config_dict and isinstance(config_dict["config"], dict):
            result.add_warning(
                "config",
                "Legacy nested 'config' structure detected, consider flattening",
            )

        return result
