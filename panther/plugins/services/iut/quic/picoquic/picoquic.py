"""Refactored PicoQUIC service manager using base classes."""

from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Protocol

from panther.core.docker_builder.service_manager_docker_mixin import (
    ServiceManagerDockerMixin,
)
from panther.plugins.plugin_decorators import register_plugin
from panther.config.core.models import ProtocolConfig, ProtocolRole
from panther.plugins.services.base.quic_service_base import BaseQUICServiceManager
from panther.plugins.services.iut.quic.picoquic.config_schema import PicoquicConfig

if TYPE_CHECKING:
    from panther.plugins.plugin_manager import PluginManager


@register_plugin(
    plugin_type="iut",
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
    config_schema={
        "timeout": {
            "type": "number",
            "default": 60,
            "description": "Service execution timeout in seconds"
        },
        "certificates": {
            "type": "object",
            "properties": {
                "cert_file": {
                    "type": "string",
                    "description": "Path to certificate file"
                },
                "key_file": {
                    "type": "string", 
                    "description": "Path to private key file"
                }
            }
        },
        "server": {
            "type": "object",
            "properties": {
                "port": {"type": "number", "default": 4443},
                "binary": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "default": "picoquicdemo"},
                        "dir": {"type": "string", "default": "/opt/picoquic"}
                    }
                }
            }
        },
        "client": {
            "type": "object",
            "properties": {
                "binary": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "default": "picoquicdemo"},
                        "dir": {"type": "string", "default": "/opt/picoquic"}
                    }
                }
            }
        }
    },
    default_config={
        "timeout": 60,
        "generate_new_certificates": True,
        "server": {
            "port": 4443,
            "binary": {"name": "picoquicdemo", "dir": "/opt/picoquic"}
        },
        "client": {
            "binary": {"name": "picoquicdemo", "dir": "/opt/picoquic"}
        }
    },
    supported_protocols=["quic", "http3"],
    capabilities=["tls13", "0rtt", "connection_migration", "multipath", "datagram", "version_negotiation"],
    tags=["quic", "implementation", "c", "minimalist", "research"],
    external_dependencies=["docker"],
)
class PicoquicServiceManager(BaseQUICServiceManager, ServiceManagerDockerMixin):
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
        service_config_to_test,  # Accept both ServiceConfig and PicoquicConfig
        service_type: Any,  # Can be string or ImplementationType enum
        protocol: ProtocolConfig,
        implementation_name: str,
        event_manager=None,
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
        # Handle both ServiceConfig and PicoquicConfig types
        if hasattr(service_config_to_test, 'implementation'):
            # This is a ServiceConfig, we need to create a mock object
            # that has both PicoquicConfig properties and ProtocolConfig
            from panther.plugins.services.iut.quic.picoquic.config_schema import PicoquicConfig
            
            # Get the implementation config
            impl_config = service_config_to_test.implementation
            
            # Create a PicoquicConfig with default version loading
            picoquic_config_data = {
                'name': impl_config.name,
                'type': impl_config.type,
            }
            
            # Only add version if it's not None
            version_value = getattr(impl_config, 'version', None)
            if version_value is not None:
                picoquic_config_data['version'] = version_value
            
            # Add any other extra attributes from implementation
            excluded_fields = {'version'}  # Skip version as we handle it separately
            for attr_name in dir(impl_config):
                if (not attr_name.startswith('_') and 
                    attr_name not in picoquic_config_data and 
                    attr_name not in excluded_fields):
                    try:
                        value = getattr(impl_config, attr_name)
                        if not callable(value) and value is not None:
                            picoquic_config_data[attr_name] = value
                    except:
                        pass
            
            picoquic_config = PicoquicConfig(**picoquic_config_data)
            
            # Create a mock object that combines PicoquicConfig with the original ServiceConfig
            class MockServiceConfig:
                def __init__(self, picoquic_config, protocol_config, original_service_config):
                    # Copy all attributes from PicoquicConfig
                    for attr in dir(picoquic_config):
                        if not attr.startswith('_'):
                            try:
                                setattr(self, attr, getattr(picoquic_config, attr))
                            except:
                                pass
                    # Override protocol with the ProtocolConfig object (for services_interface compatibility)
                    self.protocol = protocol_config
                    # Add the implementation attribute (as PicoquicConfig)
                    self.implementation = picoquic_config
                    # Add other necessary attributes from original service config
                    for attr in ['name', 'timeout', 'ports', 'volumes', 'generate_new_certificates',
                                'command_override', 'working_directory', 'depends_on', 'restart_policy',
                                'network', 'environment']:
                        if hasattr(original_service_config, attr):
                            setattr(self, attr, getattr(original_service_config, attr))
            
            service_config_to_test = MockServiceConfig(picoquic_config, protocol, service_config_to_test)
        
        # Extract emitter_registry from kwargs if present
        emitter_registry = kwargs.pop("emitter_registry", None)

        # Initialize base class with proper parameters
        super().__init__(
            service_config_to_test=service_config_to_test,
            service_type=service_type,
            protocol=protocol,
            implementation_name=implementation_name,
            event_manager=event_manager,
            emitter_registry=emitter_registry,
            **kwargs,
        )

        # Store plugin directory (parent class handles other attributes)
        self.plugin_dir = Path(__file__).parent

        # Initialize working directory
        self.working_dir = "/opt/picoquic"

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
                # Split additional parameters if they're a single string with spaces
                additional_params = server_params.protocol.additional_parameters
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
                # Split additional parameters if they're a single string with spaces
                additional_params = client_params.protocol.additional_parameters
                if isinstance(additional_params, str):
                    # Use shlex.split to properly handle quoted arguments
                    import shlex

                    args.extend(shlex.split(additional_params))
                else:
                    args.append(additional_params)

            # Add initial version
            # Note: We add the version here instead of in base class to avoid duplication
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

            # Update certificate parameters
            if "certificate" in role_params:
                cert = role_params["certificate"]
                params["cert_dir"] = cert.get("dir", params["cert_dir"])
                params["cert_file"] = (
                    f"{params['cert_dir']}/{cert.get('cert', 'cert.pem')}"
                )
                params["key_file"] = (
                    f"{params['cert_dir']}/{cert.get('key', 'key.pem')}"
                )

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
                "interface": None,  # Optional interface binding
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
            if hasattr(self.service_config_to_test, "implementation"):
                client_params = (
                    self.service_config_to_test.implementation.version.client
                )
                if hasattr(client_params, "ticket_file"):
                    template_params["ticket_file"] = {
                        "param": client_params.ticket_file.param,
                        "file": client_params.ticket_file.file,
                    }
                else:
                    template_params["ticket_file"] = {
                        "param": "-T",
                        "file": "/opt/ticket/ticket.key",
                    }

                # Add initial version if specified
                if hasattr(client_params, "initial_version"):
                    template_params["initial_version"] = client_params.initial_version

                # Add additional protocol parameters
                if hasattr(client_params, "protocol") and hasattr(
                    client_params.protocol, "additional_parameters"
                ):
                    template_params["protocol"][
                        "additional_parameters"
                    ] = client_params.protocol.additional_parameters

            # Render using client template - this ensures correct argument order
            command_str = self.render_commands(
                params=template_params, template_name="client_command.jinja"
            )
        else:
            # Server-specific template parameters
            if hasattr(self.service_config_to_test, "implementation"):
                server_params = (
                    self.service_config_to_test.implementation.version.server
                )
                if hasattr(server_params, "protocol") and hasattr(
                    server_params.protocol, "additional_parameters"
                ):
                    template_params["protocol"][
                        "additional_parameters"
                    ] = server_params.protocol.additional_parameters

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