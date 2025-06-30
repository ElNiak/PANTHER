"""Caching mixin for ConfigurationManager."""

import hashlib
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from panther.core.utils.logging_mixin import LoggerMixin

from ..base import BaseConfig

if TYPE_CHECKING:
    from ..models import ExperimentConfig


class CachingMixin(LoggerMixin):
    """Handles configuration caching for improved performance."""

    def __init__(self):
        """Initialize caching system."""
        super().__init__()
        self._loaded_experiments: Dict[str, "ExperimentConfig"] = {}
        self._validation_cache: Dict[str, bool] = {}
        self._plugin_cache: Optional[Dict[str, Any]] = None
        self._schema_cache: Optional[Dict[str, Any]] = None
        self._version_cache: Dict[str, Dict[str, List[str]]] = {}
        self._cache_hits = 0
        self._cache_misses = 0

    def clear_cache(self) -> None:
        """Clear all caches."""
        self.logger.info("Clearing all configuration caches")

        self._loaded_experiments.clear()
        self._validation_cache.clear()
        self._plugin_cache = None
        self._schema_cache = None
        self._version_cache.clear()

        # Reset statistics
        self._cache_hits = 0
        self._cache_misses = 0

        self.logger.debug("All caches cleared")

    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get cache usage statistics.

        Returns:
            Dictionary with cache statistics
        """
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = (
            (self._cache_hits / total_requests * 100) if total_requests > 0 else 0
        )

        return {
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_rate": f"{hit_rate:.1f}%",
            "cached_experiments": len(self._loaded_experiments),
            "cached_validations": len(self._validation_cache),
            "cached_plugins": self._plugin_cache is not None,
            "cached_schemas": self._schema_cache is not None,
            "cached_versions": len(self._version_cache),
            "memory_usage": self._estimate_cache_memory(),
        }

    def _generate_cache_key(
        self, source: Any, defaults: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate a cache key for configuration.

        Args:
            source: Configuration source
            defaults: Default values applied

        Returns:
            Cache key string
        """
        # Create a hashable representation
        key_parts = []

        # Handle different source types
        if isinstance(source, (str, Path)):
            key_parts.append(f"file:{source}")
            # Include file modification time if available
            try:
                mtime = Path(source).stat().st_mtime
                key_parts.append(f"mtime:{mtime}")
            except:
                pass
        elif isinstance(source, dict):
            # Hash the dictionary content
            dict_str = json.dumps(source, sort_keys=True)
            dict_hash = hashlib.md5(dict_str.encode()).hexdigest()
            key_parts.append(f"dict:{dict_hash}")
        else:
            key_parts.append(f"obj:{id(source)}")

        # Include defaults if provided
        if defaults:
            defaults_str = json.dumps(defaults, sort_keys=True)
            defaults_hash = hashlib.md5(defaults_str.encode()).hexdigest()
            key_parts.append(f"defaults:{defaults_hash}")

        # Combine parts
        return "|".join(key_parts)

    def preload_configurations(self, configs: List[Path]) -> None:
        """Preload configurations into cache.

        Args:
            configs: List of configuration file paths to preload
        """
        self.logger.info(f"Preloading {len(configs)} configurations")

        loaded = 0
        for config_path in configs:
            try:
                if config_path.exists():
                    # Load through normal mechanism to populate cache
                    self.load_experiment_config(config_path, validate=False)
                    loaded += 1
            except Exception as e:
                self.logger.warning(f"Failed to preload {config_path}: {e}")

        self.logger.info(f"Preloaded {loaded} configurations successfully")

    def _get_from_cache(self, key: str) -> Optional[BaseConfig]:
        """Get configuration from cache.

        Args:
            key: Cache key

        Returns:
            Cached configuration or None
        """
        if key in self._loaded_experiments:
            self._cache_hits += 1
            self.logger.debug(f"Cache hit for key: {key}")
            return self._loaded_experiments[key]

        self._cache_misses += 1
        self.logger.debug(f"Cache miss for key: {key}")
        return None

    def _add_to_cache(self, key: str, config: BaseConfig) -> None:
        """Add configuration to cache.

        Args:
            key: Cache key
            config: Configuration to cache
        """
        self._loaded_experiments[key] = config
        self.logger.debug(f"Added to cache: {key}")

        # Implement simple LRU eviction if cache gets too large
        max_cache_size = getattr(self, "max_cache_size", 100)
        if len(self._loaded_experiments) > max_cache_size:
            # Remove oldest entry (first in dict)
            oldest_key = next(iter(self._loaded_experiments))
            del self._loaded_experiments[oldest_key]
            self.logger.debug(f"Evicted from cache: {oldest_key}")

    def _cache_validation_result(self, config_key: str, is_valid: bool) -> None:
        """Cache validation result.

        Args:
            config_key: Configuration cache key
            is_valid: Validation result
        """
        self._validation_cache[config_key] = is_valid

    def _get_cached_validation(self, config_key: str) -> Optional[bool]:
        """Get cached validation result.

        Args:
            config_key: Configuration cache key

        Returns:
            Cached validation result or None
        """
        return self._validation_cache.get(config_key)

    def _estimate_cache_memory(self) -> str:
        """Estimate memory usage of caches.

        Returns:
            Human-readable memory estimate
        """
        # Rough estimation based on object counts
        # In reality, would need sys.getsizeof for accurate measurement

        exp_size = len(self._loaded_experiments) * 10  # ~10KB per experiment
        val_size = len(self._validation_cache) * 0.1  # ~100B per validation
        plugin_size = 5 if self._plugin_cache else 0  # ~5KB for plugin cache
        schema_size = 10 if self._schema_cache else 0  # ~10KB for schema cache
        version_size = len(self._version_cache) * 1  # ~1KB per version entry

        total_kb = exp_size + val_size + plugin_size + schema_size + version_size

        if total_kb < 1024:
            return f"{total_kb:.1f}KB"
        else:
            return f"{total_kb/1024:.1f}MB"

    def invalidate_cache_entry(self, key: str) -> None:
        """Invalidate a specific cache entry.

        Args:
            key: Cache key to invalidate
        """
        if key in self._loaded_experiments:
            del self._loaded_experiments[key]
            self.logger.debug(f"Invalidated cache entry: {key}")

        if key in self._validation_cache:
            del self._validation_cache[key]

    def warm_cache(self) -> None:
        """Warm up caches by preloading common configurations."""
        self.logger.info("Warming up configuration caches")

        # Preload plugin information
        if hasattr(self, "discover_plugins"):
            self.discover_plugins(force_refresh=True)

        # Preload schemas
        if hasattr(self, "load_plugin_schemas"):
            self.load_plugin_schemas(force_refresh=True)

        # Preload version information
        if hasattr(self, "discover_available_versions"):
            self.discover_available_versions()

        self.logger.info("Cache warming completed")
