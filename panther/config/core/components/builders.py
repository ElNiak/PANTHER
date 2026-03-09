"""Configuration builders for the unified system."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from omegaconf import DictConfig, OmegaConf

from panther.core.utils.logging_mixin import LoggerMixin

from ..models import (
    ExperimentConfig,
    GlobalConfig,
    NetworkEnvironmentConfig,
    ServiceConfig,
    TestConfig,
)


class BuilderContext:
    """Context for tracking builder operations."""

    def __init__(self):
        """Initialize builder context."""
        self.warnings: List[str] = []
        self.fixes_applied: List[str] = []
        self.errors: List[str] = []

    def add_warning(self, warning: str):
        """Add a warning message."""
        self.warnings.append(warning)

    def add_fix(self, fix: str):
        """Add a fix description."""
        self.fixes_applied.append(fix)

    def add_error(self, error: str):
        """Add an error message."""
        self.errors.append(error)

    def has_errors(self) -> bool:
        """Check if context has errors."""
        return len(self.errors) > 0

    def get_summary(self) -> Dict[str, Any]:
        """Get context summary."""
        return {
            "warnings": self.warnings,
            "fixes_applied": self.fixes_applied,
            "errors": self.errors,
            "has_errors": self.has_errors(),
        }


class BaseBuilder(LoggerMixin):
    """Base class for configuration builders."""

    def __init__(self, plugin_dir: Optional[Path] = None):
        """Initialize builder.

        Args:
            plugin_dir: Plugin directory path
        """
        super().__init__()
        self.plugin_dir = plugin_dir or Path("panther/plugins")
        self.context = BuilderContext()

    def reset_context(self):
        """Reset builder context."""
        self.context = BuilderContext()


class ExperimentBuilder(BaseBuilder):
    """Builder for experiment configurations with auto-fix support."""

    def build(
        self, config_dict: Dict[str, Any], auto_fix: bool = True
    ) -> ExperimentConfig:
        """Build experiment configuration with auto-fix.

        Args:
            config_dict: Raw configuration dictionary
            auto_fix: Whether to apply automatic fixes

        Returns:
            Built ExperimentConfig
        """
        self.reset_context()
        self.logger.info("Building experiment configuration")

        # Apply fixes if enabled
        if auto_fix:
            config_dict = self._apply_auto_fixes(config_dict)

        # Build tests
        if "tests" in config_dict:
            config_dict["tests"] = [
                self._build_test(test_dict, auto_fix)
                for test_dict in config_dict["tests"]
            ]

        # Create ExperimentConfig
        try:
            experiment_config = ExperimentConfig(**config_dict)

            if self.context.warnings:
                self.logger.warning(f"Built with {len(self.context.warnings)} warnings")
            if self.context.fixes_applied:
                self.logger.info(f"Applied {len(self.context.fixes_applied)} fixes")

            return experiment_config
        except Exception as e:
            self.context.add_error(str(e))
            raise ValueError(f"Failed to build experiment configuration: {e}")

    def _apply_auto_fixes(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Apply automatic fixes to experiment config.

        Args:
            config_dict: Configuration dictionary

        Returns:
            Fixed configuration
        """
        self.logger.info("Applying automatic fixes to experiment configuration")
        # Use summarizer for concise config logging
        from panther.core.utils import log_omega_config_summary

        log_omega_config_summary(self.logger, "Initial config", config_dict)
        # Ensure tests array exists
        if "tests" not in config_dict or not config_dict["tests"]:
            self.context.add_error("No tests defined")
            config_dict["tests"] = []
        # Use summarizer for concise config logging
        log_omega_config_summary(self.logger, "Tests after fix", config_dict)
        return config_dict

    def _build_test(self, test_dict: Dict[str, Any], auto_fix: bool) -> TestConfig:
        """Build test configuration.

        Args:
            test_dict: Test configuration dictionary
            auto_fix: Whether to apply fixes

        Returns:
            Built TestConfig
        """
        # Apply test-level fixes
        if auto_fix:
            test_dict = self._apply_test_fixes(test_dict)

        # Build network environment
        if "network_environment" in test_dict:
            test_dict["network_environment"] = self._build_network_environment(
                test_dict["network_environment"]
            )

        # Build services with port conflict prevention
        if "services" in test_dict:
            test_dict["services"] = self._build_services_with_port_registry(
                test_dict["services"], auto_fix
            )

        return TestConfig(**test_dict)

    def _build_services_with_port_registry(
        self, services_dict: Dict[str, Dict[str, Any]], auto_fix: bool
    ) -> Dict[str, Any]:
        """Build services with port conflict prevention.

        Args:
            services_dict: Dictionary of service configurations
            auto_fix: Whether to apply automatic fixes

        Returns:
            Dictionary of built service configurations
        """
        # Track allocated ports across all services
        port_registry = {}  # {port: service_name}
        built_services = {}

        for service_name, service_dict in services_dict.items():
            # Pass port registry to the service builder for unique port assignment
            built_service = self._build_service_with_port_registry(
                service_dict, auto_fix, service_name, port_registry
            )
            built_services[service_name] = built_service

        # Log port allocations for debugging
        if port_registry:
            self.logger.info(f"Port allocations for test: {port_registry}")

        return built_services

    def _build_service_with_port_registry(
        self,
        service_dict: Dict[str, Any],
        auto_fix: bool,
        service_name: str,
        port_registry: Dict[int, str],
    ) -> Any:
        """Build service configuration with port registry.

        Args:
            service_dict: Service configuration dictionary
            auto_fix: Whether to apply fixes
            service_name: Service name from the YAML key
            port_registry: Registry of allocated ports {port: service_name}

        Returns:
            Built ServiceConfig
        """
        service_builder = ServiceBuilder(self.plugin_dir)
        return service_builder.build_with_port_registry(
            service_dict, auto_fix, service_name, port_registry
        )

    def _apply_test_fixes(self, test_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Apply automatic fixes to test config.

        Args:
            test_dict: Test configuration dictionary

        Returns:
            Fixed configuration
        """
        # Ensure required fields
        if "name" not in test_dict:
            test_dict["name"] = "unnamed_test"
            self.context.add_fix("Added default test name")

        if "network_environment" not in test_dict:
            test_dict["network_environment"] = {"type": "docker_compose"}
            self.context.add_fix("Added default network environment")

        if "services" not in test_dict:
            test_dict["services"] = {}
            self.context.add_warning("Test has no services defined")

        return test_dict

    def _build_network_environment(
        self, env_dict: Dict[str, Any]
    ) -> NetworkEnvironmentConfig:
        """Build network environment configuration.

        Uses the schema registry first, then falls back to hardcoded imports
        for backwards compatibility.

        Args:
            env_dict: Environment configuration dictionary

        Returns:
            Built NetworkEnvironmentConfig
        """
        env_type = env_dict.get("type", "docker_compose")

        # 1. Try schema registry (populated by @register_plugin auto-discovery)
        try:
            from panther.plugins.core.plugin_decorators import get_config_model

            config_class = get_config_model(env_type)
            if config_class is not None:
                return config_class(**env_dict)
        except ImportError:
            pass

        # 2. Fallback: hardcoded imports for environments not yet registered
        try:
            if env_type == "docker_compose":
                from panther.plugins.environments.network_environment.docker_compose.config_schema import (
                    DockerComposeConfig,
                )

                config_class = DockerComposeConfig
            elif env_type == "localhost_single_container":
                from panther.plugins.environments.network_environment.localhost_single_container.config_schema import (
                    LocalhostSingleContainerConfig,
                )

                config_class = LocalhostSingleContainerConfig
            elif env_type == "shadow_ns":
                from panther.plugins.environments.network_environment.shadow_ns.config_schema import (
                    ShadowNSConfig,
                )

                config_class = ShadowNSConfig
            else:
                config_class = NetworkEnvironmentConfig
                self.context.add_warning(
                    f"Unknown network environment type '{env_type}', using base class"
                )
        except ImportError as e:
            self.logger.error(
                f"Failed to import config for environment type '{env_type}': {e}"
            )
            config_class = NetworkEnvironmentConfig
            self.context.add_error(f"Could not load config class for '{env_type}'")

        return config_class(**env_dict)

    def _build_service(
        self, service_dict: Dict[str, Any], auto_fix: bool, service_name: str = None
    ) -> ServiceConfig:
        """Build service configuration.

        Args:
            service_dict: Service configuration dictionary
            auto_fix: Whether to apply fixes
            service_name: Service name from the YAML key

        Returns:
            Built ServiceConfig
        """
        service_builder = ServiceBuilder(self.plugin_dir)
        return service_builder.build(service_dict, auto_fix, service_name)


class ServiceBuilder(BaseBuilder):
    """Builder for service configurations with field preservation."""

    def build(
        self,
        service_dict: Dict[str, Any],
        auto_fix: bool = True,
        service_name: str = None,
    ) -> ServiceConfig:
        """Build service configuration preserving all fields.

        Args:
            service_dict: Service configuration dictionary
            auto_fix: Whether to apply automatic fixes
            service_name: Service name from the YAML key

        Returns:
            Built ServiceConfig
        """
        self.reset_context()

        # If no explicit name is provided in the service_dict, use the service_name from the YAML key
        if "name" not in service_dict and service_name:
            service_dict["name"] = service_name
            self.context.add_fix(f"Added service name '{service_name}' from YAML key")

        # Apply fixes if enabled
        if auto_fix:
            service_dict = self._apply_auto_fixes(service_dict)

        # Extract plugin config from implementation before building
        plugin_config_data = {}
        if "implementation" in service_dict:
            (
                service_dict["implementation"],
                plugin_config_data,
            ) = self._build_implementation_with_plugin_config(
                service_dict["implementation"]
            )

        if "protocol" in service_dict:
            service_dict["protocol"] = self._build_protocol(service_dict["protocol"])

        # Set plugin_config field
        service_dict["plugin_config"] = plugin_config_data

        # Optionally validate plugin config with resolver
        if plugin_config_data and "implementation" in service_dict:
            self._validate_plugin_config_with_resolver(service_dict, plugin_config_data)

        # Create ServiceConfig
        try:
            return ServiceConfig(**service_dict)
        except Exception as e:
            self.context.add_error(str(e))
            raise ValueError(f"Failed to build service configuration: {e}")

    def build_with_port_registry(
        self,
        service_dict: Dict[str, Any],
        auto_fix: bool = True,
        service_name: str = None,
        port_registry: Dict[int, str] = None,
    ) -> ServiceConfig:
        """Build service configuration with port conflict prevention.

        Args:
            service_dict: Service configuration dictionary
            auto_fix: Whether to apply automatic fixes
            service_name: Service name from the YAML key
            port_registry: Registry of allocated ports {port: service_name}

        Returns:
            Built ServiceConfig
        """
        self.reset_context()

        # If no explicit name is provided in the service_dict, use the service_name from the YAML key
        if "name" not in service_dict and service_name:
            service_dict["name"] = service_name
            self.context.add_fix(f"Added service name '{service_name}' from YAML key")

        # Apply fixes if enabled, with port registry for unique port assignment
        if auto_fix:
            service_dict = self._apply_auto_fixes_with_port_registry(
                service_dict, service_name, port_registry
            )

        # Extract plugin config from implementation before building
        plugin_config_data = {}
        if "implementation" in service_dict:
            (
                service_dict["implementation"],
                plugin_config_data,
            ) = self._build_implementation_with_plugin_config(
                service_dict["implementation"]
            )

        if "protocol" in service_dict:
            service_dict["protocol"] = self._build_protocol(service_dict["protocol"])

        # Set plugin_config field
        service_dict["plugin_config"] = plugin_config_data

        # Optionally validate plugin config with resolver
        if plugin_config_data and "implementation" in service_dict:
            self._validate_plugin_config_with_resolver(service_dict, plugin_config_data)

        # Create ServiceConfig
        try:
            return ServiceConfig(**service_dict)
        except Exception as e:
            self.context.add_error(str(e))
            raise ValueError(f"Failed to build service configuration: {e}")

    def _apply_auto_fixes(self, service_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Apply automatic fixes to service config.

        Args:
            service_dict: Service configuration dictionary

        Returns:
            Fixed configuration
        """
        # Fix missing implementation
        if "implementation" not in service_dict:
            self.context.add_error("Missing implementation configuration")
            service_dict["implementation"] = {"name": "unknown", "type": "iut"}

        # Fix missing protocol
        if "protocol" not in service_dict:
            self.context.add_error("Missing protocol configuration")
            service_dict["protocol"] = {"name": "unknown", "role": "server"}

        # Fix server port mappings
        protocol = service_dict.get("protocol", {})
        if protocol.get("role") == "server" and not service_dict.get("ports"):
            # Get default port from protocol
            protocol_name = protocol.get("name", "unknown")
            default_ports = {
                "quic": "4443:4443",
                "http": "80:80",
                "https": "443:443",
            }

            if protocol_name in default_ports:
                service_dict["ports"] = [default_ports[protocol_name]]
                self.context.add_fix(
                    f"Added default port mapping for {protocol_name} server"
                )

        return service_dict

    def _apply_auto_fixes_with_port_registry(
        self,
        service_dict: Dict[str, Any],
        service_name: str,
        port_registry: Dict[int, str],
    ) -> Dict[str, Any]:
        """Apply automatic fixes to service config with port conflict prevention.

        Args:
            service_dict: Service configuration dictionary
            service_name: Service name for logging
            port_registry: Registry of allocated ports {port: service_name}

        Returns:
            Fixed configuration
        """
        # Fix missing implementation
        if "implementation" not in service_dict:
            self.context.add_error("Missing implementation configuration")
            service_dict["implementation"] = {"name": "unknown", "type": "iut"}

        # Fix missing protocol
        if "protocol" not in service_dict:
            self.context.add_error("Missing protocol configuration")
            service_dict["protocol"] = {"name": "unknown", "role": "server"}

        # Fix server port mappings with conflict prevention
        protocol = service_dict.get("protocol", {})
        if protocol.get("role") == "server" and not service_dict.get("ports"):
            # Get default port from protocol
            protocol_name = protocol.get("name", "unknown")
            base_ports = {
                "quic": 4443,
                "http": 80,
                "https": 443,
            }

            if protocol_name in base_ports and port_registry is not None:
                base_port = base_ports[protocol_name]

                # Find next available port
                allocated_port = self._find_next_available_port(
                    base_port, port_registry
                )
                port_registry[allocated_port] = service_name

                service_dict["ports"] = [f"{allocated_port}:{allocated_port}"]
                self.context.add_fix(
                    f"Assigned unique port {allocated_port} to {protocol_name} server '{service_name}'"
                )
            elif protocol_name in base_ports:
                # Fallback to original behavior if no port registry
                default_ports = {
                    "quic": "4443:4443",
                    "http": "80:80",
                    "https": "443:443",
                }
                service_dict["ports"] = [default_ports[protocol_name]]
                self.context.add_fix(
                    f"Added default port mapping for {protocol_name} server"
                )

        return service_dict

    def _find_next_available_port(
        self, base_port: int, port_registry: Dict[int, str]
    ) -> int:
        """Find the next available port starting from base_port.

        Args:
            base_port: Starting port number
            port_registry: Registry of allocated ports {port: service_name}

        Returns:
            Next available port number
        """
        port = base_port
        while port in port_registry:
            port += 1
        return port

    def _build_implementation(self, impl_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Build implementation configuration.

        Args:
            impl_dict: Implementation dictionary

        Returns:
            Built implementation dict
        """
        # Ensure required fields
        if "name" not in impl_dict:
            impl_dict["name"] = "unknown"
            self.context.add_warning("Implementation missing name")

        if "type" not in impl_dict:
            impl_dict["type"] = "iut"
            self.context.add_fix("Added default implementation type")

        return impl_dict

    def _build_implementation_with_plugin_config(
        self, impl_dict: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Build implementation configuration and extract plugin-specific fields.

        Args:
            impl_dict: Implementation dictionary from YAML

        Returns:
            Tuple of (implementation_dict, plugin_config_dict)
        """
        # Known fields for ImplementationConfig
        # TODO: make more dynamic
        known_fields = {
            "name",
            "type",
            "version",
            "version_config",
            "shadow_compatible",
            "gperf_compatible",
        }

        # Separate known fields from plugin-specific fields
        implementation_data = {}
        plugin_config_data = {}

        for key, value in impl_dict.items():
            if key in known_fields:
                implementation_data[key] = value
            else:
                # This is a plugin-specific field
                plugin_config_data[key] = value
                self.logger.debug(f"Extracted plugin-specific field: {key}")

        # Ensure required fields
        if "name" not in implementation_data:
            implementation_data["name"] = "unknown"
            self.context.add_warning("Implementation missing name")

        if "type" not in implementation_data:
            implementation_data["type"] = "iut"
            self.context.add_fix("Added default implementation type")

        # Copy all implementation fields to plugin config as well
        # This allows plugins to access standard fields through their config
        plugin_config_data.update(implementation_data)

        # Add protocol information if available (for testers that need it)
        if hasattr(self, "_current_protocol"):
            plugin_config_data["protocol"] = self._current_protocol

        return implementation_data, plugin_config_data

    def _validate_plugin_config_with_resolver(
        self, service_dict: Dict[str, Any], plugin_config_data: Dict[str, Any]
    ):
        """Validate plugin configuration using PluginConfigResolver if available.

        This is optional validation that logs warnings but doesn't fail the build.

        Args:
            service_dict: Full service configuration
            plugin_config_data: Extracted plugin configuration
        """
        try:
            from panther.plugins.core.plugin_config_resolver import (
                get_plugin_config_resolver,
            )

            resolver = get_plugin_config_resolver()

            # Get implementation details
            impl = service_dict.get("implementation", {})
            impl_name = impl.get("name", "")
            impl_type = impl.get("type", "").lower()

            # Get protocol for service resolution
            protocol_name = ""
            if "protocol" in service_dict:
                protocol = service_dict["protocol"]
                if isinstance(protocol, dict):
                    protocol_name = protocol.get("name", "")
                elif hasattr(protocol, "name"):
                    protocol_name = protocol.name

            if expected_class := resolver.resolve_service_config_class(
                service_type=impl_type, protocol=protocol_name, name=impl_name
            ):
                # Try to instantiate with the plugin config data
                try:
                    # Create instance to validate structure
                    self.logger.debug(
                        f"Validating plugin config for {impl_name} against {expected_class.__name__} with data: {plugin_config_data}"
                    )
                    expected_class(**plugin_config_data)
                    self.logger.debug(
                        f"Plugin config for {impl_name} validated against {expected_class.__name__}"
                    )
                except Exception as e:
                    # Log validation issues but don't fail
                    self.logger.warning(
                        f"Plugin config for {impl_name} may have issues: {e}. "
                        f"This won't prevent the service from running."
                    )
            else:
                self.logger.debug(
                    f"No plugin config schema found for {impl_name}, skipping validation"
                )

        except ImportError:
            # PluginConfigResolver not available, skip validation
            self.logger.debug("PluginConfigResolver not available, skipping validation")
        except Exception as e:
            # Any other error, log and continue
            self.logger.debug(f"Could not validate plugin config: {e}")

    def _build_protocol(self, proto_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Build protocol configuration.

        Args:
            proto_dict: Protocol dictionary

        Returns:
            Built protocol dict
        """
        # Ensure required fields
        if "name" not in proto_dict:
            proto_dict["name"] = "unknown"
            self.context.add_warning("Protocol missing name")

        if "role" not in proto_dict:
            proto_dict["role"] = "server"
            self.context.add_fix("Added default protocol role")

        # Fix client target
        if proto_dict.get("role") == "client" and not proto_dict.get("target"):
            self.context.add_warning("Client service missing target")

        return proto_dict


class GlobalConfigBuilder(BaseBuilder):
    """Builder for global configuration with environment variable resolution."""

    def build(
        self, config_dict: Dict[str, Any], resolve_env: bool = True
    ) -> GlobalConfig:
        """Build global configuration.

        Args:
            config_dict: Configuration dictionary
            resolve_env: Whether to resolve environment variables

        Returns:
            Built GlobalConfig
        """
        self.reset_context()
        self.logger.info("Building global configuration")

        # Apply environment variables if requested
        if resolve_env:
            config_dict = self._resolve_environment_variables(config_dict)

        # Apply defaults
        config_dict = self._apply_defaults(config_dict)

        # Create GlobalConfig
        try:
            global_config = GlobalConfig(**config_dict)

            # Resolve paths
            global_config = global_config.resolve_paths()

            return global_config
        except Exception as e:
            self.context.add_error(str(e))
            raise ValueError(f"Failed to build global configuration: {e}")

    def _resolve_environment_variables(
        self, config_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Resolve environment variables in configuration.

        Args:
            config_dict: Configuration dictionary

        Returns:
            Configuration with environment variables resolved
        """
        import os

        # Environment variable mappings
        env_mappings = {
            "PANTHER_LOG_LEVEL": "logging.level",
            "PANTHER_OUTPUT_DIR": "paths.output_dir",
            "PANTHER_PLUGIN_DIR": "paths.plugin_dir",
            "PANTHER_BUILD_IMAGES": "docker.force_build_docker_image",
            "PANTHER_FAST_FAIL": "fast_fail.enabled",
        }

        # Create OmegaConf for easier manipulation
        omega_config = OmegaConf.create(config_dict)

        # Apply environment variables
        for env_var, config_path in env_mappings.items():
            env_value = os.environ.get(env_var)
            if env_value is not None:
                try:
                    OmegaConf.update(omega_config, config_path, env_value, merge=False)
                    self.context.add_fix(f"Applied {env_var} to {config_path}")
                except Exception as e:
                    self.context.add_warning(f"Failed to apply {env_var}: {e}")

        return OmegaConf.to_container(omega_config, resolve=True)

    def _apply_defaults(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Apply default values to global config using Pydantic model defaults.

        Args:
            config_dict: Configuration dictionary

        Returns:
            Configuration with defaults from GlobalConfig model
        """
        from ..models.global_config import GlobalConfig

        # Create a default GlobalConfig instance to extract defaults
        default_global_config = GlobalConfig()

        # Convert to dictionary to get all default values
        defaults = default_global_config.model_dump()

        # Note: Applied Pydantic model defaults for GlobalConfig

        # Merge with defaults (user config takes precedence)
        merged = OmegaConf.merge(
            OmegaConf.create(defaults), OmegaConf.create(config_dict)
        )

        return OmegaConf.to_container(merged, resolve=False)
