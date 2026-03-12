"""CLI Test Suite.

Comprehensive test suite for the PANTHER CLI implementation.
Tests cover all commands, options, error handling, and workflows.

Test Structure:
- unit/: Unit tests for individual components
  - core/: Core CLI functionality (main, base utilities)
  - commands/: Individual command tests
  - utils/: Utility function tests
- integration/: Integration tests for complete workflows
- fixtures/: Test data and fixtures

Key Testing Features:
- Click CliRunner for command testing
- Comprehensive fixtures for different scenarios
- Mock adapters for argparse compatibility testing
- Error handling and edge case coverage
- Cross-platform compatibility testing
- Performance and timeout testing

Usage:
    # Run all tests
    pytest tests/cli/

    # Run unit tests only
    pytest tests/cli/unit/

    # Run integration tests only
    pytest tests/cli/integration/

    # Run specific command tests
    pytest tests/cli/unit/commands/test_config.py

    # Run with coverage
    pytest tests/cli/ --cov=panther.cli

    # Run with markers
    pytest tests/cli/ -m "not slow"
    pytest tests/cli/ -m "config"
"""

__version__ = "1.0.0"
__author__ = "PANTHER Team"

# Test configuration
TEST_CONFIG = {
    "timeout": 300,  # 5 minutes default timeout
    "temp_dir_prefix": "panther_cli_test_",
    "sample_configs": {
        "basic": "basic_test_config.yaml",
        "advanced": "advanced_test_config.yaml",
        "minimal": "minimal_test_config.yaml",
    },
}

# Common test patterns
COMMON_CLI_PATTERNS = {
    "success_indicators": ["✅", "success", "completed", "valid"],  # Success checkmark
    "error_indicators": ["❌", "error", "failed", "invalid"],  # Error X
    "warning_indicators": ["⚠️", "warning", "caution"],  # Warning triangle
    "info_indicators": ["ℹ️", "info", "note"],  # Info i
}

# Expected command structure
EXPECTED_COMMANDS = {
    "main": [
        "run",
        "config",
        "plugins",
        "create",
        "tutorial",
        "admin",
        "check",
        "metrics",
        "tools",
        "completion",
    ],
    "config": ["validate", "schema", "generate", "design"],
    "plugins": ["list", "install", "remove", "status", "validate"],
    "admin": ["status", "docker", "cleanup"],
    "tutorial": ["list", "run", "info"],
    "create": ["plugin", "test", "config"],
    "check": ["style", "security", "dependencies", "all"],
    "metrics": ["list", "analyze", "report", "config"],
    "tools": ["install-dev", "install-slim", "status"],
}

# Test data templates
TEST_TEMPLATES = {
    "minimal_config": {
        "logging": {"level": "INFO"},
        "tests": [
            {
                "name": "Test",
                "services": {
                    "server": {"implementation": {"name": "test", "type": "iut"}}
                },
            }
        ],
    },
    "full_config": {
        "logging": {"level": "INFO", "enable_colors": True},
        "observers": {"logger": {"enabled": True}},
        "paths": {"output_dir": "outputs"},
        "tests": [
            {
                "name": "Full Test",
                "description": "Complete test configuration",
                "network_environment": {"type": "docker_compose"},
                "services": {
                    "server": {
                        "implementation": {"name": "picoquic", "type": "iut"},
                        "protocol": {"name": "quic", "role": "server"},
                    },
                    "client": {
                        "implementation": {"name": "picoquic", "type": "iut"},
                        "protocol": {
                            "name": "quic",
                            "role": "client",
                            "target": "server",
                        },
                    },
                },
            }
        ],
    },
}
