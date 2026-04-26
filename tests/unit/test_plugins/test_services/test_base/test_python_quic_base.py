#!/usr/bin/env python3.10
"""Tests for PythonQUICServiceManager and BaseQUICServiceManager using real classes.

Tests the real implementations at:
- panther.plugins.services.base.quic_service_base.BaseQUICServiceManager
- panther.plugins.services.base.python_quic_base.PythonQUICServiceManager

All tests use real class behavior with IO boundaries mocked (filesystem,
Jinja2 template loading, logging).
"""

from __future__ import annotations

from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, patch

import pytest

from panther.config.core.models.service import (
    ImplementationConfig,
    ImplementationType,
    ProtocolConfig,
    ProtocolRole,
    ServiceConfig,
)
from panther.plugins.services.base.python_quic_base import PythonQUICServiceManager
from panther.plugins.services.base.quic_service_base import BaseQUICServiceManager

pytestmark = [pytest.mark.unit, pytest.mark.python_quic]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_service_config(
    name: str = "test_service",
    impl_name: str = "test_python_quic",
    impl_type: str = "iut",
    protocol_name: str = "quic",
    protocol_version: str = "rfc9000",
    role: str = "server",
    target: str | None = None,
) -> ServiceConfig:
    """Build a minimal ServiceConfig for testing."""
    proto_kwargs: Dict[str, Any] = {
        "name": protocol_name,
        "version": protocol_version,
        "role": role,
    }
    if role == "client":
        proto_kwargs["target"] = target or "server"

    return ServiceConfig(
        name=name,
        implementation=ImplementationConfig(name=impl_name, type=impl_type),
        protocol=ProtocolConfig(**proto_kwargs),
    )


def _make_protocol_config(
    name: str = "quic",
    version: str = "rfc9000",
    role: str = "server",
    target: str | None = None,
) -> ProtocolConfig:
    """Build a minimal ProtocolConfig for testing."""
    kwargs: Dict[str, Any] = {"name": name, "version": version, "role": role}
    if role == "client":
        kwargs["target"] = target or "server"
    return ProtocolConfig(**kwargs)


class ConcretePythonQUIC(PythonQUICServiceManager):
    """Concrete test implementation of PythonQUICServiceManager.

    Provides implementations for all abstract methods so that
    the real class can be instantiated in tests.
    """

    def _get_implementation_name(self) -> str:
        return "test_python_quic"

    def _get_python_module(self) -> str:
        return "test_quic_module"

    def _get_server_specific_args(self, **kwargs) -> List[str]:
        args: List[str] = []
        if kwargs.get("bind_address"):
            args.extend(["--bind", kwargs["bind_address"]])
        return args

    def _get_client_specific_args(self, **kwargs) -> List[str]:
        args: List[str] = []
        if kwargs.get("request_path"):
            args.extend(["--path", kwargs["request_path"]])
        return args

    def generate_deployment_commands(self, **kwargs) -> str:
        return f"python -m {self._get_python_module()} --server --port 4443"

    def _do_prepare(self, plugin_manager=None):
        pass

    def handle_event(self, event):
        """Satisfy abstract method from IPlugin."""
        pass


@pytest.fixture
def service_config():
    """Minimal ServiceConfig for server role."""
    return _make_service_config(role="server")


@pytest.fixture
def client_service_config():
    """Minimal ServiceConfig for client role."""
    return _make_service_config(role="client", target="server")


@pytest.fixture
def protocol_config():
    """Minimal ProtocolConfig for quic/server."""
    return _make_protocol_config()


@pytest.fixture
def python_quic_manager(service_config, protocol_config):
    """Create a real ConcretePythonQUIC with IO mocked out.

    Mocks the filesystem checks and Jinja2 template loading that happen
    during IServiceManager.__init__, but leaves all QUIC/Python logic real.
    """
    with (
        patch("os.path.isdir", return_value=True),
        patch("os.listdir", return_value=[]),
        patch(
            "panther.plugins.services.services_interface.Environment",
            return_value=MagicMock(),
        ),
        patch(
            "panther.plugins.services.services_interface.FileSystemLoader",
            return_value=MagicMock(),
        ),
        patch(
            "panther.plugins.services.services_interface.select_autoescape",
            return_value=[],
        ),
    ):
        manager = ConcretePythonQUIC(
            service_config_to_test=service_config,
            service_type=ImplementationType.IUT,
            protocol=protocol_config,
            implementation_name="test_python_quic",
        )
    return manager


