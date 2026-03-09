"""Configuration merger for the unified system.

This module implements the configuration merging subsystem used by
``UnifiedMerger`` (the standalone component) and ``ConfigOperationsMixin``
(the mixin variant in ``panther.config.core.mixins.config_operations``).

Two orthogonal enums control merge behaviour:

``MergeStrategy``
    Determines *how* configuration trees are combined structurally:

    - ``DEEP_MERGE`` -- Recursively merge nested dicts; later configs override
      earlier ones at leaf level. This is the default and the most common
      choice for layering base + override configs.
    - ``SHALLOW_MERGE`` -- Only merge top-level keys; nested dicts are replaced
      wholesale rather than recursed into.
    - ``REPLACE`` -- The last config wins entirely; earlier configs are ignored.
    - ``APPEND_LISTS`` -- Like deep merge, but list values are concatenated
      rather than replaced.
    - ``UNION_LISTS`` -- Like deep merge, but list values are unioned
      (deduplicated) rather than replaced.

``ConflictResolution``
    Determines *what happens* when two configs define different scalar values
    for the same key:

    - ``USE_FIRST`` -- Keep the value from the earlier (base) config.
    - ``USE_SECOND`` -- Keep the value from the later (override) config.
      This is the default.
    - ``ERROR`` -- Raise ``ValueError`` on any conflict.
    - ``COMBINE`` -- Attempt intelligent combination: concatenate lists,
      deep-merge dicts, join strings with comma, or fall back to second value.

``MergeContext`` tracks all conflicts and merge paths for auditability, and
``ConflictResolver`` applies the chosen ``ConflictResolution`` strategy.
"""

from collections.abc import Hashable
from enum import Enum
from typing import Any, Dict, List

from panther.core.utils.logging_mixin import LoggerMixin

from ..utils.merge import deep_merge


class MergeStrategy(Enum):
    """Structural strategy for combining configuration trees."""

    DEEP_MERGE = "deep_merge"
    SHALLOW_MERGE = "shallow_merge"
    REPLACE = "replace"
    APPEND_LISTS = "append_lists"
    UNION_LISTS = "union_lists"


class ConflictResolution(Enum):
    """Strategy for resolving scalar-level conflicts during merge."""

    USE_FIRST = "use_first"
    USE_SECOND = "use_second"
    ERROR = "error"
    COMBINE = "combine"


class MergeContext:
    """Audit trail for a single merge operation."""

    def __init__(self):
        """Initialize merge context."""
        self.conflicts: List[Dict[str, Any]] = []
        self.merged_paths: List[str] = []
        self.warnings: List[str] = []

    def add_conflict(self, path: str, value1: Any, value2: Any, resolution: str):
        """Record a merge conflict."""
        self.conflicts.append(
            {"path": path, "value1": value1, "value2": value2, "resolution": resolution}
        )

    def add_merged_path(self, path: str):
        """Record a merged path."""
        self.merged_paths.append(path)

    def add_warning(self, warning: str):
        """Add a warning message."""
        self.warnings.append(warning)

    def get_summary(self) -> Dict[str, Any]:
        """Get merge context summary."""
        return {
            "conflicts_count": len(self.conflicts),
            "conflicts": self.conflicts,
            "merged_paths_count": len(self.merged_paths),
            "warnings": self.warnings,
        }


class ConflictResolver:
    """Applies a ``ConflictResolution`` strategy to individual merge conflicts."""

    def __init__(self, resolution: ConflictResolution = ConflictResolution.USE_SECOND):
        """Initialize conflict resolver."""
        self.resolution = resolution

    def resolve(
        self, path: str, value1: Any, value2: Any, context: MergeContext
    ) -> Any:
        """Resolve a merge conflict."""
        if self.resolution == ConflictResolution.USE_FIRST:
            context.add_conflict(path, value1, value2, "used_first")
            return value1
        elif self.resolution == ConflictResolution.USE_SECOND:
            context.add_conflict(path, value1, value2, "used_second")
            return value2
        elif self.resolution == ConflictResolution.ERROR:
            raise ValueError(f"Merge conflict at {path}: {value1} vs {value2}")
        elif self.resolution == ConflictResolution.COMBINE:
            return self._combine_values(value1, value2, path, context)
        else:
            return value2

    def _combine_values(
        self, value1: Any, value2: Any, path: str, context: MergeContext
    ) -> Any:
        """Attempt to combine conflicting values."""
        if isinstance(value1, list) and isinstance(value2, list):
            context.add_conflict(path, value1, value2, "combined_lists")
            return value1 + value2

        if isinstance(value1, dict) and isinstance(value2, dict):
            context.add_conflict(path, value1, value2, "deep_merged_dicts")
            return deep_merge(value1, value2)

        if isinstance(value1, str) and isinstance(value2, str):
            context.add_conflict(path, value1, value2, "concatenated_strings")
            return f"{value1},{value2}"

        context.add_conflict(path, value1, value2, "defaulted_to_second")
        return value2


