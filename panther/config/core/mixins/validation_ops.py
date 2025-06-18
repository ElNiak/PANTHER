"""Validation operations mixin for ConfigurationManager."""

from typing import Any, Callable, Dict, List, Optional, Union

from panther.core.utils.logging_mixin import LoggerMixin

from ..base import BaseConfig


class ValidationError:
    """Validation error details."""
    
    def __init__(self, field: str, message: str, severity: str = "error"):
        self.field = field
        self.message = message
        self.severity = severity
    
    def __str__(self):
        return f"{self.severity.upper()}: {self.field} - {self.message}"


class ValidationResult:
    """Validation result container."""
    
    def __init__(self, is_valid: bool = True):
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
    
    def merge(self, other: 'ValidationResult'):
        """Merge another validation result into this one."""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        self.is_valid = self.is_valid and other.is_valid
    
    def __str__(self):
        lines = []
        if self.errors:
            lines.append("Errors:")
            for error in self.errors:
                lines.append(f"  - {error}")
        if self.warnings:
            lines.append("Warnings:")
            for warning in self.warnings:
                lines.append(f"  - {warning}")
        return "\n".join(lines)


class Validator:
    """Base validator interface."""
    
    def validate(self, config: Any) -> ValidationResult:
        """Validate configuration."""
        raise NotImplementedError


