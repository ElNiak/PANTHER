"""Configuration loaders for the unified system."""

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml
from omegaconf import DictConfig, OmegaConf

from panther.core.utils.logging_mixin import LoggerMixin


class BaseLoader(LoggerMixin, ABC):
    """Base class for configuration loaders."""

    def __init__(self, enable_cache: bool = True):
        """Initialize loader.

        Args:
            enable_cache: Whether to enable caching
        """
        super().__init__()
        self.enable_cache = enable_cache
        self._cache: Dict[str, Any] = {}

    @abstractmethod
    def load(self, source: Any) -> Dict[str, Any]:
        """Load configuration from source.

        Args:
            source: Configuration source

        Returns:
            Loaded configuration dictionary
        """
        pass

    def clear_cache(self):
        """Clear the loader cache."""
        self._cache.clear()


class YAMLLoader(BaseLoader):
    """YAML configuration loader with interpolation support."""

    def load(self, source: Union[str, Path]) -> Dict[str, Any]:
        """Load YAML configuration with interpolation support.

        Args:
            source: Path to YAML file

        Returns:
            Loaded configuration dictionary
        """
        path = Path(source)

        # Check cache
        if self.enable_cache and str(path) in self._cache:
            self.logger.debug(f"Loading from cache: {path}")
            return self._cache[str(path)]

        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")

        self.logger.info(f"Loading YAML configuration from {path}")

        try:
            with open(path, "r") as f:
                # Load as OmegaConf to support interpolation
                omega_config = OmegaConf.load(f)

                # Convert to regular dict but keep interpolations unresolved
                config = OmegaConf.to_container(omega_config, resolve=False)

                # Cache if enabled
                if self.enable_cache:
                    self._cache[str(path)] = config

                return config
        except Exception as e:
            raise ValueError(f"Failed to load YAML file {path}: {e}")

    def load_with_includes(self, source: Union[str, Path]) -> Dict[str, Any]:
        """Load YAML with support for includes.

        Args:
            source: Path to YAML file

        Returns:
            Loaded configuration with includes resolved
        """
        config = self.load(source)

        # Handle includes
        if "_include" in config:
            includes = config.pop("_include")
            if isinstance(includes, str):
                includes = [includes]

            base_dir = Path(source).parent
            for include in includes:
                include_path = base_dir / include
                include_config = self.load_with_includes(include_path)

                # Merge included config
                config = OmegaConf.merge(
                    OmegaConf.create(include_config), OmegaConf.create(config)
                )
                config = OmegaConf.to_container(config, resolve=False)

        return config


class VersionLoader(BaseLoader):
    """Dynamic version configuration loader."""

    def __init__(self, plugin_dir: Path, enable_cache: bool = True):
        """Initialize version loader.

        Args:
            plugin_dir: Plugin directory path
            enable_cache: Whether to enable caching
        """
        super().__init__(enable_cache)
        self.plugin_dir = plugin_dir
        self._version_registry: Dict[str, Dict[str, Any]] = {}

    def load(self, source: Any) -> Dict[str, Any]:
        """Not used directly for version loader."""
        raise NotImplementedError(
            "Use discover_versions or load_version_config instead"
        )

    def discover_versions(self, protocol: Optional[str] = None) -> Dict[str, List[str]]:
        """Discover available versions for protocols.

        Args:
            protocol: Optional protocol to filter by

        Returns:
            Dictionary mapping protocol names to version lists
        """
        cache_key = f"versions_{protocol or 'all'}"

        if self.enable_cache and cache_key in self._cache:
            return self._cache[cache_key]

        self.logger.info(f"Discovering versions for protocol: {protocol or 'all'}")

        versions = {}

        # Scan protocol directories
        protocols_dir = self.plugin_dir / "protocols"
        if protocols_dir.exists():
            for category in ["client_server", "peer_to_peer"]:
                category_dir = protocols_dir / category
                if category_dir.exists():
                    for proto_dir in category_dir.iterdir():
                        if proto_dir.is_dir():
                            proto_name = proto_dir.name

                            if protocol and proto_name != protocol:
                                continue

                            # Look for version files
                            proto_versions = self._scan_for_versions(proto_dir)
                            if proto_versions:
                                versions[proto_name] = proto_versions

        # Cache results
        if self.enable_cache:
            self._cache[cache_key] = versions

        return versions

    def load_version_config(
        self, impl_name: str, impl_type: str, protocol: str, version: str
    ) -> Optional[Dict[str, Any]]:
        """Load configuration for a specific version.

        Args:
            impl_name: Implementation name
            impl_type: Implementation type
            protocol: Protocol name
            version: Version identifier

        Returns:
            Version configuration or None
        """
        # Check registry first
        registry_key = f"{protocol}:{version}"
        if registry_key in self._version_registry:
            return self._version_registry[registry_key]

        # Try to load from file
        version_config = self._load_version_file(
            impl_name, impl_type, protocol, version
        )

        if version_config:
            self._version_registry[registry_key] = version_config

        return version_config

    def _scan_for_versions(self, directory: Path) -> List[str]:
        """Scan directory for version information.

        Args:
            directory: Directory to scan

        Returns:
            List of discovered versions
        """
        versions = []

        # Look for versions subdirectory
        versions_dir = directory / "versions"
        self.logger.debug(f"Scanning for versions in: {versions_dir}")
        if versions_dir.exists():
            versions.extend(
                item.stem
                for item in versions_dir.iterdir()
                if item.suffix in [".yaml", ".yml", ".json"]
            )
        # Look for version files in config directory
        config_dir = directory / "config"
        self.logger.debug(f"Scanning for version config files in: {config_dir}")
        if config_dir.exists():
            for item in config_dir.glob("version_*.y*ml"):
                version = item.stem.replace("version_", "")
                versions.append(version)

        return sorted(list(set(versions)))

    def _load_version_file(
        self, impl_name: str, impl_type: str, protocol: str, version: str
    ) -> Optional[Dict[str, Any]]:
        """Load version configuration from file.

        Args:
            impl_name: Implementation name
            impl_type: Implementation type
            protocol: Protocol name
            version: Version identifier

        Returns:
            Version configuration or None
        """
        # Try different paths
        paths = [
            self.plugin_dir
            / "services"
            / impl_type
            / protocol
            / impl_name
            / "versions"
            / f"{version}.yaml",
            self.plugin_dir
            / "services"
            / impl_type
            / protocol
            / impl_name
            / "config"
            / f"version_{version}.yaml",
            self.plugin_dir
            / "protocols"
            / "client_server"
            / protocol
            / "versions"
            / f"{version}.yaml",
            self.plugin_dir
            / "protocols"
            / "peer_to_peer"
            / protocol
            / "versions"
            / f"{version}.yaml",
        ]

        for path in paths:
            if path.exists():
                try:
                    with open(path) as f:
                        return yaml.safe_load(f)
                except Exception as e:
                    self.logger.warning(f"Failed to load version file {path}: {e}")

        return None


