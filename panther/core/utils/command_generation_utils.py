"""
Command Generation Utilities

This module provides shared utilities for generating deployment commands
across different service implementations, reducing code duplication and
ensuring consistency in command generation patterns.
"""

import logging
from typing import Any
from pathlib import Path
import os

from panther.plugins.protocols.config_schema import RoleEnum


logger = logging.getLogger(__name__)


class CertificateCommandBuilder:
    """Utility for building certificate-related command arguments."""

    @staticmethod
    def add_certificate_args(command_args: list[str], params: dict[str, Any]) -> None:
        """
        Add certificate parameters to command arguments.

        Args:
            command_args: List of command arguments to append to
            params: Parameters dictionary containing certificate configuration
        """
        if "certificates" in params and params["certificates"]:
            certs = params["certificates"]

            # Handle both nested and flat certificate structures
            if "cert" in certs and isinstance(certs["cert"], dict):
                # Nested structure (e.g., picoquic)
                if "param" in certs["cert"] and "file" in certs["cert"]:
                    command_args.append(certs["cert"]["param"])
                    command_args.append(certs["cert"]["file"])
                if "key" in certs and "param" in certs["key"] and "file" in certs["key"]:
                    command_args.append(certs["key"]["param"])
                    command_args.append(certs["key"]["file"])
            else:
                # Flat structure (e.g., aioquic, lsquic)
                if "cert_param" in certs and "cert_file" in certs:
                    command_args.extend([certs["cert_param"], certs["cert_file"]])
                if "key_param" in certs and "key_file" in certs:
                    command_args.extend([certs["key_param"], certs["key_file"]])


class ProtocolCommandBuilder:
    """Utility for building protocol-related command arguments."""

    @staticmethod
    def add_protocol_args(
        command_args: list[str], params: dict[str, Any], build_command_args_fn=None
    ) -> None:
        """
        Add protocol parameters (ALPN, additional parameters) to command arguments.

        Args:
            command_args: List of command arguments to append to
            params: Parameters dictionary containing protocol configuration
            build_command_args_fn: Optional function to process additional parameters
        """
        if "protocol" in params and params["protocol"]:
            proto = params["protocol"]

            # Add ALPN parameters
            if "alpn" in proto and proto["alpn"]:
                command_args.extend([proto["alpn"]["param"], proto["alpn"]["value"]])

            # Add additional protocol parameters
            if "additional_parameters" in proto and proto["additional_parameters"]:
                if build_command_args_fn:
                    # Use provided function to process additional parameters
                    additional_params = build_command_args_fn(proto["additional_parameters"])
                    command_args.extend(additional_params)
                else:
                    # Add as-is
                    command_args.append(proto["additional_parameters"])


class NetworkCommandBuilder:
    """Utility for building network-related command arguments."""

    @staticmethod
    def add_network_interface_args(
        command_args: list[str], params: dict[str, Any], include_interface: bool = True
    ) -> None:
        """
        Add network interface parameters to command arguments.

        Args:
            command_args: List of command arguments to append to
            params: Parameters dictionary containing network configuration
            include_interface: Whether to include interface parameters
        """
        if include_interface and "network" in params and params["network"]:
            network = params["network"]
            if "interface" in network and network["interface"]:
                command_args.extend([network["interface"]["param"], network["interface"]["value"]])

    @staticmethod
    def add_server_network_args(
        command_args: list[str], params: dict[str, Any], port_param: str = "-p"
    ) -> None:
        """
        Add server-specific network arguments.

        Args:
            command_args: List of command arguments to append to
            params: Parameters dictionary containing network configuration
            port_param: The parameter flag for port (default: "-p")
        """
        if "network" in params and "port" in params["network"]:
            command_args.extend([port_param, str(params["network"]["port"])])

    @staticmethod
    def add_client_network_args(
        command_args: list[str], params: dict[str, Any], target: str, include_url: bool = False
    ) -> None:
        """
        Add client-specific network arguments.

        Args:
            command_args: List of command arguments to append to
            params: Parameters dictionary containing network configuration
            target: Target server address
            include_url: Whether to format as URL (for implementations like quiche/quinn)
        """
        if "network" in params and "port" in params["network"]:
            port = params["network"]["port"]
            if include_url:
                command_args.append(f"https://{target}:{port}/index.html")
            else:
                command_args.extend([target, str(port)])


