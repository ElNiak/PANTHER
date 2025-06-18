"""Base configuration model with common functionality."""

from typing import Any, Dict, Optional

from omegaconf import DictConfig, OmegaConf
from pydantic import BaseModel, Extra


class ConfigModel(BaseModel):
    """Base configuration model with common functionality."""

    class Config:
        """Pydantic configuration."""

        extra = Extra.forbid  # Strict validation - no extra fields allowed
        validate_assignment = True  # Validate on assignment
        use_enum_values = False  # Keep enums as enums, not their values
        arbitrary_types_allowed = True  # Allow DictConfig types

    @classmethod
    def from_omega(cls, omega_conf: DictConfig) -> "ConfigModel":
        """Create model instance from OmegaConf DictConfig.

        Args:
            omega_conf: OmegaConf DictConfig instance

        Returns:
            Model instance with validated data
        """
        # Convert to container, preserving structure
        data = OmegaConf.to_container(omega_conf, resolve=True)
        return cls(**data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConfigModel":
        """Create model instance from dictionary.

        Args:
            data: Dictionary with configuration data

        Returns:
            Model instance with validated data
        """
        return cls(**data)

    def to_omega(self) -> DictConfig:
        """Convert model to OmegaConf DictConfig.

        Returns:
            OmegaConf DictConfig representation
        """
        return OmegaConf.create(self.dict())

    def to_dataclass(self, dataclass_type: type) -> Any:
        """Convert model to dataclass for backward compatibility.

        Args:
            dataclass_type: Target dataclass type

        Returns:
            Dataclass instance
        """
        from dataclasses import fields

        data = self.dict()
        kwargs = {}

        # Map fields from model to dataclass
        for field in fields(dataclass_type):
            if field.name in data:
                value = data[field.name]

                # Handle nested models
                if isinstance(value, BaseModel):
                    value = value.dict()

                kwargs[field.name] = value

        return dataclass_type(**kwargs)

    def merge_with(self, other: Optional[Dict[str, Any]]) -> "ConfigModel":
        """Merge this config with another dictionary.

        Args:
            other: Dictionary to merge with

        Returns:
            New model instance with merged data
        """
        if not other:
            return self

        # Convert to OmegaConf for merging
        self_omega = self.to_omega()
        other_omega = OmegaConf.create(other)

        # Merge configurations
        merged = OmegaConf.merge(self_omega, other_omega)

        # Create new instance
        return self.__class__.from_omega(merged)