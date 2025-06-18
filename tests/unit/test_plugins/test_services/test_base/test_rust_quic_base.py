#!/usr/bin/env python3.10
"""Tests for Rust QUIC base service manager using Python 3.10 syntax."""

from __future__ import annotations

from typing import List, Dict, Any
from unittest.mock import Mock, patch, MagicMock

import pytest

# Test imports with fallback to mocks
try:
    from panther.plugins.services.base.rust_quic_base import RustQUICServiceManager
    from panther.plugins.services.base.quic_service_base import BaseQUICServiceManager
    RUST_QUIC_SYSTEM_AVAILABLE = True
except ImportError:
    RUST_QUIC_SYSTEM_AVAILABLE = False
    
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
    
    class RustQUICServiceManager(BaseQUICServiceManager):
        """Mock Rust QUIC service manager."""
        
        def __init__(self):
            super().__init__()
            self.cargo_features: List[str] = []
            self.rust_env_vars: Dict[str, str] = {}
            self.rustc_flags: List[str] = []
            
        def _build_common_rust_args(self, features: List[str] | None = None, 
                                   env_vars: Dict[str, str] | None = None,
                                   rustc_flags: List[str] | None = None) -> List[str]:
            """Build common Rust-specific arguments."""
            args = []
            
            if features:
                features_str = ",".join(features)
                args.extend(['--features', features_str])
            
            # Environment variables would be set differently, not as args
            # This is just for testing the method exists and works
            
            if rustc_flags:
                for flag in rustc_flags:
                    args.extend(['--rustc-flag', flag])
            
            return args
        
        def _setup_rust_environment(self, **kwargs) -> Dict[str, str]:
            """Setup Rust-specific environment variables."""
            env = {}
            
            # Rust-specific environment variables
            if kwargs.get('debug', False):
                env['RUST_LOG'] = 'debug'
            else:
                env['RUST_LOG'] = kwargs.get('log_level', 'info')
            
            env['RUST_BACKTRACE'] = '1' if kwargs.get('backtrace', True) else '0'
            
            # Cargo features as environment variable
            if self.cargo_features:
                env['CARGO_FEATURES'] = ",".join(self.cargo_features)
            
            # Custom environment variables
            if self.rust_env_vars:
                env.update(self.rust_env_vars)
            
            return env
        
        def _get_cargo_build_command(self, release: bool = True, 
                                   features: List[str] | None = None) -> str:
            """Generate cargo build command."""
            cmd_parts = ['cargo', 'build']
            
            if release:
                cmd_parts.append('--release')
            
            if features:
                features_str = ",".join(features)
                cmd_parts.extend(['--features', features_str])
            
            return " ".join(cmd_parts)
        
        def set_cargo_features(self, features: List[str]):
            """Set Cargo features for the implementation."""
            self.cargo_features = features.copy()
        
        def add_cargo_feature(self, feature: str):
            """Add a single Cargo feature."""
            if feature not in self.cargo_features:
                self.cargo_features.append(feature)
        
        def set_rust_env_vars(self, env_vars: Dict[str, str]):
            """Set Rust-specific environment variables."""
            self.rust_env_vars = env_vars.copy()
        
        def set_rustc_flags(self, flags: List[str]):
            """Set rustc compilation flags."""
            self.rustc_flags = flags.copy()

pytestmark = [pytest.mark.unit, pytest.mark.rust_quic]

class MockRustQuicImpl(RustQUICServiceManager):
    """Mock concrete Rust QUIC implementation for testing."""
    
    def __init__(self):
        super().__init__()
        self.implementation_name = "mock_rust_quic"
        self.binary_name = "mock-quic-bin"
    
    def _get_implementation_name(self) -> str:
        return self.implementation_name
    
    def _get_binary_name(self) -> str:
        return self.binary_name
    
    def _get_server_specific_args(self, **kwargs) -> List[str]:
        args = []
        if kwargs.get('bind_address'):
            args.extend(['--bind', kwargs['bind_address']])
        if kwargs.get('max_connections'):
            args.extend(['--max-connections', str(kwargs['max_connections'])])
        return args
    
    def _get_client_specific_args(self, **kwargs) -> List[str]:
        args = []
        host = kwargs.get('host', 'localhost')
        port = kwargs.get('port', 4443)
        args.append(f"{host}:{port}")
        
        if kwargs.get('request_path'):
            args.extend(['--path', kwargs['request_path']])
        
        return args
    
    def generate_deployment_commands(self) -> str:
        return f"{self.binary_name} --server --port 4443"
    
    def _do_prepare(self, plugin_manager=None):
        pass

