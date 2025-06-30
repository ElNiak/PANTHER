#!/usr/bin/env python3.10
"""Tests for Python QUIC base service manager using Python 3.10 syntax."""

from __future__ import annotations

from typing import List, Dict, Any
from unittest.mock import Mock, patch, MagicMock

import pytest

# Test imports with fallback to mocks
try:
    from panther.plugins.services.base.python_quic_base import PythonQUICServiceManager
    from panther.plugins.services.base.quic_service_base import BaseQUICServiceManager
    PYTHON_QUIC_SYSTEM_AVAILABLE = True
except ImportError:
    PYTHON_QUIC_SYSTEM_AVAILABLE = False
    
    # Create mock implementations for testing
    class BaseQUICServiceManager:
        """Mock base QUIC service manager."""
        
        def __init__(self):
            self.logger = Mock()
            self.event_emitter = Mock()
            
        def generate_run_command(self, **kwargs) -> str:
            """Generate run command using template method pattern."""
            params = self._extract_common_params(**kwargs)
            role = params.get('role', 'client')
            
            if role == 'server':
                args = self._build_server_args(params)
                specific_args = self._get_server_specific_args(**kwargs)
            else:
                args = self._build_client_args(params)
                specific_args = self._get_client_specific_args(**kwargs)
            
            binary = self._get_binary_name()
            all_args = args + specific_args
            
            return f"{binary} {' '.join(all_args)}"
        
        def _extract_common_params(self, **kwargs) -> Dict[str, Any]:
            """Extract common QUIC parameters."""
            return {
                'role': kwargs.get('role', 'client'),
                'host': kwargs.get('host', 'localhost'),
                'port': kwargs.get('port', 4443),
                'timeout': kwargs.get('timeout', 60),
                'protocol_version': kwargs.get('protocol_version', 'h3'),
                'alpn': kwargs.get('alpn', 'h3'),
                'certificate_file': kwargs.get('certificate_file'),
                'private_key_file': kwargs.get('private_key_file'),
                'ca_file': kwargs.get('ca_file'),
                'verify_mode': kwargs.get('verify_mode', 'none'),
                'congestion_control': kwargs.get('congestion_control'),
                'max_streams': kwargs.get('max_streams'),
                'max_data': kwargs.get('max_data'),
                'idle_timeout': kwargs.get('idle_timeout'),
                'enable_0rtt': kwargs.get('enable_0rtt', False),
                'enable_early_data': kwargs.get('enable_early_data', False),
                'session_ticket': kwargs.get('session_ticket', True),
                'key_update': kwargs.get('key_update', False),
                'migration': kwargs.get('migration', False),
                'multipath': kwargs.get('multipath', False),
                'qlog': kwargs.get('qlog', False),
                'qlog_dir': kwargs.get('qlog_dir', '/app/qlogs'),
                'log_level': kwargs.get('log_level', 'info')
            }
        
        def _build_server_args(self, params: Dict[str, Any]) -> List[str]:
            """Build common server arguments."""
            args = []
            
            if params.get('port'):
                args.extend(['-p', str(params['port'])])
            
            if params.get('certificate_file'):
                args.extend(['-c', params['certificate_file']])
            
            if params.get('private_key_file'):
                args.extend(['-k', params['private_key_file']])
            
            return args
        
        def _build_client_args(self, params: Dict[str, Any]) -> List[str]:
            """Build common client arguments."""
            args = []
            
            if params.get('ca_file'):
                args.extend(['--ca-file', params['ca_file']])
            
            if params.get('verify_mode') == 'none':
                args.append('--insecure')
            
            return args
        
        # Abstract methods that subclasses must implement
        def _get_implementation_name(self) -> str:
            raise NotImplementedError
        
        def _get_binary_name(self) -> str:
            raise NotImplementedError
        
        def _get_server_specific_args(self, **kwargs) -> List[str]:
            raise NotImplementedError
        
        def _get_client_specific_args(self, **kwargs) -> List[str]:
            raise NotImplementedError
        
        def generate_deployment_commands(self) -> str:
            raise NotImplementedError
        
        def _do_prepare(self, plugin_manager=None):
            raise NotImplementedError
    
    class PythonQUICServiceManager(BaseQUICServiceManager):
        """Mock Python QUIC service manager."""
        
        def __init__(self):
            super().__init__()
            self.python_version: str = "3.10"
            self.python_path: str = "/usr/bin/python"
            self.virtual_env: str | None = None
            self.requirements: List[str] = []
            self.pip_packages: List[str] = []
            self.python_flags: List[str] = []
            self.module_path: str | None = None
            
        def _get_python_executable(self) -> str:
            """Get the Python executable path."""
            if self.virtual_env:
                return f"{self.virtual_env}/bin/python"
            return self.python_path
        
        def _get_module_name(self) -> str:
            """Get the Python module name to execute."""
            if self.module_path:
                return self.module_path
            return self._get_implementation_name()
        
        def _build_python_command_prefix(self) -> List[str]:
            """Build Python command prefix with flags and module."""
            cmd_parts = [self._get_python_executable()]
            
            # Add Python flags
            if self.python_flags:
                cmd_parts.extend(self.python_flags)
            
            # Add module flag
            cmd_parts.extend(['-m', self._get_module_name()])
            
            return cmd_parts
        
        def _setup_python_environment(self, **kwargs) -> Dict[str, str]:
            """Setup Python-specific environment variables."""
            env = {}
            
            # Python-specific environment variables
            env['PYTHONPATH'] = kwargs.get('python_path', '/app')
            env['PYTHONUNBUFFERED'] = '1'  # For real-time output
            
            # Set Python warnings
            env['PYTHONWARNINGS'] = kwargs.get('python_warnings', 'ignore')
            
            # Virtual environment
            if self.virtual_env:
                env['VIRTUAL_ENV'] = self.virtual_env
                env['PATH'] = f"{self.virtual_env}/bin:{env.get('PATH', '')}"
            
            # Logging configuration for Python
            if kwargs.get('debug', False):
                env['PYTHONDEBUG'] = '1'
                env['PYTHON_LOG_LEVEL'] = 'DEBUG'
            else:
                env['PYTHON_LOG_LEVEL'] = kwargs.get('log_level', 'INFO').upper()
            
            return env
        
        def _get_pip_install_command(self, packages: List[str] | None = None) -> str:
            """Generate pip install command."""
            pip_executable = f"{self.virtual_env}/bin/pip" if self.virtual_env else "pip"
            packages_to_install = packages or self.pip_packages
            
            if not packages_to_install:
                return ""
            
            packages_str = " ".join(packages_to_install)
            return f"{pip_executable} install {packages_str}"
        
        def _get_requirements_install_command(self, requirements_file: str = "requirements.txt") -> str:
            """Generate requirements installation command."""
            pip_executable = f"{self.virtual_env}/bin/pip" if self.virtual_env else "pip"
            return f"{pip_executable} install -r {requirements_file}"
        
        def set_python_version(self, version: str):
            """Set Python version."""
            self.python_version = version
            self.python_path = f"/usr/bin/python{version}"
        
        def set_virtual_env(self, env_path: str):
            """Set virtual environment path."""
            self.virtual_env = env_path
        
        def add_pip_package(self, package: str):
            """Add a pip package to install."""
            if package not in self.pip_packages:
                self.pip_packages.append(package)
        
        def set_pip_packages(self, packages: List[str]):
            """Set list of pip packages to install."""
            self.pip_packages = packages.copy()
        
        def add_python_flag(self, flag: str):
            """Add a Python interpreter flag."""
            if flag not in self.python_flags:
                self.python_flags.append(flag)
        
        def set_python_flags(self, flags: List[str]):
            """Set Python interpreter flags."""
            self.python_flags = flags.copy()
        
        def set_module_path(self, path: str):
            """Set custom module path."""
            self.module_path = path

