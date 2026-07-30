#!/usr/bin/env python3.10
"""Tests for Rust QUIC base service manager against real PANTHER implementations.

Tests the real RustQUICServiceManager and BaseQUICServiceManager classes.
IO boundaries (filesystem for templates directory) are mocked; all PANTHER
imports are real.
"""

from __future__ import annotations

from typing import Any, Dict, List
from unittest.mock import patch

import pytest

from panther.config.core.models.service import (
    ImplementationConfig,
    ImplementationType,
    ProtocolConfig,
    ProtocolRole,
    ServiceConfig,
)
from panther.plugins.services.base.quic_service_base import BaseQUICServiceManager
from panther.plugins.services.base.rust_quic_base import RustQUICServiceManager

pytestmark = [pytest.mark.unit, pytest.mark.rust_quic]


# ---------------------------------------------------------------------------
# Helpers: minimal config objects and concrete subclass
# ---------------------------------------------------------------------------


def _make_protocol(
    name: str = "quic",
    version: str = "rfc9000",
    role: ProtocolRole = ProtocolRole.SERVER,
    target: str | None = None,
) -> ProtocolConfig:
    """Create a ProtocolConfig for testing."""
    kwargs: Dict[str, Any] = {"name": name, "version": version, "role": role}
    if target is not None:
        kwargs["target"] = target
    return ProtocolConfig(**kwargs)


def _make_service_config(
    impl_name: str = "test_rust_impl",
    impl_type: ImplementationType = ImplementationType.IUT,
    protocol: ProtocolConfig | None = None,
    timeout: int = 60,
    service_name: str = "test_rust_server",
) -> ServiceConfig:
    """Create a ServiceConfig with a .name attribute for testing."""
    if protocol is None:
        protocol = _make_protocol()
    impl = ImplementationConfig(name=impl_name, type=impl_type)
    sc = ServiceConfig(implementation=impl, protocol=protocol, timeout=timeout)
    # IServiceManager.__init__ reads service_config_to_test.name
    sc.name = service_name
    return sc


class ConcreteRustQuicManager(RustQUICServiceManager):
    """Concrete subclass that implements all abstract methods for testing."""

    CARGO_BIN = "rust-quic-bin"

    def _get_implementation_name(self) -> str:
        return "test_rust_impl"

    def _get_cargo_bin_name(self) -> str:
        return self.CARGO_BIN

    def _get_server_specific_args(self, **kwargs) -> List[str]:
        args: List[str] = []
        if kwargs.get("bind_address"):
            args.extend(["--bind", kwargs["bind_address"]])
        if kwargs.get("max_connections"):
            args.extend(["--max-connections", str(kwargs["max_connections"])])
        return args

    def _get_client_specific_args(self, **kwargs) -> List[str]:
        args: List[str] = []
        if kwargs.get("request_path"):
            args.extend(["--path", kwargs["request_path"]])
        return args

    def generate_deployment_commands(self) -> str:
        return f"{self.CARGO_BIN} --server --port 4443"

    def handle_event(self, event: Any) -> None:
        pass


@pytest.fixture()
def server_protocol() -> ProtocolConfig:
    """ProtocolConfig for a QUIC server."""
    return _make_protocol(role=ProtocolRole.SERVER)


@pytest.fixture()
def client_protocol() -> ProtocolConfig:
    """ProtocolConfig for a QUIC client."""
    return _make_protocol(role=ProtocolRole.CLIENT, target="server")


@pytest.fixture()
def server_manager(server_protocol: ProtocolConfig) -> ConcreteRustQuicManager:
    """Create a ConcreteRustQuicManager configured as server."""
    sc = _make_service_config(protocol=server_protocol, service_name="rust_server")
    with patch("os.path.isdir", return_value=False):
        return ConcreteRustQuicManager(
            service_config_to_test=sc,
            service_type=ImplementationType.IUT,
            protocol=server_protocol,
            implementation_name="test_rust_impl",
        )


