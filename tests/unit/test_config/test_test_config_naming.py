"""Tests for TestConfig.generate_default_name and generate_default_description."""

from panther.config.core.models.experiment import TestConfig


class TestGenerateDefaultName:
    def test_basic_client_server(self):
        test_data = {
            "services": {
                "server": {"protocol": {"name": "quic", "role": "server"}},
                "client": {"protocol": {"name": "quic", "role": "client"}},
            }
        }
        result = TestConfig.generate_default_name(test_data)
        assert "QUIC" in result
        assert "Server" in result
        assert "Client" in result
        assert "Communication Test" in result

    def test_empty_services(self):
        assert TestConfig.generate_default_name({"services": {}}) == ""
        assert TestConfig.generate_default_name({}) == ""

    def test_with_execution_environment(self):
        test_data = {
            "services": {
                "server": {"protocol": {"name": "quic", "role": "server"}},
            },
            "execution_environment": [{"type": "strace"}],
        }
        result = TestConfig.generate_default_name(test_data)
        assert result.startswith("Strace - ")

    def test_with_non_default_network_env(self):
        test_data = {
            "services": {
                "server": {"protocol": {"name": "quic", "role": "server"}},
            },
            "network_environment": {"type": "shadow_ns"},
        }
        result = TestConfig.generate_default_name(test_data)
        assert "Shadow Ns" in result

    def test_docker_compose_no_prefix(self):
        test_data = {
            "services": {
                "server": {"protocol": {"name": "quic", "role": "server"}},
            },
            "network_environment": {"type": "docker_compose"},
        }
        result = TestConfig.generate_default_name(test_data)
        assert "Docker" not in result


class TestGenerateDefaultDescription:
    def test_basic_description(self):
        test_data = {
            "services": {
                "server": {
                    "implementation": {"name": "picoquic"},
                    "protocol": {"role": "server"},
                },
                "client": {
                    "implementation": {"name": "aioquic"},
                    "protocol": {"role": "client"},
                },
            },
            "network_environment": {"type": "docker_compose"},
        }
        result = TestConfig.generate_default_description(test_data)
        assert "picoquic (server)" in result
        assert "aioquic (client)" in result
        assert "docker compose" in result

    def test_empty_services(self):
        assert TestConfig.generate_default_description({"services": {}}) == ""
        assert TestConfig.generate_default_description({}) == ""
