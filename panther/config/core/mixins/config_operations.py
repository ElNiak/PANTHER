"""Configuration operations mixin for ConfigurationManager."""

from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional

import yaml

from panther.core.utils.logging_mixin import LoggerMixin

from ..base import BaseConfig
from ..components.merger import ConfigMerger, ConflictResolution, MergeStrategy
from ..utils.merge import deep_merge, dot_notation_update

if TYPE_CHECKING:
    from ..models import ExperimentConfig


class ConfigOperationsMixin(LoggerMixin):
    """Handles configuration operations and overrides."""

    def __init__(self):
        """Initialize configuration operations."""
        super().__init__()
        self._config_overrides: Dict[str, Any] = {}
        self._merger = ConfigMerger()

    def merge_configurations(
        self,
        *configs: Any,
        strategy: MergeStrategy = MergeStrategy.DEEP_MERGE,
        conflict: ConflictResolution = ConflictResolution.USE_SECOND,
    ) -> Dict[str, Any]:
        """Merge multiple configurations with specified strategy.

        Args:
            *configs: Configurations to merge (dicts or models)
            strategy: Merge strategy to use
            conflict: Conflict resolution strategy

        Returns:
            Merged configuration as dict
        """
        if not configs:
            return {}

        self.logger.debug(
            f"Merging {len(configs)} configurations with strategy {strategy.value}"
        )

        # Convert all configs to plain dicts
        dict_configs = []
        for config in configs:
            if isinstance(config, dict):
                dict_configs.append(config)
            elif hasattr(config, "to_dict"):
                dict_configs.append(config.to_dict())
            elif hasattr(config, "model_dump"):
                dict_configs.append(config.model_dump())
            else:
                dict_configs.append(dict(config))

        return self._merger.merge(
            *dict_configs,
            strategy=strategy,
            conflict_resolution=conflict,
        )

    def create_experiment_from_template(
        self, name: str, params: Dict[str, Any], output: Optional[Path] = None
    ) -> "ExperimentConfig":
        """Create experiment configuration from template.

        Args:
            name: Template name
            params: Template parameters to substitute
            output: Optional output path to save config

        Returns:
            Created ExperimentConfig instance
        """
        self.logger.info(f"Creating experiment from template: {name}")

        template_path = self._find_template(name)
        if not template_path:
            raise ValueError(f"Template not found: {name}")

        with open(template_path) as f:
            template_content = yaml.safe_load(f)

        # Deep merge template with params
        merged = deep_merge(template_content, params)

        from ..models.experiment import ExperimentConfig

        experiment_config = ExperimentConfig(**merged)

        if output:
            experiment_config.save(output)
            self.logger.info(f"Saved experiment configuration to: {output}")

        return experiment_config

    def apply_configuration_patch(
        self, base: BaseConfig, patch: Dict[str, Any]
    ) -> BaseConfig:
        """Apply a patch to configuration.

        Args:
            base: Base configuration
            patch: Patch to apply

        Returns:
            Patched configuration
        """
        base_dict = base.to_dict(exclude_none=False)
        merged = deep_merge(base_dict, patch)
        return base.__class__(**merged)

    def add_configuration_override(self, key: str, value: Any) -> None:
        """Add a configuration override.

        Args:
            key: Configuration key (dot notation)
            value: Override value
        """
        self._config_overrides[key] = value
        self.logger.debug(f"Added configuration override: {key} = {value}")

    def remove_configuration_override(self, key: str) -> None:
        """Remove a configuration override.

        Args:
            key: Configuration key to remove
        """
        if key in self._config_overrides:
            del self._config_overrides[key]
            self.logger.debug(f"Removed configuration override: {key}")

    def clear_configuration_overrides(self) -> None:
        """Clear all configuration overrides."""
        self._config_overrides.clear()
        self.logger.debug("Cleared all configuration overrides")

    def get_override_summary(self) -> Dict[str, Any]:
        """Get summary of current overrides."""
        return self._config_overrides.copy()

    def apply_overrides(self, config: BaseConfig) -> BaseConfig:
        """Apply all overrides to a configuration.

        Args:
            config: Configuration to apply overrides to

        Returns:
            Configuration with overrides applied
        """
        if not self._config_overrides:
            return config

        self.logger.debug(f"Applying {len(self._config_overrides)} overrides")

        data = config.to_dict(exclude_none=False)
        for key, value in self._config_overrides.items():
            try:
                dot_notation_update(data, key, value)
            except Exception as e:
                self.logger.warning(f"Failed to apply override {key}: {e}")

        return config.__class__(**data)

    def _find_template(self, name: str) -> Optional[Path]:
        """Find template file by name."""
        template_dirs = [
            Path("templates"),
            Path("experiment-config/templates"),
            getattr(self, "panther_dir", Path.cwd()) / "templates",
            getattr(self, "panther_dir", Path.cwd()) / "panther" / "templates",
        ]

        for template_dir in template_dirs:
            if template_dir.exists():
                for ext in ["", ".yaml", ".yml"]:
                    template_path = template_dir / f"{name}{ext}"
                    if template_path.exists():
                        return template_path

        return None