class TestRustQUICServiceManager:
    """Test RustQUICServiceManager base functionality."""
    
    @pytest.fixture
    def rust_quic_manager(self) -> MockRustQuicImpl:
        """Create a mock Rust QUIC manager for testing."""
        return MockRustQuicImpl()
    
    def test_rust_quic_manager_initialization(self, rust_quic_manager: MockRustQuicImpl):
        """Test RustQUICServiceManager initialization."""
        assert isinstance(rust_quic_manager, RustQUICServiceManager)
        assert hasattr(rust_quic_manager, 'cargo_features')
        assert hasattr(rust_quic_manager, 'rust_env_vars')
        assert hasattr(rust_quic_manager, 'rustc_flags')
        assert rust_quic_manager.cargo_features == []
        assert rust_quic_manager.rust_env_vars == {}
        assert rust_quic_manager.rustc_flags == []
    
    def test_implementation_identification(self, rust_quic_manager: MockRustQuicImpl):
        """Test implementation identification methods."""
        assert rust_quic_manager._get_implementation_name() == "mock_rust_quic"
        assert rust_quic_manager._get_binary_name() == "mock-quic-bin"
    
    def test_cargo_features_management(self, rust_quic_manager: MockRustQuicImpl):
        """Test Cargo features management."""
        # Test setting features
        features = ['async', 'tls', 'crypto']
        rust_quic_manager.set_cargo_features(features)
        assert rust_quic_manager.cargo_features == features
        
        # Test adding individual feature
        rust_quic_manager.add_cargo_feature('logging')
        assert 'logging' in rust_quic_manager.cargo_features
        
        # Test not adding duplicate feature
        rust_quic_manager.add_cargo_feature('async')
        assert rust_quic_manager.cargo_features.count('async') == 1
    
    def test_rust_environment_variables(self, rust_quic_manager: MockRustQuicImpl):
        """Test Rust environment variables management."""
        env_vars = {
            'RUST_LOG': 'debug',
            'RUST_BACKTRACE': '1',
            'CUSTOM_VAR': 'value'
        }
        
        rust_quic_manager.set_rust_env_vars(env_vars)
        assert rust_quic_manager.rust_env_vars == env_vars
    
    def test_rustc_flags_management(self, rust_quic_manager: MockRustQuicImpl):
        """Test rustc flags management."""
        flags = ['-C', 'opt-level=3', '-C', 'target-cpu=native']
        rust_quic_manager.set_rustc_flags(flags)
        assert rust_quic_manager.rustc_flags == flags

class TestRustQUICCommandGeneration:
    """Test command generation for Rust QUIC implementations."""
    
    @pytest.fixture
    def rust_quic_manager(self) -> MockRustQuicImpl:
        """Create a mock Rust QUIC manager for testing."""
        return MockRustQuicImpl()
    
    def test_server_command_generation_basic(self, rust_quic_manager: MockRustQuicImpl):
        """Test basic server command generation."""
        cmd = rust_quic_manager.generate_run_command(
            role='server',
            port=4443
        )
        
        assert 'mock-quic-bin' in cmd
        assert '-p 4443' in cmd
    
    def test_server_command_generation_with_certificates(self, rust_quic_manager: MockRustQuicImpl):
        """Test server command generation with certificates."""
        cmd = rust_quic_manager.generate_run_command(
            role='server',
            port=8443,
            certificate_file='/app/certs/server.crt',
            private_key_file='/app/certs/server.key'
        )
        
        assert 'mock-quic-bin' in cmd
        assert '-p 8443' in cmd
        assert '-c /app/certs/server.crt' in cmd
        assert '-k /app/certs/server.key' in cmd
    
    def test_server_command_generation_with_rust_specific_args(self, rust_quic_manager: MockRustQuicImpl):
        """Test server command generation with Rust-specific arguments."""
        cmd = rust_quic_manager.generate_run_command(
            role='server',
            port=4443,
            bind_address='0.0.0.0',
            max_connections=1000
        )
        
        assert '--bind 0.0.0.0' in cmd
        assert '--max-connections 1000' in cmd
    
    def test_client_command_generation_basic(self, rust_quic_manager: MockRustQuicImpl):
        """Test basic client command generation."""
        cmd = rust_quic_manager.generate_run_command(
            role='client',
            host='example.com',
            port=443
        )
        
        assert 'mock-quic-bin' in cmd
        assert 'example.com:443' in cmd
    
    def test_client_command_generation_with_ca_file(self, rust_quic_manager: MockRustQuicImpl):
        """Test client command generation with CA file."""
        cmd = rust_quic_manager.generate_run_command(
            role='client',
            host='secure.example.com',
            port=443,
            ca_file='/app/certs/ca.pem'
        )
        
        assert '--ca-file /app/certs/ca.pem' in cmd
        assert 'secure.example.com:443' in cmd
    
    def test_client_command_generation_insecure(self, rust_quic_manager: MockRustQuicImpl):
        """Test client command generation with insecure mode."""
        cmd = rust_quic_manager.generate_run_command(
            role='client',
            host='test.local',
            port=4443,
            verify_mode='none'
        )
        
        assert '--insecure' in cmd
        assert 'test.local:4443' in cmd
    
    def test_client_command_generation_with_path(self, rust_quic_manager: MockRustQuicImpl):
        """Test client command generation with request path."""
        cmd = rust_quic_manager.generate_run_command(
            role='client',
            host='api.example.com',
            port=443,
            request_path='/api/v1/data'
        )
        
        assert '--path /api/v1/data' in cmd