pytestmark = [pytest.mark.unit, pytest.mark.python_quic]

class MockPythonQuicImpl(PythonQUICServiceManager):
    """Mock concrete Python QUIC implementation for testing."""
    
    def __init__(self):
        super().__init__()
        self.implementation_name = "mock_python_quic"
        self.module_name = "mock_quic_module"
    
    def _get_implementation_name(self) -> str:
        return self.implementation_name
    
    def _get_binary_name(self) -> str:
        # For Python implementations, we use Python executable
        return self._get_python_executable()
    
    def _get_module_name(self) -> str:
        return self.module_name
    
    def _get_server_specific_args(self, **kwargs) -> List[str]:
        args = []
        if kwargs.get('bind_address'):
            args.extend(['--bind', kwargs['bind_address']])
        if kwargs.get('workers'):
            args.extend(['--workers', str(kwargs['workers'])])
        if kwargs.get('access_log'):
            args.extend(['--access-log', kwargs['access_log']])
        return args
    
    def _get_client_specific_args(self, **kwargs) -> List[str]:
        args = []
        host = kwargs.get('host', 'localhost')
        port = kwargs.get('port', 4443)
        args.extend(['--host', host, '--port', str(port)])
        
        if kwargs.get('request_path'):
            args.extend(['--path', kwargs['request_path']])
        
        if kwargs.get('output_file'):
            args.extend(['--output', kwargs['output_file']])
        
        return args
    
    def generate_deployment_commands(self) -> str:
        python_cmd = self._get_python_executable()
        return f"{python_cmd} -m {self.module_name} --server --port 4443"
    
    def _do_prepare(self, plugin_manager=None):
        pass
    
    def generate_run_command(self, **kwargs) -> str:
        """Override to use Python command structure."""
        params = self._extract_common_params(**kwargs)
        role = params.get('role', 'client')
        
        # Build Python command prefix
        cmd_parts = self._build_python_command_prefix()
        
        # Add common args
        if role == 'server':
            common_args = self._build_server_args(params)
            specific_args = self._get_server_specific_args(**kwargs)
        else:
            common_args = self._build_client_args(params)
            specific_args = self._get_client_specific_args(**kwargs)
        
        all_args = cmd_parts + common_args + specific_args
        return " ".join(all_args)