@pytest.fixture
def client_manager(client_service_config):
    """Create a ConcretePythonQUIC with client role."""
    protocol = _make_protocol_config(role="client", target="server")
    with (
        patch("os.path.isdir", return_value=True),
        patch("os.listdir", return_value=[]),
        patch(
            "panther.plugins.services.services_interface.Environment",
            return_value=MagicMock(),
        ),
        patch(
            "panther.plugins.services.services_interface.FileSystemLoader",
            return_value=MagicMock(),
        ),
        patch(
            "panther.plugins.services.services_interface.select_autoescape",
            return_value=[],
        ),
    ):
        manager = ConcretePythonQUIC(
            service_config_to_test=client_service_config,
            service_type=ImplementationType.IUT,
            protocol=protocol,
            implementation_name="test_python_quic",
        )
    return manager


# ===================================================================
# TestPythonQUICInheritance - class hierarchy and isinstance checks
# ===================================================================


class TestPythonQUICInheritance:
    """Verify class hierarchy relationships."""

    def test_is_instance_of_python_quic(self, python_quic_manager):
        assert isinstance(python_quic_manager, PythonQUICServiceManager)

    def test_is_instance_of_base_quic(self, python_quic_manager):
        assert isinstance(python_quic_manager, BaseQUICServiceManager)

    def test_protocol_name_set(self, python_quic_manager):
        assert python_quic_manager.protocol_name == "quic"

    def test_implementation_name_set(self, python_quic_manager):
        assert python_quic_manager.implementation_name == "test_python_quic"


# ===================================================================
# TestAbstractMethodImplementations
# ===================================================================


class TestAbstractMethodImplementations:
    """Test that abstract methods are implemented correctly."""

    def test_get_implementation_name(self, python_quic_manager):
        assert python_quic_manager._get_implementation_name() == "test_python_quic"

    def test_get_python_module(self, python_quic_manager):
        assert python_quic_manager._get_python_module() == "test_quic_module"

    def test_get_binary_name(self, python_quic_manager):
        """Real PythonQUICServiceManager._get_binary_name returns 'python -m <module>'."""
        assert python_quic_manager._get_binary_name() == "python -m test_quic_module"

    def test_get_binary_path_without_working_dir(self, python_quic_manager):
        """Without working_dir, _get_binary_path falls back to _get_binary_name."""
        python_quic_manager.working_dir = None
        assert python_quic_manager._get_binary_path() == "python -m test_quic_module"

    def test_get_binary_path_with_working_dir(self, python_quic_manager):
        """With working_dir set, _get_binary_path joins it with the binary name."""
        python_quic_manager.working_dir = "/opt/app"
        path = python_quic_manager._get_binary_path()
        assert path == "/opt/app/python -m test_quic_module"


# ===================================================================
# TestExtractCommonParams
# ===================================================================


class TestExtractCommonParams:
    """Test _extract_common_params method (real implementation)."""

    def test_defaults(self, python_quic_manager):
        params = python_quic_manager._extract_common_params()
        assert params["host"] == "localhost"
        assert params["port"] == 4443
        assert params["cert_dir"] == "/opt/certs"
        assert params["key_file"] == "/opt/certs/key.pem"
        assert params["cert_file"] == "/opt/certs/cert.pem"
        assert params["version"] == "rfc9000"
        assert params["log_level"] == "info"
        assert params["log_file"] is None
        assert params["output_dir"] == "/logs"

    def test_python_specific_defaults(self, python_quic_manager):
        """PythonQUICServiceManager adds python_path and asyncio_debug."""
        params = python_quic_manager._extract_common_params()
        assert params["python_path"] == "/opt/aioquic"
        assert params["asyncio_debug"] is False

    def test_custom_overrides(self, python_quic_manager):
        params = python_quic_manager._extract_common_params(
            host="example.com",
            port=8443,
            python_path="/custom/path",
            asyncio_debug=True,
        )
        assert params["host"] == "example.com"
        assert params["port"] == 8443
        assert params["python_path"] == "/custom/path"
        assert params["asyncio_debug"] is True

    def test_cert_dir_override(self, python_quic_manager):
        params = python_quic_manager._extract_common_params(
            cert_dir="/my/certs",
            cert_file="/my/certs/cert.pem",
            key_file="/my/certs/key.pem",
        )
        assert params["cert_dir"] == "/my/certs"
        assert params["cert_file"] == "/my/certs/cert.pem"
        assert params["key_file"] == "/my/certs/key.pem"


