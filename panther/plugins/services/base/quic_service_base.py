"""Base class for all QUIC service implementations."""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Protocol

from panther.core.command_processor.command_utils import CommandUtils
from panther.plugins.services.services_interface import IServiceManager


class BaseQUICServiceManager(IServiceManager, ABC):
    """
    This class provides common functionality for QUIC protocol implementations,
    reducing code duplication across different service managers.
    """

    def __init__(
        self,
        service_config_to_test: Any,
        service_type: Any,  # Can be string or ImplementationType enum
        protocol: Any,
        implementation_name: str,
        event_manager: Any = None,
        emitter_registry: Any = None,
        **kwargs,
    ):
        """Initialize the base QUIC service manager.

        Args:
            service_config_to_test: Service configuration
            service_type: Type of service (IUT/tester) - string or ImplementationType enum
            protocol: Protocol configuration
            implementation_name: Name of the implementation
            event_manager: Event manager instance
            emitter_registry: Emitter registry (optional)
            **kwargs: Additional configuration
        """
        # Convert string service_type to ImplementationType enum if needed
        from panther.config.core.models.service import ImplementationType

        if isinstance(service_type, str):
            # Map string to enum
            if service_type.lower() in ["iut"]:
                service_type = ImplementationType.IUT
            elif service_type.lower() in ["testers", "tester"]:
                service_type = ImplementationType.TESTERS
            else:
                # Try to create enum from string value
                try:
                    service_type = ImplementationType(service_type.lower())
                except ValueError:
                    raise ValueError(
                        f"Invalid service type: {service_type}. Must be 'iut' or 'testers'"
                    )

        super().__init__(
            service_config_to_test,
            service_type,
            protocol,
            implementation_name,
            event_manager,
        )
        self.protocol_name = "quic"
        self.implementation_name = self._get_implementation_name()

        # Handle logger property conflict by using a different attribute name
        # DON'T set self.logger - use _quic_logger instead to avoid conflicts
        self._quic_logger = logging.getLogger(f"{__name__}.{self.implementation_name}")

        # Store emitter registry if provided
        self.emitter_registry = emitter_registry

    @abstractmethod
    def _get_implementation_name(self) -> str:
        """Return the implementation name (e.g., 'picoquic', 'aioquic')."""
        pass

    @abstractmethod
    def _get_binary_name(self) -> str:
        """Return the binary name for this implementation."""
        pass

    def _get_binary_path(self) -> str:
        """Return the full path to the binary.

        This method can be overridden by implementations that need custom paths.
        By default, it combines the working directory with the binary name.

        Returns:
            Full path to the binary executable
        """
        binary_name = self._get_binary_name()

        # Check if the implementation has a working_dir attribute
        if hasattr(self, "working_dir") and self.working_dir:
            import os

            return os.path.join(self.working_dir, binary_name)

        # Fallback to just the binary name if no working directory
        return binary_name

    @abstractmethod
    def _get_server_specific_args(self, **kwargs) -> List[str]:
        """Get implementation-specific server arguments.

        Args:
            **kwargs: Configuration parameters

        Returns:
            List of server-specific command arguments
        """
        pass

    @abstractmethod
    def _get_client_specific_args(self, **kwargs) -> List[str]:
        """
        Get implementation-specific client arguments.

        Args:
            **kwargs: Configuration parameters

        Returns:
            List of client-specific command arguments
        """
        pass

    def generate_run_command(self, **kwargs) -> str:
        """Generate run command using template method pattern.

        This method provides the common structure for generating QUIC commands,
        delegating implementation-specific details to abstract methods.

        Args:
            **kwargs: Command generation parameters including:
                - role: 'client' or 'server'
                - host: Target host (for client)
                - port: Port number
                - cert_dir: Certificate directory
                - key_file: Key file path
                - version: QUIC version

        Returns:
            Complete command string
        """
        role = kwargs.get("role", "client")

        # Extract common parameters
        params = self._extract_common_params(**kwargs)

        # Build base command with full binary path
        cmd_parts = [self._get_binary_path()]

        # Add common arguments based on role
        if role == "server":
            cmd_parts.extend(self._build_server_args(params))
            cmd_parts.extend(self._get_server_specific_args(**kwargs))
        else:
            cmd_parts.extend(self._build_client_args(params))
            cmd_parts.extend(self._get_client_specific_args(**kwargs))

        # Build final command with proper escaping
        import shlex

        # Special handling for multi-part binary commands (e.g., "python script.py")
        binary_path = cmd_parts[0]
        if " " in binary_path and not binary_path.startswith('"'):
            # Split the binary path into components
            binary_components = binary_path.split()
            # Replace the first element with the split components
            cmd_parts = binary_components + cmd_parts[1:]

        command = " ".join(shlex.quote(str(part)) for part in cmd_parts)

        self._quic_logger.debug(f"Generated {role} command: {command}")
        return command

    def _extract_common_params(self, **kwargs) -> Dict[str, Any]:
        """Extract common parameters used by all implementations.

        Args:
            **kwargs: Raw parameters

        Returns:
            Dictionary of normalized common parameters
        """
        return {
            "host": kwargs.get("host", "localhost"),
            "port": kwargs.get("port", 4443),
            "cert_dir": kwargs.get("cert_dir", "/opt/certs"),
            "key_file": kwargs.get("key_file", "/opt/certs/key.pem"),
            "cert_file": kwargs.get("cert_file", "/opt/certs/cert.pem"),
            "version": kwargs.get("version", "rfc9000"),
            "log_level": kwargs.get("log_level", "info"),
            "log_file": kwargs.get("log_file"),
            "output_dir": kwargs.get("output_dir", "/logs"),
        }

    def _build_server_args(self, params: Dict[str, Any]) -> List[str]:
        """Build common server arguments.

        Args:
            params: Common parameters

        Returns:
            List of server arguments
        """
        args = []

        # Certificate and key
        if params.get("cert_file"):
            args.extend(["-c", params["cert_file"]])
        if params.get("key_file"):
            args.extend(["-k", params["key_file"]])

        # Port
        args.extend(["-p", str(params["port"])])

        # Logging
        if params.get("log_file"):
            args.extend(["-l", params["log_file"]])

        return args

    def _build_client_args(self, params: Dict[str, Any]) -> List[str]:
        """Build common client arguments.

        Args:
            params: Common parameters

        Returns:
            List of client arguments
        """
        args = []

        # Host and port (usually positional for clients)
        args.extend([params["host"], str(params["port"])])

        # Version
        version_arg = self._map_version(params["version"])
        if version_arg:
            args.extend(["-v", version_arg])

        # Logging
        if params.get("log_file"):
            args.extend(["-l", params["log_file"]])

        return args

    def _map_version(self, version: str) -> Optional[str]:
        """Map version string to implementation-specific format.

        Args:
            version: Standard version string (e.g., 'rfc9000')

        Returns:
            Implementation-specific version string or None
        """
        # Handle enum values
        version_str = str(version)

        # Extract enum value if it's in the format "VersionEnum.rfc9000"
        if "VersionEnum." in version_str and "<" not in version_str:
            version_str = version_str.split(".")[-1]

        # Also handle numeric enum values (e.g., <VersionEnum.rfc9000: 1>)
        elif "<VersionEnum." in version_str and ":" in version_str:
            # Extract the part between . and :
            dot_pos = version_str.find(".") + 1
            colon_pos = version_str.find(":")
            version_str = version_str[dot_pos:colon_pos].strip()

        # Default version mapping - implementations can override
        version_map = {
            "rfc9000": "1",
            "draft29": "ff00001d",
            "draft27": "ff00001b",
        }
        return version_map.get(version_str, "1")  # Default to "1" for rfc9000

    def generate_compile_command(self, **kwargs) -> str:
        """Generate compile command for C/C++ implementations.

        Most QUIC implementations use CMake, so we provide a sensible default.
        Implementations can override if needed.

        Args:
            **kwargs: Compile parameters including:
                - build_type: 'Release' or 'Debug'
                - jobs: Number of parallel jobs

        Returns:
            Compile command string
        """
        build_type = kwargs.get("build_type", "Release")
        jobs = kwargs.get("jobs", "$(nproc)")

        return f"cmake -DCMAKE_BUILD_TYPE={build_type} . && make -j{jobs}"

    def generate_pre_compile_command(self, **kwargs) -> str:
        """Generate pre-compile command.

        Default implementation for dependency installation or setup.

        Args:
            **kwargs: Pre-compile parameters

        Returns:
            Pre-compile command string or empty string
        """
        # Most implementations don't need pre-compile steps
        return ""

    def generate_post_compile_command(self, **kwargs) -> str:
        """Generate post-compile command.

        Default implementation for post-build steps.

        Args:
            **kwargs: Post-compile parameters

        Returns:
            Post-compile command string or empty string
        """
        # Most implementations don't need post-compile steps
        return ""

    def generate_post_run_command(self, **kwargs) -> str:
        """Generate post-run command.

        Default implementation for cleanup or result processing.

        Args:
            **kwargs: Post-run parameters

        Returns:
            Post-run command string or empty string
        """
        # Most implementations don't need post-run steps
        return ""

    def get_supported_features(self) -> Dict[str, bool]:
        """Get supported features for this implementation.

        Returns:
            Dictionary of feature support flags
        """
        # Default features - implementations can override
        return {
            "client": True,
            "server": True,
            "0rtt": True,
            "migration": True,
            "multipath": False,
            "qlog": True,
        }

    def validate_configuration(self, **kwargs) -> List[str]:
        """Validate configuration parameters.

        Args:
            **kwargs: Configuration to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Validate role
        role = kwargs.get("role")
        if role not in ["client", "server"]:
            errors.append(f"Invalid role: {role}. Must be 'client' or 'server'")

        # Validate port
        port = kwargs.get("port", 4443)
        if not isinstance(port, int) or port < 1 or port > 65535:
            errors.append(f"Invalid port: {port}. Must be between 1 and 65535")

        # Validate version
        version = kwargs.get("version", "rfc9000")
        supported_versions = ["rfc9000", "draft29", "draft27"]
        if version not in supported_versions:
            errors.append(
                f"Unsupported version: {version}. Supported: {supported_versions}"
            )

        return errors
