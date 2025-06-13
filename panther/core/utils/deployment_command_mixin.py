"""
Deployment Command Mixin

This module provides a mixin class that service managers can use to
standardize their deployment command generation, reducing code duplication
and ensuring consistency across implementations.
"""

import logging
from typing import Any

from panther.plugins.protocols.config_schema import RoleEnum
from panther.core.utils.command_generation_utils import (
    DeploymentCommandBuilder,
    DockerImageBuilder,
    TemplateRenderingHelper,
)


logger = logging.getLogger(__name__)


class DeploymentCommandMixin:
    """
    Mixin class that provides standardized deployment command generation
    for service managers, reducing code duplication.
    """

    def generate_standard_deployment_commands(
        self,
        include_interface: bool = True,
        include_url_for_client: bool = False,
        implementation_type: str = None,
        custom_env: dict[str, str] = None,
    ) -> str:
        """
        Generate deployment commands using standardized patterns.

        This method consolidates common command generation patterns found
        across different service implementations.

        Args:
            include_interface: Whether to include network interface parameters
            include_url_for_client: Whether to format client target as URL
            implementation_type: Type of implementation (rust, python, c) for env vars
            custom_env: Additional custom environment variables

        Returns:
            str: The rendered deployment command string

        Example:
            ```python
            class PicoquicServiceManager(DeploymentCommandMixin, IImplementationManager):
                def generate_deployment_commands(self) -> str:
                    return self.generate_standard_deployment_commands(
                        include_interface=False,
                        implementation_type="c"
                    )
            ```
        """
        self.logger.debug(
            "Generating deployment commands for service: %s with service parameters: %s",
            self.service_name,
            self.service_config_to_test,
        )

        self.logger.debug("Role: %s, Version: %s", self.role, self.service_version)

        # Build command arguments using the utility
        builder = DeploymentCommandBuilder(self)
        command_args = builder.build_deployment_commands(
            include_interface=include_interface, include_url_for_client=include_url_for_client
        )

        # Get appropriate parameters based on role
        if self.role == RoleEnum.server:
            params = self.service_config_to_test.implementation.version.server
        else:
            params = self.service_config_to_test.implementation.version.client

        # Add target for client
        if self.role == RoleEnum.client:
            params["target"] = self.service_config_to_test.protocol.target

        # Get environment variables if implementation type is specified
        env_vars = {}
        if implementation_type:
            implementation_name = getattr(self, "implementation_name", implementation_type)
            env_vars = builder.get_environment_variables(
                implementation_type, implementation_name, custom_env
            )
        elif custom_env:
            env_vars = custom_env

        # Render template with fallback
        return TemplateRenderingHelper.render_with_fallback(
            self, self.role, params, command_args, env_vars
        )

    def prepare_with_standard_docker_build(self, plugin_manager) -> None:
        """
        Prepare the service with standard Docker image building.

        This method consolidates the common Docker image building pattern
        found across service implementations.

        Args:
            plugin_manager: Plugin loader instance

        Example:
            ```python
            def prepare(self, plugin_manager: PluginManager | None = None):
                self.logger.debug("Preparing Picoquic service manager...")
                self.prepare_with_standard_docker_build(plugin_manager)
            ```
        """
        DockerImageBuilder.build_standard_images(
            plugin_manager, self.get_implementation_name(), self.service_config_to_test
        )

    def generate_run_command_with_defaults(
        self,
        implementation_type: str = None,
        custom_env: dict[str, str] = None,
        include_interface: bool = True,
        include_url_for_client: bool = False,
    ) -> dict[str, Any]:
        """
        Generate a complete run command configuration with standard defaults.

        This method provides a standardized way to generate the run command
        dictionary that's expected by the Docker Compose templates.

        Args:
            implementation_type: Type of implementation (rust, python, c)
            custom_env: Additional custom environment variables
            include_interface: Whether to include network interface parameters
            include_url_for_client: Whether to format client target as URL

        Returns:
            dict: The run command configuration

        Example:
            ```python
            def generate_run_command(self):
                return self.generate_run_command_with_defaults(
                    implementation_type="python",
                    custom_env={"CUSTOM_VAR": "value"}
                )
            ```
        """
        # Get role-specific parameters
        if self.role == RoleEnum.server:
            params = self.service_config_to_test.implementation.version.server
        else:
            params = self.service_config_to_test.implementation.version.client

        # Set working directory
        self.working_dir = params["binary"]["dir"]

        # Generate deployment commands
        cmd_args = (
            self.generate_deployment_commands()
            if hasattr(self, "generate_deployment_commands")
            else self.generate_standard_deployment_commands(
                include_interface=include_interface,
                include_url_for_client=include_url_for_client,
                implementation_type=implementation_type,
                custom_env=custom_env,
            )
        )

        # Build environment variables
        env_vars = {}
        if implementation_type:
            builder = DeploymentCommandBuilder(self)
            implementation_name = getattr(self, "implementation_name", implementation_type)
            env_vars = builder.get_environment_variables(
                implementation_type, implementation_name, custom_env
            )
        elif custom_env:
            env_vars = custom_env

        # Add any protocol-specific environment variables from params
        if "environment" in params:
            env_vars.update(params["environment"])

        return {
            "working_dir": self.working_dir,
            "command_binary": params["binary"]["name"],
            "command_args": cmd_args,
            "timeout": self.service_config_to_test.timeout,
            "command_env": env_vars,
        }

    def build_command_args_from_string(self, command_str: str) -> list[str]:
        """
        Helper method to split command strings into argument lists.

        This is useful for implementations that need to process
        additional_parameters strings.

        Args:
            command_str: Command string to split

        Returns:
            List of command arguments
        """
        if hasattr(self, "build_command_args"):
            return self.build_command_args(command_str)

        # Simple fallback implementation
        import shlex

        try:
            return shlex.split(command_str)
        except ValueError:
            # If shlex fails, just split on spaces
            return command_str.split()


class QuicDeploymentMixin(DeploymentCommandMixin):
    """
    Specialized mixin for QUIC implementations with QUIC-specific patterns.
    """

    def generate_quic_deployment_commands(
        self,
        include_interface: bool = True,
        include_url_for_client: bool = False,
        implementation_type: str = None,
        support_wire_version: bool = False,
    ) -> str:
        """
        Generate deployment commands with QUIC-specific handling.

        Args:
            include_interface: Whether to include network interface parameters
            include_url_for_client: Whether to format client target as URL
            implementation_type: Type of implementation (rust, python, c)
            support_wire_version: Whether this implementation supports wire version

        Returns:
            str: The rendered deployment command string
        """
        # Use the standard generation as a base
        command_str = self.generate_standard_deployment_commands(
            include_interface=include_interface,
            include_url_for_client=include_url_for_client,
            implementation_type=implementation_type,
        )

        # Add any QUIC-specific modifications if needed
        if support_wire_version and self.role == RoleEnum.client:
            # This would need to be injected into the command args
            # before template rendering in a real implementation
            pass

        return command_str
