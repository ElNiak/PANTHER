"""
Base Images Interfaces - SOLID Interface Segregation Principle

Defines focused interfaces for base image management without forcing clients
to depend on methods they don't use.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set


@dataclass
class BaseImageMetadata:
    """Metadata for base images following Single Responsibility Principle."""

    name: str
    size_mb: int
    packages: List[str]
    capabilities: List[str]
    parent_image: Optional[str] = None
    platform_support: Optional[List[str]] = None
    security_features: Optional[List[str]] = None

    def supports_platform(self, platform: str) -> bool:
        """Check if base image supports target platform."""
        if not self.platform_support:
            return True  # Default to universal support
        return platform in self.platform_support

    def has_capability(self, capability: str) -> bool:
        """Check if base image provides specific capability."""
        return capability in self.capabilities


class BaseImageStrategy(ABC):
    """
    Abstract strategy for base image selection - Strategy Pattern + OCP.

    Open for extension (new strategies), closed for modification.
    Follows Single Responsibility: only handles base image selection logic.
    """

    @abstractmethod
    def select_base_image(self, requirements: Dict[str, any]) -> str:
        """
        Select optimal base image based on requirements.

        Args:
            requirements: Plugin requirements including packages, capabilities, size constraints

        Returns:
            Base image name/tag
        """
        pass

    @abstractmethod
    def get_supported_images(self) -> List[BaseImageMetadata]:
        """Get list of base images supported by this strategy."""
        pass

    @abstractmethod
    def validate_requirements(self, requirements: Dict[str, any]) -> bool:
        """Validate that requirements can be satisfied by available base images."""
        pass


class BaseImageBuilder(ABC):
    """
    Interface for building base images - Interface Segregation Principle.

    Separate from selection logic to avoid coupling.
    """

    @abstractmethod
    def build_base_image(
        self, image_name: str, dockerfile_path: Path, context_path: Path, platform: str
    ) -> Optional[str]:
        """Build base image with platform support."""
        pass

    @abstractmethod
    def ensure_base_images_exist(self, required_images: List[str]) -> bool:
        """Ensure all required base images are built and available."""
        pass


class BaseImageCache(ABC):
    """
    Interface for base image caching - Single Responsibility Principle.

    Handles only caching concerns, separated from building and selection.
    """

    @abstractmethod
    def get_cached_image(self, image_name: str, platform: str) -> Optional[str]:
        """Get cached base image if available."""
        pass

    @abstractmethod
    def cache_image(
        self, image_name: str, tag: str, platform: str, metadata: BaseImageMetadata
    ) -> None:
        """Cache base image with metadata."""
        pass

    @abstractmethod
    def invalidate_cache(self, image_name: str) -> None:
        """Invalidate cached base image."""
        pass


class PluginRequirementsExtractor(ABC):
    """
    Interface for extracting plugin requirements - Interface Segregation.

    Handles only plugin analysis, not base image logic.
    """

    @abstractmethod
    def extract_docker_requirements(
        self, plugin_config: Dict[str, any]
    ) -> Dict[str, any]:
        """Extract Docker requirements from plugin configuration."""
        pass

    @abstractmethod
    def get_plugin_capabilities(self, plugin_name: str) -> List[str]:
        """Get capabilities required by plugin."""
        pass

    @abstractmethod
    def analyze_dependencies(self, plugins: List[str]) -> Dict[str, any]:
        """Analyze combined requirements from multiple plugins."""
        pass