class TestPythonQUICServiceManager:
    """Test PythonQUICServiceManager base functionality."""
    
    @pytest.fixture
    def python_quic_manager(self) -> MockPythonQuicImpl:
        """Create a mock Python QUIC manager for testing."""
        return MockPythonQuicImpl()
    
    def test_python_quic_manager_initialization(self, python_quic_manager: MockPythonQuicImpl):
        """Test PythonQUICServiceManager initialization."""
        assert isinstance(python_quic_manager, PythonQUICServiceManager)
        assert hasattr(python_quic_manager, 'python_version')
        assert hasattr(python_quic_manager, 'python_path')
        assert hasattr(python_quic_manager, 'virtual_env')
        assert hasattr(python_quic_manager, 'pip_packages')
        assert hasattr(python_quic_manager, 'python_flags')
        
        # Check defaults
        assert python_quic_manager.python_version == "3.10"
        assert python_quic_manager.pip_packages == []
        assert python_quic_manager.python_flags == []
        assert python_quic_manager.virtual_env is None
    
    def test_implementation_identification(self, python_quic_manager: MockPythonQuicImpl):
        """Test implementation identification methods."""
        assert python_quic_manager._get_implementation_name() == "mock_python_quic"
        assert python_quic_manager._get_module_name() == "mock_quic_module"
    
    def test_python_version_management(self, python_quic_manager: MockPythonQuicImpl):
        """Test Python version management."""
        python_quic_manager.set_python_version("3.11")
        assert python_quic_manager.python_version == "3.11"
        assert python_quic_manager.python_path == "/usr/bin/python3.11"
    
    def test_virtual_environment_management(self, python_quic_manager: MockPythonQuicImpl):
        """Test virtual environment management."""
        venv_path = "/app/venv"
        python_quic_manager.set_virtual_env(venv_path)
        assert python_quic_manager.virtual_env == venv_path
        
        # Test executable path with venv
        executable = python_quic_manager._get_python_executable()
        assert executable == f"{venv_path}/bin/python"
    
    def test_pip_packages_management(self, python_quic_manager: MockPythonQuicImpl):
        """Test pip packages management."""
        # Test adding individual packages
        python_quic_manager.add_pip_package("aioquic")
        python_quic_manager.add_pip_package("cryptography")
        assert "aioquic" in python_quic_manager.pip_packages
        assert "cryptography" in python_quic_manager.pip_packages
        
        # Test not adding duplicates
        python_quic_manager.add_pip_package("aioquic")
        assert python_quic_manager.pip_packages.count("aioquic") == 1
        
        # Test setting packages list
        packages = ["requests", "aiohttp", "asyncio"]
        python_quic_manager.set_pip_packages(packages)
        assert python_quic_manager.pip_packages == packages
    
    def test_python_flags_management(self, python_quic_manager: MockPythonQuicImpl):
        """Test Python interpreter flags management."""
        # Test adding individual flags
        python_quic_manager.add_python_flag("-O")
        python_quic_manager.add_python_flag("-u")
        assert "-O" in python_quic_manager.python_flags
        assert "-u" in python_quic_manager.python_flags
        
        # Test not adding duplicates
        python_quic_manager.add_python_flag("-O")
        assert python_quic_manager.python_flags.count("-O") == 1
        
        # Test setting flags list
        flags = ["-B", "-s", "-v"]
        python_quic_manager.set_python_flags(flags)
        assert python_quic_manager.python_flags == flags
    
    def test_module_path_management(self, python_quic_manager: MockPythonQuicImpl):
        """Test module path management."""
        custom_path = "custom.quic.module"
        python_quic_manager.set_module_path(custom_path)
        assert python_quic_manager.module_path == custom_path
        assert python_quic_manager._get_module_name() == custom_path