@pytest.fixture()
def client_manager(client_protocol: ProtocolConfig) -> ConcreteRustQuicManager:
    """Create a ConcreteRustQuicManager configured as client."""
    sc = _make_service_config(protocol=client_protocol, service_name="rust_client")
    with patch("os.path.isdir", return_value=False):
        return ConcreteRustQuicManager(
            service_config_to_test=sc,
            service_type=ImplementationType.IUT,
            protocol=client_protocol,
            implementation_name="test_rust_impl",
        )


# ---------------------------------------------------------------------------
# Test: Initialization and type hierarchy
# ---------------------------------------------------------------------------


class TestRustQUICInitialization:
    """Test RustQUICServiceManager initialization and inheritance."""

    def test_isinstance_checks(self, server_manager: ConcreteRustQuicManager) -> None:
        """Manager is an instance of the full class hierarchy."""
        assert isinstance(server_manager, RustQUICServiceManager)
        assert isinstance(server_manager, BaseQUICServiceManager)

    def test_implementation_name(self, server_manager: ConcreteRustQuicManager) -> None:
        """Implementation name is set from _get_implementation_name()."""
        assert server_manager.implementation_name == "test_rust_impl"

    def test_protocol_name(self, server_manager: ConcreteRustQuicManager) -> None:
        """Protocol name is set to 'quic'."""
        assert server_manager.protocol_name == "quic"

    def test_service_name_from_config(
        self, server_manager: ConcreteRustQuicManager
    ) -> None:
        """Service name comes from service_config_to_test.name."""
        assert server_manager.service_name == "rust_server"

    def test_role_from_protocol(self, server_manager: ConcreteRustQuicManager) -> None:
        """Role is derived from protocol config."""
        assert server_manager.role == "server"

    def test_client_role(self, client_manager: ConcreteRustQuicManager) -> None:
        """Client role is set correctly."""
        assert client_manager.role == "client"

    def test_binary_name_delegates_to_cargo_bin_name(
        self, server_manager: ConcreteRustQuicManager
    ) -> None:
        """_get_binary_name() delegates to _get_cargo_bin_name()."""
        assert server_manager._get_binary_name() == "rust-quic-bin"
        assert server_manager._get_binary_name() == server_manager._get_cargo_bin_name()

    def test_binary_path_without_working_dir(
        self, server_manager: ConcreteRustQuicManager
    ) -> None:
        """Without working_dir, _get_binary_path() returns just the binary name."""
        assert server_manager._get_binary_path() == "rust-quic-bin"

    def test_binary_path_with_working_dir(
        self, server_manager: ConcreteRustQuicManager
    ) -> None:
        """With working_dir, _get_binary_path() returns full path."""
        server_manager.working_dir = "/opt/rust-quic"
        assert server_manager._get_binary_path() == "/opt/rust-quic/rust-quic-bin"

    def test_is_tester_false_for_iut(
        self, server_manager: ConcreteRustQuicManager
    ) -> None:
        """IUT service managers report is_tester() as False."""
        assert server_manager.is_tester() is False

    def test_is_server_and_is_client(
        self,
        server_manager: ConcreteRustQuicManager,
        client_manager: ConcreteRustQuicManager,
    ) -> None:
        """is_server() and is_client() reflect the role."""
        assert server_manager.is_server() is True
        assert server_manager.is_client() is False
        assert client_manager.is_server() is False
        assert client_manager.is_client() is True

    def test_implementation_manager_is_never_tester(
        self, server_protocol: ProtocolConfig
    ) -> None:
        """IImplementationManager.is_tester() always returns False by design.

        Even when service_type is TESTERS, IImplementationManager overrides
        IServiceManager.is_tester() to always return False because IUT
        implementation managers are not testers.
        """
        sc = _make_service_config(
            impl_type=ImplementationType.TESTERS,
            protocol=server_protocol,
            service_name="rust_tester",
        )
        with patch("os.path.isdir", return_value=False):
            mgr = ConcreteRustQuicManager(
                service_config_to_test=sc,
                service_type=ImplementationType.TESTERS,
                protocol=server_protocol,
                implementation_name="test_rust_impl",
            )
        # IImplementationManager hardcodes is_tester() = False
        assert mgr.is_tester() is False


# ---------------------------------------------------------------------------
# Test: _extract_common_params (Rust override adds rust_log, rust_backtrace)
# ---------------------------------------------------------------------------


