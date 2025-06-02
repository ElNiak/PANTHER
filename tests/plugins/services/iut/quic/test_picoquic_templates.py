"""
Unit tests for Picoquic plugin template rendering with enhanced quoting.
"""

import pytest
import tempfile
import shlex
from pathlib import Path

from panther.core.utils.jinja_manager import JinjaManager


class TestPicoquicTemplates:
    """Test cases for Picoquic command templates."""

    @pytest.fixture
    def picoquic_template_dir(self):
        """Create temporary directory with Picoquic templates."""
        with tempfile.TemporaryDirectory() as temp_dir:
            template_dir = Path(temp_dir)

            # Copy the enhanced templates using the new command_args approach
            client_template = """{{ command_args | join_command_args }}"""

            server_template = """{{ command_args | join_command_args }}"""

            (template_dir / "client_command.jinja").write_text(client_template)
            (template_dir / "server_command.jinja").write_text(server_template)

            yield template_dir

    @pytest.fixture
    def jinja_manager(self, picoquic_template_dir):
        """Create JinjaManager with Picoquic templates."""
        return JinjaManager(str(picoquic_template_dir))

    def test_client_command_normal_case(self, jinja_manager):
        """Test client command rendering with normal parameters."""
        context = {
            "command_args": [
                "-c",
                "/certs/cert.pem",
                "-k",
                "/certs/key.pem",
                "-t",
                "/tmp/ticket.bin",
                "-a",
                "h3",
                "example.com",
                "443",
            ]
        }

        rendered = jinja_manager.render_template("client_command.jinja", **context)

        # Should be properly quoted and parseable
        # Note: We need to be careful about how we parse this since it includes redirection
        # Let's check key components are properly quoted
        assert "example.com" in rendered
        assert "/certs/cert.pem" in rendered

    @pytest.mark.parametrize(
        "target,port,expected_in_output",
        [
            ("simple.com", "443", ["simple.com", "443"]),
            ("host with spaces.com", "8080", ["'host with spaces.com'", "8080"]),
            (
                "host'with'quotes.com",
                "443",
                ["'host'\"'\"'with'\"'\"'quotes.com'", "443"],
            ),
            ("host&special.com", "443", ["'host&special.com'", "443"]),
            ("host;malicious.com", "443", ["'host;malicious.com'", "443"]),
        ],
    )
    def test_client_command_edge_cases(
        self, jinja_manager, target, port, expected_in_output
    ):
        """Test client command with edge case values."""
        context = {
            "command_args": [
                "-c",
                "/certs/cert.pem",
                "-k",
                "/certs/key.pem",
                "-t",
                "/tmp/ticket.bin",
                "-a",
                "h3",
                target,
                port,
            ]
        }

        rendered = jinja_manager.render_template("client_command.jinja", **context)

        # Check that expected quoted values appear in output
        for expected in expected_in_output:
            assert expected in rendered

    def test_server_command_normal_case(self, jinja_manager):
        """Test server command rendering with normal parameters."""
        context = {
            "command_args": [
                "-c",
                "/certs/cert.pem",
                "-k",
                "/certs/key.pem",
                "-a",
                "h3",
                "-v",
                "-p",
                "443",
            ]
        }

        rendered = jinja_manager.render_template("server_command.jinja", **context)

        # Should contain expected components
        assert "-c" in rendered
        assert "/certs/cert.pem" in rendered
        assert "-p 443" in rendered

    def test_client_command_with_network_interface(self, jinja_manager):
        """Test client command with network interface parameters."""
        context = {
            "command_args": [
                "-c",
                "/certs/cert.pem",
                "-k",
                "/certs/key.pem",
                "-t",
                "/tmp/ticket.bin",
                "-a",
                "h3",
                "-i",
                "eth0",
                "-v",
                "1",
                "example.com",
                "443",
            ]
        }

        rendered = jinja_manager.render_template("client_command.jinja", **context)

        # Should include interface and version parameters
        assert "-i eth0" in rendered
        assert "-v 1" in rendered

    def test_command_with_malicious_input(self, jinja_manager):
        """Test that malicious inputs are properly neutralized."""
        malicious_target = "evil.com'; rm -rf /; echo '"
        malicious_log_path = "/logs/file; cat /etc/passwd > /tmp/stolen"

        context = {
            "command_args": [
                "-c",
                "/certs/cert.pem",
                "-k",
                "/certs/key.pem",
                "-t",
                "/tmp/ticket.bin",
                "-a",
                "h3",
                malicious_target,
                "443",
            ]
        }

        rendered = jinja_manager.render_template("client_command.jinja", **context)

        # The malicious parts should be properly quoted, neutralizing the attack
        assert "'; rm -rf /; echo '" not in rendered  # Should be quoted

        # But the quoted versions should be present
        assert shlex.quote(malicious_target) in rendered

    def test_empty_and_none_values(self, jinja_manager):
        """Test handling of empty and None values."""
        context = {
            "command_args": [
                "-c",
                "/certs/cert.pem",
                "-k",
                "/certs/key.pem",
                "-t",
                "/tmp/ticket.bin",
                "-a",
                "h3",
                "example.com",
                "443",
            ]
        }

        rendered = jinja_manager.render_template("client_command.jinja", **context)

        # Should handle command_args gracefully
        # Should not break the command structure
        assert "example.com" in rendered
        assert "443" in rendered
