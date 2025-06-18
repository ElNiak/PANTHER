"""Base validation interfaces and utilities."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class ValidationSeverity(str, Enum):
    """Severity levels for validation errors."""
    
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationError:
    """Represents a validation error with context."""
    
    message: str
    severity: ValidationSeverity = ValidationSeverity.ERROR
    field_path: Optional[str] = None
    value: Optional[Any] = None
    suggestion: Optional[str] = None
    error_code: Optional[str] = None
    
    def __str__(self) -> str:
        """String representation of the validation error."""
        parts = []
        
        if self.field_path:
            parts.append(f"Field '{self.field_path}'")
        
        parts.append(self.message)
        
        if self.value is not None:
            parts.append(f"(value: {self.value})")
        
        if self.suggestion:
            parts.append(f"Suggestion: {self.suggestion}")
        
        return " - ".join(parts)


@dataclass
class ValidationContext:
    """Context information for validation."""
    
    source: Optional[str] = None
    phase: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def with_field(self, field_path: str) -> "ValidationContext":
        """Create a new context with additional field path."""
        new_context = ValidationContext(
            source=self.source,
            phase=self.phase,
            metadata=self.metadata.copy()
        )
        new_context.metadata["field_path"] = field_path
        return new_context


@dataclass
class ValidationResult:
    """Result of a validation operation."""
    
    is_valid: bool = True
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    context: Optional[ValidationContext] = None
    
    def add_error(
        self, 
        message: str, 
        field_path: Optional[str] = None,
        value: Optional[Any] = None,
        suggestion: Optional[str] = None,
        error_code: Optional[str] = None
    ) -> None:
        """Add a validation error."""
        error = ValidationError(
            message=message,
            severity=ValidationSeverity.ERROR,
            field_path=field_path,
            value=value,
            suggestion=suggestion,
            error_code=error_code
        )
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(
        self, 
        message: str, 
        field_path: Optional[str] = None,
        value: Optional[Any] = None,
        suggestion: Optional[str] = None
    ) -> None:
        """Add a validation warning."""
        warning = ValidationError(
            message=message,
            severity=ValidationSeverity.WARNING,
            field_path=field_path,
            value=value,
            suggestion=suggestion
        )
        self.warnings.append(warning)
    
    def merge(self, other: "ValidationResult") -> None:
        """Merge another validation result into this one."""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        if other.errors:
            self.is_valid = False
    
    def get_all_issues(self) -> List[ValidationError]:
        """Get all errors and warnings."""
        return self.errors + self.warnings
    
    def get_error_summary(self) -> str:
        """Get a summary of validation errors."""
        if not self.errors and not self.warnings:
            return "No validation issues found"
        
        summary_parts = []
        
        if self.errors:
            summary_parts.append(f"{len(self.errors)} error(s)")
        
        if self.warnings:
            summary_parts.append(f"{len(self.warnings)} warning(s)")
        
        return f"Validation completed with {', '.join(summary_parts)}"
    
    def format_errors(self, include_warnings: bool = True) -> str:
        """Format all errors and warnings as a readable string."""
        lines = []
        
        if self.errors:
            lines.append("ERRORS:")
            for error in self.errors:
                lines.append(f"  - {error}")
        
        if include_warnings and self.warnings:
            if lines:
                lines.append("")
            lines.append("WARNINGS:")
            for warning in self.warnings:
                lines.append(f"  - {warning}")
        
        return "\n".join(lines) if lines else "No validation issues"


class AbstractValidator(ABC):
    """Abstract base class for configuration validators."""
    
    def __init__(self, name: Optional[str] = None):
        self.name = name or self.__class__.__name__
        self.logger = logging.getLogger(f"validator.{self.name}")
    
    @abstractmethod
    def validate(
        self, 
        config: Any, 
        context: Optional[ValidationContext] = None
    ) -> ValidationResult:
        """Validate the given configuration.
        
        Args:
            config: Configuration to validate
            context: Optional validation context
            
        Returns:
            Validation result with errors and warnings
        """
        pass
    
    def supports_config_type(self, config: Any) -> bool:
        """Check if this validator supports the given configuration type.
        
        Args:
            config: Configuration to check
            
        Returns:
            True if this validator can handle the config type
        """
        return True
    
    def get_validator_info(self) -> Dict[str, Any]:
        """Get information about this validator.
        
        Returns:
            Dictionary with validator metadata
        """
        return {
            "name": self.name,
            "type": self.__class__.__name__,
            "description": self.__doc__ or "No description available"
        }


class CompositeValidator(AbstractValidator):
    """Validator that combines multiple child validators."""
    
    def __init__(self, validators: List[AbstractValidator], name: Optional[str] = None):
        super().__init__(name or "CompositeValidator")
        self.validators = validators
        self.stop_on_first_error = False
    
    def validate(
        self, 
        config: Any, 
        context: Optional[ValidationContext] = None
    ) -> ValidationResult:
        """Validate using all child validators."""
        result = ValidationResult(context=context)
        
        for validator in self.validators:
            if not validator.supports_config_type(config):
                continue
            
            try:
                validator_result = validator.validate(config, context)
                result.merge(validator_result)
                
                # Stop on first error if configured
                if self.stop_on_first_error and not validator_result.is_valid:
                    break
                    
            except Exception as e:
                self.logger.error(f"Validator {validator.name} failed: {e}")
                result.add_error(
                    f"Validator {validator.name} encountered an error: {e}",
                    error_code="VALIDATOR_EXCEPTION"
                )
        
        return result
    
    def add_validator(self, validator: AbstractValidator) -> None:
        """Add a validator to the composite."""
        self.validators.append(validator)
    
    def remove_validator(self, validator_name: str) -> bool:
        """Remove a validator by name."""
        for i, validator in enumerate(self.validators):
            if validator.name == validator_name:
                del self.validators[i]
                return True
        return False
    
    def get_validator_info(self) -> Dict[str, Any]:
        """Get information about this composite validator."""
        info = super().get_validator_info()
        info["child_validators"] = [v.get_validator_info() for v in self.validators]
        info["stop_on_first_error"] = self.stop_on_first_error
        return info


class ConditionalValidator(AbstractValidator):
    """Validator that applies child validators based on conditions."""
    
    def __init__(self, name: Optional[str] = None):
        super().__init__(name or "ConditionalValidator")
        self.conditions: List[tuple] = []  # (condition_func, validator)
    
    def add_condition(
        self, 
        condition: callable, 
        validator: AbstractValidator
    ) -> None:
        """Add a conditional validator.
        
        Args:
            condition: Function that takes config and returns bool
            validator: Validator to apply if condition is true
        """
        self.conditions.append((condition, validator))
    
    def validate(
        self, 
        config: Any, 
        context: Optional[ValidationContext] = None
    ) -> ValidationResult:
        """Validate using applicable conditional validators."""
        result = ValidationResult(context=context)
        
        for condition, validator in self.conditions:
            try:
                if condition(config):
                    validator_result = validator.validate(config, context)
                    result.merge(validator_result)
            except Exception as e:
                self.logger.error(f"Condition check failed for {validator.name}: {e}")
                result.add_error(
                    f"Failed to evaluate condition for {validator.name}: {e}",
                    error_code="CONDITION_ERROR"
                )
        
        return result


class ValidationPipeline:
    """Pipeline for orchestrating multiple validation phases."""
    
    def __init__(self):
        self.phases: Dict[str, List[AbstractValidator]] = {}
        self.logger = logging.getLogger(__name__)
    
    def add_phase(self, phase_name: str, validators: List[AbstractValidator]) -> None:
        """Add a validation phase.
        
        Args:
            phase_name: Name of the validation phase
            validators: List of validators for this phase
        """
        self.phases[phase_name] = validators
    
    def validate_all_phases(
        self, 
        config: Any, 
        context: Optional[ValidationContext] = None
    ) -> Dict[str, ValidationResult]:
        """Validate configuration through all phases.
        
        Args:
            config: Configuration to validate
            context: Optional validation context
            
        Returns:
            Dictionary mapping phase names to validation results
        """
        results = {}
        
        for phase_name, validators in self.phases.items():
            phase_context = context
            if context:
                phase_context = ValidationContext(
                    source=context.source,
                    phase=phase_name,
                    metadata=context.metadata.copy()
                )
            
            composite_validator = CompositeValidator(validators, f"{phase_name}_validator")
            results[phase_name] = composite_validator.validate(config, phase_context)
        
        return results
    
    def get_overall_result(self, phase_results: Dict[str, ValidationResult]) -> ValidationResult:
        """Combine all phase results into a single result.
        
        Args:
            phase_results: Results from all validation phases
            
        Returns:
            Combined validation result
        """
        overall_result = ValidationResult()
        
        for phase_name, result in phase_results.items():
            overall_result.merge(result)
        
        return overall_result