class TestRustExtractCommonParams:
    """Test Rust-specific parameter extraction."""

    def test_default_params(self, server_manager: ConcreteRustQuicManager) -> None:
        """Default params include both base QUIC and Rust-specific keys."""
        params = server_manager._extract_common_params()
        # Base keys
        assert params["host"] == "localhost"
        assert params["port"] == 4443
        assert params["cert_dir"] == "/opt/certs"
        assert params["version"] == "rfc9000"
        # Rust-specific keys
        assert params["rust_log"] == "info"
        assert params["rust_backtrace"] == "1"

    def test_custom_params(self, server_manager: ConcreteRustQuicManager) -> None:
        """Custom kwargs override defaults."""
        params = server_manager._extract_common_params(
            host="192.168.1.1",
            port=8443,
            rust_log="debug",
            rust_backtrace="0",
        )
        assert params["host"] == "192.168.1.1"
        assert params["port"] == 8443
        assert params["rust_log"] == "debug"
        assert params["rust_backtrace"] == "0"

    def test_cert_params(self, server_manager: ConcreteRustQuicManager) -> None:
        """Certificate-related params are extracted."""
        params = server_manager._extract_common_params(
            cert_file="/certs/server.crt",
            key_file="/certs/server.key",
        )
        assert params["cert_file"] == "/certs/server.crt"
        assert params["key_file"] == "/certs/server.key"


# ---------------------------------------------------------------------------
# Test: _build_rust_env_vars
# ---------------------------------------------------------------------------


class TestBuildRustEnvVars:
    """Test Rust-specific environment variable generation."""

    def test_default_env_vars(self, server_manager: ConcreteRustQuicManager) -> None:
        """Default env vars include RUST_LOG and RUST_BACKTRACE."""
        params = server_manager._extract_common_params()
        env = server_manager._build_rust_env_vars(params)
        assert env == {"RUST_LOG": "info", "RUST_BACKTRACE": "1"}

    def test_custom_rust_log(self, server_manager: ConcreteRustQuicManager) -> None:
        """Custom rust_log is reflected in env vars."""
        params = server_manager._extract_common_params(rust_log="debug")
        env = server_manager._build_rust_env_vars(params)
        assert env["RUST_LOG"] == "debug"

    def test_custom_backtrace(self, server_manager: ConcreteRustQuicManager) -> None:
        """Custom rust_backtrace is reflected in env vars."""
        params = server_manager._extract_common_params(rust_backtrace="full")
        env = server_manager._build_rust_env_vars(params)
        assert env["RUST_BACKTRACE"] == "full"


# ---------------------------------------------------------------------------
# Test: generate_compile_command (Rust overrides base to use cargo)
# ---------------------------------------------------------------------------


class TestRustCompileCommand:
    """Test Rust-specific compile command generation."""

    def test_release_build_default(
        self, server_manager: ConcreteRustQuicManager
    ) -> None:
        """Default compile command uses cargo build --release."""
        cmd = server_manager.generate_compile_command()
        assert "cargo build --release" in cmd

    def test_debug_build(self, server_manager: ConcreteRustQuicManager) -> None:
        """Debug build omits --release flag."""
        cmd = server_manager.generate_compile_command(build_type="debug")
        assert "cargo build" in cmd
        assert "--release" not in cmd

    def test_jobs_flag(self, server_manager: ConcreteRustQuicManager) -> None:
        """Custom jobs value is included."""
        cmd = server_manager.generate_compile_command(jobs="4")
        assert "--jobs 4" in cmd

    def test_default_jobs_uses_nproc(
        self, server_manager: ConcreteRustQuicManager
    ) -> None:
        """Default jobs parameter uses $(nproc)."""
        cmd = server_manager.generate_compile_command()
        assert "--jobs $(nproc)" in cmd


# ---------------------------------------------------------------------------
# Test: generate_run_command (template method)
# ---------------------------------------------------------------------------


