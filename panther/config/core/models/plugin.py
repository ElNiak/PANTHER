"""Plugin configuration models."""

import logging
import os
from pathlib import Path
from typing import Any, ClassVar, Dict, Optional, Type, TypeVar

from pydantic import Field, field_validator

from .base_model import BaseUnifiedModel

T = TypeVar("T", bound="BaseUnifiedModel")


class BasePluginConfig(BaseUnifiedModel):
    """Base configuration for all plugins.

    This class provides common configuration fields and functionality
    that all plugin configurations should inherit from.
    """

    # Common fields for all plugins
    enabled: bool = Field(True, description="Whether the plugin is enabled")
    version: Optional[str] = Field(None, description="Plugin version")
    priority: int = Field(100, description="Plugin execution priority")

    # Allow extra fields for plugin-specific configuration
    # (inherited from BaseUnifiedModel Config)

    def validate_plugin_specific(self) -> None:
        """Override this method to add plugin-specific validation."""
        pass

    def get_plugin_type(self) -> str:
        """Get the plugin type based on class name.

        Returns:
            Plugin type string
        """
        class_name = self.__class__.__name__
        if class_name.endswith("Config"):
            return class_name[:-6].lower()
        return class_name.lower()

    def to_dict(self, **kwargs) -> Dict[str, Any]:
        """Convert to dictionary with plugin-specific handling.

        Returns:
            Dictionary representation
        """
        data = super().to_dict(**kwargs)
        # Include extra fields but exclude Pydantic internals
        excluded_keys = {
            "model_fields",
            "model_config",
            "model_fields_set",
            "__dict__",
            "__weakref__",
        }
        for key in self.__dict__:
            if (
                key not in data
                and not key.startswith("_")
                and key not in excluded_keys
                and not hasattr(getattr(self, key), "__func__")
            ):  # Exclude methods
                try:
                    value = getattr(self, key)
                    # Only include serializable values
                    if value is not None:
                        data[key] = value
                except AttributeError:
                    pass
        return data


class ExecutionEnvironmentPluginConfig(BasePluginConfig):
    """Base configuration for execution environment plugins."""

    # Common fields for execution environments
    output_format: str = Field("json", description="Output format for results")
    collect_metrics: bool = Field(True, description="Whether to collect metrics")

    def get_plugin_type(self) -> str:
        """Return execution environment plugin type."""
        return "execution_environment"

    def get_plugin_config(self, config_class: Type[T], validate: bool = True) -> T:
        """Get typed plugin configuration with defaults.

        For plugin configs, this method provides compatibility with environment configs
        by returning self if the config_class matches exactly, or a new instance with defaults.

        Args:
            config_class: The plugin configuration class
            validate: Whether to validate (currently ignored for plugin configs)

        Returns:
            Typed plugin configuration instance
        """
        # If the requested config class matches our exact type, return self
        if self.__class__ == config_class:
            return self

        # Otherwise, create a new instance with defaults
        return config_class()


class NetworkEnvironmentPluginConfig(BasePluginConfig):
    """Base configuration for network environment plugins."""

    # Common fields for network environments
    network_name: str = Field("panther_network", description="Network name")
    subnet: Optional[str] = Field(None, description="Network subnet")
    enable_ipv6: bool = Field(False, description="Enable IPv6 support")

    def get_plugin_type(self) -> str:
        """Return network environment plugin type."""
        return "network_environment"


