"""Configuration merger for the unified system."""

from enum import Enum
from typing import Any, Dict, List, Optional, Union

from omegaconf import DictConfig, OmegaConf

from panther.core.utils.logging_mixin import LoggerMixin


class MergeStrategy(Enum):
    """Configuration merge strategies."""
    
    DEEP_MERGE = "deep_merge"
    SHALLOW_MERGE = "shallow_merge"
    REPLACE = "replace"
    APPEND_LISTS = "append_lists"
    UNION_LISTS = "union_lists"


class ConflictResolution(Enum):
    """Conflict resolution strategies."""
    
    USE_FIRST = "use_first"
    USE_SECOND = "use_second"
    ERROR = "error"
    COMBINE = "combine"


class MergeContext:
    """Context for tracking merge operations."""
    
    def __init__(self):
        """Initialize merge context."""
        self.conflicts: List[Dict[str, Any]] = []
        self.merged_paths: List[str] = []
        self.warnings: List[str] = []
    
    def add_conflict(self, path: str, value1: Any, value2: Any, resolution: str):
        """Record a merge conflict.
        
        Args:
            path: Configuration path where conflict occurred
            value1: First conflicting value
            value2: Second conflicting value
            resolution: How the conflict was resolved
        """
        self.conflicts.append({
            "path": path,
            "value1": value1,
            "value2": value2,
            "resolution": resolution
        })
    
    def add_merged_path(self, path: str):
        """Record a merged path.
        
        Args:
            path: Path that was merged
        """
        self.merged_paths.append(path)
    
    def add_warning(self, warning: str):
        """Add a warning message.
        
        Args:
            warning: Warning message
        """
        self.warnings.append(warning)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get merge context summary.
        
        Returns:
            Summary dictionary
        """
        return {
            "conflicts_count": len(self.conflicts),
            "conflicts": self.conflicts,
            "merged_paths_count": len(self.merged_paths),
            "warnings": self.warnings
        }


class ConflictResolver:
    """Handles merge conflict resolution."""
    
    def __init__(self, resolution: ConflictResolution = ConflictResolution.USE_SECOND):
        """Initialize conflict resolver.
        
        Args:
            resolution: Default conflict resolution strategy
        """
        self.resolution = resolution
    
    def resolve(self, path: str, value1: Any, value2: Any, context: MergeContext) -> Any:
        """Resolve a merge conflict.
        
        Args:
            path: Configuration path
            value1: First value
            value2: Second value
            context: Merge context
            
        Returns:
            Resolved value
        """
        if self.resolution == ConflictResolution.USE_FIRST:
            context.add_conflict(path, value1, value2, "used_first")
            return value1
        elif self.resolution == ConflictResolution.USE_SECOND:
            context.add_conflict(path, value1, value2, "used_second")
            return value2
        elif self.resolution == ConflictResolution.ERROR:
            raise ValueError(f"Merge conflict at {path}: {value1} vs {value2}")
        elif self.resolution == ConflictResolution.COMBINE:
            # Try to intelligently combine values
            return self._combine_values(value1, value2, path, context)
        else:
            return value2
    
    def _combine_values(self, value1: Any, value2: Any, path: str, context: MergeContext) -> Any:
        """Attempt to combine conflicting values.
        
        Args:
            value1: First value
            value2: Second value
            path: Configuration path
            context: Merge context
            
        Returns:
            Combined value
        """
        # For lists, concatenate
        if isinstance(value1, list) and isinstance(value2, list):
            context.add_conflict(path, value1, value2, "combined_lists")
            return value1 + value2
        
        # For dicts, deep merge
        if isinstance(value1, dict) and isinstance(value2, dict):
            context.add_conflict(path, value1, value2, "deep_merged_dicts")
            merged = OmegaConf.merge(
                OmegaConf.create(value1),
                OmegaConf.create(value2)
            )
            return OmegaConf.to_container(merged)
        
        # For strings, concatenate with separator
        if isinstance(value1, str) and isinstance(value2, str):
            context.add_conflict(path, value1, value2, "concatenated_strings")
            return f"{value1},{value2}"
        
        # Default to second value
        context.add_conflict(path, value1, value2, "defaulted_to_second")
        return value2


class UnifiedMerger(LoggerMixin):
    """OmegaConf-based configuration merger."""
    
    def __init__(self):
        """Initialize merger."""
        super().__init__()
    
    def merge(
        self,
        *configs: Union[Dict[str, Any], DictConfig],
        strategy: MergeStrategy = MergeStrategy.DEEP_MERGE,
        conflict_resolution: ConflictResolution = ConflictResolution.USE_SECOND
    ) -> DictConfig:
        """Merge multiple configurations.
        
        Args:
            *configs: Configurations to merge
            strategy: Merge strategy
            conflict_resolution: Conflict resolution strategy
            
        Returns:
            Merged configuration as DictConfig
        """
        if not configs:
            return OmegaConf.create({})
        
        self.logger.info(f"Merging {len(configs)} configurations with strategy {strategy.value}")
        
        # Create merge context
        context = MergeContext()
        resolver = ConflictResolver(conflict_resolution)
        
        # Convert all to OmegaConf
        omega_configs = []
        for config in configs:
            if isinstance(config, DictConfig):
                omega_configs.append(config)
            else:
                omega_configs.append(OmegaConf.create(config))
        
        # Apply merge strategy
        if strategy == MergeStrategy.DEEP_MERGE:
            result = self._deep_merge(omega_configs, resolver, context)
        elif strategy == MergeStrategy.SHALLOW_MERGE:
            result = self._shallow_merge(omega_configs, resolver, context)
        elif strategy == MergeStrategy.REPLACE:
            result = omega_configs[-1] if omega_configs else OmegaConf.create({})
            context.add_merged_path("root")
        elif strategy == MergeStrategy.APPEND_LISTS:
            result = self._merge_append_lists(omega_configs, resolver, context)
        elif strategy == MergeStrategy.UNION_LISTS:
            result = self._merge_union_lists(omega_configs, resolver, context)
        else:
            result = self._deep_merge(omega_configs, resolver, context)
        
        # Log merge summary
        summary = context.get_summary()
        if summary['conflicts_count'] > 0:
            self.logger.warning(f"Resolved {summary['conflicts_count']} conflicts during merge")
        if summary['warnings']:
            for warning in summary['warnings']:
                self.logger.warning(warning)
        
        return result
    
    def _deep_merge(
        self,
        configs: List[DictConfig],
        resolver: ConflictResolver,
        context: MergeContext
    ) -> DictConfig:
        """Perform deep merge of configurations.
        
        Args:
            configs: List of configurations
            resolver: Conflict resolver
            context: Merge context
            
        Returns:
            Merged configuration
        """
        if not configs:
            return OmegaConf.create({})
        
        if len(configs) == 1:
            return configs[0]
        
        # Use OmegaConf's merge with custom conflict handling
        result = configs[0]
        
        for i, config in enumerate(configs[1:], 1):
            try:
                # OmegaConf.merge handles deep merging
                result = OmegaConf.merge(result, config)
                context.add_merged_path(f"config_{i}")
            except Exception as e:
                # Handle merge conflicts
                if resolver.resolution == ConflictResolution.ERROR:
                    raise
                else:
                    # Manual merge with conflict resolution
                    result = self._merge_with_resolver(result, config, resolver, context)
        
        return result
    
    def _shallow_merge(
        self,
        configs: List[DictConfig],
        resolver: ConflictResolver,
        context: MergeContext
    ) -> DictConfig:
        """Perform shallow merge of configurations.
        
        Args:
            configs: List of configurations
            resolver: Conflict resolver
            context: Merge context
            
        Returns:
            Merged configuration
        """
        result = OmegaConf.create({})
        
        for config in configs:
            for key, value in config.items():
                if key in result:
                    # Resolve conflict
                    result[key] = resolver.resolve(key, result[key], value, context)
                else:
                    result[key] = value
                    context.add_merged_path(key)
        
        return result
    
    def _merge_append_lists(
        self,
        configs: List[DictConfig],
        resolver: ConflictResolver,
        context: MergeContext
    ) -> DictConfig:
        """Merge with list appending.
        
        Args:
            configs: List of configurations
            resolver: Conflict resolver
            context: Merge context
            
        Returns:
            Merged configuration
        """
        if not configs:
            return OmegaConf.create({})
        
        result = configs[0]
        
        for config in configs[1:]:
            result = self._merge_configs_append_lists(result, config, resolver, context)
        
        return result
    
    def _merge_union_lists(
        self,
        configs: List[DictConfig],
        resolver: ConflictResolver,
        context: MergeContext
    ) -> DictConfig:
        """Merge with list union (unique values).
        
        Args:
            configs: List of configurations
            resolver: Conflict resolver
            context: Merge context
            
        Returns:
            Merged configuration
        """
        if not configs:
            return OmegaConf.create({})
        
        result = configs[0]
        
        for config in configs[1:]:
            result = self._merge_configs_union_lists(result, config, resolver, context)
        
        return result
    
    def _merge_with_resolver(
        self,
        base: DictConfig,
        override: DictConfig,
        resolver: ConflictResolver,
        context: MergeContext,
        path: str = ""
    ) -> DictConfig:
        """Merge two configs with conflict resolution.
        
        Args:
            base: Base configuration
            override: Override configuration
            resolver: Conflict resolver
            context: Merge context
            path: Current path in configuration
            
        Returns:
            Merged configuration
        """
        result = OmegaConf.create({})
        
        # Add all keys from base
        for key in base:
            current_path = f"{path}.{key}" if path else key
            
            if key in override:
                base_val = base[key]
                override_val = override[key]
                
                if isinstance(base_val, DictConfig) and isinstance(override_val, DictConfig):
                    # Recursive merge
                    result[key] = self._merge_with_resolver(
                        base_val, override_val, resolver, context, current_path
                    )
                elif base_val != override_val:
                    # Conflict
                    result[key] = resolver.resolve(current_path, base_val, override_val, context)
                else:
                    # Same value
                    result[key] = base_val
            else:
                result[key] = base[key]
        
        # Add keys only in override
        for key in override:
            if key not in base:
                current_path = f"{path}.{key}" if path else key
                result[key] = override[key]
                context.add_merged_path(current_path)
        
        return result
    
    def _merge_configs_append_lists(
        self,
        base: DictConfig,
        override: DictConfig,
        resolver: ConflictResolver,
        context: MergeContext
    ) -> DictConfig:
        """Merge configs with list appending.
        
        Args:
            base: Base configuration
            override: Override configuration
            resolver: Conflict resolver
            context: Merge context
            
        Returns:
            Merged configuration
        """
        # Convert to regular merge but handle lists specially
        def list_merger(base_val: Any, override_val: Any) -> Any:
            if isinstance(base_val, list) and isinstance(override_val, list):
                return base_val + override_val
            return None
        
        # Use OmegaConf with custom merger
        OmegaConf.register_new_resolver("append_lists", list_merger)
        result = OmegaConf.merge(base, override)
        
        return result
    
    def _merge_configs_union_lists(
        self,
        base: DictConfig,
        override: DictConfig,
        resolver: ConflictResolver,
        context: MergeContext
    ) -> DictConfig:
        """Merge configs with list union.
        
        Args:
            base: Base configuration
            override: Override configuration
            resolver: Conflict resolver
            context: Merge context
            
        Returns:
            Merged configuration
        """
        # Convert to regular merge but handle lists specially
        def list_union(base_val: Any, override_val: Any) -> Any:
            if isinstance(base_val, list) and isinstance(override_val, list):
                # Create union of lists
                return list(set(base_val + override_val))
            return None
        
        # Use OmegaConf with custom merger
        OmegaConf.register_new_resolver("union_lists", list_union)
        result = OmegaConf.merge(base, override)
        
        return result