class TestRustRunCommandGeneration:
    """Test run command generation for Rust QUIC implementations."""

    def test_server_command_includes_binary(
        self, server_manager: ConcreteRustQuicManager
    ) -> None:
        """Server command starts with the binary name."""
        cmd = server_manager.generate_run_command(role="server")
        assert "rust-quic-bin" in cmd

    def test_server_command_includes_port(
        self, server_manager: ConcreteRustQuicManager
    ) -> None:
        """Server command includes port flag."""
        cmd = server_manager.generate_run_command(role="server", port=8443)
        assert "-p" in cmd
        assert "8443" in cmd

    def test_server_command_includes_certs(
        self, server_manager: ConcreteRustQuicManager
    ) -> None:
        """Server command includes cert and key flags."""
        cmd = server_manager.generate_run_command(
            role="server",
            cert_file="/certs/cert.pem",
            key_file="/certs/key.pem",
        )
        assert "-c" in cmd
        assert "/certs/cert.pem" in cmd
        assert "-k" in cmd
        assert "/certs/key.pem" in cmd

    def test_server_command_with_specific_args(
        self, server_manager: ConcreteRustQuicManager
    ) -> None:
        """Server command includes implementation-specific args."""
        cmd = server_manager.generate_run_command(
            role="server",
            bind_address="0.0.0.0",
            max_connections=1000,
        )
        assert "--bind" in cmd
        assert "0.0.0.0" in cmd
        assert "--max-connections" in cmd
        assert "1000" in cmd

    def test_client_command_includes_host_and_port(
        self, client_manager: ConcreteRustQuicManager
    ) -> None:
        """Client command includes host and port as positional args."""
        cmd = client_manager.generate_run_command(
            role="client", host="example.com", port=443
        )
        assert "rust-quic-bin" in cmd
        assert "example.com" in cmd
        assert "443" in cmd

    def test_client_command_includes_version(
        self, client_manager: ConcreteRustQuicManager
    ) -> None:
        """Client command includes -v flag with mapped version."""
        cmd = client_manager.generate_run_command(
            role="client", host="example.com", port=443, version="rfc9000"
        )
        assert "-v" in cmd

    def test_client_command_with_specific_args(
        self, client_manager: ConcreteRustQuicManager
    ) -> None:
        """Client command includes implementation-specific args."""
        cmd = client_manager.generate_run_command(
            role="client",
            host="example.com",
            port=443,
            request_path="/api/data",
        )
        assert "--path" in cmd
        assert "/api/data" in cmd

    def test_default_role_is_client(
        self, client_manager: ConcreteRustQuicManager
    ) -> None:
        """When no role is specified, default is client."""
        cmd = client_manager.generate_run_command(host="localhost", port=4443)
        # Client commands include host and port as positional args
        assert "localhost" in cmd
        assert "4443" in cmd

    def test_command_returns_string(
        self, server_manager: ConcreteRustQuicManager
    ) -> None:
        """generate_run_command always returns a string."""
        cmd = server_manager.generate_run_command(role="server")
        assert isinstance(cmd, str)

    def test_server_log_file(self, server_manager: ConcreteRustQuicManager) -> None:
        """Server command includes -l flag when log_file is specified."""
        cmd = server_manager.generate_run_command(
            role="server", log_file="/logs/server.log"
        )
        assert "-l" in cmd
        assert "/logs/server.log" in cmd

    def test_client_log_file(self, client_manager: ConcreteRustQuicManager) -> None:
        """Client command includes -l flag when log_file is specified."""
        cmd = client_manager.generate_run_command(
            role="client",
            host="localhost",
            port=4443,
            log_file="/logs/client.log",
        )
        assert "-l" in cmd
        assert "/logs/client.log" in cmd


# ---------------------------------------------------------------------------
# Test: get_supported_features (Rust adds memory_safety, async, tokio, performance)
# ---------------------------------------------------------------------------


