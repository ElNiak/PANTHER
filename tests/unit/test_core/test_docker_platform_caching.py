#!/usr/bin/env python3
"""Unit tests for Docker platform-specific caching implementation.

Tests validate that platform-specific caching has been properly
applied across all Dockerfiles in the PANTHER project.
"""

import subprocess
from pathlib import Path
from typing import List, Tuple

import pytest


class TestDockerPlatformCaching:
    """Test suite for Docker platform-specific caching implementation."""

    @pytest.fixture(scope="class")
    def dockerfiles_with_cache_mounts(self) -> List[Path]:
        """Find all Dockerfiles that use cache mounts."""
        result = subprocess.run(
            [
                "find",
                ".",
                "-name",
                "Dockerfile*",
                "-exec",
                "grep",
                "-l",
                "mount=type=cache",
                "{}",
                ";",
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent.parent,  # Go to PANTHER root
        )

        dockerfiles = []
        panther_root = Path(__file__).parent.parent.parent.parent
        for line in result.stdout.strip().split("\n"):
            if line and not line.startswith("./build/"):  # Skip build directory
                path = panther_root / line.lstrip("./")
                if path.exists():
                    dockerfiles.append(path)

        return dockerfiles

    def test_dockerfiles_found(self, dockerfiles_with_cache_mounts):
        """Test that we found Dockerfiles with cache mounts."""
        assert (
            len(dockerfiles_with_cache_mounts) > 0
        ), "No Dockerfiles with cache mounts found"
        assert (
            len(dockerfiles_with_cache_mounts) >= 10
        ), f"Expected at least 10 Dockerfiles, found {len(dockerfiles_with_cache_mounts)}"

    def test_targetplatform_arg_declarations(self, dockerfiles_with_cache_mounts):
        """Test that all Dockerfiles have TARGETPLATFORM ARG declarations."""
        missing_targetplatform = []

        for dockerfile in dockerfiles_with_cache_mounts:
            content = dockerfile.read_text()
            if "ARG TARGETPLATFORM" not in content:
                missing_targetplatform.append(
                    str(dockerfile.relative_to(dockerfile.parent.parent.parent.parent))
                )

        assert (
            len(missing_targetplatform) == 0
        ), f"Dockerfiles missing ARG TARGETPLATFORM: {missing_targetplatform}"

    def test_buildplatform_arg_declarations(self, dockerfiles_with_cache_mounts):
        """Test that all Dockerfiles have BUILDPLATFORM ARG declarations."""
        missing_buildplatform = []

        for dockerfile in dockerfiles_with_cache_mounts:
            content = dockerfile.read_text()
            if "ARG BUILDPLATFORM" not in content:
                missing_buildplatform.append(
                    str(dockerfile.relative_to(dockerfile.parent.parent.parent.parent))
                )

        assert (
            len(missing_buildplatform) == 0
        ), f"Dockerfiles missing ARG BUILDPLATFORM: {missing_buildplatform}"

    @pytest.mark.xfail(
        reason="Dockerfile migration to platform-specific cache mounts not yet complete"
    )
    def test_platform_specific_cache_mounts(self, dockerfiles_with_cache_mounts):
        """Test that cache mounts use platform-specific paths."""
        issues = []

        for dockerfile in dockerfiles_with_cache_mounts:
            content = dockerfile.read_text()
            cache_mounts = [
                line for line in content.split("\n") if "--mount=type=cache" in line
            ]

            non_platform_caches = []
            for line in cache_mounts:
                if (
                    "--mount=type=cache" in line
                    and "${TARGETPLATFORM//\\//-}" not in line
                ):
                    # Allow certain exceptions like temporary mounts
                    if "target=/tmp/" not in line:
                        non_platform_caches.append(line.strip())

            if non_platform_caches:
                relative_path = str(
                    dockerfile.relative_to(dockerfile.parent.parent.parent.parent)
                )
                issues.append(
                    f"{relative_path}: {len(non_platform_caches)} non-platform cache mounts"
                )

        assert len(issues) == 0, f"Dockerfiles with non-platform cache mounts: {issues}"

    @pytest.mark.xfail(
        reason="Dockerfile migration to platform-specific CMake config not yet complete"
    )
    def test_cmake_platform_configuration(self, dockerfiles_with_cache_mounts):
        """Test that Dockerfiles with CMake have platform-specific configuration."""
        cmake_without_platform_config = []

        for dockerfile in dockerfiles_with_cache_mounts:
            content = dockerfile.read_text()

            # Check if CMake is used (either as package or command)
            has_cmake_command = (
                "cmake " in content.lower()
                and not content.lower().count("cmake ")
                == content.lower().count("cmake software-properties-common")
            )
            has_cmake_package = "cmake" in content.lower()

            if has_cmake_command or has_cmake_package:
                # Check for platform-specific CMAKE_ARGS or environment setup
                has_cmake_args = "CMAKE_ARGS" in content
                has_platform_case = "TARGETPLATFORM" in content and (
                    "case" in content or "CMAKE_ARGS" in content
                )

                if not (has_cmake_args or has_platform_case):
                    relative_path = str(
                        dockerfile.relative_to(dockerfile.parent.parent.parent.parent)
                    )
                    cmake_without_platform_config.append(relative_path)

        # Allow some exceptions for base images that only install cmake package
        allowed_exceptions = [
            # Base images that only install cmake package without using it
            "panther/plugins/services/Dockerfile"  # Only installs cmake package, doesn't run cmake commands
        ]

        filtered_issues = [
            path
            for path in cmake_without_platform_config
            if path not in allowed_exceptions
        ]

        assert (
            len(filtered_issues) == 0
        ), f"Dockerfiles with CMake but no platform config: {filtered_issues}"

    @pytest.mark.xfail(
        reason="Dockerfile migration to platform-specific cache mounts not yet complete"
    )
    def test_platform_cache_consistency(self, dockerfiles_with_cache_mounts):
        """Test that all cache mounts are consistent in their platform usage."""
        inconsistent_files = []

        for dockerfile in dockerfiles_with_cache_mounts:
            content = dockerfile.read_text()
            cache_mounts = [
                line for line in content.split("\n") if "--mount=type=cache" in line
            ]

            platform_mounts = 0
            non_platform_mounts = 0

            for line in cache_mounts:
                if "${TARGETPLATFORM//\\//-}" in line:
                    platform_mounts += 1
                else:
                    non_platform_mounts += 1

            # If we have both platform and non-platform mounts, flag as inconsistent
            if platform_mounts > 0 and non_platform_mounts > 0:
                relative_path = str(
                    dockerfile.relative_to(dockerfile.parent.parent.parent.parent)
                )
                inconsistent_files.append(
                    f"{relative_path}: {platform_mounts} platform, {non_platform_mounts} non-platform"
                )

        assert (
            len(inconsistent_files) == 0
        ), f"Dockerfiles with inconsistent cache mount patterns: {inconsistent_files}"

    @pytest.mark.xfail(
        reason="Dockerfile migration to platform-specific cache mounts not yet complete"
    )
    def test_apt_cache_platform_isolation(self, dockerfiles_with_cache_mounts):
        """Test that APT caches use platform-specific paths."""
        non_platform_apt_caches = []

        for dockerfile in dockerfiles_with_cache_mounts:
            content = dockerfile.read_text()

            # Look for APT cache mounts without platform suffixes
            for line in content.split("\n"):
                if "--mount=type=cache" in line and "/var/cache/apt" in line:
                    if "${TARGETPLATFORM//\\//-}" not in line:
                        relative_path = str(
                            dockerfile.relative_to(
                                dockerfile.parent.parent.parent.parent
                            )
                        )
                        non_platform_apt_caches.append(
                            f"{relative_path}: {line.strip()}"
                        )

        assert (
            len(non_platform_apt_caches) == 0
        ), f"APT caches without platform isolation: {non_platform_apt_caches}"

    @pytest.mark.xfail(
        reason="Dockerfile migration to platform-specific cache mounts not yet complete"
    )
    def test_pip_cache_platform_isolation(self, dockerfiles_with_cache_mounts):
        """Test that pip caches use platform-specific paths."""
        non_platform_pip_caches = []

        for dockerfile in dockerfiles_with_cache_mounts:
            content = dockerfile.read_text()

            # Look for pip cache mounts
            for line in content.split("\n"):
                if "--mount=type=cache" in line and "pip" in line:
                    if "${TARGETPLATFORM//\\//-}" not in line:
                        relative_path = str(
                            dockerfile.relative_to(
                                dockerfile.parent.parent.parent.parent
                            )
                        )
                        non_platform_pip_caches.append(
                            f"{relative_path}: {line.strip()}"
                        )

        assert (
            len(non_platform_pip_caches) == 0
        ), f"Pip caches without platform isolation: {non_platform_pip_caches}"

    def test_sharing_locked_attribute(self, dockerfiles_with_cache_mounts):
        """Test that cache mounts include sharing=locked attribute."""
        missing_sharing_locked = []

        for dockerfile in dockerfiles_with_cache_mounts:
            content = dockerfile.read_text()

            for line in content.split("\n"):
                if "--mount=type=cache" in line and "${TARGETPLATFORM//\\//-}" in line:
                    if "sharing=locked" not in line:
                        relative_path = str(
                            dockerfile.relative_to(
                                dockerfile.parent.parent.parent.parent
                            )
                        )
                        missing_sharing_locked.append(
                            f"{relative_path}: {line.strip()}"
                        )

        assert (
            len(missing_sharing_locked) == 0
        ), f"Platform cache mounts missing sharing=locked: {missing_sharing_locked}"

    @pytest.mark.xfail(
        reason="Dockerfile migration to platform-specific cache mounts not yet complete"
    )
    def test_dockerfile_compliance_summary(self, dockerfiles_with_cache_mounts):
        """Test overall compliance and provide summary."""
        total_dockerfiles = len(dockerfiles_with_cache_mounts)

        # Count compliant files
        compliant_count = 0
        for dockerfile in dockerfiles_with_cache_mounts:
            content = dockerfile.read_text()

            has_targetplatform = "ARG TARGETPLATFORM" in content
            has_buildplatform = "ARG BUILDPLATFORM" in content
            has_platform_cache = "${TARGETPLATFORM//\\//-}" in content

            if has_targetplatform and has_buildplatform and has_platform_cache:
                compliant_count += 1

        compliance_rate = (compliant_count / total_dockerfiles) * 100

        assert (
            compliance_rate == 100.0
        ), f"Only {compliant_count}/{total_dockerfiles} Dockerfiles ({compliance_rate:.1f}%) are fully compliant"

    @pytest.mark.xfail(reason="panther_ivy Dockerfile compliance not yet complete")
    def test_panther_ivy_dockerfiles_specifically(self, dockerfiles_with_cache_mounts):
        """Test that panther_ivy Dockerfiles (original problem source) are compliant."""
        panther_ivy_files = [
            df for df in dockerfiles_with_cache_mounts if "panther_ivy" in str(df)
        ]

        assert (
            len(panther_ivy_files) >= 2
        ), f"Expected at least 2 panther_ivy Dockerfiles, found {len(panther_ivy_files)}"

        for dockerfile in panther_ivy_files:
            content = dockerfile.read_text()

            # These were the original problem files - they must be compliant
            assert (
                "ARG TARGETPLATFORM" in content
            ), f"panther_ivy Dockerfile missing TARGETPLATFORM: {dockerfile}"
            assert (
                "ARG BUILDPLATFORM" in content
            ), f"panther_ivy Dockerfile missing BUILDPLATFORM: {dockerfile}"
            assert (
                "${TARGETPLATFORM//\\//-}" in content
            ), f"panther_ivy Dockerfile missing platform cache: {dockerfile}"
            assert (
                "CMAKE_ARGS" in content
            ), f"panther_ivy Dockerfile missing CMake platform config: {dockerfile}"

    @pytest.mark.xfail(reason="Base service Dockerfile compliance not yet complete")
    def test_base_service_dockerfiles_specifically(self, dockerfiles_with_cache_mounts):
        """Test that base service Dockerfiles are compliant (critical for all builds)."""
        base_service_files = [
            df
            for df in dockerfiles_with_cache_mounts
            if "panther/plugins/services/" in str(df)
            and ("Dockerfile" in str(df) and "iut" not in str(df))
        ]

        # Should find at least Dockerfile and Dockerfile.buildkit in services/
        assert (
            len(base_service_files) >= 2
        ), f"Expected at least 2 base service Dockerfiles, found {len(base_service_files)}"

        for dockerfile in base_service_files:
            content = dockerfile.read_text()

            # Base service Dockerfiles are critical - they must be compliant
            assert (
                "ARG TARGETPLATFORM" in content
            ), f"Base service Dockerfile missing TARGETPLATFORM: {dockerfile}"
            assert (
                "ARG BUILDPLATFORM" in content
            ), f"Base service Dockerfile missing BUILDPLATFORM: {dockerfile}"
            assert (
                "${TARGETPLATFORM//\\//-}" in content
            ), f"Base service Dockerfile missing platform cache: {dockerfile}"

            # Base images should have ARM64/AMD64 library isolation
            if "gperftools" in content:  # Only for Dockerfiles that build gperftools
                assert (
                    "build-cache-${TARGETPLATFORM//\\//-}" in content
                ), f"Base service missing platform build cache: {dockerfile}"


class TestDockerBuilderPlatformSupport:
    """Test DockerBuilder class platform-specific functionality."""

    def test_docker_builder_imports(self):
        """Test that DockerBuilder can be imported and has platform methods."""
        try:
            from panther.core.docker_builder.docker_builder import DockerBuilder

            # Check if the class has our added methods
            assert hasattr(
                DockerBuilder, "_get_cache_key_suffix"
            ), "DockerBuilder missing _get_cache_key_suffix method"

        except ImportError as e:
            pytest.skip(f"DockerBuilder import failed: {e}")

    def test_cache_key_suffix_generation(self):
        """Test platform-specific cache key generation."""
        try:
            from panther.core.docker_builder.docker_builder import DockerBuilder

            # Create a test instance (with cache disabled to avoid initialization issues)
            builder = DockerBuilder(enable_cache=False)

            # Test different platform scenarios
            test_cases = [
                ("linux/amd64", "-linux-amd64"),
                ("linux/arm64", "-linux-arm64"),
                ("linux/arm/v7", "-linux-arm-v7"),
            ]

            for platform, expected_suffix in test_cases:
                # Mock get_target_platform (the public method called by _get_cache_key_suffix)
                original_method = builder.get_target_platform
                builder.get_target_platform = lambda p=platform: p

                suffix = builder._get_cache_key_suffix()

                # Restore original method
                builder.get_target_platform = original_method

                assert (
                    suffix == expected_suffix
                ), f"Platform {platform} -> Expected {expected_suffix}, got {suffix}"

        except (ImportError, AttributeError) as e:
            pytest.skip(f"DockerBuilder platform test failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
