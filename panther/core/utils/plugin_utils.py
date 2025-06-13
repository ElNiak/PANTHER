"""
Plugin Utilities

This module provides common utilities and patterns for plugin development and management.
"""

import logging
import os
from pathlib import Path
from typing import Any
from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)


class PluginInitializationError(Exception):
    """Exception raised when plugin initialization fails."""


class PluginUtils:
    """Utility class for common plugin operations."""

    @staticmethod
    def setup_plugin_directories(
        plugin_dir: Path,
        service_type: str,
        protocol_name: str | None = None,
        implementation_name: str | None = None,
    ) -> dict[str, Path]:
        """
        Set up standard plugin directory structure.

        Args:
            plugin_dir: Base plugin directory
            service_type: Type of service (iut, testers, etc.)
            protocol_name: Protocol name (for IUT plugins)
            implementation_name: Implementation name

        Returns:
            dict: Dictionary of standard directory paths
        """
        base_path = plugin_dir

        if service_type.upper() == "TESTERS":
            # Testers: plugin_dir/testers/implementation_name/
            templates_dir = base_path / service_type.lower() / implementation_name / "templates"
            config_dir = base_path / service_type.lower() / implementation_name / "version_configs"
        else:
            # IUT: plugin_dir/iut/protocol/implementation_name/
            templates_dir = (
                base_path / service_type.lower() / protocol_name / implementation_name / "templates"
            )
            config_dir = (
                base_path
                / service_type.lower()
                / protocol_name
                / implementation_name
                / "version_configs"
            )

        return {
            "templates_dir": templates_dir,
            "config_versions_dir": config_dir,
            "base_dir": base_path,
            "service_dir": base_path / service_type.lower(),
        }

    @staticmethod
    def setup_jinja_environment(templates_dir: Path) -> Environment:
        """
        Set up a Jinja2 environment with common filters and settings.

        Args:
            templates_dir: Directory containing templates

        Returns:
            Environment: Configured Jinja2 environment
        """
        if not templates_dir.exists():
            logger.warning(f"Templates directory does not exist: {templates_dir}")
            # Create a minimal environment
            env = Environment(autoescape=True)
        else:
            env = Environment(loader=FileSystemLoader(templates_dir), autoescape=True)

        # Add common filters
        env.filters["realpath"] = os.path.abspath
        env.filters["is_dict"] = lambda x: isinstance(x, dict)
        env.filters["basename"] = os.path.basename
        env.filters["dirname"] = os.path.dirname

        # Set common options
        env.trim_blocks = True
        env.lstrip_blocks = True

        return env

    @staticmethod
    def validate_plugin_requirements(
        templates_dir: Path, required_templates: list[str] | None = None
    ) -> bool:
        """
        Validate that a plugin meets basic requirements.

        Args:
            templates_dir: Templates directory to check
            required_templates: List of required template files

        Returns:
            bool: True if validation passes

        Raises:
            PluginInitializationError: If validation fails
        """
        if not templates_dir.exists():
            raise PluginInitializationError(f"Templates directory missing: {templates_dir}")

        if required_templates:
            for template in required_templates:
                template_path = templates_dir / template
                if not template_path.exists():
                    raise PluginInitializationError(f"Required template missing: {template_path}")

        return True

    @staticmethod
    def get_plugin_metadata(
        plugin_class: type, default_metadata: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Extract plugin metadata from class or decorator.

        Args:
            plugin_class: Plugin class to extract metadata from
            default_metadata: Default metadata values

        Returns:
            dict: Plugin metadata
        """
        metadata = default_metadata or {}

        # Check for plugin registration decorator metadata
        if hasattr(plugin_class, "__plugin_metadata__"):
            metadata.update(plugin_class.__plugin_metadata__)

        # Add class-based metadata
        metadata.update(
            {
                "class_name": plugin_class.__name__,
                "module": plugin_class.__module__,
            }
        )

        return metadata


class PluginInitializationMixin:
    """
    Mixin class that provides common plugin initialization patterns.

    This mixin standardizes plugin setup across different plugin types.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._plugin_initialized = False
        self._plugin_directories = {}
        self._jinja_env = None

    def setup_plugin_paths(
        self,
        service_type: str,
        protocol_name: str | None = None,
        implementation_name: str | None = None,
    ) -> None:
        """
        Set up plugin directory paths.

        Args:
            service_type: Type of service
            protocol_name: Protocol name (for IUT plugins)
            implementation_name: Implementation name
        """
        if not hasattr(self, "_plugin_dir") or not self._plugin_dir:
            self._plugin_dir = (
                Path(os.path.dirname(__file__)).parent.parent / "plugins" / "services"
            )

        self._plugin_directories = PluginUtils.setup_plugin_directories(
            self._plugin_dir, service_type, protocol_name, implementation_name
        )

        # Set common attributes for backward compatibility
        self.templates_dir = str(self._plugin_directories["templates_dir"])
        self.config_versions_dir = str(self._plugin_directories["config_versions_dir"])

    def setup_template_environment(self) -> None:
        """Set up the Jinja2 template environment."""
        templates_dir = self._plugin_directories.get("templates_dir")
        if templates_dir:
            self._jinja_env = PluginUtils.setup_jinja_environment(templates_dir)
            # Set for backward compatibility
            self.jinja_env = self._jinja_env

    def validate_plugin_setup(self, required_templates: list[str] | None = None) -> bool:
        """
        Validate that the plugin is properly set up.

        Args:
            required_templates: List of required template files

        Returns:
            bool: True if validation passes
        """
        templates_dir = self._plugin_directories.get("templates_dir")
        if templates_dir:
            return PluginUtils.validate_plugin_requirements(templates_dir, required_templates)
        return True

    def initialize_plugin(
        self,
        service_type: str,
        protocol_name: str | None = None,
        implementation_name: str | None = None,
        required_templates: list[str] | None = None,
    ) -> None:
        """
        Complete plugin initialization with all standard setup.

        Args:
            service_type: Type of service
            protocol_name: Protocol name
            implementation_name: Implementation name
            required_templates: Required template files
        """
        if self._plugin_initialized:
            return

        try:
            self.setup_plugin_paths(service_type, protocol_name, implementation_name)
            self.setup_template_environment()
            self.validate_plugin_setup(required_templates)
            self._plugin_initialized = True

            if hasattr(self, "logger"):
                self.logger.debug(f"Plugin {self.__class__.__name__} initialized successfully")

        except Exception as e:
            if hasattr(self, "logger"):
                self.logger.error(f"Plugin initialization failed: {e}")
            raise PluginInitializationError(f"Failed to initialize plugin: {e}") from e


class ServiceManagerInitializationMixin(PluginInitializationMixin):
    """
    Specialized mixin for service manager plugin initialization.

    This provides service manager specific initialization patterns.
    """

    def initialize_service_manager(
        self,
        service_config_to_test: Any,
        service_type: str,
        protocol: Any,
        implementation_name: str,
    ) -> None:
        """
        Initialize service manager with standard patterns.

        Args:
            service_config_to_test: Service configuration
            service_type: Type of service
            protocol: Protocol configuration
            implementation_name: Implementation name
        """
        # Standard service manager attributes
        self.service_config_to_test = service_config_to_test
        self.implementation_name = implementation_name
        self.service_name = (
            service_config_to_test.name
            if hasattr(service_config_to_test, "name")
            else implementation_name
        )

        # Initialize plugin directories and templates
        protocol_name = getattr(protocol, "name", None) if protocol else None
        self.initialize_plugin(service_type, protocol_name, implementation_name)

        # Log initialization if logger is available
        if hasattr(self, "logger"):
            self.log_initialization(implementation_name, f"service_type={service_type}")
            if hasattr(self, "log_config_loaded"):
                self.log_config_loaded(
                    (
                        service_config_to_test.__dict__
                        if hasattr(service_config_to_test, "__dict__")
                        else {}
                    ),
                    implementation_name,
                )