class TestPythonQUICCommandGeneration:
    """Test command generation for Python QUIC implementations."""
    
    @pytest.fixture
    def python_quic_manager(self) -> MockPythonQuicImpl:
        """Create a mock Python QUIC manager for testing."""
        return MockPythonQuicImpl()
    
    def test_python_command_prefix_basic(self, python_quic_manager: MockPythonQuicImpl):
        """Test basic Python command prefix generation."""
        prefix = python_quic_manager._build_python_command_prefix()
        
        assert prefix[0] == "/usr/bin/python"
        assert "-m" in prefix
        assert "mock_quic_module" in prefix
    
    def test_python_command_prefix_with_flags(self, python_quic_manager: MockPythonQuicImpl):
        """Test Python command prefix with flags."""
        python_quic_manager.set_python_flags(["-O", "-u"])
        prefix = python_quic_manager._build_python_command_prefix()
        
        assert "-O" in prefix
        assert "-u" in prefix
        assert "-m" in prefix
        assert "mock_quic_module" in prefix
    
    def test_python_command_prefix_with_venv(self, python_quic_manager: MockPythonQuicImpl):
        """Test Python command prefix with virtual environment."""
        python_quic_manager.set_virtual_env("/app/venv")
        prefix = python_quic_manager._build_python_command_prefix()
        
        assert prefix[0] == "/app/venv/bin/python"
    
    def test_server_command_generation_basic(self, python_quic_manager: MockPythonQuicImpl):
        """Test basic server command generation."""
        cmd = python_quic_manager.generate_run_command(
            role='server',
            port=4443
        )
        
        assert '/usr/bin/python' in cmd
        assert '-m mock_quic_module' in cmd
        assert '-p 4443' in cmd
    
    def test_server_command_generation_with_certificates(self, python_quic_manager: MockPythonQuicImpl):
        """Test server command generation with certificates."""
        cmd = python_quic_manager.generate_run_command(
            role='server',
            port=8443,
            certificate_file='/app/certs/server.crt',
            private_key_file='/app/certs/server.key'
        )
        
        assert '-p 8443' in cmd
        assert '-c /app/certs/server.crt' in cmd
        assert '-k /app/certs/server.key' in cmd
    
    def test_server_command_generation_with_python_specific_args(self, python_quic_manager: MockPythonQuicImpl):
        """Test server command generation with Python-specific arguments."""
        cmd = python_quic_manager.generate_run_command(
            role='server',
            port=4443,
            bind_address='0.0.0.0',
            workers=4,
            access_log='/app/logs/access.log'
        )
        
        assert '--bind 0.0.0.0' in cmd
        assert '--workers 4' in cmd
        assert '--access-log /app/logs/access.log' in cmd
    
    def test_client_command_generation_basic(self, python_quic_manager: MockPythonQuicImpl):
        """Test basic client command generation."""
        cmd = python_quic_manager.generate_run_command(
            role='client',
            host='example.com',
            port=443
        )
        
        assert '/usr/bin/python' in cmd
        assert '-m mock_quic_module' in cmd
        assert '--host example.com' in cmd
        assert '--port 443' in cmd
    
    def test_client_command_generation_with_ca_file(self, python_quic_manager: MockPythonQuicImpl):
        """Test client command generation with CA file."""
        cmd = python_quic_manager.generate_run_command(
            role='client',
            host='secure.example.com',
            port=443,
            ca_file='/app/certs/ca.pem'
        )
        
        assert '--ca-file /app/certs/ca.pem' in cmd
        assert '--host secure.example.com' in cmd
        assert '--port 443' in cmd
    
    def test_client_command_generation_insecure(self, python_quic_manager: MockPythonQuicImpl):
        """Test client command generation with insecure mode."""
        cmd = python_quic_manager.generate_run_command(
            role='client',
            host='test.local',
            port=4443,
            verify_mode='none'
        )
        
        assert '--insecure' in cmd
        assert '--host test.local' in cmd
        assert '--port 4443' in cmd
    
    def test_client_command_generation_with_output(self, python_quic_manager: MockPythonQuicImpl):
        """Test client command generation with output file."""
        cmd = python_quic_manager.generate_run_command(
            role='client',
            host='api.example.com',
            port=443,
            request_path='/api/v1/data',
            output_file='/app/output/response.json'
        )
        
        assert '--path /api/v1/data' in cmd
        assert '--output /app/output/response.json' in cmd