class CompositeLoader(BaseLoader):
    """Composite loader that combines multiple loaders."""

    def __init__(self, loaders: List[BaseLoader], enable_cache: bool = True):
        """Initialize composite loader.

        Args:
            loaders: List of loaders to combine
            enable_cache: Whether to enable caching
        """
        super().__init__(enable_cache)
        self.loaders = loaders

    def load(self, source: Any) -> Dict[str, Any]:
        """Load configuration using multiple loaders.

        Args:
            source: Configuration source

        Returns:
            Merged configuration from all loaders
        """
        configs = []

        for loader in self.loaders:
            try:
                config = loader.load(source)
                if config:
                    configs.append(config)
            except Exception as e:
                # Check if this might be a validation error that should be more visible
                error_str = str(e).lower()
                if any(
                    keyword in error_str
                    for keyword in ["validation", "invalid", "required", "field"]
                ):
                    self.logger.error(
                        f"Loader {loader.__class__.__name__} failed with validation error: {e}"
                    )
                else:
                    self.logger.debug(f"Loader {loader.__class__.__name__} failed: {e}")

        if not configs:
            raise ValueError(f"No loader could process source: {source}")

        # Merge all configurations
        if len(configs) == 1:
            return configs[0]

        merged = configs[0]
        for config in configs[1:]:
            merged = OmegaConf.merge(OmegaConf.create(merged), OmegaConf.create(config))
            merged = OmegaConf.to_container(merged, resolve=False)

        return merged


class PluginConfigLoader(BaseLoader):
    """Loader for plugin-specific configurations."""

    def __init__(self, plugin_dir: Path, enable_cache: bool = True):
        """Initialize plugin config loader.

        Args:
            plugin_dir: Plugin directory path
            enable_cache: Whether to enable caching
        """
        super().__init__(enable_cache)
        self.plugin_dir = plugin_dir
        self.yaml_loader = YAMLLoader(enable_cache)

    def load(self, source: str) -> Dict[str, Any]:
        """Load plugin configuration.

        Args:
            source: Plugin name or path

        Returns:
            Plugin configuration
        """
        # Try to find plugin config
        plugin_path = self._find_plugin_config(source)

        if not plugin_path:
            raise ValueError(f"Plugin configuration not found for: {source}")

        return self.yaml_loader.load(plugin_path)

    def load_schema(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """Load plugin schema.

        Args:
            plugin_name: Plugin name

        Returns:
            Plugin schema or None
        """
        schema_path = self._find_plugin_schema(plugin_name)

        if schema_path and schema_path.exists():
            if schema_path.suffix == ".json":
                with open(schema_path) as f:
                    return json.load(f)
            else:
                return self.yaml_loader.load(schema_path)

        return None

    def _find_plugin_config(self, plugin_name: str) -> Optional[Path]:
        """Find plugin configuration file.

        Args:
            plugin_name: Plugin name

        Returns:
            Path to config file or None
        """
        # Standard locations to check
        locations = [
            self.plugin_dir / "services" / "iut" / "**" / plugin_name / "config.yaml",
            self.plugin_dir
            / "services"
            / "testers"
            / "**"
            / plugin_name
            / "config.yaml",
            self.plugin_dir / "environments" / "**" / plugin_name / "config.yaml",
        ]

        for pattern in locations:
            for path in self.plugin_dir.glob(pattern.replace("**", "*")):
                if path.exists():
                    return path

        return None

    def _find_plugin_schema(self, plugin_name: str) -> Optional[Path]:
        """Find plugin schema file.

        Args:
            plugin_name: Plugin name

        Returns:
            Path to schema file or None
        """
        # Check for schema files
        patterns = [
            self.plugin_dir / "**" / plugin_name / "schema.json",
            self.plugin_dir / "**" / plugin_name / "schema.yaml",
            self.plugin_dir / "**" / plugin_name / "config_schema.py",
        ]

        for pattern in patterns:
            matches = list(
                self.plugin_dir.glob(
                    str(pattern).replace(str(self.plugin_dir) + "/", "")
                )
            )
            if matches:
                return matches[0]

        return None
