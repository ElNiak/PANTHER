"""Refactored PicoQUIC service manager using base classes."""

from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Protocol, Tuple

from panther.config.core.models import ProtocolConfig, ProtocolRole
from panther.config.core.models.service import ServiceConfig
from panther.core.docker_builder.plugin_mixin.service_manager_docker_mixin import (
    ServiceManagerDockerMixin,
)
from panther.core.exceptions.error_handler_mixin import ErrorHandlerMixin
from panther.plugins.core.plugin_decorators import register_plugin
from panther.plugins.core.structures.plugin_type import PluginType
from panther.plugins.services.base.quic_service_base import BaseQUICServiceManager
from panther.plugins.services.iut.iut_event_mixin import IUTManagerEventMixin
from panther.plugins.services.iut.iut_service_manager_mixin import (
    IUTServiceManagerMixin,
)
from panther.plugins.services.iut.quic.picoquic.config_schema import PicoquicConfig

if TYPE_CHECKING:
    from panther.plugins.plugin_manager import PluginManager


@register_plugin(
    plugin_type=PluginType.IUT,
    name="picoquic",
    version="1.0.0",  # Plugin version, not protocol version
    author="PANTHER Team",
    description="PicoQUIC - Minimalist implementation of the QUIC protocol",
    license="MIT",
    homepage="https://github.com/private-octopus/picoquic",
    min_panther_version="1.0.0",
    dependencies=[
        {"name": "quic_protocol", "version_spec": ">=1.0.0", "plugin_type": "protocol"}
    ],
    supported_protocols=["quic"],
    capabilities=[
        "tls13",
        "0rtt",
        "connection_migration",
        "multipath",
        "datagram",
        "version_negotiation",
    ],
    tags=["quic", "implementation", "c", "minimalist", "research"],
    external_dependencies=[
        "docker",
        "picotls",
    ],  # TODO: ARM: https://github.com/h2o/picotls/wiki/Using-picotls
)
class PicoquicServiceManager(
    IUTServiceManagerMixin,
    ServiceManagerDockerMixin,
    IUTManagerEventMixin,
    BaseQUICServiceManager,
    ErrorHandlerMixin,
):
    """
    PicoQUIC service manager with auto-discovered version configurations.

    Version configurations are automatically loaded from the version_configs/
    directory based on the QUIC protocol plugin's defined versions.

    This implementation reduces code duplication by:
    - Inheriting common QUIC functionality from BaseQUICServiceManager
    - Auto-discovering version configurations from YAML files
    - Using protocol-defined version validation
    """

    def __init__(
        self,
        service_config_to_test: ServiceConfig,  # Accept both ServiceConfig and PicoquicConfig
        service_type: Any,  # Can be string or ImplementationType enum
        protocol: ProtocolConfig,
        implementation_name: str,
        event_manager=None,
        global_config=None,
        test_case=None,  # Reference to parent test case for execution environment access
        **kwargs,
    ):
        """Initialize the PicoQUIC service manager.

        Args:
            service_config_to_test: Service configuration
            service_type: Type of service (iut)
            protocol: Protocol configuration
            implementation_name: Implementation name (picoquic)
            event_manager: Event manager for monitoring
        """

        # Extract emitter_registry from kwargs if present
        emitter_registry = kwargs.pop("emitter_registry", None)

        # Store original service config for compatibility
        self._original_service_config = service_config_to_test

        # Initialize base class with proper parameters
        super().__init__(
            service_config_to_test=service_config_to_test,
            service_type=service_type,
            protocol=protocol,
            implementation_name=implementation_name,
            event_manager=event_manager,
            emitter_registry=emitter_registry,
            global_config=global_config,
            test_case=test_case,  # Pass test case reference for execution environment access
            **kwargs,
        )

        # Store plugin directory (parent class handles other attributes)
        self.plugin_dir = Path(__file__).parent

        # Initialize working directory
        self.working_dir = "/opt/picoquic"

        # Cache plugin config for easy access
        self._plugin_config = None
        
        self.standard_iut_initialization(
            service_config_to_test, service_type, protocol, 
            implementation_name, event_manager,
            plugin_dir=Path(__file__).parent
        )

    def _get_plugin_config(self) -> Optional[PicoquicConfig]:
        """Get plugin config with caching and fallback."""
        if self._plugin_config is None:
            try:
                self._plugin_config = self.service_config_to_test.get_plugin_config(
                    PicoquicConfig
                )
            except Exception as e:
                self.logger.debug(f"Could not get plugin config, using defaults: {e}")
                # Create default config
                self._plugin_config = PicoquicConfig()
        return self._plugin_config

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

        # Get server parameters from plugin config
        plugin_config = self._get_plugin_config()
        if (
            plugin_config
            and hasattr(plugin_config, "version")
            and hasattr(plugin_config.version, "server")
        ):
            server_params = plugin_config.version.server

            # Add protocol-specific parameters
            if isinstance(server_params, dict) and "protocol" in server_params:
                protocol_params = server_params["protocol"]
                if (
                    isinstance(protocol_params, dict)
                    and "additional_parameters" in protocol_params
                ):
                    # Split additional parameters if they're a single string with spaces
                    additional_params = protocol_params["additional_parameters"]
                    if isinstance(additional_params, str):
                        # Use shlex.split to properly handle quoted arguments
                        import shlex

                        args.extend(shlex.split(additional_params))
                    else:
                        args.append(additional_params)

        return args

    def _get_client_specific_args(self, **kwargs) -> List[str]:
        """Get PicoQUIC-specific client arguments.

        Args:
            **kwargs: Configuration parameters

        Returns:
            List of client-specific arguments
        """
        args = []

        # Get client parameters from plugin config
        plugin_config = self._get_plugin_config()
        if (
            plugin_config
            and hasattr(plugin_config, "version")
            and hasattr(plugin_config.version, "client")
        ):
            client_params = plugin_config.version.client

            # Add ticket file for 0-RTT
            if isinstance(client_params, dict) and "ticket_file" in client_params:
                ticket_file_params = client_params["ticket_file"]
                if (
                    isinstance(ticket_file_params, dict)
                    and "param" in ticket_file_params
                    and "file" in ticket_file_params
                ):
                    args.extend(
                        [ticket_file_params["param"], ticket_file_params["file"]]
                    )

            # Add protocol-specific parameters
            if isinstance(client_params, dict) and "protocol" in client_params:
                protocol_params = client_params["protocol"]
                if (
                    isinstance(protocol_params, dict)
                    and "additional_parameters" in protocol_params
                ):
                    # Split additional parameters if they're a single string with spaces
                    additional_params = protocol_params["additional_parameters"]
                    if isinstance(additional_params, str):
                        # Use shlex.split to properly handle quoted arguments
                        import shlex

                        args.extend(shlex.split(additional_params))
                    else:
                        args.append(additional_params)

            # Add initial version
            # Note: We add the version here instead of in base class to avoid duplication
            if isinstance(client_params, dict) and "initial_version" in client_params:
                args.extend(["-v", client_params["initial_version"]])

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
                # Convert enum to string if necessary
                version = protocol_cfg.version
                if hasattr(version, "name"):
                    params["version"] = version.name
                elif hasattr(version, "value"):
                    params["version"] = str(version.value)
                else:
                    params["version"] = str(version)

        # Get role-specific parameters
        role_params = self._get_role_params()
        if role_params:
            # Update network parameters
            if "network" in role_params:
                params["port"] = role_params["network"].get("port", params["port"])
                # Always pass network configuration to template (including interface if present)
                params["network"] = role_params["network"]

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
        # Try to get from plugin config first
        plugin_config = self._get_plugin_config()
        if plugin_config and hasattr(plugin_config, "version"):
            version = plugin_config.version
            role = self.service_config_to_test.protocol.role

            if role == ProtocolRole.SERVER and hasattr(version, "server"):
                return version.server
            elif role == ProtocolRole.CLIENT and hasattr(version, "client"):
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

        # First try to get version from plugin config
        plugin_config = self._get_plugin_config()
        if (
            plugin_config
            and hasattr(plugin_config, "version")
            and hasattr(plugin_config.version, "version")
        ):
            version_str = plugin_config.version.version
        # Fallback to implementation version if available
        elif hasattr(self.service_config_to_test.implementation, "version"):
            version_obj = self.service_config_to_test.implementation.version
            if isinstance(version_obj, str):
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
        """Generate the run command structure using templates for correct ordering.

        Returns:
            Dictionary with run command configuration
        """
        # Extract parameters for template rendering
        params = self._extract_common_params()

        # Get role from protocol configuration
        role = "client"  # default
        if hasattr(self.service_config_to_test, "protocol") and hasattr(
            self.service_config_to_test.protocol, "role"
        ):
            role_obj = self.service_config_to_test.protocol.role
            # Convert role enum to string if needed
            if hasattr(role_obj, "name"):
                role = (
                    role_obj.name.lower()
                )  # 'CLIENT' -> 'client', 'SERVER' -> 'server'
            elif hasattr(role_obj, "value"):
                role = role_obj.value.lower()
            else:
                role = str(role_obj).lower()

        # Prepare template parameters
        template_params = {
            "binary_path": self._get_binary_path(),
            "certificates": {
                "cert_param": "-c",
                "cert_file": params.get("cert_file", "/opt/certs/cert.pem"),
                "key_param": "-k",
                "key_file": params.get("key_file", "/opt/certs/key.pem"),
            },
            "logging": {
                "log_path": params.get("log_file", "-"),  # "-" for stdout
                "err_path": params.get("err_file", "-"),  # "-" for stderr
            },
            "network": {
                "port": params.get("port", 4443),
                "interface": params.get("network", {}).get("interface")
                if params.get("network")
                else None,
            },
            "protocol": {
                "alpn": {"param": "-a", "value": "hq-interop"},  # Default ALPN for QUIC
                "additional_parameters": "",
            },
        }

        # Add role-specific parameters
        if role == "client":
            # Client-specific template parameters
            template_params["target"] = params.get("host", "localhost")

            # Add ticket file for 0-RTT if available
            plugin_config = self._get_plugin_config()
            if (
                plugin_config
                and hasattr(plugin_config, "version")
                and hasattr(plugin_config.version, "client")
            ):
                client_params = plugin_config.version.client

                if isinstance(client_params, dict):
                    # Handle ticket file
                    if "ticket_file" in client_params and isinstance(
                        client_params["ticket_file"], dict
                    ):
                        template_params["ticket_file"] = {
                            "param": client_params["ticket_file"].get("param", "-T"),
                            "file": client_params["ticket_file"].get(
                                "file", "/opt/ticket/ticket.key"
                            ),
                        }
                    else:
                        template_params["ticket_file"] = {
                            "param": "-T",
                            "file": "/opt/ticket/ticket.key",
                        }

                    # Add initial version if specified
                    if "initial_version" in client_params:
                        template_params["initial_version"] = client_params[
                            "initial_version"
                        ]

                    # Add additional protocol parameters
                    if "protocol" in client_params and isinstance(
                        client_params["protocol"], dict
                    ):
                        protocol_params = client_params["protocol"]
                        if "additional_parameters" in protocol_params:
                            template_params["protocol"][
                                "additional_parameters"
                            ] = protocol_params["additional_parameters"]
            else:
                # Default ticket file
                template_params["ticket_file"] = {
                    "param": "-T",
                    "file": "/opt/ticket/ticket.key",
                }

            # Render using client template - this ensures correct argument order
            command_str = self.render_commands(
                params=template_params, template_name="client_command.jinja"
            )
        else:
            # Server-specific template parameters
            plugin_config = self._get_plugin_config()
            if (
                plugin_config
                and hasattr(plugin_config, "version")
                and hasattr(plugin_config.version, "server")
            ):
                server_params = plugin_config.version.server

                if isinstance(server_params, dict) and "protocol" in server_params:
                    protocol_params = server_params["protocol"]
                    if (
                        isinstance(protocol_params, dict)
                        and "additional_parameters" in protocol_params
                    ):
                        template_params["protocol"][
                            "additional_parameters"
                        ] = protocol_params["additional_parameters"]

            # Render using server template
            command_str = self.render_commands(
                params=template_params, template_name="server_command.jinja"
            )

        # Get working directory
        role_params = self._get_role_params()
        if role_params and "binary" in role_params and "dir" in role_params["binary"]:
            self.working_dir = role_params["binary"]["dir"]

        # Parse the rendered command to extract binary and args
        import shlex

        command_parts = shlex.split(command_str)
        if command_parts:
            command_binary = command_parts[0]
            command_args = " ".join(shlex.quote(part) for part in command_parts[1:])
        else:
            command_binary = self._get_binary_path()
            command_args = ""

        return {
            "working_dir": self.working_dir,
            "command_binary": command_binary,
            "command_args": command_args,
            "timeout": self.service_config_to_test.timeout,
            "environment": {},
        }

    def get_output_patterns(self) -> List[Tuple[str, str]]:
        """
        Get phase-based output patterns for PicoQUIC service.

        Returns:
            List of (output_type, filename_pattern) tuples organized by execution phases
        """
        return [
            # Pre-compile phase outputs
            ("pre_compile_stdout", "pre-compile/stdout.log"),
            ("pre_compile_stderr", "pre-compile/stderr.log"),
            # Compile phase outputs
            ("compile_stdout", "compile/stdout.log"),
            ("compile_stderr", "compile/stderr.log"),
            # Post-compile phase outputs
            ("post_compile_stdout", "post-compile/stdout.log"),
            ("post_compile_stderr", "post-compile/stderr.log"),
            # Pre-run phase outputs
            ("pre_run_stdout", "pre-run/stdout.log"),
            ("pre_run_stderr", "pre-run/stderr.log"),
            # Runtime phase outputs (main execution)
            ("runtime_stdout", "runtime/stdout.log"),
            ("runtime_stderr", "runtime/stderr.log"),
            # Post-run phase outputs
            ("post_run_stdout", "post-run/stdout.log"),
            ("post_run_stderr", "post-run/stderr.log"),
            # Test phase outputs
            ("test_stdout", "test/stdout.log"),
            ("test_stderr", "test/stderr.log"),
            # Artifacts - protocol-specific files organized by type
            ("qlog", "artifacts/*.qlog"),
            ("sslkeylog", "artifacts/sslkeylogfile.txt"),
            ("keys", "artifacts/*keys.log"),
            ("pcap", "artifacts/{service_name}.pcap"),
            ("congestion", "artifacts/*congestion*.log"),
            ("binary", "artifacts/picoquicdemo"),
            ("analysis", "artifacts/analysis_{service_name}.json"),
        ]

    def generate_post_run_commands(self) -> List[str]:
        """Generate post-run commands with phase-based output organization."""
        return [
            # Create artifacts directory
            "mkdir -p /app/logs/artifacts;",
            # Copy binary to artifacts (not root logs)
            "cp /opt/picoquic/picoquicdemo /app/logs/artifacts/picoquicdemo 2>/dev/null || true;",
            # Copy any QUIC logs to artifacts
            "find /tmp -name \"*.qlog\" -exec cp {} /app/logs/artifacts/ \\; 2>/dev/null || true;",
            # Copy SSL key logs to artifacts
            "find /tmp -name \"*keys.log\" -exec cp {} /app/logs/artifacts/ \\; 2>/dev/null || true;",
        ]

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