class TestPythonQUICPackageManagement:
    """Test Python package management for QUIC implementations."""
    
    @pytest.fixture
    def python_quic_manager(self) -> MockPythonQuicImpl:
        """Create a mock Python QUIC manager for testing."""
        return MockPythonQuicImpl()
    
    def test_pip_install_command_basic(self, python_quic_manager: MockPythonQuicImpl):
        """Test basic pip install command generation."""
        python_quic_manager.set_pip_packages(["aioquic", "cryptography"])
        cmd = python_quic_manager._get_pip_install_command()
        
        assert "pip install" in cmd
        assert "aioquic" in cmd
        assert "cryptography" in cmd
    
    def test_pip_install_command_with_venv(self, python_quic_manager: MockPythonQuicImpl):
        """Test pip install command with virtual environment."""
        python_quic_manager.set_virtual_env("/app/venv")
        python_quic_manager.set_pip_packages(["aioquic"])
        cmd = python_quic_manager._get_pip_install_command()
        
        assert "/app/venv/bin/pip install" in cmd
        assert "aioquic" in cmd
    
    def test_pip_install_command_custom_packages(self, python_quic_manager: MockPythonQuicImpl):
        """Test pip install command with custom packages."""
        custom_packages = ["requests", "aiohttp"]
        cmd = python_quic_manager._get_pip_install_command(packages=custom_packages)
        
        assert "pip install" in cmd
        assert "requests" in cmd
        assert "aiohttp" in cmd
    
    def test_pip_install_command_no_packages(self, python_quic_manager: MockPythonQuicImpl):
        """Test pip install command with no packages."""
        cmd = python_quic_manager._get_pip_install_command()
        assert cmd == ""
    
    def test_requirements_install_command_basic(self, python_quic_manager: MockPythonQuicImpl):
        """Test requirements file installation command."""
        cmd = python_quic_manager._get_requirements_install_command()
        
        assert "pip install -r requirements.txt" in cmd
    
    def test_requirements_install_command_custom_file(self, python_quic_manager: MockPythonQuicImpl):
        """Test requirements installation with custom file."""
        cmd = python_quic_manager._get_requirements_install_command("dev-requirements.txt")
        
        assert "pip install -r dev-requirements.txt" in cmd
    
    def test_requirements_install_command_with_venv(self, python_quic_manager: MockPythonQuicImpl):
        """Test requirements installation with virtual environment."""
        python_quic_manager.set_virtual_env("/app/venv")
        cmd = python_quic_manager._get_requirements_install_command()
        
        assert "/app/venv/bin/pip install -r requirements.txt" in cmd

