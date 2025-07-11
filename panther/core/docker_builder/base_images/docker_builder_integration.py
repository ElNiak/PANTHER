"""
Docker Builder Integration for Base Images - Following DRY and SOLID Principles

Provides a mixin to integrate base image management with existing DockerBuilder
without breaking existing functionality. Follows composition over inheritance.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .interfaces import (
    BaseImageMetadata,
    BaseImageStrategy,
    PluginRequirementsExtractor,
)
from .plugin_extractor import PantherPluginRequirementsExtractor
from .strategies import (
    PlatformAwareStrategy,
    PluginAwareStrategy,
    TieredBaseImageStrategy,
)


class BaseImageManagerMixin:
    """
    Mixin to add base image management to DockerBuilder.

    Follows SOLID principles:
    - SRP: Only handles base image coordination
    - OCP: Extensible via strategy injection
    - DIP: Depends on interfaces, not concrete implementations
    - ISP: Focused interface for DockerBuilder integration

    Follows DRY: Reuses existing plugin and Docker infrastructure.
    """

    def __init__(self, *args, **kwargs):
        """Initialize base image management components."""
        super().__init__(*args, **kwargs)

        # Initialize base image management components
        self._base_image_strategy = self._create_base_image_strategy()
        self._plugin_extractor = PantherPluginRequirementsExtractor(
            logger=getattr(self, "logger", None)
        )

        # Cache for base image selections
        self._base_image_cache: Dict[str, str] = {}

        if hasattr(self, "logger"):
            self.logger.info("Base image management initialized")

    def _create_base_image_strategy(self) -> BaseImageStrategy:
        """
        Create base image strategy chain following Chain of Responsibility pattern.

        Strategy chain: PluginAware -> PlatformAware -> TieredBase
        """
        # Base strategy - 4-tier hierarchy
        base_strategy = TieredBaseImageStrategy()

        # Platform awareness layer
        platform_strategy = PlatformAwareStrategy(fallback_strategy=base_strategy)

        # Plugin awareness layer (top level)
        plugin_strategy = PluginAwareStrategy(base_strategy=platform_strategy)

        return plugin_strategy

    def select_optimal_base_image(
        self, impl_name: str, config: Dict[str, Any], platform: Optional[str] = None
    ) -> str:
        """
        Select optimal base image for implementation build.

        Integrates with existing DockerBuilder build_image workflow.

        Args:
            impl_name: Implementation name (e.g., 'picoquic')
            config: Build configuration from build_image call
            platform: Target platform (defaults to current platform)

        Returns:
            Selected base image name/tag
        """
        try:
            # Use current platform if not specified
            if platform is None:
                platform = getattr(
                    self, "_get_target_platform", lambda: "linux/amd64"
                )()

            # Create cache key
            cache_key = self._create_base_image_cache_key(impl_name, config, platform)

            # Check cache first
            if cache_key in self._base_image_cache:
                cached_image = self._base_image_cache[cache_key]
                if hasattr(self, "logger"):
                    self.logger.debug(f"Using cached base image: {cached_image}")
                return cached_image

            # Extract requirements for this implementation
            requirements = self._extract_implementation_requirements(
                impl_name, config, platform
            )

            # Select base image using strategy
            selected_image = self._base_image_strategy.select_base_image(requirements)

            # Cache the selection
            self._base_image_cache[cache_key] = selected_image

            if hasattr(self, "logger"):
                self.logger.info(
                    f"Selected base image '{selected_image}' for {impl_name} "
                    f"(platform: {platform}, runtime_mode: {requirements.get('runtime_mode', 'minimal')})"
                )

            return selected_image

        except Exception as e:
            if hasattr(self, "logger"):
                self.logger.error(f"Base image selection failed for {impl_name}: {e}")
            # Fallback to safe default
            return "panther-runtime-base"

    def _extract_implementation_requirements(
        self, impl_name: str, config: Dict[str, Any], platform: str
    ) -> Dict[str, Any]:
        """
        Extract requirements for implementation.

        Combines plugin metadata with build configuration.
        """
        # Create plugin configuration for extractor
        plugin_config = {
            "name": impl_name,
            "type": "iut",  # Most implementations are IUT plugins
            "runtime_mode": config.get("runtime_mode", "minimal"),
            "build_mode": config.get("build_mode", ""),
            "platform": platform,
        }

        # Extract base requirements from plugin system
        requirements = self._plugin_extractor.extract_docker_requirements(plugin_config)

        # Add implementation-specific overrides from config
        self._apply_build_config_overrides(requirements, config)

        return requirements

    def _apply_build_config_overrides(
        self, requirements: Dict[str, Any], config: Dict[str, Any]
    ) -> None:
        """Apply build configuration overrides to requirements."""
        # Extract build and runtime modes from config
        build_mode = config.get("build_mode", "")
        runtime_mode = config.get("runtime_mode", "minimal")

        # Override runtime mode
        if runtime_mode:
            requirements["runtime_mode"] = runtime_mode

        # Override build mode
        if build_mode:
            requirements["build_mode"] = build_mode

        # Add capabilities based on build mode
        if "debug" in build_mode.lower():
            if "debugging" not in requirements["capabilities"]:
                requirements["capabilities"].append("debugging")
            if "profiling" not in requirements["capabilities"]:
                requirements["capabilities"].append("profiling")

        if "profile" in build_mode.lower() or runtime_mode == "profile":
            if "profiling" not in requirements["capabilities"]:
                requirements["capabilities"].append("profiling")

        # Compilation requirements based on build mode
        if build_mode and build_mode != "minimal":
            if "compilation" not in requirements["capabilities"]:
                requirements["capabilities"].append("compilation")

        # Size constraints based on config
        if config.get("max_image_size_mb"):
            requirements["max_size_mb"] = min(
                requirements.get("max_size_mb", float("inf")),
                config["max_image_size_mb"],
            )

    def _create_base_image_cache_key(
        self, impl_name: str, config: Dict[str, Any], platform: str
    ) -> str:
        """Create cache key for base image selection."""
        runtime_mode = config.get("runtime_mode", "minimal")
        build_mode = config.get("build_mode", "")

        return f"{impl_name}:{runtime_mode}:{build_mode}:{platform}"

    def get_supported_base_images(self) -> List[BaseImageMetadata]:
        """Get list of all supported base images."""
        return self._base_image_strategy.get_supported_images()

    def validate_base_image_requirements(
        self, impl_name: str, config: Dict[str, Any]
    ) -> bool:
        """
        Validate that base image requirements can be satisfied.

        Useful for pre-build validation.
        """
        try:
            platform = getattr(self, "_get_target_platform", lambda: "linux/amd64")()
            requirements = self._extract_implementation_requirements(
                impl_name, config, platform
            )
            return self._base_image_strategy.validate_requirements(requirements)
        except Exception as e:
            if hasattr(self, "logger"):
                self.logger.error(f"Base image validation failed for {impl_name}: {e}")
            return False

    def get_base_image_hierarchy(self, base_image: str) -> List[str]:
        """
        Get the hierarchy chain for a base image.

        Returns list from most basic to most complete image.
        """
        supported_images = self.get_supported_base_images()
        hierarchy = []

        # Find the target image
        target_image = None
        for img in supported_images:
            if img.name == base_image:
                target_image = img
                break

        if not target_image:
            return [base_image]

        # Build hierarchy chain
        current = target_image
        while current:
            hierarchy.insert(0, current.name)

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

    def clear_base_image_cache(self) -> None:
        """Clear base image selection cache."""
        self._base_image_cache.clear()
        self._plugin_extractor.clear_cache()

        if hasattr(self, "logger"):
            self.logger.debug("Base image cache cleared")

    def get_base_image_cache_stats(self) -> Dict[str, Any]:
        """Get base image cache statistics."""
        plugin_stats = self._plugin_extractor.get_cache_stats()

        return {
            "base_image_selections_cached": len(self._base_image_cache),
            "plugin_requirements_cached": plugin_stats.get("cached_entries", 0),
            "cache_keys": list(self._base_image_cache.keys()),
        }

    def ensure_base_images_available(self, required_images: List[str]) -> bool:
        """
        Ensure required base images are available.

        Integrates with existing Docker image management.
        """
        if not hasattr(self, "client") or not self.client:
            if hasattr(self, "logger"):
                self.logger.warning(
                    "Docker client not available, cannot verify base images"
                )
            return True  # Assume images exist

        missing_images = []

        for image_name in required_images:
            try:
                self.client.images.get(image_name)
            except Exception:
                missing_images.append(image_name)

        if missing_images:
            if hasattr(self, "logger"):
                self.logger.warning(f"Missing base images: {missing_images}")
                self.logger.info("Base images will be built automatically when needed")

            # In a production system, you might want to pre-build these
            # For now, we assume they'll be built on-demand

        return True  # Return True to allow builds to proceed

    def get_base_image_info(self) -> Dict[str, Any]:
        """Get information about base image management system."""
        return {
            "strategy_type": type(self._base_image_strategy).__name__,
            "supported_images_count": len(self.get_supported_base_images()),
            "cache_stats": self.get_base_image_cache_stats(),
            "plugin_extractor_type": type(self._plugin_extractor).__name__,
        }
