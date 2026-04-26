#!/usr/bin/env python3
"""
Quick E2E test to validate that our test service works with real PANTHER.

This is a minimal test that runs a real PANTHER experiment using our test service
to verify the E2E setup is working correctly.
"""

import subprocess
import tempfile
from pathlib import Path

import yaml


def create_minimal_config():
    """Create a minimal test configuration."""
    config = {
        "logging": {"level": "INFO"},
        "observers": {
            "logger": {"enabled": True, "log_level": "INFO"},
            "storage": {"enabled": True},
        },
        "paths": {"output_dir": "test_outputs"},
        "docker": {"build_docker_image": True},
        "tests": [
            {
                "name": "Quick E2E Test",
                "description": "Minimal test to validate E2E setup",
                "network_environment": {"type": "docker_compose"},
                "services": {
                    "quick_test": {
                        "implementation": {
                            "name": "test_output_service",
                            "type": "iut",
                            "runtime_seconds": 2,
                            "create_additional_files": False,
                        },
                        "protocol": {
                            "name": "quic",
                            "version": "rfc9000",
                            "role": "server",
                        },
                        "timeout": 20,
                    }
                },
                "steps": {"wait": 5},
            }
        ],
    }
    return config


def main():
    """Run quick E2E test."""
    print("🚀 Quick E2E Test - Real PANTHER with Test Service")
    print("=" * 50)

    # Create temporary config
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        config = create_minimal_config()
        yaml.dump(config, f)
        config_file = f.name

    try:
        print(f"📝 Created test config: {config_file}")

        # Run PANTHER
        cmd = ["python", "-m", "panther", "--experiment-config", config_file, "--debug"]

        print(f"🔄 Running: {' '.join(cmd)}")

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120  # 2 minute timeout
        )

        print(f"📊 PANTHER exit code: {result.returncode}")

        if result.returncode == 0:
            print("✅ SUCCESS: PANTHER experiment completed!")
            print("\nKey output lines:")
            for line in result.stdout.split("\n"):
                if any(
                    keyword in line
                    for keyword in [
                        "test_output_service",
                        "SUCCESS",
                        "completed",
                        "ERROR",
                    ]
                ):
                    print(f"  {line}")
        else:
            print("❌ FAILURE: PANTHER experiment failed")
            print("STDOUT:")
            print(result.stdout)
            print("STDERR:")
            print(result.stderr)

        return result.returncode

    except subprocess.TimeoutExpired:
        print("⏰ TIMEOUT: Experiment took too long")
        return 1
    except Exception as e:
        print(f"💥 ERROR: {e}")
        return 1
    finally:
        # Cleanup
        Path(config_file).unlink(missing_ok=True)


if __name__ in {"__main__", "__mp_main__"}:
    exit(main())
