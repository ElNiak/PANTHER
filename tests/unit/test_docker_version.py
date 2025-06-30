#!/usr/bin/env python3
"""Test script to demonstrate Docker version checking."""

import sys
from unittest.mock import patch, MagicMock

# Add current directory to path to import panther_builder
sys.path.insert(0, ".")


def test_docker_version_check():
    """Test different Docker version scenarios."""

    print("=== Testing Docker Version Checking ===\n")

    # Test 1: Normal case (should work with real Docker)
    print("1. Testing with real Docker installation:")
    try:
        from panther_builder import BuildManager

        BuildManager()
        print("✅ Real Docker test completed\n")
    except Exception as e:
        print(f"❌ Real Docker test failed: {e}\n")

    # Test 2: Mock old Docker version
    print("2. Testing with old Docker version (26.0.0):")
    with patch("docker.from_env") as mock_docker:
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_client.version.return_value = {"Version": "26.0.0"}
        mock_docker.return_value = mock_client

        try:
            # Reload the module to test with mocked Docker
            import importlib
            import panther_builder

            importlib.reload(panther_builder)

            panther_builder.BuildManager()
            print("✅ Old Docker version test completed\n")
        except Exception as e:
            print(f"❌ Old Docker version test failed: {e}\n")

    # Test 3: Mock Docker not available
    print("3. Testing with Docker not available:")
    with patch("docker.from_env", side_effect=Exception("Docker not available")):
        try:
            import importlib
            import panther_builder

            importlib.reload(panther_builder)

            panther_builder.BuildManager()
            print("✅ No Docker test completed\n")
        except Exception as e:
            print(f"❌ No Docker test failed: {e}\n")


if __name__ == "__main__":
    test_docker_version_check()
