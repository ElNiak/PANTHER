"""Pydantic-based configuration validator."""

from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, ValidationError as PydanticValidationError

from panther.config.models.base import ConfigModel
from panther.config.validators.base_validator import (
    AbstractValidator,
    ValidationContext,
    ValidationResult,
)


class PydanticValidator(AbstractValidator):
    """Validator that uses Pydantic models for validation."""
    
    def __init__(self, model_class: Type[ConfigModel], name: Optional[str] = None):
        super().__init__(name or f"PydanticValidator[{model_class.__name__}]")
        self.model_class = model_class
    
    def validate(
        self, 
        config: Any, 
        context: Optional[ValidationContext] = None
    ) -> ValidationResult:
        """Validate configuration using Pydantic model.
        
        Args:
            config: Configuration to validate (dict or ConfigModel)
            context: Optional validation context
            
        Returns:
            Validation result with converted Pydantic errors
        """
        result = ValidationResult(context=context)
        
        try:
            # Handle different input types
            if isinstance(config, dict):
                # Create model from dictionary
                model_instance = self.model_class.from_dict(config)
            elif isinstance(config, self.model_class):
                # Already the correct model type
                model_instance = config
            elif isinstance(config, BaseModel):
                # Convert from another Pydantic model
                model_instance = self.model_class.from_dict(config.dict())
            else:
                result.add_error(
                    f"Unsupported configuration type: {type(config)}",
                    error_code="UNSUPPORTED_TYPE"
                )
                return result
            
            # Validation passed if we get here
            self.logger.debug(f"Pydantic validation passed for {self.model_class.__name__}")
            
        except PydanticValidationError as e:
            # Convert Pydantic errors to our format
            self._convert_pydantic_errors(e, result)
        except Exception as e:
            result.add_error(
                f"Unexpected error during Pydantic validation: {e}",
                error_code="VALIDATION_EXCEPTION"
            )
        
        return result
    
    def _convert_pydantic_errors(
        self, 
        pydantic_error: PydanticValidationError, 
        result: ValidationResult
    ) -> None:
        """Convert Pydantic validation errors to our format.
        
        Args:
            pydantic_error: Pydantic validation error
            result: Validation result to add errors to
        """
        for error in pydantic_error.errors():
            # Build field path
            field_path = self._build_field_path(error.get("loc", []))
            
            # Get error details
            error_type = error.get("type", "validation_error")
            message = error.get("msg", "Validation failed")
            value = error.get("input")
            
            # Generate suggestion based on error type
            suggestion = self._generate_suggestion(error_type, error, field_path)
            
            # Map Pydantic error types to our error codes
            error_code = self._map_error_code(error_type)
            
            result.add_error(
                message=message,
                field_path=field_path,
                value=value,
                suggestion=suggestion,
                error_code=error_code
            )
    
    def _build_field_path(self, location: List[Any]) -> str:
        """Build a human-readable field path from Pydantic location.
        
        Args:
            location: Pydantic error location
            
        Returns:
            Dot-separated field path
        """
        if not location:
            return "root"
        
        path_parts = []
        for part in location:
            if isinstance(part, str):
                path_parts.append(part)
            elif isinstance(part, int):
                path_parts.append(f"[{part}]")
            else:
                path_parts.append(str(part))
        
        return ".".join(path_parts)
    
    def _generate_suggestion(
        self, 
        error_type: str, 
        error: Dict[str, Any], 
        field_path: str
    ) -> Optional[str]:
        """Generate helpful suggestions based on error type.
        
        Args:
            error_type: Pydantic error type
            error: Full error dictionary
            field_path: Field path where error occurred
            
        Returns:
            Suggestion string or None
        """
        suggestions = {
            "missing": f"Add the required field '{field_path}'",
            "extra_forbidden": f"Remove the extra field '{field_path}'",
            "type_error.integer": f"Provide an integer value for '{field_path}'",
            "type_error.float": f"Provide a numeric value for '{field_path}'",
            "type_error.bool": f"Provide a boolean value (true/false) for '{field_path}'",
            "type_error.str": f"Provide a string value for '{field_path}'",
            "type_error.list": f"Provide a list value for '{field_path}'",
            "type_error.dict": f"Provide a dictionary value for '{field_path}'",
            "value_error.missing": f"Provide a value for '{field_path}'",
            "value_error.number.not_ge": f"Use a value >= {error.get('ctx', {}).get('limit_value', 'minimum')}",
            "value_error.number.not_le": f"Use a value <= {error.get('ctx', {}).get('limit_value', 'maximum')}",
            "value_error.str.regex": f"Ensure '{field_path}' matches the required format",
            "value_error.email": f"Provide a valid email address for '{field_path}'",
            "value_error.url": f"Provide a valid URL for '{field_path}'",
        }
        
        return suggestions.get(error_type)
    
    def _map_error_code(self, pydantic_error_type: str) -> str:
        """Map Pydantic error types to our error codes.
        
        Args:
            pydantic_error_type: Pydantic error type string
            
        Returns:
            Our error code
        """
        error_code_mapping = {
            "missing": "MISSING_FIELD",
            "extra_forbidden": "EXTRA_FIELD",
            "type_error": "TYPE_ERROR",
            "value_error": "VALUE_ERROR",
            "assertion_error": "ASSERTION_ERROR",
        }
        
        # Try exact match first
        if pydantic_error_type in error_code_mapping:
            return error_code_mapping[pydantic_error_type]
        
        # Try prefix matches
        for prefix, code in error_code_mapping.items():
            if pydantic_error_type.startswith(prefix):
                return code
        
        return "VALIDATION_ERROR"
    
    def supports_config_type(self, config: Any) -> bool:
        """Check if this validator supports the configuration type."""
        return (
            isinstance(config, dict) or 
            isinstance(config, self.model_class) or
            isinstance(config, BaseModel)
        )
    
    def get_validator_info(self) -> Dict[str, Any]:
        """Get information about this validator."""
        info = super().get_validator_info()
        info.update({
            "model_class": self.model_class.__name__,
            "model_fields": list(self.model_class.__fields__.keys()) if hasattr(self.model_class, '__fields__') else [],
            "validation_type": "pydantic"
        })
        return info


