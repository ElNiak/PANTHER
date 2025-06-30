"""Configuration operations mixin for ConfigurationManager."""

from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from omegaconf import DictConfig, OmegaConf

from panther.core.utils.logging_mixin import LoggerMixin

from ..base import BaseConfig

if TYPE_CHECKING:
    from ..models import ExperimentConfig


class MergeStrategy(Enum):
    """Configuration merge strategies."""

    DEEP_MERGE = "deep_merge"
    SHALLOW_MERGE = "shallow_merge"
    REPLACE = "replace"


class ConflictResolution(Enum):
    """Conflict resolution strategies for merging."""

    USE_FIRST = "use_first"
    USE_SECOND = "use_second"
    ERROR = "error"
    COMBINE_LISTS = "combine_lists"


class ConfigOperationsMixin(LoggerMixin):
    """Handles configuration operations and overrides."""

    def __init__(self):
        """Initialize configuration operations."""
        super().__init__()
        self._config_overrides: Dict[str, Any] = {}

    def merge_configurations(
        self,
        *configs: Any,
        strategy: MergeStrategy = MergeStrategy.DEEP_MERGE,
        conflict: ConflictResolution = ConflictResolution.USE_SECOND,
    ) -> DictConfig:
        """Merge multiple configurations with specified strategy.

        Args:
            *configs: Configurations to merge (dicts, DictConfigs, or models)
            strategy: Merge strategy to use
            conflict: Conflict resolution strategy

        Returns:
            Merged configuration as DictConfig
        """
        if not configs:
            return OmegaConf.create({})

        self.logger.debug(
            f"Merging {len(configs)} configurations with strategy {strategy.value}"
        )

        # Convert all configs to OmegaConf
        omega_configs = []
        for config in configs:
            if isinstance(config, DictConfig):
                omega_configs.append(config)
            elif isinstance(config, dict):
                omega_configs.append(OmegaConf.create(config))
            elif hasattr(config, "to_omega"):
                omega_configs.append(config.to_omega())
            else:
                omega_configs.append(OmegaConf.create(config))

        # Perform merge based on strategy
        if strategy == MergeStrategy.DEEP_MERGE:
            result = self._deep_merge(omega_configs, conflict)
        elif strategy == MergeStrategy.SHALLOW_MERGE:
            result = self._shallow_merge(omega_configs, conflict)
        else:  # REPLACE
            result = omega_configs[-1] if omega_configs else OmegaConf.create({})

        return result

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

        # Load template
        template_path = self._find_template(name)
        if not template_path:
            raise ValueError(f"Template not found: {name}")

        # Load template content
        with open(template_path) as f:
            import yaml

            template_content = yaml.safe_load(f)

        # Create OmegaConf with template
        template_config = OmegaConf.create(template_content)

        # Apply parameters
        param_config = OmegaConf.create(params)
        merged = OmegaConf.merge(template_config, param_config)

        # Resolve interpolations
        resolved = OmegaConf.to_container(merged, resolve=True)

        # Create ExperimentConfig
        from ..models.experiment import ExperimentConfig

        experiment_config = ExperimentConfig(**resolved)

        # Save if output specified
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
        # Convert to OmegaConf for patching
        base_omega = base.to_omega()
        patch_omega = OmegaConf.create(patch)

        # Apply patch
        patched = OmegaConf.merge(base_omega, patch_omega)

        # Create new instance
        return base.__class__.from_omega(patched)

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
        """Get summary of current overrides.

        Returns:
            Dictionary of current overrides
        """
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

        # Convert to OmegaConf
        omega_config = config.to_omega()

        # Apply each override
        for key, value in self._config_overrides.items():
            try:
                OmegaConf.update(omega_config, key, value, merge=False)
            except Exception as e:
                self.logger.warning(f"Failed to apply override {key}: {e}")

        # Create new instance
        return config.__class__.from_omega(omega_config)

    def _deep_merge(
        self, configs: List[DictConfig], conflict: ConflictResolution
    ) -> DictConfig:
        """Perform deep merge of configurations.

        Args:
            configs: List of OmegaConf configs
            conflict: Conflict resolution strategy

        Returns:
            Merged configuration
        """
        if not configs:
            return OmegaConf.create({})

        if len(configs) == 1:
            return configs[0]

        # OmegaConf.merge handles deep merging by default
        # For conflict resolution, we need custom handling
        if conflict == ConflictResolution.USE_SECOND:
            # Default OmegaConf behavior
            return OmegaConf.merge(*configs)

        # For other strategies, we need manual merging
        result = configs[0]
        for config in configs[1:]:
            result = self._merge_with_conflict_resolution(result, config, conflict)

        return result

    def _shallow_merge(
        self, configs: List[DictConfig], conflict: ConflictResolution
    ) -> DictConfig:
        """Perform shallow merge of configurations.

        Args:
            configs: List of OmegaConf configs
            conflict: Conflict resolution strategy

        Returns:
            Merged configuration
        """
        result = OmegaConf.create({})

        for config in configs:
            for key, value in config.items():
                if key in result and conflict == ConflictResolution.ERROR:
                    raise ValueError(f"Conflict on key: {key}")
                elif key in result and conflict == ConflictResolution.USE_FIRST:
                    continue
                result[key] = value

        return result

    def _merge_with_conflict_resolution(
        self, base: DictConfig, override: DictConfig, conflict: ConflictResolution
    ) -> DictConfig:
        """Merge with custom conflict resolution.

        Args:
            base: Base configuration
            override: Override configuration
            conflict: Conflict resolution strategy

        Returns:
            Merged configuration
        """
        if conflict == ConflictResolution.ERROR:
            # Check for conflicts first
            for key in override:
                if key in base:
                    base_val = base[key]
                    override_val = override[key]
                    if isinstance(base_val, DictConfig) and isinstance(
                        override_val, DictConfig
                    ):
                        # Recursive check
                        self._merge_with_conflict_resolution(
                            base_val, override_val, conflict
                        )
                    elif base_val != override_val:
                        raise ValueError(f"Conflict on key: {key}")

        elif conflict == ConflictResolution.COMBINE_LISTS:
            # Special handling for lists
            result = OmegaConf.create({})

            # Add all base items
            for key, value in base.items():
                result[key] = value

            # Merge override items
            for key, value in override.items():
                if key in result:
                    base_val = result[key]
                    if isinstance(base_val, list) and isinstance(value, list):
                        # Combine lists
                        result[key] = base_val + value
                    elif isinstance(base_val, DictConfig) and isinstance(
                        value, DictConfig
                    ):
                        # Recursive merge
                        result[key] = self._merge_with_conflict_resolution(
                            base_val, value, conflict
                        )
                    else:
                        # Replace
                        result[key] = value
                else:
                    result[key] = value

            return result

        # Default behavior (USE_FIRST or USE_SECOND)
        return OmegaConf.merge(base, override)

    def _find_template(self, name: str) -> Optional[Path]:
        """Find template file by name.

        Args:
            name: Template name

        Returns:
            Path to template file or None
        """
        # Look in standard template locations
        template_dirs = [
            Path("templates"),
            Path("experiment-config/templates"),
            getattr(self, "panther_dir", Path.cwd()) / "templates",
            getattr(self, "panther_dir", Path.cwd()) / "panther" / "templates",
        ]

        for template_dir in template_dirs:
            if template_dir.exists():
                # Try with and without .yaml extension
                for ext in ["", ".yaml", ".yml"]:
                    template_path = template_dir / f"{name}{ext}"
                    if template_path.exists():
                        return template_path

        return None