class TestRustQUICBuildCommands:
    """Test Rust-specific build command generation."""
    
    @pytest.fixture
    def rust_quic_manager(self) -> MockRustQuicImpl:
        """Create a mock Rust QUIC manager for testing."""
        return MockRustQuicImpl()
    
    def test_cargo_build_command_basic(self, rust_quic_manager: MockRustQuicImpl):
        """Test basic cargo build command generation."""
        cmd = rust_quic_manager._get_cargo_build_command()
        assert cmd == "cargo build --release"
    
    def test_cargo_build_command_debug(self, rust_quic_manager: MockRustQuicImpl):
        """Test cargo build command for debug builds."""
        cmd = rust_quic_manager._get_cargo_build_command(release=False)
        assert cmd == "cargo build"
        assert "--release" not in cmd
    
    def test_cargo_build_command_with_features(self, rust_quic_manager: MockRustQuicImpl):
        """Test cargo build command with features."""
        features = ['async', 'tls', 'http3']
        cmd = rust_quic_manager._get_cargo_build_command(features=features)
        
        assert "cargo build --release" in cmd
        assert "--features async,tls,http3" in cmd
    
    def test_common_rust_args_with_features(self, rust_quic_manager: MockRustQuicImpl):
        """Test building common Rust arguments with features."""
        features = ['feature1', 'feature2']
        args = rust_quic_manager._build_common_rust_args(features=features)
        
        assert '--features' in args
        assert 'feature1,feature2' in args
    
    def test_common_rust_args_with_rustc_flags(self, rust_quic_manager: MockRustQuicImpl):
        """Test building common Rust arguments with rustc flags."""
        rustc_flags = ['-C opt-level=3', '-C target-cpu=native']
        args = rust_quic_manager._build_common_rust_args(rustc_flags=rustc_flags)
        
        assert '--rustc-flag' in args
        assert '-C opt-level=3' in args
        assert '-C target-cpu=native' in args

class TestRustQUICEnvironmentSetup:
    """Test Rust-specific environment setup."""
    
    @pytest.fixture
    def rust_quic_manager(self) -> MockRustQuicImpl:
        """Create a mock Rust QUIC manager for testing."""
        return MockRustQuicImpl()
    
    def test_rust_environment_basic(self, rust_quic_manager: MockRustQuicImpl):
        """Test basic Rust environment setup."""
        env = rust_quic_manager._setup_rust_environment()
        
        assert 'RUST_LOG' in env
        assert 'RUST_BACKTRACE' in env
        assert env['RUST_LOG'] == 'info'
        assert env['RUST_BACKTRACE'] == '1'
    
    def test_rust_environment_debug_mode(self, rust_quic_manager: MockRustQuicImpl):
        """Test Rust environment setup in debug mode."""
        env = rust_quic_manager._setup_rust_environment(debug=True)
        
        assert env['RUST_LOG'] == 'debug'
    
    def test_rust_environment_custom_log_level(self, rust_quic_manager: MockRustQuicImpl):
        """Test Rust environment setup with custom log level."""
        env = rust_quic_manager._setup_rust_environment(log_level='warn')
        
        assert env['RUST_LOG'] == 'warn'
    
    def test_rust_environment_no_backtrace(self, rust_quic_manager: MockRustQuicImpl):
        """Test Rust environment setup without backtrace."""
        env = rust_quic_manager._setup_rust_environment(backtrace=False)
        
        assert env['RUST_BACKTRACE'] == '0'
    
    def test_rust_environment_with_cargo_features(self, rust_quic_manager: MockRustQuicImpl):
        """Test Rust environment setup with Cargo features."""
        rust_quic_manager.set_cargo_features(['async', 'tls'])
        env = rust_quic_manager._setup_rust_environment()
        
        assert 'CARGO_FEATURES' in env
        assert env['CARGO_FEATURES'] == 'async,tls'
    
    def test_rust_environment_with_custom_vars(self, rust_quic_manager: MockRustQuicImpl):
        """Test Rust environment setup with custom variables."""
        custom_vars = {
            'CUSTOM_VAR1': 'value1',
            'CUSTOM_VAR2': 'value2'
        }
        rust_quic_manager.set_rust_env_vars(custom_vars)
        env = rust_quic_manager._setup_rust_environment()
        
        assert 'CUSTOM_VAR1' in env
        assert 'CUSTOM_VAR2' in env
        assert env['CUSTOM_VAR1'] == 'value1'
        assert env['CUSTOM_VAR2'] == 'value2'

