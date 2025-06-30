"""Base configuration class combining Pydantic and OmegaConf features."""

import json
from abc import ABC
from pathlib import Path
from typing import Any, Dict, Optional, Type, TypeVar, Union

import yaml
from omegaconf import DictConfig, OmegaConf
from pydantic import BaseModel, Field

T = TypeVar("T", bound="BaseConfig")


class BaseConfig(BaseModel, ABC):
    """Base configuration class combining Pydantic BaseModel and OmegaConf features.

    This class provides:
    - Pydantic validation and type checking
    - OmegaConf interpolation and merging
    - YAML/JSON serialization
    - Deep merging with conflict resolution
    """

    class Config:
        extra = "allow"  # Allow extra fields for flexibility
        validate_assignment = True
        use_enum_values = True
        arbitrary_types_allowed = True

    # Internal OmegaConf representation
    omega_config: Optional[DictConfig] = Field(
        None, exclude=True, alias="_omega_config"
    )

    def __init__(self, **data):
        """Initialize with support for OmegaConf interpolation."""
        super().__init__(**data)
        # Create OmegaConf representation for interpolation
        self.omega_config = OmegaConf.create(self.to_dict())

    def validate_config(self) -> "BaseConfig":
        """Perform full validation with context.

        Returns:
            Self for chaining

        Raises:
            ValidationError: If validation fails
        """
        # Pydantic validation happens automatically
        # Additional context-aware validation can be added in subclasses
        return self

    def to_omega(self) -> DictConfig:
        """Convert to OmegaConf DictConfig.

        Returns:
            OmegaConf DictConfig representation
        """
        if self.omega_config is None:
            self.omega_config = OmegaConf.create(self.to_dict())
        return self.omega_config

    @classmethod
    def from_omega(cls: Type[T], config: DictConfig) -> T:
        """Create instance from OmegaConf DictConfig.

        Args:
            config: OmegaConf DictConfig

        Returns:
            New instance of this class
        """
        # Convert to dict and create instance
        data = OmegaConf.to_container(config, resolve=True)
        return cls(**data)

    def to_dict(self, exclude_none: bool = True) -> Dict[str, Any]:
        """Convert to standard dictionary.

        Args:
            exclude_none: Whether to exclude None values

        Returns:
            Dictionary representation
        """
        # Use model_dump instead of dict() for Pydantic v2 compatibility
        # and exclude internal fields like omega_config
        excluded_fields = {
            "omega_config",
            "model_fields",
            "model_config",
            "model_fields_set",
        }
        try:
            # Pydantic v2
            return self.model_dump(exclude_none=exclude_none, exclude=excluded_fields)
        except AttributeError:
            # Pydantic v1 fallback
            return self.dict(exclude_none=exclude_none, exclude=excluded_fields)

    def to_yaml(self, resolve: bool = True) -> str:
        """Convert to YAML string.

        Args:
            resolve: Whether to resolve interpolations

        Returns:
            YAML string representation
        """
        omega_config = self.to_omega()
        if resolve:
            omega_config = OmegaConf.to_container(omega_config, resolve=True)
            omega_config = OmegaConf.create(omega_config)
        return OmegaConf.to_yaml(omega_config)

    def to_json(self, indent: Optional[int] = 2) -> str:
        """Convert to JSON string.

        Args:
            indent: JSON indentation level

        Returns:
            JSON string representation
        """
        import json

        return json.dumps(self.to_dict(), indent=indent)

    def merge(
        self, other: Union["BaseConfig", Dict[str, Any], DictConfig]
    ) -> "BaseConfig":
        """Deep merge with another configuration.

        Args:
            other: Configuration to merge with

        Returns:
            New merged configuration instance
        """
        # Convert everything to OmegaConf for merging
        self_omega = self.to_omega()

        if isinstance(other, BaseConfig):
            other_omega = other.to_omega()
        elif isinstance(other, DictConfig):
            other_omega = other
        else:
            other_omega = OmegaConf.create(other)

        # Merge using OmegaConf
        merged = OmegaConf.merge(self_omega, other_omega)

        # Create new instance from merged config
        return self.__class__.from_omega(merged)

    def interpolate(self) -> "BaseConfig":
        """Resolve all ${} interpolations.

        Returns:
            New instance with resolved interpolations
        """
        omega_config = self.to_omega()
        resolved = OmegaConf.to_container(omega_config, resolve=True)
        return self.__class__(**resolved)

    def get_schema(self) -> Dict[str, Any]:
        """Get JSON schema for this configuration.

        Returns:
            JSON schema dictionary
        """
        return self.model_json_schema()

    def save(self, path: Union[str, Path], format: str = "yaml") -> None:
        """Save configuration to file.

        Args:
            path: File path to save to
            format: Output format ('yaml' or 'json')
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        if format == "yaml":
            content = self.to_yaml()
        elif format == "json":
            content = self.to_json()
        else:
            raise ValueError(f"Unsupported format: {format}")

        path.write_text(content)

    @classmethod
    def load(cls: Type[T], path: Union[str, Path]) -> T:
        """Load configuration from file.

        Args:
            path: File path to load from

        Returns:
            New instance loaded from file
        """
        path = Path(path)

        if path.suffix in {".yaml", ".yml"}:
            with open(path) as f:
                data = yaml.safe_load(f)
        elif path.suffix == ".json":
            with open(path) as f:
                data = json.load(f)
        else:
            raise ValueError(f"Unsupported file type: {path.suffix}")

        return cls(**data)

    def update_field(self, field_path: str, value: Any) -> "BaseConfig":
        """Update a nested field using dot notation.

        Args:
            field_path: Dot-separated field path (e.g., 'logging.level')
            value: New value for the field

        Returns:
            New instance with updated field
        """
        omega_config = self.to_omega()
        OmegaConf.update(omega_config, field_path, value)
        return self.__class__.from_omega(omega_config)

    def get_field(self, field_path: str, default: Any = None) -> Any:
        """Get a nested field using dot notation.

        Args:
            field_path: Dot-separated field path
            default: Default value if field not found

        Returns:
            Field value or default
        """
        omega_config = self.to_omega()
        return OmegaConf.select(omega_config, field_path, default=default)