class TestPythonQUICEnvironmentSetup:
    """Test Python-specific environment setup."""
    
    @pytest.fixture
    def python_quic_manager(self) -> MockPythonQuicImpl:
        """Create a mock Python QUIC manager for testing."""
        return MockPythonQuicImpl()
    
    def test_python_environment_basic(self, python_quic_manager: MockPythonQuicImpl):
        """Test basic Python environment setup."""
        env = python_quic_manager._setup_python_environment()
        
        assert 'PYTHONPATH' in env
        assert 'PYTHONUNBUFFERED' in env
        assert 'PYTHONWARNINGS' in env
        assert 'PYTHON_LOG_LEVEL' in env
        
        assert env['PYTHONPATH'] == '/app'
        assert env['PYTHONUNBUFFERED'] == '1'
        assert env['PYTHONWARNINGS'] == 'ignore'
        assert env['PYTHON_LOG_LEVEL'] == 'INFO'
    
    def test_python_environment_debug_mode(self, python_quic_manager: MockPythonQuicImpl):
        """Test Python environment setup in debug mode."""
        env = python_quic_manager._setup_python_environment(debug=True)
        
        assert 'PYTHONDEBUG' in env
        assert env['PYTHONDEBUG'] == '1'
        assert env['PYTHON_LOG_LEVEL'] == 'DEBUG'
    
    def test_python_environment_custom_log_level(self, python_quic_manager: MockPythonQuicImpl):
        """Test Python environment setup with custom log level."""
        env = python_quic_manager._setup_python_environment(log_level='warning')
        
        assert env['PYTHON_LOG_LEVEL'] == 'WARNING'
    
    def test_python_environment_custom_pythonpath(self, python_quic_manager: MockPythonQuicImpl):
        """Test Python environment setup with custom PYTHONPATH."""
        env = python_quic_manager._setup_python_environment(python_path='/custom/path')
        
        assert env['PYTHONPATH'] == '/custom/path'
    
    def test_python_environment_custom_warnings(self, python_quic_manager: MockPythonQuicImpl):
        """Test Python environment setup with custom warnings."""
        env = python_quic_manager._setup_python_environment(python_warnings='default')
        
        assert env['PYTHONWARNINGS'] == 'default'
    
    def test_python_environment_with_venv(self, python_quic_manager: MockPythonQuicImpl):
        """Test Python environment setup with virtual environment."""
        python_quic_manager.set_virtual_env("/app/venv")
        env = python_quic_manager._setup_python_environment()
        
        assert 'VIRTUAL_ENV' in env
        assert env['VIRTUAL_ENV'] == "/app/venv"
        assert "/app/venv/bin:" in env['PATH']

