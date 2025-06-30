"""Refactored quic-go service manager using base classes."""

from pathlib import Path
from typing import List, Optional, Tuple

from panther.core.docker_builder.plugin_mixin.service_manager_docker_mixin import (
    ServiceManagerDockerMixin,
)
from panther.plugins.core.plugin_decorators import register_plugin
from panther.plugins.core.structures.plugin_type import PluginType
from panther.plugins.services.base.quic_service_base import BaseQUICServiceManager
from panther.plugins.services.iut.iut_event_mixin import IUTManagerEventMixin
from panther.plugins.services.iut.iut_service_manager_mixin import (
    IUTServiceManagerMixin,
)
from panther.plugins.services.iut.quic.quic_go.config_schema import QuicGoConfig


@register_plugin(
    plugin_type=PluginType.IUT,
    name="quic_go",
    version="2.0.0",
    description="quic-go - Go implementation of QUIC (Refactored)",
    author="PANTHER Team",
    dependencies=["docker"],
    supported_protocols=["quic"],
    capabilities=["rfc9000", "0rtt", "migration"],
)
class QuicGoServiceManager(
    IUTServiceManagerMixin,
    ServiceManagerDockerMixin,
    IUTManagerEventMixin,
    BaseQUICServiceManager,
):
    """Refactored quic-go service manager with minimal code."""

    def __init__(self, *args, global_config=None, **kwargs):
        """Initialize QuicGo service manager with dual plugin config approach."""
        super().__init__(*args, global_config=global_config, **kwargs)

        # Cache plugin config for easy access
        self._plugin_config = None

    def _get_plugin_config(self) -> Optional[QuicGoConfig]:
        """Get plugin config with caching and fallback."""
        if self._plugin_config is None:
            try:
                self._plugin_config = self.service_config_to_test.get_plugin_config(
                    QuicGoConfig
                )
            except Exception as e:
                self.logger.debug(f"Could not get plugin config, using defaults: {e}")
                # Create default config
                self._plugin_config = QuicGoConfig()
        return self._plugin_config

    def _get_implementation_name(self) -> str:
        return "quic_go"

    def _get_binary_name(self) -> str:
        # quic-go uses example binaries
        return "server" if self.role == "server" else "client"

    def _get_server_specific_args(self, **kwargs) -> List[str]:
        """quic-go server specific arguments with plugin config support."""
        args = []

        # Get plugin config values with fallbacks
        plugin_config = self._get_plugin_config()

        # Document root for serving files - Check plugin_config first
        if kwargs.get("www"):
            www = kwargs["www"]
        elif (
            hasattr(self.service_config_to_test, "plugin_config")
            and self.service_config_to_test.plugin_config
        ):
            www = self.service_config_to_test.plugin_config.get("www", "/var/www")
        elif (
            plugin_config
            and hasattr(plugin_config, "version")
            and hasattr(plugin_config.version, "server")
        ):
            server_params = plugin_config.version.server
            www = server_params.get("www", "/var/www") if server_params else "/var/www"
        else:
            www = "/var/www"
        args.extend(["-www", www])

        # Certificate files - Check plugin_config first
        certfile = kwargs.get("certfile")
        keyfile = kwargs.get("keyfile")

        if (
            not certfile
            and hasattr(self.service_config_to_test, "plugin_config")
            and self.service_config_to_test.plugin_config
        ):
            certfile = self.service_config_to_test.plugin_config.get("certfile")
            keyfile = self.service_config_to_test.plugin_config.get("keyfile")
        elif (
            not certfile
            and plugin_config
            and hasattr(plugin_config, "version")
            and hasattr(plugin_config.version, "server")
        ):
            server_params = plugin_config.version.server
            if server_params:
                certfile = server_params.get("certfile")
                keyfile = server_params.get("keyfile")

        if certfile and keyfile:
            args.extend(["-certfile", certfile])
            args.extend(["-keyfile", keyfile])

        # Enable qlog - Check plugin_config first
        qlog = kwargs.get("qlog", False)
        if (
            not qlog
            and hasattr(self.service_config_to_test, "plugin_config")
            and self.service_config_to_test.plugin_config
        ):
            qlog = self.service_config_to_test.plugin_config.get("qlog", False)
        elif (
            not qlog
            and plugin_config
            and hasattr(plugin_config, "version")
            and hasattr(plugin_config.version, "server")
        ):
            server_params = plugin_config.version.server
            qlog = server_params.get("qlog", False) if server_params else False

        if qlog:
            args.append("-qlog")

        return args

    def _get_client_specific_args(self, **kwargs) -> List[str]:
        """quic-go client specific arguments with plugin config support."""
        args = []

        # Get plugin config values with fallbacks
        plugin_config = self._get_plugin_config()

        # Target URL - Check plugin_config first
        host = kwargs.get("host")
        port = kwargs.get("port")
        path = kwargs.get("path")

        if (
            not host
            and hasattr(self.service_config_to_test, "plugin_config")
            and self.service_config_to_test.plugin_config
        ):
            host = self.service_config_to_test.plugin_config.get("host", "localhost")
            port = self.service_config_to_test.plugin_config.get("port", 4443)
            path = self.service_config_to_test.plugin_config.get("path", "/")
        elif (
            not host
            and plugin_config
            and hasattr(plugin_config, "version")
            and hasattr(plugin_config.version, "client")
        ):
            client_params = plugin_config.version.client
            if client_params:
                host = client_params.get("host", "localhost")
                port = client_params.get("port", 4443)
                path = client_params.get("path", "/")

        if not host:
            host = "localhost"
        if not port:
            port = 4443
        if not path:
            path = "/"

        url = f"https://{host}:{port}{path}"
        args.append(url)

        # Insecure mode (skip cert verification) - Check plugin_config first
        insecure = kwargs.get("insecure")
        if (
            insecure is None
            and hasattr(self.service_config_to_test, "plugin_config")
            and self.service_config_to_test.plugin_config
        ):
            insecure = self.service_config_to_test.plugin_config.get("insecure", True)
        elif (
            insecure is None
            and plugin_config
            and hasattr(plugin_config, "version")
            and hasattr(plugin_config.version, "client")
        ):
            client_params = plugin_config.version.client
            insecure = client_params.get("insecure", True) if client_params else True
        else:
            insecure = True if insecure is None else insecure

        if insecure:
            args.append("-insecure")

        # Enable qlog - Check plugin_config first
        qlog = kwargs.get("qlog", False)
        if (
            not qlog
            and hasattr(self.service_config_to_test, "plugin_config")
            and self.service_config_to_test.plugin_config
        ):
            qlog = self.service_config_to_test.plugin_config.get("qlog", False)
        elif (
            not qlog
            and plugin_config
            and hasattr(plugin_config, "version")
            and hasattr(plugin_config.version, "client")
        ):
            client_params = plugin_config.version.client
            qlog = client_params.get("qlog", False) if client_params else False

        if qlog:
            args.append("-qlog")

        # Verbose output
        if kwargs.get("verbose", False):
            args.append("-v")

        return args

    def generate_compile_command(self, **kwargs) -> str:
        """Go-specific compile command."""
        return "go build -o server ./example/main.go && go build -o client ./example/client/main.go"

    def _extract_common_params(self, **kwargs):
        """Extract Go-specific parameters."""
        params = super()._extract_common_params(**kwargs)

        # Go-specific environment
        params["go_path"] = kwargs.get("go_path", "/opt/quic-go")
        params["go_env"] = kwargs.get("go_env", {})

        return params

    def get_output_patterns(self) -> List[Tuple[str, str]]:
        """
        Get phase-based output patterns for quic-go service.

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
            ("go_binaries", "artifacts/server"),
            ("go_client", "artifacts/client"),
            ("go_modules", "artifacts/go.mod"),
            ("analysis", "artifacts/analysis_{service_name}.json"),
        ]

    def generate_post_run_commands(self) -> List[str]:
        """quic-go post-run cleanup with phase-based output organization."""
        return [
            # Create artifacts directory
            "mkdir -p /app/logs/artifacts;",
            # Copy binaries to artifacts (not root logs)
            "cp /opt/quic-go/server /app/logs/artifacts/ 2>/dev/null || true;",
            "cp /opt/quic-go/client /app/logs/artifacts/ 2>/dev/null || true;",
            # Copy Go module files to artifacts
            "cp /opt/quic-go/go.mod /app/logs/artifacts/ 2>/dev/null || true;",
            # Copy any QUIC logs to artifacts
            "find /tmp -name '*.qlog' -exec cp {} /app/logs/artifacts/ \\; 2>/dev/null || true;",
        ]

    def generate_deployment_commands(self) -> str:
        """Generate deployment commands for compatibility."""
        role = getattr(self, "role", "client")
        if role == "server":
            return f"{self._get_binary_name()} -www /var/www"
        else:
            return f"{self._get_binary_name()} https://localhost:4443/ -insecure"

    def _do_prepare(self, plugin_manager=None):
        """Prepare the quic-go service."""
        pass

    def get_supported_features(self) -> dict:
        """Get quic-go specific supported features."""
        features = super().get_supported_features()
        # quic-go has excellent HTTP/3 and Go-specific features
        features.update(
            {
                "http3": True,
                "golang": True,
                "performance": True,
                "memory_efficient": True,
                "concurrent": True,
            }
        )
        return features
