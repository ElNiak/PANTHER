"""Refactored PicoQUIC service manager using base classes."""

from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from panther.core.utils import ServiceManagerDockerMixin
from panther.plugins.plugin_decorators import register_plugin
from panther.plugins.protocols.config_schema import ProtocolConfig, RoleEnum
from panther.plugins.services.base.quic_service_base import BaseQUICServiceManager
from panther.plugins.services.base.service_command_builder import ServiceCommandBuilder
from panther.plugins.services.iut.quic.picoquic.config_schema import PicoquicConfig

if TYPE_CHECKING:
    from panther.plugins.plugin_manager import PluginManager


@register_plugin(
    plugin_type="iut",
    name="picoquic",
    version="2.0.0",  # Bumped version for refactored implementation
    description="PicoQUIC - Lightweight QUIC implementation by Christian Huitema (Refactored)",
    author="PANTHER Team",
    dependencies=["docker"],
    supported_protocols=["quic"],
    capabilities=["rfc9000", "0rtt", "migration"],
    external_dependencies=["docker"],
)
class PicoquicServiceManager(BaseQUICServiceManager, ServiceManagerDockerMixin):
    """Refactored PicoQUIC service manager using base classes.

    This implementation reduces code duplication by inheriting common QUIC
    functionality from BaseQUICServiceManager.
    """

    def __init__(
        self,
        service_config_to_test: PicoquicConfig,
        service_type: str,
        protocol: ProtocolConfig,
        implementation_name: str,
        event_manager=None,
    ):
        """Initialize the PicoQUIC service manager.

        Args:
            service_config_to_test: Service configuration
            service_type: Type of service (iut)
            protocol: Protocol configuration
            implementation_name: Implementation name (picoquic)
            event_manager: Event manager for monitoring
        """
        # Initialize base class with correct parameters
        super().__init__(
            service_config_to_test=service_config_to_test,
            service_type=service_type,
            protocol=protocol,
            implementation_name=implementation_name,
            event_manager=event_manager,
        )

        # Store configuration
        self.service_config_to_test = service_config_to_test
        self.service_type = service_type
        self.protocol = protocol
        self.implementation_name = implementation_name
        self.plugin_dir = Path(__file__).parent

        # Initialize working directory
        self.working_dir = "/opt/picoquic"

        # Service name for Docker
        self.service_name = service_config_to_test.name

    def _get_implementation_name(self) -> str:
        """Return the implementation name."""
        return "picoquic"

    def _get_binary_name(self) -> str:
        """Return the binary name for PicoQUIC."""
        return "picoquicdemo"

    def _get_server_specific_args(self, **kwargs) -> List[str]:
        """Get PicoQUIC-specific server arguments.

        Args:
            **kwargs: Configuration parameters

        Returns:
            List of server-specific arguments
        """
        args = []

        # Get server parameters from config
        if hasattr(self.service_config_to_test, "implementation"):
            server_params = self.service_config_to_test.implementation.version.server

            # Add protocol-specific parameters
            if hasattr(server_params, "protocol") and hasattr(
                server_params.protocol, "additional_parameters"
            ):
                args.append(server_params.protocol.additional_parameters)

        return args

    def _get_client_specific_args(self, **kwargs) -> List[str]:
        """Get PicoQUIC-specific client arguments.

        Args:
            **kwargs: Configuration parameters

        Returns:
            List of client-specific arguments
        """
        args = []

        # Get client parameters from config
        if hasattr(self.service_config_to_test, "implementation"):
            client_params = self.service_config_to_test.implementation.version.client

            # Add ticket file for 0-RTT
            if hasattr(client_params, "ticket_file"):
                args.extend(
                    [client_params.ticket_file.param, client_params.ticket_file.file]
                )

            # Add protocol-specific parameters
            if hasattr(client_params, "protocol") and hasattr(
                client_params.protocol, "additional_parameters"
            ):
                args.append(client_params.protocol.additional_parameters)

            # Add initial version
            if hasattr(client_params, "initial_version"):
                args.extend(["-v", client_params.initial_version])

        return args

    def _extract_common_params(self, **kwargs) -> Dict[str, Any]:
        """Extract common parameters from configuration.

        Returns:
            Dictionary of common parameters
        """
        # Get base parameters
        params = super()._extract_common_params(**kwargs)

        # Override with config values if available
        if hasattr(self.service_config_to_test, "protocol"):
            protocol_cfg = self.service_config_to_test.protocol

            if hasattr(protocol_cfg, "target"):
                params["host"] = protocol_cfg.target

            if hasattr(protocol_cfg, "version"):
                params["version"] = protocol_cfg.version

        # Get role-specific parameters
        role_params = self._get_role_params()
        if role_params:
            # Update network parameters
            if "network" in role_params:
                params["port"] = role_params["network"].get("port", params["port"])

            # Update certificate parameters
            if "certificate" in role_params:
                cert = role_params["certificate"]
                params["cert_dir"] = cert.get("dir", params["cert_dir"])
                params[
                    "cert_file"
                ] = f"{params['cert_dir']}/{cert.get('cert', 'cert.pem')}"
                params[
                    "key_file"
                ] = f"{params['cert_dir']}/{cert.get('key', 'key.pem')}"

        return params

    def _get_role_params(self) -> Optional[Dict[str, Any]]:
        """Get role-specific parameters from configuration.

        Returns:
            Role parameters or None
        """
        if not hasattr(self.service_config_to_test, "implementation"):
            return None

        impl = self.service_config_to_test.implementation
        if not hasattr(impl, "version"):
            return None

        version = impl.version
        role = self.service_config_to_test.protocol.role

        if role == RoleEnum.server and hasattr(version, "server"):
            return version.server
        elif role == RoleEnum.client and hasattr(version, "client"):
            return version.client

        return None

    def get_service_name(self) -> str:
        """Get the service name."""
        return self.service_name

    def _get_docker_image_name(self, implementation_name: str = None) -> str:
        """Get the Docker image name for PicoQUIC.

        Args:
            implementation_name: Implementation name (unused)

        Returns:
            Docker image name with version tag
        """
        version_str = "latest"

        if hasattr(self.service_config_to_test.implementation, "version"):
            version_obj = self.service_config_to_test.implementation.version
            if hasattr(version_obj, "version"):
                version_str = version_obj.version
            elif isinstance(version_obj, str):
                version_str = version_obj

        return f"picoquic:{version_str}"

    def generate_pre_compile_commands(self) -> List[str]:
        """Generate pre-compile commands."""
        # PicoQUIC doesn't need pre-compile commands
        return []

    def generate_compile_commands(self) -> List[str]:
        """Generate compile commands."""
        # PicoQUIC is pre-compiled in Docker image
        return []

    def generate_pre_run_commands(self) -> List[str]:
        """Generate pre-run commands."""
        # No specific pre-run commands for PicoQUIC
        return []

    def generate_run_command(self) -> Dict[str, Any]:
        """Generate the run command structure.

        Returns:
            Dictionary with run command configuration
        """
        # Extract parameters
        params = self._extract_common_params()

        # Generate command using base class
        command_str = self.generate_run_command(**params)

        # Get role parameters for working directory
        role_params = self._get_role_params()
        if role_params and "binary" in role_params and "dir" in role_params["binary"]:
            self.working_dir = role_params["binary"]["dir"]

        return {
            "working_dir": self.working_dir,
            "command_binary": self._get_binary_name(),
            "command_args": command_str.replace(self._get_binary_name(), "").strip(),
            "timeout": self.service_config_to_test.timeout,
            "environment": {},
        }

    def generate_post_run_commands(self) -> List[str]:
        """Generate post-run commands."""
        return ["cp /opt/picoquic/picoquicdemo /app/logs/picoquicdemo;"]

    def _do_prepare(self, plugin_manager: Optional["PluginManager"] = None):
        """Prepare the service manager.

        Args:
            plugin_manager: Plugin manager for Docker operations
        """
        # Delegate to Docker mixin for image building
        if hasattr(super(), "prepare"):
            super().prepare(plugin_manager)

    def generate_deployment_commands(self) -> str:
        """Generate deployment commands for compatibility.

        This method exists for backward compatibility with the old interface.

        Returns:
            Command string
        """
        params = self._extract_common_params()
        return (
            self.generate_run_command(**params)
            .replace(self._get_binary_name(), "")
            .strip()
        )