class UnifiedMerger(LoggerMixin):
    """Pure-dict configuration merger.

    Merges an arbitrary number of configuration dicts according to a
    ``MergeStrategy`` and a ``ConflictResolution`` policy. Produces a
    single merged dict plus an auditable ``MergeContext``.
    """

    def __init__(self):
        """Initialize merger."""
        super().__init__()

    def merge(
        self,
        *configs: Dict[str, Any],
        strategy: MergeStrategy = MergeStrategy.DEEP_MERGE,
        conflict_resolution: ConflictResolution = ConflictResolution.USE_SECOND,
    ) -> Dict[str, Any]:
        """Merge multiple configurations.

        Args:
            *configs: Configuration dicts to merge.
            strategy: Merge strategy.
            conflict_resolution: Conflict resolution strategy.

        Returns:
            Merged configuration dict.
        """
        if not configs:
            return {}

        self.logger.info(
            f"Merging {len(configs)} configurations with strategy {strategy.value}"
        )

        # Ensure all inputs are plain dicts
        dict_configs = [dict(c) if not isinstance(c, dict) else c for c in configs]

        context = MergeContext()
        resolver = ConflictResolver(conflict_resolution)

        if strategy == MergeStrategy.DEEP_MERGE:
            result = self._deep_merge(dict_configs, resolver, context)
        elif strategy == MergeStrategy.SHALLOW_MERGE:
            result = self._shallow_merge(dict_configs, resolver, context)
        elif strategy == MergeStrategy.REPLACE:
            result = dict_configs[-1] if dict_configs else {}
            context.add_merged_path("root")
        elif strategy == MergeStrategy.APPEND_LISTS:
            result = self._merge_with_list_strategy(
                dict_configs, resolver, context, "append"
            )
        elif strategy == MergeStrategy.UNION_LISTS:
            result = self._merge_with_list_strategy(
                dict_configs, resolver, context, "union"
            )
        else:
            result = self._deep_merge(dict_configs, resolver, context)

        summary = context.get_summary()
        if summary["conflicts_count"] > 0:
            self.logger.warning(
                f"Resolved {summary['conflicts_count']} conflicts during merge"
            )
        for warning in summary["warnings"]:
            self.logger.warning(warning)

        return result

    def _deep_merge(
        self,
        configs: List[Dict[str, Any]],
        resolver: ConflictResolver,
        context: MergeContext,
    ) -> Dict[str, Any]:
        """Perform deep merge of configurations."""
        if not configs:
            return {}
        if len(configs) == 1:
            return configs[0]

        result = configs[0]
        for i, config in enumerate(configs[1:], 1):
            result = deep_merge(result, config)
            context.add_merged_path(f"config_{i}")
        return result

    def _shallow_merge(
        self,
        configs: List[Dict[str, Any]],
        resolver: ConflictResolver,
        context: MergeContext,
    ) -> Dict[str, Any]:
        """Perform shallow merge of configurations."""
        result: Dict[str, Any] = {}
        for config in configs:
            for key, value in config.items():
                if key in result:
                    result[key] = resolver.resolve(key, result[key], value, context)
                else:
                    result[key] = value
                    context.add_merged_path(key)
        return result

    def _merge_with_list_strategy(
        self,
        configs: List[Dict[str, Any]],
        resolver: ConflictResolver,
        context: MergeContext,
        list_mode: str,
    ) -> Dict[str, Any]:
        """Merge with special list handling (append or union)."""
        if not configs:
            return {}

        result = configs[0]
        for config in configs[1:]:
            result = self._merge_lists_recursive(result, config, list_mode, context)
        return result

    def _merge_lists_recursive(
        self,
        base: Dict[str, Any],
        override: Dict[str, Any],
        list_mode: str,
        context: MergeContext,
        path: str = "",
    ) -> Dict[str, Any]:
        """Recursively merge dicts with special list handling."""
        result = base.copy()
        for key, value in override.items():
            current_path = f"{path}.{key}" if path else key
            if key in result:
                base_val = result[key]
                if isinstance(base_val, dict) and isinstance(value, dict):
                    result[key] = self._merge_lists_recursive(
                        base_val, value, list_mode, context, current_path
                    )
                elif isinstance(base_val, list) and isinstance(value, list):
                    if list_mode == "append":
                        result[key] = base_val + value
                    else:  # union
                        seen = set()
                        merged_list = []
                        for item in base_val + value:
                            try:
                                key_repr = (
                                    item if isinstance(item, Hashable) else id(item)
                                )
                            except TypeError:
                                key_repr = id(item)
                            if key_repr not in seen:
                                seen.add(key_repr)
                                merged_list.append(item)
                        result[key] = merged_list
                    context.add_merged_path(current_path)
                else:
                    result[key] = value
            else:
                result[key] = value
                context.add_merged_path(current_path)
        return result