class MultiModelPydanticValidator(AbstractValidator):
    """Pydantic validator that can handle multiple model types."""
    
    def __init__(self, model_classes: Dict[str, Type[ConfigModel]], name: Optional[str] = None):
        super().__init__(name or "MultiModelPydanticValidator")
        self.model_classes = model_classes
        self.validators = {
            key: PydanticValidator(model_class, f"PydanticValidator[{key}]")
            for key, model_class in model_classes.items()
        }
    
    def validate(
        self, 
        config: Any, 
        context: Optional[ValidationContext] = None
    ) -> ValidationResult:
        """Validate using the appropriate model based on configuration content."""
        result = ValidationResult(context=context)
        
        # Determine which model to use
        model_key = self._determine_model_type(config)
        
        if model_key not in self.validators:
            result.add_error(
                f"Cannot determine configuration type. Available types: {list(self.model_classes.keys())}",
                error_code="UNKNOWN_CONFIG_TYPE"
            )
            return result
        
        # Use the appropriate validator
        validator = self.validators[model_key]
        return validator.validate(config, context)
    
    def _determine_model_type(self, config: Any) -> Optional[str]:
        """Determine which model type to use based on configuration content.
        
        Args:
            config: Configuration to analyze
            
        Returns:
            Model key or None if cannot determine
        """
        if not isinstance(config, dict):
            return None
        
        # Simple heuristics based on common keys
        # This can be enhanced with more sophisticated detection
        key_patterns = {
            "experiment": ["tests", "name", "description"],
            "global": ["logging", "paths", "docker", "observers"],
            "service": ["implementation", "protocol", "timeout"],
            "test": ["network_environment", "services", "steps"],
        }
        
        config_keys = set(config.keys())
        
        # Find the best match
        best_match = None
        best_score = 0
        
        for model_key, pattern_keys in key_patterns.items():
            if model_key in self.model_classes:
                score = len(set(pattern_keys) & config_keys)
                if score > best_score:
                    best_score = score
                    best_match = model_key
        
        return best_match
    
    def supports_config_type(self, config: Any) -> bool:
        """Check if any of the model validators support the config type."""
        return any(
            validator.supports_config_type(config) 
            for validator in self.validators.values()
        )
    
    def get_validator_info(self) -> Dict[str, Any]:
        """Get information about this multi-model validator."""
        info = super().get_validator_info()
        info.update({
            "supported_models": list(self.model_classes.keys()),
            "validators": {
                key: validator.get_validator_info() 
                for key, validator in self.validators.items()
            }
        })
        return info