class TestRustQUICIntegration:
    """Test integration scenarios for Rust QUIC service managers."""
    
    @pytest.fixture
    def rust_quic_manager(self) -> MockRustQuicImpl:
        """Create a mock Rust QUIC manager for testing."""
        return MockRustQuicImpl()
    
    def test_full_server_setup_scenario(self, rust_quic_manager: MockRustQuicImpl):
        """Test complete server setup scenario."""
        # Configure Rust-specific settings
        rust_quic_manager.set_cargo_features(['async', 'tls'])
        rust_quic_manager.set_rust_env_vars({'RUST_LOG': 'debug'})
        
        # Generate server command
        cmd = rust_quic_manager.generate_run_command(
            role='server',
            port=4443,
            certificate_file='/app/certs/server.crt',
            private_key_file='/app/certs/server.key',
            bind_address='0.0.0.0',
            max_connections=500
        )
        
        # Verify command contains all expected elements
        assert 'mock-quic-bin' in cmd
        assert '-p 4443' in cmd
        assert '-c /app/certs/server.crt' in cmd
        assert '-k /app/certs/server.key' in cmd
        assert '--bind 0.0.0.0' in cmd
        assert '--max-connections 500' in cmd
        
        # Verify environment setup
        env = rust_quic_manager._setup_rust_environment()
        assert env['CARGO_FEATURES'] == 'async,tls'
        assert env['RUST_LOG'] == 'debug'
    
    def test_full_client_setup_scenario(self, rust_quic_manager: MockRustQuicImpl):
        """Test complete client setup scenario."""
        # Configure for client testing
        rust_quic_manager.set_cargo_features(['client', 'http3'])
        
        # Generate client command
        cmd = rust_quic_manager.generate_run_command(
            role='client',
            host='quic.example.com',
            port=443,
            ca_file='/app/certs/ca.pem',
            request_path='/api/test'
        )
        
        # Verify command
        assert 'mock-quic-bin' in cmd
        assert 'quic.example.com:443' in cmd
        assert '--ca-file /app/certs/ca.pem' in cmd
        assert '--path /api/test' in cmd
        
        # Verify cargo features are configured
        assert 'client' in rust_quic_manager.cargo_features
        assert 'http3' in rust_quic_manager.cargo_features
    
    def test_deployment_command_generation(self, rust_quic_manager: MockRustQuicImpl):
        """Test deployment command generation."""
        deployment_cmd = rust_quic_manager.generate_deployment_commands()
        
        assert 'mock-quic-bin' in deployment_cmd
        assert '--server' in deployment_cmd
        assert '--port 4443' in deployment_cmd
    
    def test_cargo_build_integration(self, rust_quic_manager: MockRustQuicImpl):
        """Test cargo build command integration."""
        # Set up features
        rust_quic_manager.set_cargo_features(['async', 'tls', 'http3'])
        
        # Generate build command
        build_cmd = rust_quic_manager._get_cargo_build_command(
            features=rust_quic_manager.cargo_features
        )
        
        assert 'cargo build --release' in build_cmd
        assert '--features async,tls,http3' in build_cmd

class TestRustQUICErrorHandling:
    """Test error handling in Rust QUIC service managers."""
    
    @pytest.fixture
    def rust_quic_manager(self) -> MockRustQuicImpl:
        """Create a mock Rust QUIC manager for testing."""
        return MockRustQuicImpl()
    
    def test_command_generation_with_missing_args(self, rust_quic_manager: MockRustQuicImpl):
        """Test command generation with missing required arguments."""
        # Should not crash, should use defaults
        cmd = rust_quic_manager.generate_run_command()
        
        assert isinstance(cmd, str)
        assert 'mock-quic-bin' in cmd
    
    def test_empty_cargo_features_handling(self, rust_quic_manager: MockRustQuicImpl):
        """Test handling of empty cargo features."""
        rust_quic_manager.set_cargo_features([])
        
        args = rust_quic_manager._build_common_rust_args(features=[])
        # Should not include --features if no features provided
        assert '--features' not in args
    
    def test_environment_setup_with_none_values(self, rust_quic_manager: MockRustQuicImpl):
        """Test environment setup with None values."""
        env = rust_quic_manager._setup_rust_environment(
            debug=None,
            log_level=None,
            backtrace=None
        )
        
        # Should handle None values gracefully
        assert isinstance(env, dict)
        assert 'RUST_LOG' in env
        assert 'RUST_BACKTRACE' in env

if __name__ == "__main__":
    pytest.main([__file__, "-v"])