class LoggingCommandBuilder:
    """Utility for building logging-related command arguments."""

    @staticmethod
    def add_logging_redirection(command_args: list[str], params: dict[str, Any]) -> None:
        """
        Add logging redirection parameters to command arguments.

        Args:
            command_args: List of command arguments to append to
            params: Parameters dictionary containing logging configuration
        """
        if "logging" in params and params["logging"]:
            logging_config = params["logging"]
            if "log_path" in logging_config and "err_path" in logging_config:
                command_args.extend(
                    [">", logging_config["log_path"], "2>", logging_config["err_path"]]
                )


class EnvironmentVariableBuilder:
    """Utility for building environment variables for different implementation types."""

    @staticmethod
    def get_rust_env_vars(implementation: str = "rust") -> dict[str, str]:
        """
        Get standard environment variables for Rust-based implementations.

        Args:
            implementation: The specific implementation name

        Returns:
            Dict of environment variables
        """
        return {
            "RUST_LOG": f"{implementation}=trace",
            "RUST_BACKTRACE": "1",
            f"{implementation.upper()}_LOG_DIR": f"/app/logs/{implementation}",
        }

    @staticmethod
    def get_python_env_vars(implementation: str = "python") -> dict[str, str]:
        """
        Get standard environment variables for Python-based implementations.

        Args:
            implementation: The specific implementation name

        Returns:
            Dict of environment variables
        """
        return {
            "PYTHONPATH": f"/opt/{implementation}",
            "PYTHONUNBUFFERED": "1",
        }

    @staticmethod
    def get_c_env_vars(implementation: str = "c", lib_path: str = None) -> dict[str, str]:
        """
        Get standard environment variables for C-based implementations.

        Args:
            implementation: The specific implementation name
            lib_path: Optional library path override

        Returns:
            Dict of environment variables
        """
        env_vars = {}
        if lib_path:
            env_vars["LD_LIBRARY_PATH"] = lib_path
        env_vars[f"{implementation.upper()}_LOGS_DIR"] = f"/app/logs/{implementation}"
        return env_vars


class DockerImageBuilder:
    """Utility for standardized Docker image building."""

    @staticmethod
    def build_standard_images(
        plugin_manager, implementation_name: str, service_config: Any
    ) -> None:
        """
        Build standard Docker images for a service.

        Args:
            plugin_manager: Plugin loader instance
            implementation_name: Name of the implementation
            service_config: Service configuration object
        """
        if not plugin_manager:
            logger.warning("No plugin manager provided, skipping Docker image build")
            return

        # Build base image
        base_dockerfile_path = Path(
            os.path.join(os.getcwd(), "panther", "plugins", "services", "Dockerfile")
        )

        logger.debug("Building base Docker image from %s", base_dockerfile_path)
        plugin_manager.build_docker_image_from_path(base_dockerfile_path, "panther_base", "service")

        # Build implementation image
        logger.debug("Building Docker image for %s", implementation_name)
        plugin_manager.build_docker_image(
            implementation_name, service_config.implementation.version
        )


class TemplateRenderingHelper:
    """Utility for standardized template rendering with fallback."""

    @staticmethod
    def render_with_fallback(
        service_manager,
        role: RoleEnum,
        params: dict[str, Any],
        command_args: list[str],
        env_vars: dict[str, str],
    ) -> str:
        """
        Render command template with structured args and fallback to simple template.

        Args:
            service_manager: Service manager instance with render methods
            role: Service role (client/server)
            params: Parameters for template rendering
            command_args: Command arguments list
            env_vars: Environment variables dict

        Returns:
            Rendered command string
        """
        try:
            # Try structured template first
            template_name = f"{str(role.name)}_command_structured.jinja"
            return service_manager.render_template_with_structured_args(
                template_name, params, command_args, env_vars
            )
        except Exception as e:
            logger.warning(
                "Failed to render structured template for service '%s': %s",
                service_manager.service_name,
                e,
            )
            try:
                # Fallback to original template
                template_name = f"{str(role.name)}_command.jinja"
                return service_manager.render_commands(params, template_name)
            except Exception as e2:
                logger.error(
                    "Failed to render fallback command template for service '%s': %s",
                    service_manager.service_name,
                    e2,
                )
                raise e2


