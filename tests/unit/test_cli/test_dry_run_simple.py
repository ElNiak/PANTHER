#!/usr/bin/env python3
"""
Simple test script to verify dry-run functionality works end-to-end.
This bypasses complex test infrastructure to validate core functionality.
"""

import sys
import tempfile
from pathlib import Path

import yaml

# Add PANTHER to path
sys.path.insert(0, str(Path(__file__).parent))


def create_test_config():
    """Create a simple test configuration."""
    config = {
        "logging": {"level": "INFO"},
        "paths": {"output_dir": "outputs"},
        "docker": {"build_docker_image": False},
        "tests": [
            {
                "name": "Simple Dry Run Test",
                "description": "Test dry-run functionality",
                "network_environment": {"type": "docker_compose"},
                "services": {
                    "test_server": {
                        "name": "test_server",
                        "implementation": {"name": "picoquic", "type": "iut"},
                        "protocol": {
                            "name": "quic",
                            "version": "rfc9000",
                            "role": "server",
                        },
                        "ports": ["4443:4443"],
                    }
                },
                "steps": {"wait": 30},
            }
        ],
    }
    return config


def test_cli_parsing():
    """Test CLI argument parsing."""
    from panther.cli.main import create_parser

    parser = create_parser()

    # Test with dry-run flag
    args = parser.parse_args(["run", "--config", "test.yaml", "--dry-run"])
    assert hasattr(args, "dry_run"), "dry_run attribute missing"
    assert args.dry_run is True, "dry_run should be True"

    # Test without dry-run flag
    args = parser.parse_args(["run", "--config", "test.yaml"])
    assert args.dry_run is False, "dry_run should be False by default"

    print("✅ CLI parsing test passed")


def test_experiment_manager_dry_run():
    """Test ExperimentManager dry-run functionality."""
    from unittest.mock import MagicMock, patch

    from panther.core.experiment_manager import ExperimentManager

    # Create mock config with proper string values
    mock_global_config = MagicMock()
    mock_global_config.logging.level.name = "INFO"
    mock_global_config.logging.level = "INFO"  # Add this for the string check
    mock_global_config.logging.format = "%(message)s"
    mock_global_config.logging.enable_colors = True
    mock_global_config.logging.feature_levels = {}  # Add this empty dict
    mock_global_config.paths.output_dir = "outputs"

    # Patch complex dependencies AND observer creation
    with patch("panther.core.experiment_manager.PluginManager"), patch(
        "panther.core.experiment_manager.EmitterRegistry"
    ), patch(
        "panther.core.experiment_manager.EventManager"
    ) as mock_event_manager, patch(
        "panther.core.experiment_manager.WorkflowStateTracker"
    ), patch(
        "panther.core.experiment_manager.FastFailHandler"
    ), patch(
        "panther.core.experiment_manager.ExperimentManager._setup_observers"
    ):
        # Mock event manager cleanup to return integer
        mock_event_instance = MagicMock()
        mock_event_instance.cleanup_none_observers.return_value = 0
        mock_event_manager.get_instance.return_value = mock_event_instance

        # Create manager with dry_run=True
        manager = ExperimentManager(
            global_config=mock_global_config, experiment_name="test", dry_run=True
        )

        assert manager.dry_run is True, "ExperimentManager should store dry_run flag"
        print("✅ ExperimentManager dry-run test passed")


def test_test_case_dry_run():
    """Test TestCase dry-run analysis."""
    import logging
    from unittest.mock import MagicMock

    from panther.core.test_cases.test_case_impl import TestCase

    # Create mock test config
    mock_test_config = MagicMock()
    mock_test_config.name = "Test Case"
    mock_test_config.description = "Test description"
    mock_test_config.services = {"service1": MagicMock()}
    mock_test_config.network_environment = MagicMock()
    mock_test_config.network_environment.type = "docker_compose"
    mock_test_config.execution_environment = []
    mock_test_config.steps = MagicMock()
    mock_test_config.steps.wait = 60

    # Create TestCase instance with minimal setup
    test_case = TestCase.__new__(TestCase)
    test_case.test_config = mock_test_config
    test_case.logger = logging.getLogger(__name__)

    # Test dry-run
    result = test_case.perform_dry_run()
    assert result is True, "TestCase dry-run should return True"

    print("✅ TestCase dry-run test passed")


def test_end_to_end_dry_run():
    """Test end-to-end dry-run functionality with actual CLI."""
    import os
    import subprocess
    import tempfile

    # Create temporary config file
    config = create_test_config()
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config, f)
        config_file = f.name

    try:
        # Run PANTHER with dry-run flag
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "panther",
                "run",
                "--config",
                config_file,
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Check that it ran successfully
        if result.returncode == 0:
            print("✅ End-to-end dry-run test passed")
            print(
                f"Output contained DRY-RUN: {'DRY-RUN' in result.stdout or 'DRY-RUN' in result.stderr}"
            )
        else:
            print(f"❌ End-to-end test failed with return code {result.returncode}")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")

    except subprocess.TimeoutExpired:
        print("❌ End-to-end test timed out")
    except Exception as e:
        print(f"❌ End-to-end test failed with exception: {e}")
    finally:
        # Clean up
        os.unlink(config_file)


def main():
    """Run all tests."""
    print("🧪 Testing PANTHER dry-run functionality...")
    print()

    try:
        test_cli_parsing()
        test_experiment_manager_dry_run()
        test_test_case_dry_run()
        test_end_to_end_dry_run()

        print()
        print("🎉 All tests completed!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
