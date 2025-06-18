"""Configuration merging system with hierarchical support."""

import logging
from enum import Enum
from typing import Any, Dict, List, Optional, Type, Union

from omegaconf import DictConfig, ListConfig, OmegaConf

from panther.config.models.base import ConfigModel
from panther.core.exceptions.error_handler_mixin import ErrorHandlerMixin


class MergeStrategy(str, Enum):
    """Strategies for merging configurations."""
    
    REPLACE = "replace"  # Replace values completely
    DEEP_MERGE = "deep_merge"  # Deep merge dictionaries, replace lists
    APPEND = "append"  # Append to lists, merge dictionaries
    PREPEND = "prepend"  # Prepend to lists, merge dictionaries
    SELECTIVE = "selective"  # Use field-specific strategies


class MergeConflictResolution(str, Enum):
    """How to resolve merge conflicts."""
    
    OVERRIDE = "override"  # Later values override earlier ones
    PRESERVE = "preserve"  # Earlier values are preserved
    FAIL = "fail"  # Fail on conflicts
    WARN = "warn"  # Warn but continue with override


class MergeContext:
    """Context for merge operations."""
    
    def __init__(
        self,
        strategy: MergeStrategy = MergeStrategy.DEEP_MERGE,
        conflict_resolution: MergeConflictResolution = MergeConflictResolution.OVERRIDE,
        field_strategies: Optional[Dict[str, MergeStrategy]] = None
    ):
        self.strategy = strategy
        self.conflict_resolution = conflict_resolution
        self.field_strategies = field_strategies or {}
        self.merge_path: List[str] = []
        self.conflicts: List[Dict[str, Any]] = []
    
    def push_path(self, key: str) -> None:
        """Push a key onto the merge path."""
        self.merge_path.append(key)
    
    def pop_path(self) -> str:
        """Pop a key from the merge path."""
        return self.merge_path.pop()
    
    def get_current_path(self) -> str:
        """Get the current path as a dot-separated string."""
        return ".".join(self.merge_path)
    
    def add_conflict(self, key: str, old_value: Any, new_value: Any) -> None:
        """Record a merge conflict."""
        conflict = {
            "path": self.get_current_path(),
            "key": key,
            "old_value": old_value,
            "new_value": new_value
        }
        self.conflicts.append(conflict)
    
    def get_strategy_for_field(self, field_path: str) -> MergeStrategy:
        """Get the merge strategy for a specific field."""
        return self.field_strategies.get(field_path, self.strategy)