# ===================================================================
# TestBuildServerArgs
# ===================================================================


class TestBuildServerArgs:
    """Test _build_server_args method."""

    def test_default_server_args(self, python_quic_manager):
        params = python_quic_manager._extract_common_params()
        args = python_quic_manager._build_server_args(params)
        # Default params include cert_file, key_file, port
        assert "-c" in args
        assert "/opt/certs/cert.pem" in args
        assert "-k" in args
        assert "/opt/certs/key.pem" in args
        assert "-p" in args
        assert "4443" in args

    def test_with_log_file(self, python_quic_manager):
        params = python_quic_manager._extract_common_params(log_file="/logs/server.log")
        args = python_quic_manager._build_server_args(params)
        assert "-l" in args
        assert "/logs/server.log" in args

    def test_custom_port(self, python_quic_manager):
        params = python_quic_manager._extract_common_params(port=8443)
        args = python_quic_manager._build_server_args(params)
        assert "8443" in args


# ===================================================================
# TestBuildClientArgs
# ===================================================================


class TestBuildClientArgs:
    """Test _build_client_args method."""

    def test_default_client_args(self, python_quic_manager):
        params = python_quic_manager._extract_common_params()
        args = python_quic_manager._build_client_args(params)
        # Client args include host and port as positional, plus version
        assert "localhost" in args
        assert "4443" in args
        # Version mapping: rfc9000 -> "1"
        assert "-v" in args
        assert "1" in args

    def test_custom_host_port(self, python_quic_manager):
        params = python_quic_manager._extract_common_params(
            host="example.com", port=443
        )
        args = python_quic_manager._build_client_args(params)
        assert "example.com" in args
        assert "443" in args

    def test_with_log_file(self, python_quic_manager):
        params = python_quic_manager._extract_common_params(log_file="/logs/client.log")
        args = python_quic_manager._build_client_args(params)
        assert "-l" in args
        assert "/logs/client.log" in args


# ===================================================================
# TestMapVersion
# ===================================================================


class TestMapVersion:
    """Test _map_version method."""

    def test_rfc9000(self, python_quic_manager):
        assert python_quic_manager._map_version("rfc9000") == "1"

    def test_draft29(self, python_quic_manager):
        assert python_quic_manager._map_version("draft29") == "ff00001d"

    def test_draft27(self, python_quic_manager):
        assert python_quic_manager._map_version("draft27") == "ff00001b"

    def test_unknown_version_defaults_to_1(self, python_quic_manager):
        assert python_quic_manager._map_version("unknown_v") == "1"

    def test_version_enum_format(self, python_quic_manager):
        """Handles 'VersionEnum.rfc9000' format."""
        assert python_quic_manager._map_version("VersionEnum.rfc9000") == "1"

    def test_version_enum_numeric_format(self, python_quic_manager):
        """Handles '<VersionEnum.rfc9000: 1>' format."""
        assert python_quic_manager._map_version("<VersionEnum.rfc9000: 1>") == "1"


# ===================================================================
# TestGenerateRunCommand
# ===================================================================