class ValidationOperationsMixin(LoggerMixin):
    """Handles validation operations."""
    
    def __init__(self):
        """Initialize validation operations."""
        super().__init__()
        self._strict_mode = False
        self._custom_validators: List[Callable] = []
        self._validation_errors: List[ValidationError] = []
    
    def validate_experiment_config(self, config: Union[Dict, 'ExperimentConfig']) -> ValidationResult:
        """Validate experiment configuration.
        
        Args:
            config: Configuration to validate (dict or ExperimentConfig)
            
        Returns:
            Validation result
        """
        self.logger.info("Validating experiment configuration")
        result = ValidationResult()
        
        # Convert to ExperimentConfig if needed
        if isinstance(config, dict):
            try:
                from ..models.experiment import ExperimentConfig
                config = ExperimentConfig(**config)
            except Exception as e:
                result.add_error("config", f"Failed to parse configuration: {e}")
                return result
        
        # Schema validation (Pydantic handles this automatically)
        try:
            config.validate()
        except Exception as e:
            result.add_error("schema", str(e))
        
        # Business rules validation
        if hasattr(self, 'validators'):
            for validator in self.validators:
                if hasattr(validator, 'validate_experiment'):
                    validator_result = validator.validate_experiment(config)
                    result.merge(validator_result)
        
        # Custom validators
        for custom_validator in self._custom_validators:
            try:
                custom_result = custom_validator(config)
                if isinstance(custom_result, ValidationResult):
                    result.merge(custom_result)
            except Exception as e:
                result.add_error("custom", f"Custom validator failed: {e}")
        
        # Specific experiment validations
        result.merge(self._validate_experiment_specific(config))
        
        # Store errors for later retrieval
        self._validation_errors = result.errors + result.warnings
        
        return result
    
    def validate_global_config(self, config: Union[Dict, 'GlobalConfig']) -> ValidationResult:
        """Validate global configuration.
        
        Args:
            config: Configuration to validate
            
        Returns:
            Validation result
        """
        self.logger.info("Validating global configuration")
        result = ValidationResult()
        
        # Convert to GlobalConfig if needed
        if isinstance(config, dict):
            try:
                from ..models.global_config import GlobalConfig
                config = GlobalConfig(**config)
            except Exception as e:
                result.add_error("config", f"Failed to parse configuration: {e}")
                return result
        
        # Schema validation
        try:
            config.validate()
        except Exception as e:
            result.add_error("schema", str(e))
        
        # Business rules
        if hasattr(self, 'validators'):
            for validator in self.validators:
                if hasattr(validator, 'validate_global'):
                    validator_result = validator.validate_global(config)
                    result.merge(validator_result)
        
        # Specific global config validations
        result.merge(self._validate_global_specific(config))
        
        return result
    
    def validate_service_configuration(self, service: Dict[str, Any]) -> 'ServiceConfig':
        """Validate and build service configuration.
        
        Args:
            service: Service configuration dictionary
            
        Returns:
            Validated ServiceConfig instance
            
        Raises:
            ValueError: If validation fails
        """
        from ..models.service import ServiceConfig
        
        # Create ServiceConfig instance (validates schema)
        try:
            service_config = ServiceConfig(**service)
        except Exception as e:
            raise ValueError(f"Invalid service configuration: {e}")
        
        # Additional business rules
        result = self._validate_service_specific(service_config)
        if not result.is_valid:
            raise ValueError(f"Service validation failed: {result}")
        
        return service_config
    
    def validate_environment_config(self, env: Dict[str, Any]) -> 'EnvironmentConfig':
        """Validate environment configuration.
        
        Args:
            env: Environment configuration dictionary
            
        Returns:
            Validated environment config
        """
        # Use dynamic config resolution instead of hardcoded mappings
        # This allows new plugins to be added without modifying core code
        
        # Get the config resolver (should be available through dependency injection)
        if hasattr(self, 'config_resolver'):
            config_resolver = self.config_resolver
        else:
            # Create a new instance if not injected
            from panther.plugins.plugin_config_resolver import PluginConfigResolver
            config_resolver = PluginConfigResolver()
        
        env_type = env.get('type', '')
        
        # Try to discover the category by attempting to resolve in both categories
        # This allows the plugin system to determine where the plugin exists
        for category in ['network_environment', 'execution_environment']:
            config_class = config_resolver.resolve_environment_config_class(env_type, category)
            if config_class:
                # Found the config class in this category
                return config_resolver.create_environment_config_dynamic(env, category)
        
        # If not found in any category, try to infer from the context
        # Check if we're being called with network or execution context
        if hasattr(self, '_current_env_category'):
            env_category = self._current_env_category
        else:
            # Default to base environment if we can't determine the category
            env_category = 'environment'
            self.logger.warning(
                f"Could not determine category for environment type '{env_type}'. "
                f"Using base environment configuration."
            )
            
        # Use dynamic resolution with determined or default category
        return config_resolver.create_environment_config_dynamic(env, env_category)
    
    def set_validation_mode(self, strict: bool) -> None:
        """Set validation mode.
        
        Args:
            strict: Whether to use strict validation
        """
        self._strict_mode = strict
        self.logger.info(f"Validation mode set to: {'strict' if strict else 'lenient'}")
    
    def add_custom_validator(self, validator: Callable) -> None:
        """Add a custom validator function.
        
        Args:
            validator: Validator function that takes config and returns ValidationResult
        """
        self._custom_validators.append(validator)
        self.logger.debug(f"Added custom validator: {validator.__name__}")
    
    def get_validation_errors(self) -> List[ValidationError]:
        """Get list of validation errors from last validation.
        
        Returns:
            List of validation errors
        """
        return self._validation_errors.copy()
    
    def _run_validators(self, config: Any, validators: List[Validator]) -> ValidationResult:
        """Run a list of validators on configuration.
        
        Args:
            config: Configuration to validate
            validators: List of validators to run
            
        Returns:
            Combined validation result
        """
        result = ValidationResult()
        
        for validator in validators:
            try:
                validator_result = validator.validate(config)
                result.merge(validator_result)
            except Exception as e:
                result.add_error("validator", f"{validator.__class__.__name__} failed: {e}")
        
        return result
    
    def _validate_experiment_specific(self, config: 'ExperimentConfig') -> ValidationResult:
        """Perform experiment-specific validations.
        
        Args:
            config: Experiment configuration
            
        Returns:
            Validation result
        """
        result = ValidationResult()
        
        # Validate tests
        if not config.tests:
            result.add_error("tests", "At least one test must be defined")
        
        for i, test in enumerate(config.tests):
            # Validate service references
            if hasattr(test, 'services'):
                for service_name, service in test.services.items():
                    if hasattr(service.protocol, 'target') and service.protocol.target:
                        if service.protocol.target not in test.services:
                            result.add_error(
                                f"tests[{i}].services.{service_name}.protocol.target",
                                f"Target service '{service.protocol.target}' not found"
                            )
            
            # Validate timeout consistency
            if hasattr(test, 'timeout') and test.timeout:
                if hasattr(test, 'steps') and test.steps.wait > test.timeout:
                    result.add_warning(
                        f"tests[{i}].steps.wait",
                        f"Wait time ({test.steps.wait}s) exceeds test timeout ({test.timeout}s)"
                    )
        
        return result
    
    def _validate_global_specific(self, config: 'GlobalConfig') -> ValidationResult:
        """Perform global config specific validations.
        
        Args:
            config: Global configuration
            
        Returns:
            Validation result
        """
        result = ValidationResult()
        
        # Validate paths
        if hasattr(config, 'paths'):
            if not config.paths.output_dir:
                result.add_error("paths.output_dir", "Output directory must be specified")
        
        # Validate feature log levels
        if hasattr(config, 'logging') and hasattr(config.logging, 'feature_levels'):
            valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            for feature, level in config.logging.feature_levels.to_dict().items():
                if level and level.upper() not in valid_levels:
                    result.add_error(
                        f"logging.feature_levels.{feature}",
                        f"Invalid log level: {level}"
                    )
        
        return result
    
    def _validate_service_specific(self, service: 'ServiceConfig') -> ValidationResult:
        """Perform service-specific validations.
        
        Args:
            service: Service configuration
            
        Returns:
            Validation result
        """
        result = ValidationResult()
        
        # Validate port mappings for servers
        if service.protocol.role == "server" and not service.ports:
            result.add_warning("ports", "Server services should define port mappings")
        
        # Validate timeout
        if service.timeout <= 0:
            result.add_error("timeout", "Timeout must be positive")
        elif service.timeout < 10:
            result.add_warning("timeout", "Very short timeout may cause issues")
        
        return result