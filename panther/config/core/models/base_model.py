"""Base model for all configuration models."""

from typing import Any, Dict

from ..base import BaseConfig
from ..utils.merge import deep_merge


class BaseUnifiedModel(BaseConfig):
    """Base model for unified configuration models.

    Extends BaseConfig with additional functionality
    specific to the unified configuration system.
    """

    def to_dict(
        self, exclude_none: bool = True, exclude_defaults: bool = False
    ) -> Dict[str, Any]:
        """Convert to dictionary with additional options."""
        excluded_fields = {"model_fields", "model_config", "model_fields_set"}
        return self.model_dump(
            exclude_none=exclude_none,
            exclude_defaults=exclude_defaults,
            exclude=excluded_fields,
        )

    def update_from_dict(self, data: Dict[str, Any]) -> "BaseUnifiedModel":
        """Update model from dictionary."""
        current = self.to_dict(exclude_none=False)
        merged = deep_merge(current, data)
        return self.__class__(**merged)

    def has_field(self, field_path: str) -> bool:
        """Check if a field exists using dot notation."""
        try:
            self.get_field(field_path)
            return True
        except Exception:
            return False

    def clone(self) -> "BaseUnifiedModel":
        """Create a deep copy of the model."""
        return self.__class__(**self.to_dict(exclude_none=False))