class TestGenerateRunCommand:
    """Test generate_run_command method with real shlex quoting."""

    def test_server_command_defaults(self, python_quic_manager):
        """Server command includes binary path and default args."""
        cmd = python_quic_manager.generate_run_command(role="server")
        # The real generate_run_command uses shlex.quote on all parts.
        # Binary "python -m test_quic_module" gets split by space handling.
        assert "python" in cmd
        assert "test_quic_module" in cmd
        # Default cert/key/port args
        assert "-c" in cmd
        assert "-k" in cmd
        assert "-p" in cmd

    def test_server_command_custom_port(self, python_quic_manager):
        cmd = python_quic_manager.generate_run_command(role="server", port=8443)
        assert "8443" in cmd

    def test_server_command_with_custom_certs(self, python_quic_manager):
        cmd = python_quic_manager.generate_run_command(
            role="server",
            cert_file="/custom/cert.pem",
            key_file="/custom/key.pem",
        )
        assert "/custom/cert.pem" in cmd
        assert "/custom/key.pem" in cmd

    def test_server_command_with_specific_args(self, python_quic_manager):
        """Implementation-specific args from _get_server_specific_args."""
        cmd = python_quic_manager.generate_run_command(
            role="server", bind_address="0.0.0.0"
        )
        assert "--bind" in cmd
        assert "0.0.0.0" in cmd

    def test_client_command_defaults(self, python_quic_manager):
        cmd = python_quic_manager.generate_run_command(role="client")
        assert "python" in cmd
        assert "test_quic_module" in cmd
        assert "localhost" in cmd
        assert "4443" in cmd

    def test_client_command_custom_host(self, python_quic_manager):
        cmd = python_quic_manager.generate_run_command(
            role="client", host="example.com", port=443
        )
        assert "example.com" in cmd
        assert "443" in cmd

    def test_client_command_with_specific_args(self, python_quic_manager):
        cmd = python_quic_manager.generate_run_command(
            role="client", request_path="/api/data"
        )
        assert "--path" in cmd
        assert "/api/data" in cmd

    def test_default_role_is_client(self, python_quic_manager):
        """If no role specified, defaults to client."""
        cmd = python_quic_manager.generate_run_command()
        # Client args include host/port positional
        assert "localhost" in cmd
        assert "4443" in cmd

    def test_command_uses_shlex_quoting(self, python_quic_manager):
        """The real implementation applies shlex.quote to all parts."""
        cmd = python_quic_manager.generate_run_command(role="server")
        # shlex.quote wraps arguments -- at minimum the command is a string
        assert isinstance(cmd, str)
        # No bare semicolons or pipes (injection safety)
        assert ";" not in cmd
        assert "|" not in cmd

    def test_server_command_with_log_file(self, python_quic_manager):
        cmd = python_quic_manager.generate_run_command(
            role="server", log_file="/logs/quic.log"
        )
        assert "-l" in cmd
        assert "/logs/quic.log" in cmd


# ===================================================================
# TestBuildPythonEnvVars
# ===================================================================


class TestBuildPythonEnvVars:
    """Test _build_python_env_vars method (Python-specific)."""

    def test_default_env_vars(self, python_quic_manager):
        params = python_quic_manager._extract_common_params()
        env = python_quic_manager._build_python_env_vars(params)
        assert env["PYTHONPATH"] == "/opt/aioquic"
        assert env["PYTHONUNBUFFERED"] == "1"
        assert "PYTHONASYNCIODEBUG" not in env

    def test_asyncio_debug_enabled(self, python_quic_manager):
        params = python_quic_manager._extract_common_params(asyncio_debug=True)
        env = python_quic_manager._build_python_env_vars(params)
        assert env["PYTHONASYNCIODEBUG"] == "1"

    def test_custom_python_path(self, python_quic_manager):
        params = python_quic_manager._extract_common_params(python_path="/custom/lib")
        env = python_quic_manager._build_python_env_vars(params)
        assert env["PYTHONPATH"] == "/custom/lib"


# ===================================================================
# TestGenerateCompileCommand
# ===================================================================


class TestGenerateCompileCommand:
    """Test generate_compile_command for Python implementations."""

    def test_python_compile_command(self, python_quic_manager):
        """Python implementations use pip install instead of compilation."""
        cmd = python_quic_manager.generate_compile_command()
        assert "pip install -r requirements.txt" in cmd
        assert "|| true" in cmd

    def test_compile_command_is_string(self, python_quic_manager):
        cmd = python_quic_manager.generate_compile_command()
        assert isinstance(cmd, str)


# ===================================================================
# TestGetSupportedFeatures
# ===================================================================