class ConfigMerger(ErrorHandlerMixin):
    """Configuration merger using OmegaConf with advanced merging strategies."""
    
    def __init__(self):
        super().__init__()
        self._merger_logger = logging.getLogger(__name__)
        self._default_context = MergeContext()
    
    def merge(
        self,
        base: Union[Dict[str, Any], DictConfig, ConfigModel],
        *configs: Union[Dict[str, Any], DictConfig, ConfigModel],
        context: Optional[MergeContext] = None
    ) -> DictConfig:
        """Merge multiple configurations hierarchically.
        
        Args:
            base: Base configuration
            *configs: Additional configurations to merge
            context: Merge context with strategy and options
            
        Returns:
            Merged OmegaConf DictConfig
        """
        if context is None:
            context = self._default_context
        
        # Convert all inputs to OmegaConf
        omega_base = self._to_omega_conf(base)
        omega_configs = [self._to_omega_conf(config) for config in configs]
        
        # Start with base
        result = omega_base.copy()
        
        # Merge each configuration
        for i, config in enumerate(omega_configs):
            self._merger_logger.debug(f"Merging configuration {i+1}/{len(omega_configs)}")
            result = self._merge_single(result, config, context)
        
        # Log conflicts if any
        if context.conflicts:
            self._merger_logger.warning(f"Merge completed with {len(context.conflicts)} conflicts")
            for conflict in context.conflicts:
                self._merger_logger.debug(f"Conflict at {conflict['path']}.{conflict['key']}: "
                                f"{conflict['old_value']} -> {conflict['new_value']}")
        
        return result
    
    def merge_with_defaults(
        self,
        config: Union[Dict[str, Any], DictConfig, ConfigModel],
        defaults: Union[Dict[str, Any], DictConfig, ConfigModel],
        context: Optional[MergeContext] = None
    ) -> DictConfig:
        """Merge configuration with defaults, prioritizing user config.
        
        Args:
            config: User configuration
            defaults: Default configuration
            context: Merge context
            
        Returns:
            Merged configuration with defaults filled in
        """
        if context is None:
            context = MergeContext(
                strategy=MergeStrategy.DEEP_MERGE,
                conflict_resolution=MergeConflictResolution.PRESERVE  # Preserve user values
            )
        
        return self.merge(defaults, config, context=context)
    
    def merge_hierarchical(
        self,
        *configs: Union[Dict[str, Any], DictConfig, ConfigModel],
        hierarchy: Optional[List[str]] = None
    ) -> DictConfig:
        """Merge configurations in hierarchical order (last wins).
        
        Args:
            *configs: Configurations in priority order (low to high)
            hierarchy: Optional hierarchy description for logging
            
        Returns:
            Merged configuration
        """
        if not configs:
            return OmegaConf.create({})
        
        if hierarchy and len(hierarchy) != len(configs):
            self._merger_logger.warning("Hierarchy length doesn't match config count")
        
        context = MergeContext(
            strategy=MergeStrategy.DEEP_MERGE,
            conflict_resolution=MergeConflictResolution.OVERRIDE
        )
        
        result = self.merge(*configs, context=context)
        
        if hierarchy:
            self._merger_logger.debug(f"Merged hierarchy: {' -> '.join(hierarchy)}")
        
        return result
    
    def _to_omega_conf(
        self, 
        config: Union[Dict[str, Any], DictConfig, ConfigModel]
    ) -> DictConfig:
        """Convert configuration to OmegaConf DictConfig."""
        if isinstance(config, DictConfig):
            return config.copy()
        elif isinstance(config, ConfigModel):
            return config.to_omega()
        elif isinstance(config, dict):
            return OmegaConf.create(config)
        else:
            raise ValueError(f"Unsupported configuration type: {type(config)}")
    
    def _merge_single(
        self,
        base: DictConfig,
        overlay: DictConfig,
        context: MergeContext
    ) -> DictConfig:
        """Merge a single configuration into the base.
        
        Args:
            base: Base configuration
            overlay: Configuration to merge in
            context: Merge context
            
        Returns:
            Merged configuration
        """
        strategy = context.strategy
        
        if strategy == MergeStrategy.REPLACE:
            return overlay.copy()
        elif strategy == MergeStrategy.DEEP_MERGE:
            return self._deep_merge(base, overlay, context)
        elif strategy == MergeStrategy.APPEND:
            return self._append_merge(base, overlay, context)
        elif strategy == MergeStrategy.PREPEND:
            return self._prepend_merge(base, overlay, context)
        elif strategy == MergeStrategy.SELECTIVE:
            return self._selective_merge(base, overlay, context)
        else:
            raise ValueError(f"Unknown merge strategy: {strategy}")
    
    def _deep_merge(
        self,
        base: DictConfig,
        overlay: DictConfig,
        context: MergeContext
    ) -> DictConfig:
        """Perform deep merge of configurations."""
        # Use OmegaConf's built-in merge with some customizations
        try:
            result = OmegaConf.merge(base, overlay)
            return result
        except Exception as e:
            self._merger_logger.error(f"OmegaConf merge failed: {e}")
            # Fallback to manual merge
            return self._manual_deep_merge(base, overlay, context)
    
    def _manual_deep_merge(
        self,
        base: DictConfig,
        overlay: DictConfig,
        context: MergeContext
    ) -> DictConfig:
        """Manual deep merge implementation."""
        result = base.copy()
        
        for key, value in overlay.items():
            context.push_path(key)
            
            try:
                if key not in result:
                    # New key, just add it
                    result[key] = value
                else:
                    # Key exists, need to merge
                    existing_value = result[key]
                    
                    if self._should_merge_recursively(existing_value, value):
                        result[key] = self._manual_deep_merge(existing_value, value, context)
                    else:
                        # Handle conflict
                        self._handle_conflict(result, key, existing_value, value, context)
            finally:
                context.pop_path()
        
        return result
    
    def _append_merge(
        self,
        base: DictConfig,
        overlay: DictConfig,
        context: MergeContext
    ) -> DictConfig:
        """Merge by appending lists and merging dictionaries."""
        result = base.copy()
        
        for key, value in overlay.items():
            if key not in result:
                result[key] = value
            else:
                existing = result[key]
                
                if isinstance(existing, ListConfig) and isinstance(value, ListConfig):
                    # Append lists
                    result[key] = OmegaConf.create(list(existing) + list(value))
                elif isinstance(existing, DictConfig) and isinstance(value, DictConfig):
                    # Merge dictionaries
                    result[key] = self._deep_merge(existing, value, context)
                else:
                    # Replace other types
                    self._handle_conflict(result, key, existing, value, context)
        
        return result
    
    def _prepend_merge(
        self,
        base: DictConfig,
        overlay: DictConfig,
        context: MergeContext
    ) -> DictConfig:
        """Merge by prepending lists and merging dictionaries."""
        result = base.copy()
        
        for key, value in overlay.items():
            if key not in result:
                result[key] = value
            else:
                existing = result[key]
                
                if isinstance(existing, ListConfig) and isinstance(value, ListConfig):
                    # Prepend lists
                    result[key] = OmegaConf.create(list(value) + list(existing))
                elif isinstance(existing, DictConfig) and isinstance(value, DictConfig):
                    # Merge dictionaries
                    result[key] = self._deep_merge(existing, value, context)
                else:
                    # Replace other types
                    self._handle_conflict(result, key, existing, value, context)
        
        return result
    
    def _selective_merge(
        self,
        base: DictConfig,
        overlay: DictConfig,
        context: MergeContext
    ) -> DictConfig:
        """Merge using field-specific strategies."""
        result = base.copy()
        
        for key, value in overlay.items():
            field_path = f"{context.get_current_path()}.{key}" if context.get_current_path() else key
            field_strategy = context.get_strategy_for_field(field_path)
            
            # Create temporary context with field-specific strategy
            temp_context = MergeContext(
                strategy=field_strategy,
                conflict_resolution=context.conflict_resolution,
                field_strategies=context.field_strategies
            )
            temp_context.merge_path = context.merge_path.copy()
            temp_context.conflicts = context.conflicts
            
            if key not in result:
                result[key] = value
            else:
                existing = result[key]
                
                if field_strategy == MergeStrategy.REPLACE:
                    result[key] = value
                elif isinstance(existing, DictConfig) and isinstance(value, DictConfig):
                    result[key] = self._merge_single(existing, value, temp_context)
                else:
                    self._handle_conflict(result, key, existing, value, context)
        
        return result
    
    def _should_merge_recursively(self, existing: Any, new: Any) -> bool:
        """Check if two values should be merged recursively."""
        return (
            isinstance(existing, DictConfig) and 
            isinstance(new, DictConfig)
        )
    
    def _handle_conflict(
        self,
        result: DictConfig,
        key: str,
        existing_value: Any,
        new_value: Any,
        context: MergeContext
    ) -> None:
        """Handle merge conflicts based on resolution strategy."""
        context.add_conflict(key, existing_value, new_value)
        
        resolution = context.conflict_resolution
        
        if resolution == MergeConflictResolution.OVERRIDE:
            result[key] = new_value
        elif resolution == MergeConflictResolution.PRESERVE:
            # Keep existing value, do nothing
            pass
        elif resolution == MergeConflictResolution.FAIL:
            raise ValueError(
                f"Merge conflict at {context.get_current_path()}.{key}: "
                f"{existing_value} vs {new_value}"
            )
        elif resolution == MergeConflictResolution.WARN:
            self._merger_logger.warning(
                f"Merge conflict at {context.get_current_path()}.{key}: "
                f"overriding {existing_value} with {new_value}"
            )
            result[key] = new_value
    
    def create_merge_context(
        self,
        strategy: MergeStrategy = MergeStrategy.DEEP_MERGE,
        conflict_resolution: MergeConflictResolution = MergeConflictResolution.OVERRIDE,
        field_strategies: Optional[Dict[str, MergeStrategy]] = None
    ) -> MergeContext:
        """Create a merge context with specified options.
        
        Args:
            strategy: Default merge strategy
            conflict_resolution: How to resolve conflicts
            field_strategies: Field-specific strategies
            
        Returns:
            Configured merge context
        """
        return MergeContext(
            strategy=strategy,
            conflict_resolution=conflict_resolution,
            field_strategies=field_strategies
        )
    
    def get_merge_report(self, context: MergeContext) -> Dict[str, Any]:
        """Get a report of the merge operation.
        
        Args:
            context: Merge context with conflict information
            
        Returns:
            Dictionary with merge statistics and conflicts
        """
        return {
            "total_conflicts": len(context.conflicts),
            "conflicts": context.conflicts,
            "strategy": context.strategy.value,
            "conflict_resolution": context.conflict_resolution.value,
            "field_strategies": {
                path: strategy.value 
                for path, strategy in context.field_strategies.items()
            }
        }