class DeploymentCommandBuilder:
    """
    Main utility class that combines all command building utilities
    for generating complete deployment commands.
    """

    def __init__(self, service_manager):
        """
        Initialize the deployment command builder.

        Args:
            service_manager: The service manager instance
        """
        self.service_manager = service_manager
        self.logger = logger

    def build_deployment_commands(
        self, include_interface: bool = True, include_url_for_client: bool = False
    ) -> list[str]:
        """
        Build complete deployment command arguments using all utilities.

        Args:
            include_interface: Whether to include network interface parameters
            include_url_for_client: Whether to format client target as URL

        Returns:
            List of command arguments
        """
        # Get appropriate parameters based on role
        if self.service_manager.role == RoleEnum.server:
            params = self.service_manager.service_config_to_test.implementation.version.server
        else:
            params = self.service_manager.service_config_to_test.implementation.version.client

        # Add target for client
        if self.service_manager.role == RoleEnum.client:
            params["target"] = self.service_manager.service_config_to_test.protocol.target

        # Set working directory
        self.service_manager.working_dir = params["binary"]["dir"]

        # Initialize command arguments list
        command_args = []

        # Add certificate parameters
        CertificateCommandBuilder.add_certificate_args(command_args, params)

        # Add ticket file for client
        if self.service_manager.role == RoleEnum.client and "ticket_file" in params:
            ticket = params["ticket_file"]
            if "param" in ticket and "file" in ticket:
                command_args.extend([ticket["param"], ticket["file"]])

        # Add protocol parameters
        build_fn = getattr(self.service_manager, "build_command_args", None)
        ProtocolCommandBuilder.add_protocol_args(command_args, params, build_fn)

        # Add network interface
        NetworkCommandBuilder.add_network_interface_args(command_args, params, include_interface)

        # Add initial version if specified
        if self.service_manager.role == RoleEnum.client and "initial_version" in params:
            command_args.extend(["-v", params["initial_version"]])

        # Add role-specific network parameters
        if self.service_manager.role == RoleEnum.server:
            NetworkCommandBuilder.add_server_network_args(command_args, params)
        else:  # client
            NetworkCommandBuilder.add_client_network_args(
                command_args, params, params.get("target", ""), include_url_for_client
            )

        # Add logging redirection
        LoggingCommandBuilder.add_logging_redirection(command_args, params)

        self.logger.debug("Generated command arguments: %s", command_args)
        return command_args

    def get_environment_variables(
        self, implementation_type: str, implementation_name: str, custom_env: dict[str, str] = None
    ) -> dict[str, str]:
        """
        Get environment variables based on implementation type.

        Args:
            implementation_type: Type of implementation (rust, python, c)
            implementation_name: Name of the specific implementation
            custom_env: Additional custom environment variables

        Returns:
            Dict of environment variables
        """
        env_vars = {}

        if implementation_type == "rust":
            env_vars.update(EnvironmentVariableBuilder.get_rust_env_vars(implementation_name))
        elif implementation_type == "python":
            env_vars.update(EnvironmentVariableBuilder.get_python_env_vars(implementation_name))
        elif implementation_type == "c":
            lib_path = f"/opt/{implementation_name}/lib"
            env_vars.update(
                EnvironmentVariableBuilder.get_c_env_vars(implementation_name, lib_path)
            )

        # Add custom environment variables
        if custom_env:
            env_vars.update(custom_env)

        return env_vars
