"""Base configuration class using pure Pydantic v2."""

import json
from pathlib import Path
from typing import Any, Dict, Optional, Type, TypeVar, Union

import yaml
from pydantic import BaseModel, ConfigDict

from .utils.merge import deep_merge, dot_notation_update

T = TypeVar("T", bound="BaseConfig")


class BaseConfig(BaseModel):
    """Base configuration class using pure Pydantic v2.

    Provides:
    - Pydantic validation and type checking
    - YAML/JSON serialization
    - Deep merging via pure dict operations
    - Dot-notation field access
    """

    model_config = ConfigDict(
        extra="allow",
        validate_assignment=True,
        use_enum_values=True,
        arbitrary_types_allowed=True,
    )

    def validate_config(self) -> "BaseConfig":
        """Perform full validation with context."""
        return self

    def to_dict(self, exclude_none: bool = True) -> Dict[str, Any]:
        """Convert to standard dictionary."""
        excluded_fields = {"model_fields", "model_config", "model_fields_set"}
        return self.model_dump(exclude_none=exclude_none, exclude=excluded_fields)

    def to_yaml(self, resolve: bool = True) -> str:
        """Convert to YAML string."""
        return yaml.dump(self.to_dict(), default_flow_style=False, sort_keys=False)

    def to_json(self, indent: Optional[int] = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def merge(self, other: Union["BaseConfig", Dict[str, Any]]) -> "BaseConfig":
        """Deep merge with another configuration."""
        self_dict = self.to_dict(exclude_none=False)
        if isinstance(other, BaseConfig):
            other_dict = other.to_dict(exclude_none=False)
        else:
            other_dict = other
        merged = deep_merge(self_dict, other_dict)
        return self.__class__(**merged)

    def get_schema(self) -> Dict[str, Any]:
        """Get JSON schema for this configuration."""
        return self.model_json_schema()

    def save(self, path: Union[str, Path], format: str = "yaml") -> None:
        """Save configuration to file."""
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
        """Load configuration from file."""
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
        """Update a nested field using dot notation."""
        data = self.to_dict(exclude_none=False)
        dot_notation_update(data, field_path, value)
        return self.__class__(**data)

    def get_field(self, field_path: str, default: Any = None) -> Any:
        """Get a nested field using dot notation."""
        data = self.to_dict(exclude_none=False)
        keys = field_path.split(".")
        current = data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current