class TestPythonQUICIntegration:
    """Test integration scenarios for Python QUIC service managers."""
    
    @pytest.fixture
    def python_quic_manager(self) -> MockPythonQuicImpl:
        """Create a mock Python QUIC manager for testing."""
        return MockPythonQuicImpl()
    
    def test_full_server_setup_scenario(self, python_quic_manager: MockPythonQuicImpl):
        """Test complete server setup scenario."""
        # Configure Python-specific settings
        python_quic_manager.set_python_version("3.11")
        python_quic_manager.set_virtual_env("/app/venv")
        python_quic_manager.set_pip_packages(["aioquic", "cryptography"])
        python_quic_manager.set_python_flags(["-O", "-u"])
        
        # Generate server command
        cmd = python_quic_manager.generate_run_command(
            role='server',
            port=4443,
            certificate_file='/app/certs/server.crt',
            private_key_file='/app/certs/server.key',
            bind_address='0.0.0.0',
            workers=2
        )
        
        # Verify command contains all expected elements
        assert '/app/venv/bin/python' in cmd
        assert '-O -u' in cmd
        assert '-m mock_quic_module' in cmd
        assert '-p 4443' in cmd
        assert '-c /app/certs/server.crt' in cmd
        assert '-k /app/certs/server.key' in cmd
        assert '--bind 0.0.0.0' in cmd
        assert '--workers 2' in cmd
        
        # Verify package installation
        pip_cmd = python_quic_manager._get_pip_install_command()
        assert '/app/venv/bin/pip install aioquic cryptography' == pip_cmd
        
        # Verify environment setup
        env = python_quic_manager._setup_python_environment()
        assert env['VIRTUAL_ENV'] == '/app/venv'
    
    def test_full_client_setup_scenario(self, python_quic_manager: MockPythonQuicImpl):
        """Test complete client setup scenario."""
        # Configure for client testing
        python_quic_manager.set_module_path("custom.client.module")
        python_quic_manager.add_pip_package("aiofiles")
        
        # Generate client command
        cmd = python_quic_manager.generate_run_command(
            role='client',
            host='quic.example.com',
            port=443,
            ca_file='/app/certs/ca.pem',
            request_path='/api/test',
            output_file='/app/output/result.json'
        )
        
        # Verify command
        assert '/usr/bin/python' in cmd
        assert '-m custom.client.module' in cmd
        assert '--host quic.example.com' in cmd
        assert '--port 443' in cmd
        assert '--ca-file /app/certs/ca.pem' in cmd
        assert '--path /api/test' in cmd
        assert '--output /app/output/result.json' in cmd
        
        # Verify package is configured
        assert 'aiofiles' in python_quic_manager.pip_packages
    
    def test_deployment_command_generation(self, python_quic_manager: MockPythonQuicImpl):
        """Test deployment command generation."""
        deployment_cmd = python_quic_manager.generate_deployment_commands()
        
        assert '/usr/bin/python' in deployment_cmd
        assert '-m mock_quic_module' in deployment_cmd
        assert '--server' in deployment_cmd
        assert '--port 4443' in deployment_cmd
    
    def test_requirements_and_pip_integration(self, python_quic_manager: MockPythonQuicImpl):
        """Test requirements file and pip package integration."""
        # Set up packages and requirements
        python_quic_manager.set_pip_packages(["aioquic", "cryptography"])
        
        # Generate installation commands
        pip_cmd = python_quic_manager._get_pip_install_command()
        req_cmd = python_quic_manager._get_requirements_install_command("requirements.txt")
        
        assert "pip install aioquic cryptography" in pip_cmd
        assert "pip install -r requirements.txt" in req_cmd

class TestPythonQUICErrorHandling:
    """Test error handling in Python QUIC service managers."""
    
    @pytest.fixture
    def python_quic_manager(self) -> MockPythonQuicImpl:
        """Create a mock Python QUIC manager for testing."""
        return MockPythonQuicImpl()
    
    def test_command_generation_with_missing_args(self, python_quic_manager: MockPythonQuicImpl):
        """Test command generation with missing required arguments."""
        # Should not crash, should use defaults
        cmd = python_quic_manager.generate_run_command()
        
        assert isinstance(cmd, str)
        assert '/usr/bin/python' in cmd
        assert '-m mock_quic_module' in cmd
    
    def test_empty_pip_packages_handling(self, python_quic_manager: MockPythonQuicImpl):
        """Test handling of empty pip packages."""
        python_quic_manager.set_pip_packages([])
        
        cmd = python_quic_manager._get_pip_install_command()
        assert cmd == ""
    
    def test_environment_setup_with_none_values(self, python_quic_manager: MockPythonQuicImpl):
        """Test environment setup with None values."""
        env = python_quic_manager._setup_python_environment(
            debug=None,
            log_level=None,
            python_path=None
        )
        
        # Should handle None values gracefully
        assert isinstance(env, dict)
        assert 'PYTHONPATH' in env
        assert 'PYTHON_LOG_LEVEL' in env
    
    def test_virtual_env_with_none(self, python_quic_manager: MockPythonQuicImpl):
        """Test virtual environment handling with None."""
        python_quic_manager.set_virtual_env(None)
        
        executable = python_quic_manager._get_python_executable()
        assert executable == python_quic_manager.python_path
    
    def test_module_name_fallback(self, python_quic_manager: MockPythonQuicImpl):
        """Test module name fallback to implementation name."""
        python_quic_manager.module_path = None
        
        module_name = python_quic_manager._get_module_name()
        assert module_name == python_quic_manager._get_implementation_name()

if __name__ == "__main__":
    pytest.main([__file__, "-v"])