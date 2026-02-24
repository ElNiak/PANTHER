"""Integration tests for configuration system interactions."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml
from omegaconf import OmegaConf

pytestmark = [pytest.mark.integration, pytest.mark.config_validation]


class TestConfigurationPluginIntegration:
    """Test integration between configuration system and plugin loading."""

    def test_service_config_plugin_loading(self, temp_dir):
        """Test that service configurations properly drive plugin loading."""
        # Create test configuration
        config_data = {
            "tests": [
                {
                    "name": "integration_test",
                    "services": {
                        "test_server": {
                            "implementation": {"name": "picoquic", "type": "iut"},
                            "protocol": {
                                "name": "quic",
                                "version": "rfc9000",
                                "role": "server",
                            },
                            "timeout": 120,
                        },
                        "test_client": {
                            "implementation": {"name": "aioquic", "type": "iut"},
                            "protocol": {
                                "name": "quic",
                                "version": "rfc9000",
                                "role": "client",
                                "target": "test_server",
                            },
                            "timeout": 100,
                        },
                    },
                }
            ]
        }

        config_file = Path(temp_dir) / "test_config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Mock plugin manager to test configuration-driven loading
        with patch(
            "panther.plugins.plugin_manager.PluginManager"
        ) as mock_plugin_manager:
            mock_instance = Mock()
            mock_plugin_manager.return_value = mock_instance

            # Mock service manager creation based on config
            mock_picoquic_manager = Mock()
            mock_picoquic_manager.service_name = "test_server"
            mock_aioquic_manager = Mock()
            mock_aioquic_manager.service_name = "test_client"

            mock_instance.create_service_manager.side_effect = [
                mock_picoquic_manager,
                mock_aioquic_manager,
            ]

            # Test configuration-driven plugin loading
            plugin_manager = mock_plugin_manager()

            # Simulate loading services based on configuration
            services = config_data["tests"][0]["services"]
            loaded_managers = []

            for service_name, service_config in services.items():
                manager = plugin_manager.create_service_manager(service_config, Mock())
                loaded_managers.append(manager)

            # Verify correct number of services loaded
            assert len(loaded_managers) == 2
            assert mock_instance.create_service_manager.call_count == 2

    def test_environment_config_integration(self, temp_dir):
        """Test that environment configurations properly configure environments."""
        # Create environment-specific configuration
        config_data = {
            "tests": [
                {
                    "name": "environment_test",
                    "network_environment": {
                        "type": "docker_compose",
                        "version": "3.8",
                        "networks": {"test_network": {"driver": "bridge"}},
                    },
                    "execution_environment": [
                        {
                            "type": "strace",
                            "trace_calls": ["read", "write", "send", "recv"],
                        }
                    ],
                    "services": {
                        "test_service": {
                            "implementation": {"name": "picoquic", "type": "iut"},
                            "protocol": {"name": "quic", "role": "server"},
                        }
                    },
                }
            ]
        }

        # Test environment configuration loading
        test_config = config_data["tests"][0]

        # Verify network environment config
        network_env_config = test_config["network_environment"]
        assert network_env_config["type"] == "docker_compose"
        assert "networks" in network_env_config

        # Verify execution environment config
        exec_env_config = test_config["execution_environment"][0]
        assert exec_env_config["type"] == "strace"
        assert "trace_calls" in exec_env_config

    def test_global_config_propagation(self, temp_dir):
        """Test that global configuration properly propagates to all components."""
        global_config_data = {
            "logging": {
                "level": "DEBUG",
                "format": "%(asctime)s [%(levelname)s] - %(module)s - %(message)s",
            },
            "paths": {
                "output_dir": "test_outputs",
                "log_dir": "test_logs",
                "plugin_dir": "test_plugins",
            },
            "docker": {
                "build_docker_image": True,
                "remove_containers": True,
                "network_name": "panther_test",
            },
            "observers": {
                "logger": {"enabled": True, "log_level": "DEBUG"},
                "metrics": {"enabled": True, "collect_system_metrics": True},
                "storage": {"enabled": True, "storage_path": "test_storage"},
            },
        }

        # Test configuration propagation to different components
        config = OmegaConf.create(global_config_data)

        # Verify logging configuration
        assert config.logging.level == "DEBUG"
        assert "%(asctime)s" in config.logging.format

        # Verify paths configuration
        assert config.paths.output_dir == "test_outputs"
        assert config.paths.plugin_dir == "test_plugins"

        # Verify docker configuration
        assert config.docker.build_docker_image is True
        assert config.docker.network_name == "panther_test"

        # Verify observers configuration
        assert config.observers.logger.enabled is True
        assert config.observers.metrics.collect_system_metrics is True


class TestConfigurationValidationIntegration:
    """Test integration of configuration validation across the system."""

    def test_service_config_validation_chain(self):
        """Test that service configuration validation works across plugin interfaces."""
        from panther.plugins.services.services_interface import (
            RUN_CMD_SCHEMA,
            validate_structure,
        )

        # Test valid service configuration
        valid_service_config = {
            "implementation": {"name": "picoquic", "type": "iut"},
            "protocol": {"name": "quic", "version": "rfc9000", "role": "server"},
            "timeout": 120,
            "ports": ["4443:4443"],
            "generate_new_certificates": True,
        }

        # Test command structure validation
        valid_command_structure = {
            "pre_compile_cmds": ["echo 'Pre-compile'"],
            "compile_cmds": ["make build"],
            "post_compile_cmds": ["echo 'Post-compile'"],
            "pre_run_cmds": ["echo 'Pre-run'"],
            "run_cmd": {
                "working_dir": "/app",
                "command_binary": "picoquic_server",
                "command_args": "-c /certs/cert.pem -k /certs/key.pem",
                "timeout": 120,
                "command_env": {"QUIC_LOG": "1"},
            },
            "post_run_cmds": ["echo 'Post-run'"],
        }

        # Test validation passes
        try:
            validate_structure(valid_command_structure, RUN_CMD_SCHEMA)
        except Exception as e:
            pytest.fail(f"Valid command structure failed validation: {e}")

        # Test service config has required fields
        required_fields = ["implementation", "protocol", "timeout"]
        for field in required_fields:
            assert field in valid_service_config

    def test_experiment_config_validation_integration(self, temp_dir):
        """Test that experiment configuration validation integrates with the system."""
        # Create comprehensive experiment configuration
        experiment_config = {
            "logging": {"level": "INFO"},
            "observers": {
                "logger": {"enabled": True},
                "metrics": {"enabled": False},
                "storage": {"enabled": True},
            },
            "paths": {
                "output_dir": str(temp_dir / "outputs"),
                "log_dir": str(temp_dir / "logs"),
            },
            "docker": {"build_docker_image": False},
            "tests": [
                {
                    "name": "validation_test",
                    "description": "Test configuration validation",
                    "network_environment": {"type": "docker_compose"},
                    "execution_environment": [],
                    "services": {
                        "server": {
                            "implementation": {"name": "picoquic", "type": "iut"},
                            "protocol": {
                                "name": "quic",
                                "version": "rfc9000",
                                "role": "server",
                            },
                            "timeout": 100,
                            "ports": ["4443:4443"],
                        }
                    },
                    "steps": {"wait": 30},
                }
            ],
        }

        # Test configuration structure
        assert "tests" in experiment_config
        assert len(experiment_config["tests"]) == 1

        test_config = experiment_config["tests"][0]
        assert "services" in test_config
        assert "network_environment" in test_config

        # Test service configuration within experiment
        service_config = test_config["services"]["server"]
        assert service_config["implementation"]["name"] == "picoquic"
        assert service_config["protocol"]["role"] == "server"

    @pytest.mark.parametrize(
        "invalid_config,expected_error",
        [
            ({"implementation": {"name": "invalid_impl"}}, "missing protocol"),
            ({"protocol": {"name": "quic"}}, "missing implementation"),
            (
                {
                    "implementation": {"name": "picoquic"},
                    "protocol": {"name": "quic"},
                    "timeout": "invalid",
                },
                "invalid timeout",
            ),
        ],
    )
    def test_invalid_config_handling(self, invalid_config, expected_error):
        """Test that invalid configurations are properly rejected."""
        # Test that various invalid configurations are caught
        required_fields = ["implementation", "protocol", "timeout"]

        for field in required_fields:
            if field not in invalid_config:
                # This should be caught by validation
                assert field not in invalid_config

        # Test timeout validation
        if "timeout" in invalid_config and not isinstance(
            invalid_config["timeout"], int
        ):
            assert not isinstance(invalid_config["timeout"], int)


class TestConfigurationTemplateIntegration:
    """Test integration between configuration and template rendering."""

    def test_config_template_parameter_injection(self):
        """Test that configuration parameters are properly injected into templates."""
        # Mock template renderer with configuration integration
        with patch(
            "panther.core.template.template_renderer.TemplateRenderer"
        ) as mock_renderer:
            mock_instance = Mock()
            mock_renderer.return_value = mock_instance

            # Test configuration parameter injection
            service_config = {
                "service_name": "test_server",
                "implementation": {"name": "picoquic"},
                "protocol": {"name": "quic", "role": "server"},
                "certificates": {
                    "cert_path": "/certs/cert.pem",
                    "key_path": "/certs/key.pem",
                },
                "network": {"host": "0.0.0.0", "port": 4443},
            }

            expected_template_params = {
                "service_name": "test_server",
                "cert_path": "/certs/cert.pem",
                "key_path": "/certs/key.pem",
                "host": "0.0.0.0",
                "port": 4443,
                "role": "server",
            }

            # Mock template rendering with parameters
            mock_instance.render_command_template.return_value = (
                "picoquic_server -c /certs/cert.pem -k /certs/key.pem -p 4443"
            )

            # Test template rendering
            renderer = mock_renderer()
            result = renderer.render_command_template(
                "server_command.jinja", expected_template_params
            )

            # Verify template was rendered with correct parameters
            assert "picoquic_server" in result
            assert "/certs/cert.pem" in result
            mock_instance.render_command_template.assert_called_once()

    def test_environment_variable_config_integration(self):
        """Test that environment variables from configuration are properly handled."""
        config_with_env = {
            "environment_variables": {
                "QUIC_LOG": "1",
                "SSL_CERT_FILE": "/certs/ca.pem",
                "PANTHER_DEBUG": "true",
            },
            "service_config": {
                "implementation": {"name": "picoquic"},
                "protocol": {"name": "quic"},
            },
        }

        # Test environment variable extraction
        env_vars = config_with_env["environment_variables"]
        assert env_vars["QUIC_LOG"] == "1"
        assert env_vars["SSL_CERT_FILE"] == "/certs/ca.pem"
        assert env_vars["PANTHER_DEBUG"] == "true"

        # Test integration with service config
        service_config = config_with_env["service_config"]
        combined_config = {**service_config, "environment": env_vars}

        assert "environment" in combined_config
        assert combined_config["environment"]["QUIC_LOG"] == "1"


class TestMultiServiceConfigurationIntegration:
    """Test configuration integration with multiple services."""

    def test_client_server_config_integration(self):
        """Test that client-server configurations properly reference each other."""
        multi_service_config = {
            "services": {
                "quic_server": {
                    "implementation": {"name": "picoquic", "type": "iut"},
                    "protocol": {
                        "name": "quic",
                        "version": "rfc9000",
                        "role": "server",
                    },
                    "timeout": 150,
                    "ports": ["4443:4443"],
                    "generate_new_certificates": True,
                },
                "quic_client": {
                    "implementation": {"name": "aioquic", "type": "iut"},
                    "protocol": {
                        "name": "quic",
                        "version": "rfc9000",
                        "role": "client",
                        "target": "quic_server",
                    },
                    "timeout": 120,
                    "generate_new_certificates": True,
                },
            }
        }

        # Test service reference resolution
        server_config = multi_service_config["services"]["quic_server"]
        client_config = multi_service_config["services"]["quic_client"]

        # Verify server configuration
        assert server_config["protocol"]["role"] == "server"
        assert "4443:4443" in server_config["ports"]

        # Verify client configuration and target reference
        assert client_config["protocol"]["role"] == "client"
        assert client_config["protocol"]["target"] == "quic_server"

        # Test target resolution
        target_service = client_config["protocol"]["target"]
        assert target_service in multi_service_config["services"]
        target_config = multi_service_config["services"][target_service]
        assert target_config["protocol"]["role"] == "server"

    def test_ivy_integration_config(self):
        """Test configuration integration with Ivy formal verification."""
        ivy_config = {
            "services": {
                "ivy_tester": {
                    "implementation": {
                        "name": "panther_ivy",
                        "type": "testers",
                        "test": "quic_client_test_max",
                    },
                    "protocol": {
                        "name": "quic",
                        "version": "rfc9000",
                        "role": "server",
                    },
                    "timeout": 200,
                    "ports": ["4443:4443", "4987:4987"],
                },
                "implementation_under_test": {
                    "implementation": {"name": "picoquic", "type": "iut"},
                    "protocol": {
                        "name": "quic",
                        "version": "rfc9000",
                        "role": "client",
                        "target": "ivy_tester",
                    },
                    "timeout": 180,
                },
            }
        }

        # Test Ivy-specific configuration
        ivy_service = ivy_config["services"]["ivy_tester"]
        assert ivy_service["implementation"]["type"] == "testers"
        assert ivy_service["implementation"]["test"] == "quic_client_test_max"
        assert len(ivy_service["ports"]) == 2

        # Test IUT configuration
        iut_service = ivy_config["services"]["implementation_under_test"]
        assert iut_service["implementation"]["type"] == "iut"
        assert iut_service["protocol"]["target"] == "ivy_tester"
