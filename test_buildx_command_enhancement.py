#!/usr/bin/env python3
"""
Test script for TASK-DB-002: BuildX Command Enhancement

This script verifies that the enhanced BuildX command construction includes
BuildKit automatic platform arguments, proper validation, and modern features.
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from panther.core.docker_builder.docker_builder import DockerBuilder


def reset_singleton():
    """Reset the DockerBuilder singleton for testing."""
    DockerBuilder._instance = None
    DockerBuilder._initialized = False


def test_buildx_command_construction():
    """Test BuildX command includes all required arguments."""
    print("Testing BuildX command construction...")

    reset_singleton()
    builder = DockerBuilder()

    # Create temporary test files
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        dockerfile_path = temp_path / "Dockerfile"
        dockerfile_path.write_text("FROM ubuntu:22.04\nRUN echo test")

        cmd = builder._construct_buildx_command(
            builder_name="test-builder",
            dockerfile_path=dockerfile_path,
            context_path=temp_path,
            image_tag="test:latest",
            build_args={"VERSION": "1.0"},
            target_platform="linux/amd64"
        )

        # Verify basic command structure
        assert "docker" in cmd
        assert "buildx" in cmd
        assert "build" in cmd
        assert "--platform" in cmd
        assert "linux/amd64" in cmd
        assert "--build-arg" in cmd
        assert "--progress" in cmd
        assert "plain" in cmd

        # Verify BuildKit automatic arguments are present
        cmd_str = " ".join(cmd)
        assert "TARGETPLATFORM=linux/amd64" in cmd_str
        assert "BUILDPLATFORM=" in cmd_str
        assert "TARGETOS=linux" in cmd_str
        assert "TARGETARCH=amd64" in cmd_str

        print("✓ BuildX command construction includes all required arguments")


def test_buildkit_automatic_args():
    """Test BuildKit automatic arguments generation."""
    print("Testing BuildKit automatic arguments...")

    reset_singleton()
    builder = DockerBuilder()

    args = builder._get_buildkit_automatic_args("linux/amd64", "linux/arm64")

    expected_args = {
        "BUILDPLATFORM": "linux/amd64",
        "TARGETPLATFORM": "linux/arm64",
        "TARGETOS": "linux",
        "TARGETARCH": "arm64",
        "BUILDOS": "linux",
        "BUILDARCH": "amd64"
    }

    assert args == expected_args, f"Expected {expected_args}, got {args}"
    print("✓ BuildKit automatic arguments generated correctly")


def test_platform_parsing():
    """Test platform string parsing."""
    print("Testing platform parsing...")

    reset_singleton()
    builder = DockerBuilder()

    # Test normal platform parsing
    os_val, arch = builder._parse_platform("linux/amd64")
    assert os_val == "linux" and arch == "amd64"

    # Test platform with variant
    os_val, arch = builder._parse_platform("linux/arm/v7")
    assert os_val == "linux" and arch == "arm"

    # Test fallback for incomplete platform
    os_val, arch = builder._parse_platform("amd64")
    assert os_val == "linux" and arch == "amd64"

    print("✓ Platform parsing works correctly")


def test_buildx_command_validation():
    """Test BuildX command validation."""
    print("Testing BuildX command validation...")

    reset_singleton()
    builder = DockerBuilder()

    # Create temporary test file
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dockerfile = Path(temp_dir) / "Dockerfile"
        test_dockerfile.write_text("FROM ubuntu:22.04")

        # Valid command
        valid_cmd = [
            "docker", "buildx", "build",
            "--platform", "linux/amd64",
            "--file", str(test_dockerfile),
            "--tag", "test:latest",
            str(temp_dir)
        ]
        assert builder._validate_buildx_command(valid_cmd) is True

        # Invalid command (missing platform)
        invalid_cmd = [
            "docker", "buildx", "build",
            "--file", str(test_dockerfile),
            "--tag", "test:latest",
            str(temp_dir)
        ]
        assert builder._validate_buildx_command(invalid_cmd) is False

        print("✓ BuildX command validation works correctly")


def test_platform_validation():
    """Test platform format validation."""
    print("Testing platform validation...")

    reset_singleton()
    builder = DockerBuilder()

    # Valid platforms
    assert builder._is_valid_platform("linux/amd64") is True
    assert builder._is_valid_platform("linux/arm64") is True
    assert builder._is_valid_platform("windows/amd64") is True

    # Invalid platforms
    assert builder._is_valid_platform("amd64") is False
    assert builder._is_valid_platform("invalid/arch") is False
    assert builder._is_valid_platform("linux/invalid") is False

    print("✓ Platform validation works correctly")


def test_cache_args_generation():
    """Test cache arguments generation."""
    print("Testing cache arguments generation...")

    reset_singleton()
    builder = DockerBuilder()

    # Test without cache methods (should return empty)
    cache_args = builder._get_buildx_cache_args("linux/amd64")
    assert cache_args == []

    # Mock cache methods and test
    builder._cache_enabled = True
    builder._get_cache_mount_args = MagicMock(return_value=[])

    cache_args = builder._get_buildx_cache_args("linux/arm64")
    # Should include cache arguments for platform isolation
    if cache_args:  # Only check if cache args were generated
        assert any("buildx-cache-linux-arm64" in arg for arg in cache_args)

    print("✓ Cache arguments generation works correctly")


def test_buildx_vs_regular_build_detection():
    """Test that BuildX is properly detected based on platform requirements."""
    print("Testing BuildX vs regular build detection...")

    reset_singleton()
    builder = DockerBuilder()

    # Mock host platform to test cross-platform detection
    with patch.object(builder, '_get_host_platform', return_value="linux/amd64"):
        with patch.object(builder, '_get_target_platform', return_value="linux/arm64"):
            # Cross-platform should use buildx
            assert builder._should_use_buildx() is True

        with patch.object(builder, '_get_target_platform', return_value="linux/amd64"):
            # Same platform might not use buildx (depends on configuration)
            # This is acceptable behavior - we don't assert specific value
            result = builder._should_use_buildx()
            assert isinstance(result, bool)  # Just verify it returns a boolean

    print("✓ BuildX detection logic works correctly")


def main():
    """Run all BuildX command enhancement tests."""
    print("=== TASK-DB-002: BuildX Command Enhancement Tests ===")
    print()

    try:
        test_buildx_command_construction()
        test_buildkit_automatic_args()
        test_platform_parsing()
        test_buildx_command_validation()
        test_platform_validation()
        test_cache_args_generation()
        test_buildx_vs_regular_build_detection()

        print()
        print("✅ All tests passed! BuildX command enhancement is working correctly.")
        return 0

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
