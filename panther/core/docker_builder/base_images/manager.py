"""
Base Image Manager - Facade Pattern with SOLID Principles

Coordinates base image operations following:
- Single Responsibility: Only manages base image orchestration
- Dependency Inversion: Depends on abstractions, not concrete implementations
- Open/Closed: Extensible through strategy injection
- DRY: Central coordination without duplication
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .interfaces import (
    BaseImageBuilder,
    BaseImageCache,
    BaseImageMetadata,
    BaseImageStrategy,
    PluginRequirementsExtractor,
)
from .strategies import (
    PlatformAwareStrategy,
    PluginAwareStrategy,
    TieredBaseImageStrategy,
)


class BaseImageManager:
    """
    Facade for base image operations following SOLID and DRY principles.

    Coordinates:
    - Strategy-based image selection
    - Caching operations
    - Plugin requirements analysis
    - Image building coordination

    Follows Facade pattern: Simplifies complex subsystem interactions.
    Follows DIP: Depends on interfaces, not concrete implementations.
    """

    def __init__(
        self,
        cache: Optional[BaseImageCache] = None,
        builder: Optional[BaseImageBuilder] = None,
        requirements_extractor: Optional[PluginRequirementsExtractor] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize with dependency injection - Dependency Inversion Principle.

        Args:
            cache: Base image cache implementation
            builder: Base image builder implementation
            requirements_extractor: Plugin requirements analyzer
            logger: Logger instance
        """
        self._cache = cache
        self._builder = builder
        self._requirements_extractor = requirements_extractor
        self._logger = logger or logging.getLogger(__name__)

        # Initialize strategy chain following Chain of Responsibility + Strategy patterns
        self._strategy_chain = self._build_strategy_chain()

    def _build_strategy_chain(self) -> BaseImageStrategy:
        """
        Build strategy chain following Chain of Responsibility + Decorator patterns.

        Chain: PluginAware -> PlatformAware -> TieredBase
        Each layer adds capabilities while delegating to the next.
        """
        # Base strategy - handles core tier selection
        base_strategy = TieredBaseImageStrategy()

        # Platform awareness layer
        platform_strategy = PlatformAwareStrategy(fallback_strategy=base_strategy)

        # Plugin awareness layer (top level)
        plugin_strategy = PluginAwareStrategy(base_strategy=platform_strategy)

        return plugin_strategy

    def select_optimal_base_image(
        self,
        plugin_config: Dict[str, Any],
        build_config: Dict[str, Any],
        platform: str = "linux/amd64",
    ) -> str:
        """
        Select optimal base image using strategy chain.

        Main entry point for base image selection following Facade pattern.

        Args:
            plugin_config: Plugin configuration and requirements
            build_config: Build-specific configuration
            platform: Target platform

        Returns:
            Selected base image name/tag
        """
        try:
            # Extract requirements using composition
            requirements = self._extract_unified_requirements(
                plugin_config, build_config, platform
            )

            # Check cache first (performance optimization)
            cached_image = self._check_cache(requirements)
            if cached_image:
                self._logger.debug(f"Using cached base image: {cached_image}")
                return cached_image

            # Use strategy chain for selection
            selected_image = self._strategy_chain.select_base_image(requirements)

            # Cache result for future use
            self._cache_selection(requirements, selected_image)

            self._logger.info(
                f"Selected base image: {selected_image} for platform: {platform}"
            )
            return selected_image

        except Exception as e:
            self._logger.error(f"Base image selection failed: {e}")
            # Fallback to safest option
            return "panther-runtime-base"

    def _extract_unified_requirements(
        self, plugin_config: Dict[str, Any], build_config: Dict[str, Any], platform: str
    ) -> Dict[str, Any]:
        """
        Extract and unify requirements from multiple sources - DRY principle.

        Single method handles all requirement extraction logic.
        """
        unified_requirements = {
            "platform": platform,
            "capabilities": [],
            "packages": [],
            "plugins": [],
            "max_size_mb": float("inf"),
        }

        # Extract from plugin config
        if self._requirements_extractor and plugin_config:
            plugin_reqs = self._requirements_extractor.extract_docker_requirements(
                plugin_config
            )
            self._merge_requirements(unified_requirements, plugin_reqs)

        # Extract from build config
        if build_config:
            build_reqs = self._extract_build_requirements(build_config)
            self._merge_requirements(unified_requirements, build_reqs)

        return unified_requirements

    def _extract_build_requirements(
        self, build_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract requirements from build configuration - Single Responsibility.
        """
        build_mode = build_config.get("build_mode", "")
        runtime_mode = build_config.get("runtime_mode", "minimal")

        requirements = {"capabilities": [], "max_size_mb": float("inf")}

        # Map build modes to capabilities
        if "debug" in build_mode.lower():
            requirements["capabilities"].extend(["debugging", "profiling"])

        if "release" in build_mode.lower():
            requirements["capabilities"].append("compilation")

        if runtime_mode == "full":
            requirements["capabilities"].extend(["development", "debugging"])
        elif runtime_mode == "minimal":
            requirements["max_size_mb"] = 500  # Prefer smaller images

        return requirements

    def _merge_requirements(
        self, base: Dict[str, Any], additional: Dict[str, Any]
    ) -> None:
        """
        Merge additional requirements into base requirements - DRY principle.
        """
        for key, value in additional.items():
            if key in base:
                if isinstance(base[key], list) and isinstance(value, list):
                    # Merge lists without duplicates
                    base[key] = list(set(base[key] + value))
                elif key == "max_size_mb":
                    # Take minimum size constraint
                    base[key] = min(base[key], value)
                else:
                    # Override with new value
                    base[key] = value
            else:
                base[key] = value

    def _check_cache(self, requirements: Dict[str, Any]) -> Optional[str]:
        """Check cache for previously selected base image."""
        if not self._cache:
            return None

        # Create cache key from requirements
        cache_key = self._create_cache_key(requirements)
        platform = requirements.get("platform", "linux/amd64")

        return self._cache.get_cached_image(cache_key, platform)

    def _cache_selection(
        self, requirements: Dict[str, Any], selected_image: str
    ) -> None:
        """Cache the selection for future use."""
        if not self._cache:
            return

        cache_key = self._create_cache_key(requirements)
        platform = requirements.get("platform", "linux/amd64")

        # Create metadata for caching
        metadata = BaseImageMetadata(
            name=selected_image,
            size_mb=0,  # Will be populated by cache implementation
            packages=[],
            capabilities=requirements.get("capabilities", []),
        )

        self._cache.cache_image(cache_key, selected_image, platform, metadata)

    def _create_cache_key(self, requirements: Dict[str, Any]) -> str:
        """
        Create deterministic cache key from requirements - DRY principle.
        """
        # Sort to ensure consistent keys
        capabilities = sorted(requirements.get("capabilities", []))
        plugins = sorted(requirements.get("plugins", []))
        platform = requirements.get("platform", "linux/amd64")
        max_size = requirements.get("max_size_mb", float("inf"))

        return f"{platform}:{':'.join(capabilities)}:{':'.join(plugins)}:{max_size}"

    def ensure_base_images_available(
        self, required_images: List[str], platform: str = "linux/amd64"
    ) -> bool:
        """
        Ensure all required base images are built and available.

        Coordinates with builder following Single Responsibility Principle.
        """
        if not self._builder:
            self._logger.warning("No builder configured, assuming images exist")
            return True

        try:
            return self._builder.ensure_base_images_exist(required_images)
        except Exception as e:
            self._logger.error(f"Failed to ensure base images: {e}")
            return False

    def get_supported_images(self) -> List[BaseImageMetadata]:
        """Get all supported base images from strategy chain."""
        return self._strategy_chain.get_supported_images()

    def validate_configuration(
        self, plugin_config: Dict[str, Any], build_config: Dict[str, Any]
    ) -> bool:
        """
        Validate that configuration can be satisfied by available base images.

        Coordinates validation across all components.
        """
        try:
            requirements = self._extract_unified_requirements(
                plugin_config,
                build_config,
                "linux/amd64",  # Default platform for validation
            )

            return self._strategy_chain.validate_requirements(requirements)

        except Exception as e:
            self._logger.error(f"Configuration validation failed: {e}")
            return False

    def get_image_hierarchy(self, base_image: str) -> List[str]:
        """
        Get the hierarchy chain for a base image - useful for dependency analysis.

        Returns list from most basic to most complete image.
        """
        supported_images = self.get_supported_images()
        hierarchy = []

        # Find the target image
        target_image = None
        for img in supported_images:
            if img.name == base_image:
                target_image = img
                break

        if not target_image:
            return [base_image]  # Unknown image, return as-is

        # Build hierarchy chain
        current = target_image
        while current:
            hierarchy.insert(0, current.name)  # Add to front

            # Find parent
            if current.parent_image:
                parent = None
                for img in supported_images:
                    if img.name == current.parent_image:
                        parent = img
                        break
                current = parent
            else:
                current = None

        return hierarchy

    def invalidate_cache(self, cache_pattern: Optional[str] = None) -> None:
        """
        Invalidate cache entries matching pattern.

        Args:
            cache_pattern: Pattern to match cache keys, None for all
        """
        if not self._cache:
            return

        if cache_pattern:
            self._cache.invalidate_cache(cache_pattern)
        else:
            # Clear all cache - implementation dependent
            self._logger.info("Cache invalidation requested")

    def get_strategy_chain_info(self) -> Dict[str, Any]:
        """
        Get information about the current strategy chain - useful for debugging.
        """
        return {
            "strategy_type": type(self._strategy_chain).__name__,
            "supported_images_count": len(self.get_supported_images()),
            "cache_enabled": self._cache is not None,
            "builder_enabled": self._builder is not None,
            "requirements_extractor_enabled": self._requirements_extractor is not None,
        }