class TestRustSupportedFeatures:
    """Test Rust-specific feature support declarations."""

    def test_base_quic_features_present(
        self, server_manager: ConcreteRustQuicManager
    ) -> None:
        """Base QUIC features (client, server, 0rtt, etc.) are present."""
        features = server_manager.get_supported_features()
        assert features["client"] is True
        assert features["server"] is True
        assert features["0rtt"] is True
        assert features["qlog"] is True

    def test_rust_specific_features_present(
        self, server_manager: ConcreteRustQuicManager
    ) -> None:
        """Rust-specific features are added by the Rust subclass."""
        features = server_manager.get_supported_features()
        assert features["memory_safety"] is True
        assert features["async"] is True
        assert features["tokio"] is True
        assert features["performance"] is True

    def test_multipath_default_false(
        self, server_manager: ConcreteRustQuicManager
    ) -> None:
        """Multipath is False by default."""
        features = server_manager.get_supported_features()
        assert features["multipath"] is False


# ---------------------------------------------------------------------------
# Test: validate_configuration
# ---------------------------------------------------------------------------


class TestRustConfigValidation:
    """Test configuration validation inherited from BaseQUICServiceManager."""

    def test_valid_server_config(self, server_manager: ConcreteRustQuicManager) -> None:
        """Valid server configuration returns no errors."""
        errors = server_manager.validate_configuration(
            role="server", port=4443, version="rfc9000"
        )
        assert errors == []

    def test_valid_client_config(self, server_manager: ConcreteRustQuicManager) -> None:
        """Valid client configuration returns no errors."""
        errors = server_manager.validate_configuration(
            role="client", port=443, version="rfc9000"
        )
        assert errors == []

    def test_invalid_role(self, server_manager: ConcreteRustQuicManager) -> None:
        """Invalid role produces an error."""
        errors = server_manager.validate_configuration(role="invalid", port=4443)
        assert any("Invalid role" in e for e in errors)

    def test_invalid_port_too_high(
        self, server_manager: ConcreteRustQuicManager
    ) -> None:
        """Port > 65535 produces an error."""
        errors = server_manager.validate_configuration(role="server", port=99999)
        assert any("Invalid port" in e for e in errors)

    def test_invalid_port_zero(self, server_manager: ConcreteRustQuicManager) -> None:
        """Port 0 produces an error."""
        errors = server_manager.validate_configuration(role="server", port=0)
        assert any("Invalid port" in e for e in errors)

    def test_unsupported_version(self, server_manager: ConcreteRustQuicManager) -> None:
        """Unsupported version produces an error."""
        errors = server_manager.validate_configuration(
            role="server", port=4443, version="draft99"
        )
        assert any("Unsupported version" in e for e in errors)

    def test_multiple_errors(self, server_manager: ConcreteRustQuicManager) -> None:
        """Multiple validation errors can be returned at once."""
        errors = server_manager.validate_configuration(
            role="peer", port=-1, version="unknown"
        )
        assert len(errors) >= 2


# ---------------------------------------------------------------------------
# Test: version mapping
# ---------------------------------------------------------------------------


class TestVersionMapping:
    """Test _map_version used during client command generation."""

    def test_rfc9000_maps_to_1(self, server_manager: ConcreteRustQuicManager) -> None:
        """rfc9000 maps to version string '1'."""
        assert server_manager._map_version("rfc9000") == "1"

    def test_draft29_maps_correctly(
        self, server_manager: ConcreteRustQuicManager
    ) -> None:
        """draft29 maps to hex representation."""
        assert server_manager._map_version("draft29") == "ff00001d"

    def test_draft27_maps_correctly(
        self, server_manager: ConcreteRustQuicManager
    ) -> None:
        """draft27 maps to hex representation."""
        assert server_manager._map_version("draft27") == "ff00001b"

    def test_unknown_version_defaults_to_1(
        self, server_manager: ConcreteRustQuicManager
    ) -> None:
        """Unknown version defaults to '1'."""
        assert server_manager._map_version("v2_future") == "1"


# ---------------------------------------------------------------------------
# Test: generate_deployment_commands and other command hooks
# ---------------------------------------------------------------------------


