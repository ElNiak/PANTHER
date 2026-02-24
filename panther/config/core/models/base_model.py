"""Base model for all configuration models."""

from typing import Any, Dict

from omegaconf import DictConfig, OmegaConf

from ..base import BaseConfig


class BaseUnifiedModel(BaseConfig):
    """Base model for unified configuration models.

    This class extends BaseConfig with additional functionality
    specific to the unified configuration system.
    """

    class Config:
        extra = "allow"  # Allow extra fields for flexibility
        validate_assignment = True
        use_enum_values = True
        arbitrary_types_allowed = True
        json_schema_extra = {
            "additionalProperties": True  # Allow additional properties in JSON schema
        }

    def __init__(self, **data):
        """Initialize with automatic OmegaConf conversion."""
        # Pre-process data to handle OmegaConf inputs
        if len(data) == 1 and isinstance(next(iter(data.values())), DictConfig):
            # Handle case where DictConfig is passed as single argument
            omega_config = next(iter(data.values()))
            data = OmegaConf.to_container(omega_config, resolve=True)

        super().__init__(**data)

    def to_dict(
        self, exclude_none: bool = True, exclude_defaults: bool = False
    ) -> Dict[str, Any]:
        """Convert to dictionary with additional options.

        Args:
            exclude_none: Whether to exclude None values
            exclude_defaults: Whether to exclude default values

        Returns:
            Dictionary representation
        """
        # Use model_dump for Pydantic v2 compatibility and exclude internal fields
        excluded_fields = {
            "omega_config",
            "model_fields",
            "model_config",
            "model_fields_set",
        }
        try:
            # Pydantic v2
            return self.model_dump(
                exclude_none=exclude_none,
                exclude_defaults=exclude_defaults,
                exclude=excluded_fields,
            )
        except AttributeError:
            # Pydantic v1 fallback
            return self.dict(
                exclude_none=exclude_none,
                exclude_defaults=exclude_defaults,
                exclude=excluded_fields,
            )

    def update_from_dict(self, data: Dict[str, Any]) -> "BaseUnifiedModel":
        """Update model from dictionary.

        Args:
            data: Dictionary with updates

        Returns:
            Updated model instance
        """
        # Merge with current data
        current = self.to_dict(exclude_none=False)
        merged = OmegaConf.merge(OmegaConf.create(current), OmegaConf.create(data))
        merged_dict = OmegaConf.to_container(merged, resolve=True)

        # Create new instance
        return self.__class__(**merged_dict)

    def has_field(self, field_path: str) -> bool:
        """Check if a field exists using dot notation.

        Args:
            field_path: Dot-separated field path

        Returns:
            True if field exists
        """
        try:
            self.get_field(field_path)
            return True
        except:
            return False

    def clone(self) -> "BaseUnifiedModel":
        """Create a deep copy of the model.

        Returns:
            Cloned instance
        """
        return self.__class__(**self.to_dict(exclude_none=False))