class TestGetSupportedFeatures:
    """Test get_supported_features method."""

    def test_base_features(self, python_quic_manager):
        """Python QUIC inherits base QUIC features."""
        features = python_quic_manager.get_supported_features()
        assert features["client"] is True
        assert features["server"] is True
        assert features["0rtt"] is True
        assert features["qlog"] is True

    def test_python_specific_features(self, python_quic_manager):
        """Python QUIC adds async/python-specific features."""
        features = python_quic_manager.get_supported_features()
        assert features["async"] is True
        assert features["asyncio"] is True
        assert features["python"] is True
        assert features["interpreted"] is True

    def test_multipath_default_false(self, python_quic_manager):
        features = python_quic_manager.get_supported_features()
        assert features["multipath"] is False

    def test_migration_default_true(self, python_quic_manager):
        features = python_quic_manager.get_supported_features()
        assert features["migration"] is True


# ===================================================================
# TestPrePostCompileCommands
# ===================================================================


class TestPrePostCommands:
    """Test pre/post compile and run commands."""

    def test_pre_compile_default_empty(self, python_quic_manager):
        assert python_quic_manager.generate_pre_compile_command() == ""

    def test_post_compile_default_empty(self, python_quic_manager):
        assert python_quic_manager.generate_post_compile_command() == ""

    def test_post_run_default_empty(self, python_quic_manager):
        assert python_quic_manager.generate_post_run_command() == ""


# ===================================================================
# TestValidateConfiguration
# ===================================================================


class TestValidateConfiguration:
    """Test validate_configuration method."""

    def test_valid_server_config(self, python_quic_manager):
        errors = python_quic_manager.validate_configuration(
            role="server", port=4443, version="rfc9000"
        )
        assert errors == []

    def test_valid_client_config(self, python_quic_manager):
        errors = python_quic_manager.validate_configuration(
            role="client", port=443, version="rfc9000"
        )
        assert errors == []

    def test_invalid_role(self, python_quic_manager):
        errors = python_quic_manager.validate_configuration(role="observer", port=4443)
        assert any("Invalid role" in e for e in errors)

    def test_invalid_port_zero(self, python_quic_manager):
        errors = python_quic_manager.validate_configuration(role="server", port=0)
        assert any("Invalid port" in e for e in errors)

    def test_invalid_port_too_high(self, python_quic_manager):
        errors = python_quic_manager.validate_configuration(role="server", port=70000)
        assert any("Invalid port" in e for e in errors)

    def test_unsupported_version(self, python_quic_manager):
        errors = python_quic_manager.validate_configuration(
            role="server", version="draft99"
        )
        assert any("Unsupported version" in e for e in errors)

    def test_multiple_errors(self, python_quic_manager):
        errors = python_quic_manager.validate_configuration(
            role="invalid", port=-1, version="draft99"
        )
        assert len(errors) >= 2


# ===================================================================
# TestDeploymentCommands
# ===================================================================


class TestDeploymentCommands:
    """Test deployment command generation (concrete implementation)."""

    def test_deployment_command(self, python_quic_manager):
        cmd = python_quic_manager.generate_deployment_commands()
        assert "python -m test_quic_module" in cmd
        assert "--server" in cmd
        assert "--port 4443" in cmd


# ===================================================================
# TestIntegrationScenarios
# ===================================================================