class TestRustCommandHooks:
    """Test various command generation hooks."""

    def test_deployment_commands(self, server_manager: ConcreteRustQuicManager) -> None:
        """generate_deployment_commands returns the expected string."""
        cmd = server_manager.generate_deployment_commands()
        assert "rust-quic-bin" in cmd
        assert "--server" in cmd
        assert "--port 4443" in cmd

    def test_pre_compile_command_default_empty(
        self, server_manager: ConcreteRustQuicManager
    ) -> None:
        """Default pre-compile command is empty."""
        cmd = server_manager.generate_pre_compile_command()
        assert cmd == ""

    def test_post_compile_command_default_empty(
        self, server_manager: ConcreteRustQuicManager
    ) -> None:
        """Default post-compile command is empty."""
        cmd = server_manager.generate_post_compile_command()
        assert cmd == ""

    def test_post_run_command_default_empty(
        self, server_manager: ConcreteRustQuicManager
    ) -> None:
        """Default post-run command is empty."""
        cmd = server_manager.generate_post_run_command()
        assert cmd == ""


# ---------------------------------------------------------------------------
# Test: server/client arg building (base class methods)
# ---------------------------------------------------------------------------


class TestArgBuilding:
    """Test _build_server_args and _build_client_args from base class."""

    def test_server_args_include_cert_key_port(
        self, server_manager: ConcreteRustQuicManager
    ) -> None:
        """Server args include -c, -k, and -p flags."""
        params = {
            "cert_file": "/certs/cert.pem",
            "key_file": "/certs/key.pem",
            "port": 4443,
            "log_file": None,
        }
        args = server_manager._build_server_args(params)
        assert "-c" in args
        assert "/certs/cert.pem" in args
        assert "-k" in args
        assert "/certs/key.pem" in args
        assert "-p" in args
        assert "4443" in args

    def test_server_args_with_log_file(
        self, server_manager: ConcreteRustQuicManager
    ) -> None:
        """Server args include -l when log_file is present."""
        params = {
            "cert_file": None,
            "key_file": None,
            "port": 4443,
            "log_file": "/logs/server.log",
        }
        args = server_manager._build_server_args(params)
        assert "-l" in args
        assert "/logs/server.log" in args

    def test_client_args_include_host_port_version(
        self, client_manager: ConcreteRustQuicManager
    ) -> None:
        """Client args include host, port, and version flag."""
        params = {
            "host": "example.com",
            "port": 443,
            "version": "rfc9000",
            "log_file": None,
        }
        args = client_manager._build_client_args(params)
        assert "example.com" in args
        assert "443" in args
        assert "-v" in args

    def test_client_args_with_log_file(
        self, client_manager: ConcreteRustQuicManager
    ) -> None:
        """Client args include -l when log_file is present."""
        params = {
            "host": "localhost",
            "port": 4443,
            "version": "rfc9000",
            "log_file": "/logs/client.log",
        }
        args = client_manager._build_client_args(params)
        assert "-l" in args
        assert "/logs/client.log" in args


# ---------------------------------------------------------------------------
# Test: output patterns (QUIC-specific)
# ---------------------------------------------------------------------------


class TestOutputPatterns:
    """Test output pattern generation for QUIC protocol."""

    def test_quic_output_patterns_include_qlog(
        self, server_manager: ConcreteRustQuicManager
    ) -> None:
        """QUIC services include qlog in their output patterns."""
        patterns = server_manager.get_output_patterns()
        pattern_types = [p[0] for p in patterns]
        assert "qlog" in pattern_types

    def test_quic_output_patterns_include_pcap(
        self, server_manager: ConcreteRustQuicManager
    ) -> None:
        """QUIC services include pcap in their output patterns."""
        patterns = server_manager.get_output_patterns()
        pattern_types = [p[0] for p in patterns]
        assert "pcap" in pattern_types

    def test_standard_output_patterns_present(
        self, server_manager: ConcreteRustQuicManager
    ) -> None:
        """Standard stdout/stderr patterns are always present."""
        patterns = server_manager.get_output_patterns()
        pattern_types = [p[0] for p in patterns]
        assert "stdout" in pattern_types
        assert "stderr" in pattern_types

    def test_add_custom_output_pattern(
        self, server_manager: ConcreteRustQuicManager
    ) -> None:
        """Custom output patterns can be added."""
        server_manager.add_output_pattern("flamegraph", "flamegraph.svg")
        patterns = server_manager.get_output_patterns()
        pattern_types = [p[0] for p in patterns]
        assert "flamegraph" in pattern_types


