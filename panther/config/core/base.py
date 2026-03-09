"""Base configuration class using pure Pydantic v2."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Type, TypeVar, Union

import yaml
from pydantic import BaseModel, ConfigDict

from .utils.merge import deep_merge, dot_notation_update

T = TypeVar("T", bound="BaseConfig")


class BaseConfig(BaseModel):
    """Base for all PANTHER configuration models (pure Pydantic v2).

    Hierarchy::

        BaseConfig
        ├── GlobalConfig, LoggingConfig, PathsConfig, DockerConfig, ...
        ├── ExperimentConfig, TestConfig, StepsConfig, ExperimentMetadata
        ├── ServiceConfig, ProtocolConfig, NetworkConfig, ImplementationConfig
        ├── EnvironmentConfig
        │   ├── NetworkEnvironmentConfig
        │   └── ExecutionEnvironmentConfig
        ├── ObserversConfig, BaseObserverConfig, ...
        ├── BasePluginConfig
        │   ├── ServicePluginConfig   (IUT/tester plugins)
        │   ├── NetworkEnvironmentPluginConfig
        │   ├── ExecutionEnvironmentPluginConfig
        │   └── ProtocolPluginConfig
        └── BaseProtocolConfig (ABC)
            ├── ClientServerProtocolConfig
            └── PeerToPeerProtocolConfig

    model_config settings:
        - ``extra="allow"`` — plugins add custom fields without schema changes
        - ``validate_assignment=True`` — mutations are validated
        - ``use_enum_values=True`` — enums serialize as values
        - ``arbitrary_types_allowed=True`` — accepts non-standard types

    Methods:
        Serialization: to_dict, to_yaml, to_json, save, load
        Merging: merge, update_from_dict
        Field access: get_field, update_field, has_field
        Introspection: get_schema, validate_config, check_extra_fields, clone
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

    def to_dict(
        self, exclude_none: bool = True, exclude_defaults: bool = False
    ) -> Dict[str, Any]:
        """Convert to standard dictionary."""
        excluded_fields = {"model_fields", "model_config", "model_fields_set"}
        return self.model_dump(
            exclude_none=exclude_none,
            exclude_defaults=exclude_defaults,
            exclude=excluded_fields,
        )

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

    def update_from_dict(self, data: Dict[str, Any]) -> "BaseConfig":
        """Update model from dictionary."""
        current = self.to_dict(exclude_none=False)
        merged = deep_merge(current, data)
        return self.__class__(**merged)

    def has_field(self, field_path: str) -> bool:
        """Check if a field exists using dot notation."""
        sentinel = object()
        return self.get_field(field_path, default=sentinel) is not sentinel

    def clone(self) -> "BaseConfig":
        """Create a deep copy of the model."""
        return self.__class__(**self.to_dict(exclude_none=False))

    @classmethod
    def check_extra_fields(
        cls,
        data: Dict[str, Any],
        context_label: str = "",
        exclude: Optional[Set[str]] = None,
    ) -> List[str]:
        """Check for undeclared fields and log warnings.

        Args:
            data: Raw dictionary from YAML or user input.
            context_label: Label for log messages; defaults to class name.
            exclude: Field names to skip (e.g. builder-injected fields).

        Returns:
            List of extra field names found.
        """
        from .utils.field_partition import warn_extra_fields

        return warn_extra_fields(
            data, cls, context_label=context_label or cls.__name__, exclude=exclude
        )