class TestIntegrationScenarios:
    """End-to-end scenarios combining multiple real methods."""

    def test_full_server_command_generation(self, python_quic_manager):
        """Generate a full server command and verify all parts."""
        cmd = python_quic_manager.generate_run_command(
            role="server",
            port=8443,
            cert_file="/app/certs/server.crt",
            key_file="/app/certs/server.key",
            bind_address="0.0.0.0",
            log_file="/logs/server.log",
        )
        assert "python" in cmd
        assert "test_quic_module" in cmd
        assert "8443" in cmd
        assert "/app/certs/server.crt" in cmd
        assert "/app/certs/server.key" in cmd
        assert "--bind" in cmd
        assert "0.0.0.0" in cmd
        assert "/logs/server.log" in cmd

    def test_full_client_command_generation(self, python_quic_manager):
        """Generate a full client command and verify all parts."""
        cmd = python_quic_manager.generate_run_command(
            role="client",
            host="quic.example.com",
            port=443,
            request_path="/api/test",
            log_file="/logs/client.log",
        )
        assert "python" in cmd
        assert "test_quic_module" in cmd
        assert "quic.example.com" in cmd
        assert "443" in cmd
        assert "--path" in cmd
        assert "/api/test" in cmd
        assert "/logs/client.log" in cmd

    def test_env_vars_and_command_together(self, python_quic_manager):
        """Verify that env vars and commands are independently generated."""
        params = python_quic_manager._extract_common_params(
            asyncio_debug=True, python_path="/custom/path"
        )
        env = python_quic_manager._build_python_env_vars(params)
        cmd = python_quic_manager.generate_run_command(role="server")

        # env vars
        assert env["PYTHONASYNCIODEBUG"] == "1"
        assert env["PYTHONPATH"] == "/custom/path"
        # command is still generated independently
        assert isinstance(cmd, str)
        assert "python" in cmd

    def test_features_include_both_base_and_python(self, python_quic_manager):
        """Supported features merge base QUIC and Python-specific flags."""
        features = python_quic_manager.get_supported_features()
        # Base QUIC
        assert features["client"] is True
        assert features["server"] is True
        assert features["0rtt"] is True
        assert features["qlog"] is True
        # Python-specific
        assert features["async"] is True
        assert features["asyncio"] is True
        assert features["python"] is True

    def test_validate_then_generate(self, python_quic_manager):
        """Validate config, then generate command if valid."""
        errors = python_quic_manager.validate_configuration(
            role="server", port=4443, version="rfc9000"
        )
        assert errors == []

        cmd = python_quic_manager.generate_run_command(role="server", port=4443)
        assert isinstance(cmd, str)
        assert "4443" in cmd


# ===================================================================
# TestConstructorVariations
# ===================================================================


class TestConstructorVariations:
    """Test different constructor parameter combinations."""

    def _make_manager(self, **kwargs):
        """Helper to construct a ConcretePythonQUIC with IO mocked."""
        svc = kwargs.pop(
            "service_config",
            _make_service_config(role="server"),
        )
        proto = kwargs.pop(
            "protocol",
            _make_protocol_config(role="server"),
        )
        stype = kwargs.pop("service_type", ImplementationType.IUT)
        impl = kwargs.pop("implementation_name", "test_python_quic")
        with (
            patch("os.path.isdir", return_value=True),
            patch("os.listdir", return_value=[]),
            patch(
                "panther.plugins.services.services_interface.Environment",
                return_value=MagicMock(),
            ),
            patch(
                "panther.plugins.services.services_interface.FileSystemLoader",
                return_value=MagicMock(),
            ),
            patch(
                "panther.plugins.services.services_interface.select_autoescape",
                return_value=[],
            ),
        ):
            return ConcretePythonQUIC(
                service_config_to_test=svc,
                service_type=stype,
                protocol=proto,
                implementation_name=impl,
                **kwargs,
            )

    def test_with_string_service_type(self):
        """Accept string 'iut' for service_type."""
        mgr = self._make_manager(service_type="iut")
        assert mgr.service_type_normalized == "IUT"

    def test_with_testers_service_type(self):
        """Accept 'testers' for service_type."""
        mgr = self._make_manager(service_type="testers")
        assert mgr.service_type_normalized == "TESTERS"

    def test_with_event_manager(self):
        """Accept an event_manager parameter."""
        mock_em = Mock()
        mgr = self._make_manager(event_manager=mock_em)
        assert mgr.event_manager is mock_em

    def test_with_global_config(self):
        """Accept a global_config parameter."""
        mock_gc = Mock()
        mgr = self._make_manager(global_config=mock_gc)
        assert mgr.global_config is mock_gc

    def test_invalid_service_type_raises(self):
        """Invalid service_type string raises ValueError."""
        with pytest.raises(ValueError, match="Invalid service type"):
            self._make_manager(service_type="invalid_type")

    def test_client_role_config(self):
        """Construct with client-role configs."""
        svc = _make_service_config(role="client", target="server")
        proto = _make_protocol_config(role="client", target="server")
        mgr = self._make_manager(
            service_config=svc,
            protocol=proto,
        )
        assert mgr.role == ProtocolRole.CLIENT


# ===================================================================
# TestIsTester
# ===================================================================


class TestIsTester:
    """Test is_tester method inherited from IImplementationManager."""

    def test_is_not_tester(self, python_quic_manager):
        """IUT implementations return False for is_tester."""
        assert python_quic_manager.is_tester() is False


if __name__ in {"__main__", "__mp_main__"}:
    pytest.main([__file__, "-v"])