class ServicePluginConfig(BasePluginConfig):
    """Base configuration for service plugins (IUT and testers)."""

    VERSION_CLASS: ClassVar[Optional[type]] = None

    type: str = Field(..., description="Implementation type")

    # Common fields for services
    docker_image: Optional[str] = Field(None, description="Docker image name")
    build_from_source: bool = Field(True, description="Build from source")
    source_repository: Optional[str] = Field(None, description="Source repository URL")

    @field_validator("type", mode="before", check_fields=False)
    @classmethod
    def validate_type(cls, v):
        """Convert string to ImplementationType enum with case-insensitive handling.

        Note: check_fields=False allows inheritance by subclasses that define 'type' field.
        """
        if isinstance(v, str):
            # Case-insensitive mapping to enum values
            v_upper = v.upper()
            if v_upper == "IUT":
                return "iut"
            elif v_upper == "TESTERS":
                return "testers"
            else:
                return v.lower()
        return v

    @classmethod
    def load_version(
        cls,
        version_configs_dir: Optional[str] = None,
        version: Optional[str] = None,
        protocol_version_override: Optional[str] = None,
    ):
        """Generic version loading using VERSION_CLASS.

        Subclasses set ``VERSION_CLASS`` to their VersionBase subclass.
        Default ``version_configs_dir`` is ``version_configs/`` next to the
        subclass's ``config_schema.py``.

        Args:
            version_configs_dir: Directory containing version YAML files.
            version: Specific version to load (e.g. ``'rfc9000'``).
            protocol_version_override: Protocol version from experiment config.

        Returns:
            VERSION_CLASS instance, or ``None`` if VERSION_CLASS is not set.
        """
        if cls.VERSION_CLASS is None:
            # Intentionally returns None instead of raising NotImplementedError.
            # Plugins like aioquic that don't set VERSION_CLASS use this in
            # default_factory=lambda: SomeConfig.load_version(), which executes
            # at import time.  Raising would break import of those plugins.
            return None

        import yaml

        from ..utils.merge import deep_merge

        # Determine directory
        if version_configs_dir is None:
            import inspect

            src_file = inspect.getfile(cls)
            version_configs_dir = str(
                Path(os.path.dirname(src_file)) / "version_configs"
            )

        effective_version = protocol_version_override or version

        if effective_version:
            version_path = os.path.join(
                version_configs_dir, f"{effective_version}.yaml"
            )
            if not os.path.exists(version_path):
                raise FileNotFoundError(
                    f"Version config file not found: {version_path}"
                )
            with open(version_path) as f:
                raw_dict = yaml.safe_load(f) or {}
        else:
            # Load first YAML found (sorted for determinism)
            if not os.path.exists(version_configs_dir):
                logging.warning(
                    "Version configs directory %s not found, using defaults",
                    version_configs_dir,
                )
                return cls.VERSION_CLASS()
            version_files = sorted(
                f for f in os.listdir(version_configs_dir) if f.endswith(".yaml")
            )
            if not version_files:
                logging.warning(
                    "No version files found in %s, using defaults", version_configs_dir
                )
                return cls.VERSION_CLASS()
            version_path = os.path.join(version_configs_dir, version_files[0])
            with open(version_path) as f:
                raw_dict = yaml.safe_load(f) or {}

        # Merge with defaults using pure dict merge
        default_dict = cls.VERSION_CLASS().model_dump()
        merged = deep_merge(default_dict, raw_dict)
        return cls.VERSION_CLASS(**merged)

    @classmethod
    def create_with_protocol_context(cls, protocol=None):
        """Create plugin config instance with optional protocol context.

        If ``VERSION_CLASS`` is set and *protocol* carries a version, the
        matching version config is loaded automatically.

        Args:
            protocol: Optional protocol configuration for context-aware creation

        Returns:
            Plugin configuration instance
        """
        if (
            cls.VERSION_CLASS is not None
            and protocol
            and getattr(protocol, "version", None)
        ):
            try:
                version_config = cls.load_version(
                    protocol_version_override=protocol.version
                )
                return cls(version=version_config)
            except (FileNotFoundError, ValueError) as e:
                raise ValueError(
                    f"Could not load protocol version {protocol.version}: {e}"
                ) from e
        return cls()

    def get_plugin_type(self) -> str:
        """Return service plugin type."""
        return "service"


class ProtocolPluginConfig(BasePluginConfig):
    """Base configuration for protocol plugins."""

    # Common fields for protocols
    protocol_version: str = Field(..., description="Protocol version")
    default_port: int = Field(..., description="Default port number")
    supports_tls: bool = Field(True, description="Whether protocol supports TLS")

    def get_plugin_type(self) -> str:
        """Return protocol plugin type."""
        return "protocol"