# ---------------------------------------------------------------------------
# Test: integration scenarios
# ---------------------------------------------------------------------------


class TestRustQUICIntegration:
    """Integration tests combining multiple real API calls."""

    def test_full_server_command_pipeline(
        self, server_manager: ConcreteRustQuicManager
    ) -> None:
        """Full server pipeline: params -> args -> command."""
        params = server_manager._extract_common_params(
            host="0.0.0.0",
            port=4443,
            cert_file="/certs/cert.pem",
            key_file="/certs/key.pem",
            rust_log="debug",
        )

        # Check Rust params extracted
        assert params["rust_log"] == "debug"
        assert params["rust_backtrace"] == "1"

        # Build env vars
        env = server_manager._build_rust_env_vars(params)
        assert env["RUST_LOG"] == "debug"

        # Build server args
        args = server_manager._build_server_args(params)
        assert "-c" in args
        assert "-p" in args

        # Full command
        cmd = server_manager.generate_run_command(
            role="server",
            port=4443,
            cert_file="/certs/cert.pem",
            key_file="/certs/key.pem",
        )
        assert "rust-quic-bin" in cmd
        assert isinstance(cmd, str)

    def test_full_client_command_pipeline(
        self, client_manager: ConcreteRustQuicManager
    ) -> None:
        """Full client pipeline: params -> args -> command."""
        params = client_manager._extract_common_params(
            host="quic.example.com",
            port=443,
            version="rfc9000",
        )

        # Build client args
        args = client_manager._build_client_args(params)
        assert "quic.example.com" in args
        assert "443" in args

        # Full command
        cmd = client_manager.generate_run_command(
            role="client",
            host="quic.example.com",
            port=443,
            request_path="/api/test",
        )
        assert "rust-quic-bin" in cmd
        assert "quic.example.com" in cmd
        assert "--path" in cmd

    def test_compile_and_run_commands_differ(
        self, server_manager: ConcreteRustQuicManager
    ) -> None:
        """Compile command uses cargo, run command uses the binary."""
        compile_cmd = server_manager.generate_compile_command()
        run_cmd = server_manager.generate_run_command(role="server")

        assert "cargo build" in compile_cmd
        assert "rust-quic-bin" in run_cmd
        assert "cargo" not in run_cmd

    def test_features_combine_base_and_rust(
        self, server_manager: ConcreteRustQuicManager
    ) -> None:
        """Supported features combine base QUIC and Rust-specific features."""
        features = server_manager.get_supported_features()

        # Base QUIC features
        assert features["client"] is True
        assert features["server"] is True
        assert features["0rtt"] is True

        # Rust-specific features
        assert features["memory_safety"] is True
        assert features["tokio"] is True

        # Total features should be > base features alone
        assert len(features) >= 10

    def test_validation_then_command(
        self, server_manager: ConcreteRustQuicManager
    ) -> None:
        """Validate config, then generate command if valid."""
        errors = server_manager.validate_configuration(
            role="server", port=4443, version="rfc9000"
        )
        assert errors == []

        cmd = server_manager.generate_run_command(role="server", port=4443)
        assert "rust-quic-bin" in cmd
        assert "4443" in cmd


# ---------------------------------------------------------------------------
# Test: string representation (StringRepresentationMixin)
# ---------------------------------------------------------------------------


class TestStringRepresentation:
    """Test __str__ and __repr__ from StringRepresentationMixin."""

    def test_str_includes_class_name(
        self, server_manager: ConcreteRustQuicManager
    ) -> None:
        """String representation includes the class name."""
        s = str(server_manager)
        assert "ConcreteRustQuicManager" in s

    def test_str_includes_implementation(
        self, server_manager: ConcreteRustQuicManager
    ) -> None:
        """String representation includes implementation name."""
        s = str(server_manager)
        assert "test_rust_impl" in s

    def test_repr_matches_str(self, server_manager: ConcreteRustQuicManager) -> None:
        """repr() and str() return the same value."""
        assert repr(server_manager) == str(server_manager)


if __name__ in {"__main__", "__mp_main__"}:
    pytest.main([__file__, "-v"])
