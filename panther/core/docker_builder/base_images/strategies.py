"""
Base Image Strategies - Strategy Pattern Implementation with SOLID Principles

Implements concrete strategies following:
- Open/Closed Principle: Extensible without modifying existing strategies
- Liskov Substitution Principle: All strategies are interchangeable
- Single Responsibility: Each strategy handles one selection approach
- DRY Principle: Shared logic in base classes, no code duplication
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .interfaces import BaseImageMetadata, BaseImageStrategy


class TieredBaseImageStrategy(BaseImageStrategy):
    """
    4-Tier hierarchical base image strategy following DRY and SOLID principles.

    Hierarchy: runtime -> dev -> build -> builder
    - runtime: Minimal production images
    - dev: Development with debug tools
    - build: Compilation and build tools
    - builder: Full development environment

    Follows OCP: Can extend with new tiers without modifying existing code.
    Follows SRP: Only handles tiered selection logic.
    """

    def __init__(self):
        self._base_images = self._initialize_base_image_registry()

    def _initialize_base_image_registry(self) -> Dict[str, BaseImageMetadata]:
        """Initialize base image registry with metadata - DRY principle."""
        return {
            # Runtime tier - minimal images
            "panther-runtime-base": BaseImageMetadata(
                name="panther-runtime-base",
                size_mb=150,
                packages=["ca-certificates", "curl"],
                capabilities=["runtime", "networking"],
                platform_support=["linux/amd64", "linux/arm64"],
                security_features=["non-root", "minimal-attack-surface"],
            ),
            # Dev tier - development tools
            "panther-dev-base": BaseImageMetadata(
                name="panther-dev-base",
                size_mb=300,
                packages=["ca-certificates", "curl", "git", "python3", "pip"],
                capabilities=["runtime", "networking", "development", "python"],
                parent_image="panther-runtime-base",
                platform_support=["linux/amd64", "linux/arm64"],
                security_features=["non-root"],
            ),
            # Build tier - compilation tools
            "panther-build-base": BaseImageMetadata(
                name="panther-build-base",
                size_mb=800,
                packages=[
                    "ca-certificates",
                    "curl",
                    "git",
                    "python3",
                    "pip",
                    "build-essential",
                    "cmake",
                ],
                capabilities=[
                    "runtime",
                    "networking",
                    "development",
                    "python",
                    "compilation",
                    "cmake",
                ],
                parent_image="panther-dev-base",
                platform_support=["linux/amd64", "linux/arm64"],
                security_features=["build-isolation"],
            ),
            # Builder tier - full development environment
            "panther-builder": BaseImageMetadata(
                name="panther-builder",
                size_mb=1200,
                packages=[
                    "ca-certificates",
                    "curl",
                    "git",
                    "python3",
                    "pip",
                    "build-essential",
                    "cmake",
                    "gdb",
                    "valgrind",
                    "strace",
                ],
                capabilities=[
                    "runtime",
                    "networking",
                    "development",
                    "python",
                    "compilation",
                    "cmake",
                    "debugging",
                    "profiling",
                ],
                parent_image="panther-build-base",
                platform_support=["linux/amd64", "linux/arm64"],
                security_features=["build-isolation", "debug-capabilities"],
            ),
        }

    def select_base_image(self, requirements: Dict[str, any]) -> str:
        """
        Select optimal base image from 4-tier hierarchy.

        Strategy: Start from minimal and move up hierarchy as requirements increase.
        Follows DRY: Single algorithm for all tier selections.
        """
        required_capabilities = requirements.get("capabilities", [])
        max_size_mb = requirements.get("max_size_mb", float("inf"))
        platform = requirements.get("platform", "linux/amd64")

        # Define tier ordering - DRY principle: single source of truth
        tier_order = [
            "panther-runtime-base",
            "panther-dev-base",
            "panther-build-base",
            "panther-builder",
        ]

        for image_name in tier_order:
            image_meta = self._base_images[image_name]

            # Check constraints
            if not self._meets_requirements(
                image_meta, required_capabilities, max_size_mb, platform
            ):
                continue

            return image_name

        # Fallback: use largest image if none match perfectly
        return "panther-builder"

    def _meets_requirements(
        self,
        image_meta: BaseImageMetadata,
        required_capabilities: List[str],
        max_size_mb: float,
        platform: str,
    ) -> bool:
        """
        Check if image meets all requirements - Single Responsibility.

        Extracted to separate method following SRP and DRY principles.
        """
        # Size constraint
        if image_meta.size_mb > max_size_mb:
            return False

        # Platform support
        if not image_meta.supports_platform(platform):
            return False

        # Capability requirements
        for capability in required_capabilities:
            if not image_meta.has_capability(capability):
                return False

        return True

    def get_supported_images(self) -> List[BaseImageMetadata]:
        """Get all supported base images in hierarchy order."""
        tier_order = [
            "panther-runtime-base",
            "panther-dev-base",
            "panther-build-base",
            "panther-builder",
        ]
        return [self._base_images[name] for name in tier_order]

    def validate_requirements(self, requirements: Dict[str, any]) -> bool:
        """Validate requirements can be satisfied by at least one tier."""
        try:
            selected = self.select_base_image(requirements)
            return selected is not None
        except Exception:
            return False


class PlatformAwareStrategy(BaseImageStrategy):
    """
    Platform-specific base image selection following SOLID principles.

    Follows SRP: Only handles platform-specific selection logic.
    Follows OCP: Extensible for new platforms without modifying existing code.
    """

    def __init__(self, fallback_strategy: BaseImageStrategy):
        """
        Use Dependency Inversion Principle: Depend on abstraction, not concrete strategy.
        """
        self._fallback_strategy = fallback_strategy
        self._platform_mappings = self._initialize_platform_mappings()

    def _initialize_platform_mappings(self) -> Dict[str, Dict[str, str]]:
        """Platform-specific image mappings - DRY principle."""
        return {
            "linux/amd64": {
                "runtime": "panther-runtime-base:amd64",
                "development": "panther-dev-base:amd64",
                "build": "panther-build-base:amd64",
                "full": "panther-builder:amd64",
            },
            "linux/arm64": {
                "runtime": "panther-runtime-base:arm64",
                "development": "panther-dev-base:arm64",
                "build": "panther-build-base:arm64",
                "full": "panther-builder:arm64",
            },
            "linux/arm/v7": {
                "runtime": "panther-runtime-base:armv7",
                "development": "panther-dev-base:armv7",
                "build": "panther-build-base:armv7",
                "full": "panther-builder:armv7",
            },
        }

    def select_base_image(self, requirements: Dict[str, any]) -> str:
        """
        Platform-aware selection with intelligent fallback.

        Follows LSP: Can substitute for any BaseImageStrategy.
        """
        platform = requirements.get("platform", "linux/amd64")
        tier = self._determine_tier_from_requirements(requirements)

        # Try platform-specific mapping first
        if platform in self._platform_mappings:
            platform_images = self._platform_mappings[platform]
            if tier in platform_images:
                return platform_images[tier]

        # Fallback to base strategy (Composition over Inheritance)
        return self._fallback_strategy.select_base_image(requirements)

    def _determine_tier_from_requirements(self, requirements: Dict[str, any]) -> str:
        """Determine tier based on capabilities - DRY principle."""
        capabilities = requirements.get("capabilities", [])

        # Tier determination logic - single source of truth
        if any(cap in capabilities for cap in ["debugging", "profiling"]):
            return "full"
        elif any(cap in capabilities for cap in ["compilation", "cmake"]):
            return "build"
        elif any(cap in capabilities for cap in ["development", "python"]):
            return "development"
        else:
            return "runtime"

    def get_supported_images(self) -> List[BaseImageMetadata]:
        """Delegate to fallback strategy - DRY principle."""
        return self._fallback_strategy.get_supported_images()

    def validate_requirements(self, requirements: Dict[str, any]) -> bool:
        """Validate with platform awareness."""
        platform = requirements.get("platform", "linux/amd64")

        # Check if platform is supported
        if platform not in self._platform_mappings:
            # Fall back to base strategy validation
            return self._fallback_strategy.validate_requirements(requirements)

        # Platform supported, delegate to fallback for detailed validation
        return self._fallback_strategy.validate_requirements(requirements)


class PluginAwareStrategy(BaseImageStrategy):
    """
    Plugin-specific base image selection following SOLID principles.

    Analyzes plugin requirements and selects optimal base images.
    Follows SRP: Only handles plugin-specific selection logic.
    """

    def __init__(self, base_strategy: BaseImageStrategy):
        """Composition: Use base strategy for core selection logic."""
        self._base_strategy = base_strategy
        self._plugin_requirements_cache = {}

    def select_base_image(self, requirements: Dict[str, any]) -> str:
        """
        Select base image considering plugin-specific needs.

        Enhances base strategy with plugin analysis.
        """
        # Extract plugin information
        plugins = requirements.get("plugins", [])

        # Augment requirements with plugin-specific needs
        enhanced_requirements = self._enhance_requirements_with_plugins(
            requirements, plugins
        )

        # Delegate to base strategy with enhanced requirements
        return self._base_strategy.select_base_image(enhanced_requirements)

    def _enhance_requirements_with_plugins(
        self, base_requirements: Dict[str, any], plugins: List[str]
    ) -> Dict[str, any]:
        """
        Enhance requirements based on plugin analysis - DRY principle.

        Single method handles all plugin enhancement logic.
        """
        enhanced = base_requirements.copy()

        # Collect capabilities from all plugins
        all_capabilities = set(enhanced.get("capabilities", []))

        for plugin in plugins:
            plugin_caps = self._get_plugin_capabilities(plugin)
            all_capabilities.update(plugin_caps)

        enhanced["capabilities"] = list(all_capabilities)

        # Adjust size requirements if needed
        if len(plugins) > 3:  # Many plugins need more space
            current_max = enhanced.get("max_size_mb", float("inf"))
            enhanced["max_size_mb"] = min(current_max, 1500)  # Allow larger images

        return enhanced

    def _get_plugin_capabilities(self, plugin_name: str) -> List[str]:
        """
        Get capabilities required by specific plugin - caching for performance.

        DRY principle: Single source for plugin capability mapping.
        """
        if plugin_name in self._plugin_requirements_cache:
            return self._plugin_requirements_cache[plugin_name]

        # Plugin capability mapping
        plugin_capabilities = {
            "quic": ["networking", "compilation"],
            "ivy": ["python", "debugging", "compilation"],
            "http": ["networking"],
            "strace": ["debugging", "profiling"],
            "gdb": ["debugging"],
            "valgrind": ["debugging", "profiling"],
            "picoquic": ["networking", "compilation", "cmake"],
            "quiche": ["networking", "compilation"],
            "default": ["runtime"],
        }

        capabilities = plugin_capabilities.get(
            plugin_name, plugin_capabilities["default"]
        )
        self._plugin_requirements_cache[plugin_name] = capabilities
        return capabilities

    def get_supported_images(self) -> List[BaseImageMetadata]:
        """Delegate to base strategy."""
        return self._base_strategy.get_supported_images()

    def validate_requirements(self, requirements: Dict[str, any]) -> bool:
        """Validate with plugin awareness."""
        plugins = requirements.get("plugins", [])
        enhanced_requirements = self._enhance_requirements_with_plugins(
            requirements, plugins
        )
        return self._base_strategy.validate_requirements(enhanced_requirements)
