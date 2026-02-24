"""
Plugin Directory Mixin Module.

Provides shared plugin directory, Docker image naming, and Docker attribute
setup methods used by both IUT and Tester service managers.
"""

from __future__ import annotations

import inspect
from pathlib import Path


class PluginDirectoryMixin:
    """
    Mixin providing plugin directory detection and Docker attribute setup.

    Extracted from IUTServiceManagerMixin and TesterServiceManagerMixin
    where these methods were byte-identical. Both IUT and Tester service
    managers inherit from this mixin to avoid code duplication while
    maintaining their specialized behaviors (template rendering, role
    management, test parameters, etc.) in separate classes.
    """

    _plugin_dir: Path | None

    def _get_plugin_dir(self) -> Path:
        """
        Get the plugin directory via stack frame inspection.

        Walks up the call stack to find the file of the actual service
        implementation class (skipping the standard_*_initialization
        and __init__ frames).

        Returns:
            Path: Plugin directory path
        """
        frame = inspect.currentframe()
        try:
            # Walk up 2 frames: skip standard_*_initialization and __init__
            caller_frame = frame.f_back if frame else None
            caller_frame = caller_frame.f_back if caller_frame else None
            if caller_frame and caller_frame.f_code.co_filename:
                return Path(caller_frame.f_code.co_filename).parent
        finally:
            del frame

        return Path(__file__).parent

    def _get_docker_image_name(self, implementation_name: str | None = None) -> str:
        """
        Get the Docker image name.

        Override this method to customize Docker image naming.
        Default implementation uses implementation_name:latest format.

        Args:
            implementation_name: Name of the implementation

        Returns:
            str: Docker image name
        """
        implementation_name = implementation_name or getattr(
            self, "implementation_name", "unknown"
        )
        return f"{implementation_name}:latest"

    def _setup_docker_attributes(self) -> None:
        """
        Set up Docker-related attributes.

        Override this method to customize Docker configuration.
        Default implementation sets docker_image_name and docker_file_path.
        """
        self.docker_image_name = self._get_docker_image_name()
        plugin_dir = self._plugin_dir or self._get_plugin_dir()
        self.docker_file_path = plugin_dir / "Dockerfile"
