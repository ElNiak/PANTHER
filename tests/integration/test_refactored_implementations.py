"""Integration tests for all refactored QUIC implementations.

This test suite verifies that all refactored QUIC service managers:
1. Can be instantiated correctly
2. Generate valid commands
3. Work with the base class infrastructure
4. Maintain backward compatibility
"""

from unittest.mock import Mock, patch

import pytest

from panther.plugins.services.iut.quic.aioquic.aioquic import AioquicServiceManager
from panther.plugins.services.iut.quic.lsquic.lsquic import LsquicServiceManager
from panther.plugins.services.iut.quic.mvfst.mvfst import MvfstServiceManager
from panther.plugins.services.iut.quic.picoquic.picoquic import PicoquicServiceManager
from panther.plugins.services.iut.quic.picoquic_shadow.picoquic_shadow import (
    PicoquicShadowServiceManager,
)
from panther.plugins.services.iut.quic.quant.quant import QuantServiceManager
from panther.plugins.services.iut.quic.quic_go.quic_go import QuicGoServiceManager
from panther.plugins.services.iut.quic.quiche.quiche import QuicheServiceManager
from panther.plugins.services.iut.quic.quinn.quinn import QuinnServiceManager


class TestRefactoredImplementations:
    """Test all refactored QUIC implementations."""

    # All refactored service manager classes
    implementations = [
        ("lsquic", LsquicServiceManager),
        ("mvfst", MvfstServiceManager),
        ("aioquic", AioquicServiceManager),
        ("picoquic", PicoquicServiceManager),
        ("picoquic_shadow", PicoquicShadowServiceManager),
        ("quant", QuantServiceManager),
        ("quic_go", QuicGoServiceManager),
        ("quiche", QuicheServiceManager),
        ("quinn", QuinnServiceManager),
    ]

    @pytest.fixture
    def mock_event_emitter(self):
        """Mock event emitter for service managers."""
        return Mock()

    @pytest.mark.parametrize("impl_name,impl_class", implementations)
    def test_service_manager_instantiation(
        self, impl_name, impl_class, mock_event_emitter
    ):
        """Test that all refactored service managers can be instantiated."""
        try:
            # Create service manager with minimal config
            config = {
                "implementation": {"name": impl_name, "type": "iut"},
                "protocol": {"name": "quic", "version": "rfc9000", "role": "server"},
            }

            service_manager = impl_class(
                config=config, event_emitter=mock_event_emitter
            )

            # Verify basic properties
            assert service_manager is not None
            assert hasattr(service_manager, "_get_implementation_name")
            assert hasattr(service_manager, "_get_binary_name")
            assert hasattr(service_manager, "generate_run_command")

        except Exception as e:
            pytest.fail(f"Failed to instantiate {impl_name}: {e}")

    @pytest.mark.parametrize("impl_name,impl_class", implementations)
    def test_server_command_generation(self, impl_name, impl_class, mock_event_emitter):
        """Test server command generation for all implementations."""
        config = {
            "implementation": {"name": impl_name, "type": "iut"},
            "protocol": {"name": "quic", "version": "rfc9000", "role": "server"},
            "host": "0.0.0.0",
            "port": 4443,
        }

        service_manager = impl_class(config=config, event_emitter=mock_event_emitter)

        # Generate server command
        command = service_manager.generate_run_command(
            role="server", host="0.0.0.0", port=4443
        )

        # Verify command is generated
        assert command is not None
        assert isinstance(command, str)
        assert len(command) > 0

        # Verify command contains expected elements
        assert "4443" in command  # Port should be present

    @pytest.mark.parametrize("impl_name,impl_class", implementations)
    def test_client_command_generation(self, impl_name, impl_class, mock_event_emitter):
        """Test client command generation for all implementations."""
        config = {
            "implementation": {"name": impl_name, "type": "iut"},
            "protocol": {"name": "quic", "version": "rfc9000", "role": "client"},
        }

        service_manager = impl_class(config=config, event_emitter=mock_event_emitter)

        # Generate client command
        command = service_manager.generate_run_command(
            role="client", host="localhost", port=4443
        )

        # Verify command is generated
        assert command is not None
        assert isinstance(command, str)
        assert len(command) > 0

        # Verify command contains expected elements
        assert any(target in command for target in ["localhost", "4443"])

    @pytest.mark.parametrize("impl_name,impl_class", implementations)
    def test_base_class_methods(self, impl_name, impl_class, mock_event_emitter):
        """Test that base class methods are properly implemented."""
        config = {
            "implementation": {"name": impl_name, "type": "iut"},
            "protocol": {"name": "quic", "version": "rfc9000", "role": "server"},
        }

        service_manager = impl_class(config=config, event_emitter=mock_event_emitter)

        # Test required abstract methods are implemented
        assert callable(getattr(service_manager, "_get_implementation_name", None))
        assert callable(getattr(service_manager, "_get_binary_name", None))
        assert callable(getattr(service_manager, "generate_deployment_commands", None))
        assert callable(getattr(service_manager, "_do_prepare", None))

        # Test implementation name matches expected
        impl_name_result = service_manager._get_implementation_name()
        assert impl_name_result == impl_name

    @pytest.mark.parametrize("impl_name,impl_class", implementations)
    def test_supported_features(self, impl_name, impl_class, mock_event_emitter):
        """Test that supported features are properly defined."""
        config = {
            "implementation": {"name": impl_name, "type": "iut"},
            "protocol": {"name": "quic", "version": "rfc9000", "role": "server"},
        }

        service_manager = impl_class(config=config, event_emitter=mock_event_emitter)

        # Test supported features method exists and returns dict
        if hasattr(service_manager, "get_supported_features"):
            features = service_manager.get_supported_features()
            assert isinstance(features, dict)

            # All QUIC implementations should support basic QUIC
            assert features.get("quic", True)  # Default to True if not specified

    @pytest.mark.parametrize("impl_name,impl_class", implementations)
    def test_post_run_commands(self, impl_name, impl_class, mock_event_emitter):
        """Test post-run commands generation."""
        config = {
            "implementation": {"name": impl_name, "type": "iut"},
            "protocol": {"name": "quic", "version": "rfc9000", "role": "server"},
        }

        service_manager = impl_class(config=config, event_emitter=mock_event_emitter)

        # Test post-run commands if method exists
        if hasattr(service_manager, "generate_post_run_commands"):
            post_run_commands = service_manager.generate_post_run_commands()
            assert isinstance(post_run_commands, list)
            # Commands should be strings if present
            for cmd in post_run_commands:
                assert isinstance(cmd, str)

    def test_rust_implementations_inheritance(self, mock_event_emitter):
        """Test that Rust implementations properly inherit from RustQUICServiceManager."""
        rust_implementations = [
            ("quiche", QuicheServiceManager),
            ("quinn", QuinnServiceManager),
        ]

        for impl_name, impl_class in rust_implementations:
            config = {
                "implementation": {"name": impl_name, "type": "iut"},
                "protocol": {"name": "quic", "version": "rfc9000", "role": "server"},
            }

            service_manager = impl_class(
                config=config, event_emitter=mock_event_emitter
            )

            # Check that Rust-specific methods are available
            # (They should inherit from RustQUICServiceManager)
            assert hasattr(service_manager, "_get_implementation_name")

            # Test Rust-specific compile command if available
            if hasattr(service_manager, "generate_compile_command"):
                compile_cmd = service_manager.generate_compile_command()
                assert isinstance(compile_cmd, str)
                # Should contain cargo build command
                assert "cargo build" in compile_cmd

    def test_python_implementations_inheritance(self, mock_event_emitter):
        """Test that Python implementations properly inherit from PythonQUICServiceManager."""
        python_implementations = [("aioquic", AioquicServiceManager)]

        for impl_name, impl_class in python_implementations:
            config = {
                "implementation": {"name": impl_name, "type": "iut"},
                "protocol": {"name": "quic", "version": "rfc9000", "role": "server"},
            }

            service_manager = impl_class(
                config=config, event_emitter=mock_event_emitter
            )

            # Check that Python-specific methods are available
            assert hasattr(service_manager, "_get_implementation_name")

            # Test Python-specific methods if available
            if hasattr(service_manager, "_get_python_module"):
                python_module = service_manager._get_python_module()
                assert isinstance(python_module, str)
                assert len(python_module) > 0

    def test_command_structure_consistency(self, mock_event_emitter):
        """Test that all implementations generate consistently structured commands."""
        test_params = {
            "role": "server",
            "host": "0.0.0.0",
            "port": 4443,
            "certfile": "/certs/cert.pem",
            "keyfile": "/certs/key.pem",
        }

        for impl_name, impl_class in self.implementations:
            config = {
                "implementation": {"name": impl_name, "type": "iut"},
                "protocol": {"name": "quic", "version": "rfc9000", "role": "server"},
            }

            service_manager = impl_class(
                config=config, event_emitter=mock_event_emitter
            )

            command = service_manager.generate_run_command(**test_params)

            # Verify command structure
            assert isinstance(command, str)
            assert len(command.strip()) > 0

            # Command should not be empty or just whitespace
            assert command.strip() != ""

            # Should not contain obvious shell injection patterns
            dangerous_patterns = [";rm", "&&rm", "|rm", ";cat", "&&cat"]
            for pattern in dangerous_patterns:
                assert pattern not in command

    def test_error_handling(self, mock_event_emitter):
        """Test error handling in refactored implementations."""
        for impl_name, impl_class in self.implementations:
            # Test with minimal config - should not crash
            config = {
                "implementation": {"name": impl_name, "type": "iut"},
                "protocol": {"name": "quic", "version": "rfc9000", "role": "server"},
            }

            try:
                service_manager = impl_class(
                    config=config, event_emitter=mock_event_emitter
                )

                # Should handle empty kwargs gracefully
                command = service_manager.generate_run_command()
                assert isinstance(command, str)

            except Exception as e:
                pytest.fail(
                    f"Implementation {impl_name} failed with minimal config: {e}"
                )


class TestBackwardCompatibility:
    """Test backward compatibility of refactored implementations."""

    @pytest.mark.parametrize(
        "impl_name,impl_class", TestRefactoredImplementations.implementations
    )
    def test_deployment_commands_compatibility(self, impl_name, impl_class):
        """Test that deployment commands work for backward compatibility."""
        mock_event_emitter = Mock()

        config = {
            "implementation": {"name": impl_name, "type": "iut"},
            "protocol": {"name": "quic", "version": "rfc9000", "role": "server"},
        }

        service_manager = impl_class(config=config, event_emitter=mock_event_emitter)

        # Test deployment commands method exists
        assert hasattr(service_manager, "generate_deployment_commands")

        deployment_cmd = service_manager.generate_deployment_commands()
        assert isinstance(deployment_cmd, str)
        assert len(deployment_cmd) > 0


if __name__ == "__main__":
    # Run tests when executed directly
    pytest.main([__file__, "-v"])
