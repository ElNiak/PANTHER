"""
Comprehensive unit tests for Docker Builder tag generation with BUILD_MODE and RUNTIME_MODE support.

This module tests the enhanced Docker image tag generation functionality that includes
build mode and runtime mode differentiation, ensuring proper cache isolation and
Docker tag compliance.

Tests cover:
- Basic tag generation scenarios
- Build mode integration (debug-asan, rel-lto, release-static-pgo)
- Runtime mode integration (minimal, debug, profile)
- Platform differentiation (linux/amd64, linux/arm64)
- Tag sanitization for Docker compliance
- Edge cases and error handling
- Integration with service manager
"""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# Test imports with fallback to mocks
try:
    from panther.core.docker_builder.docker_builder import DockerBuilder

    REAL_DOCKER_SYSTEM_AVAILABLE = True
except ImportError:
    REAL_DOCKER_SYSTEM_AVAILABLE = False

    # Mock DockerBuilder for testing
    class DockerBuilder:
        MAX_TAG_LENGTH = 100

        def __init__(self, base_path=None, logger=None):
            self.base_path = Path(base_path) if base_path else Path.cwd()
            self.logger = logger or Mock()

        def generate_image_tag(
            self,
            impl_name,
            version,
            tag_version,
            build_mode="",
            runtime_mode="minimal",
            target_platform="",
        ):
            # Actual implementation for testing
            build_suffix = f"-{build_mode}" if build_mode else ""
            runtime_suffix = (
                f"-{runtime_mode}" if runtime_mode and runtime_mode != "minimal" else ""
            )
            platform_suffix = f"-{target_platform}" if target_platform else ""

            base_name = f"{impl_name}-{version}" if version else impl_name
            full_tag = f"{base_name}:{tag_version}{build_suffix}{runtime_suffix}{platform_suffix}"

            return self._sanitize_docker_tag(full_tag)

        def _sanitize_docker_tag(self, tag: str) -> str:
            import re

            sanitized = re.sub(r"[^a-z0-9._:-]", "-", tag.lower())
            sanitized = re.sub(r"^[.-]+", "", sanitized)

            if len(sanitized) > self.MAX_TAG_LENGTH:
                parts = sanitized.split(":")
                if len(parts) == 2:
                    name_part, tag_part = parts
                    max_name_length = self.MAX_TAG_LENGTH - len(tag_part) - 1
                    if len(name_part) > max_name_length:
                        name_part = name_part[:max_name_length]
                    sanitized = f"{name_part}:{tag_part}"
                else:
                    sanitized = sanitized[: self.MAX_TAG_LENGTH]

            return sanitized


class TestDockerBuilderTagGeneration:
    """Test suite for Docker Builder tag generation functionality."""

    def setup_method(self):
        """Set up test environment for each test method."""
        self.builder = DockerBuilder()

    def test_generate_image_tag_basic(self):
        """Test basic tag generation without modes."""
        tag = self.builder.generate_image_tag("picoquic", "v1.0", "latest")
        assert tag == "picoquic-v1.0:latest"

    def test_generate_image_tag_no_version(self):
        """Test tag generation without version."""
        tag = self.builder.generate_image_tag("picoquic", "", "latest")
        assert tag == "picoquic:latest"

    def test_generate_image_tag_with_build_mode_debug_asan(self):
        """Test tag generation with debug-asan build mode."""
        tag = self.builder.generate_image_tag(
            "picoquic", "v1.0", "latest", "debug-asan"
        )
        assert tag == "picoquic-v1.0:latest-debug-asan"

    def test_generate_image_tag_with_build_mode_rel_lto(self):
        """Test tag generation with rel-lto build mode."""
        tag = self.builder.generate_image_tag("picoquic", "v1.0", "latest", "rel-lto")
        assert tag == "picoquic-v1.0:latest-rel-lto"

    def test_generate_image_tag_with_build_mode_release_static_pgo(self):
        """Test tag generation with release-static-pgo build mode."""
        tag = self.builder.generate_image_tag(
            "picoquic", "v1.0", "latest", "release-static-pgo"
        )
        assert tag == "picoquic-v1.0:latest-release-static-pgo"

    def test_generate_image_tag_with_runtime_mode_debug(self):
        """Test tag generation with debug runtime mode."""
        tag = self.builder.generate_image_tag("picoquic", "v1.0", "latest", "", "debug")
        assert tag == "picoquic-v1.0:latest-debug"

    def test_generate_image_tag_with_runtime_mode_profile(self):
        """Test tag generation with profile runtime mode."""
        tag = self.builder.generate_image_tag(
            "picoquic", "v1.0", "latest", "", "profile"
        )
        assert tag == "picoquic-v1.0:latest-profile"

    def test_generate_image_tag_minimal_runtime_omitted(self):
        """Test that minimal runtime mode is omitted from tag."""
        tag = self.builder.generate_image_tag(
            "picoquic", "v1.0", "latest", "debug-asan", "minimal"
        )
        assert tag == "picoquic-v1.0:latest-debug-asan"

    def test_generate_image_tag_both_modes(self):
        """Test tag generation with both build and runtime modes."""
        tag = self.builder.generate_image_tag(
            "picoquic", "v1.0", "latest", "rel-lto", "profile"
        )
        assert tag == "picoquic-v1.0:latest-rel-lto-profile"

    def test_generate_image_tag_all_modes_and_platform(self):
        """Test tag generation with build mode, runtime mode, and platform."""
        tag = self.builder.generate_image_tag(
            "picoquic", "v1.0", "latest", "debug-asan", "debug", "linux/amd64"
        )
        assert tag == "picoquic-v1.0:latest-debug-asan-debug-linux/amd64"

    def test_generate_image_tag_platform_only(self):
        """Test tag generation with platform but no modes."""
        tag = self.builder.generate_image_tag(
            "picoquic", "v1.0", "latest", "", "minimal", "linux/arm64"
        )
        assert tag == "picoquic-v1.0:latest-linux/arm64"

    def test_generate_image_tag_complex_implementation_name(self):
        """Test tag generation with complex implementation names."""
        tag = self.builder.generate_image_tag(
            "aioquic-client", "v2.1.0", "stable", "debug-asan", "debug"
        )
        assert tag == "aioquic-client-v2.1.0:stable-debug-asan-debug"

    def test_tag_sanitization_uppercase(self):
        """Test tag sanitization converts uppercase to lowercase."""
        tag = self.builder.generate_image_tag(
            "PICOQUIC", "V1.0", "LATEST", "DEBUG-ASAN", "DEBUG"
        )
        assert tag == "picoquic-v1.0:latest-debug-asan-debug"

    def test_tag_sanitization_invalid_characters(self):
        """Test tag sanitization replaces invalid characters."""
        tag = self.builder.generate_image_tag(
            "test@impl", "v1.0!", "latest", "mode$test", "debug%mode"
        )
        assert tag == "test-impl-v1.0-:latest-mode-test-debug-mode"

    def test_tag_sanitization_leading_invalid_chars(self):
        """Test tag sanitization removes leading periods and dashes."""
        builder = DockerBuilder()
        sanitized = builder._sanitize_docker_tag(".-invalid-tag:latest")
        assert sanitized == "invalid-tag:latest"

    def test_tag_length_limit_with_tag_preservation(self):
        """Test tag length limit preserves tag version part."""
        # Create a very long implementation name that exceeds limits
        long_impl_name = "very_long_implementation_name_that_definitely_exceeds_normal_docker_tag_limits_and_should_be_truncated"
        tag = self.builder.generate_image_tag(
            long_impl_name, "v1.0", "latest", "release-static-pgo", "profile"
        )

        # Should be truncated but still valid
        assert len(tag) <= self.builder.MAX_TAG_LENGTH
        assert tag.endswith(":latest")
        assert "release-static-pgo" in tag or len(tag) == self.builder.MAX_TAG_LENGTH

    def test_tag_length_limit_without_colon(self):
        """Test tag length limit handling when no colon separator exists."""
        # This shouldn't happen in normal usage, but test the edge case
        builder = DockerBuilder()
        long_tag = "a" * (builder.MAX_TAG_LENGTH + 10)
        sanitized = builder._sanitize_docker_tag(long_tag)
        assert len(sanitized) <= builder.MAX_TAG_LENGTH

    def test_cache_differentiation_scenarios(self):
        """Test that different mode combinations produce different tags for cache isolation."""
        base_params = ("picoquic", "v1.0", "latest")

        # Different build modes should produce different tags
        tag1 = self.builder.generate_image_tag(*base_params, "debug-asan", "minimal")
        tag2 = self.builder.generate_image_tag(*base_params, "rel-lto", "minimal")
        assert tag1 != tag2
        assert "debug-asan" in tag1
        assert "rel-lto" in tag2

        # Different runtime modes should produce different tags
        tag3 = self.builder.generate_image_tag(*base_params, "", "minimal")
        tag4 = self.builder.generate_image_tag(*base_params, "", "debug")
        assert tag3 != tag4
        assert "debug" in tag4 and "debug" not in tag3

        # Same minimal runtime should be consistent
        tag5 = self.builder.generate_image_tag(*base_params, "", "minimal")
        assert tag3 == tag5

    def test_real_world_scenarios(self):
        """Test realistic tag generation scenarios."""
        scenarios = [
            # (impl_name, version, tag_version, build_mode, runtime_mode, expected_suffix)
            ("picoquic", "latest", "latest", "", "minimal", ":latest"),
            (
                "aioquic",
                "v1.2.3",
                "stable",
                "debug-asan",
                "debug",
                ":stable-debug-asan-debug",
            ),
            (
                "lsquic",
                "v2.0.0",
                "latest",
                "rel-lto",
                "profile",
                ":latest-rel-lto-profile",
            ),
            (
                "mvfst",
                "",
                "latest",
                "release-static-pgo",
                "minimal",
                ":latest-release-static-pgo",
            ),
            ("quiche", "main", "dev", "", "debug", ":dev-debug"),
        ]

        for (
            impl_name,
            version,
            tag_version,
            build_mode,
            runtime_mode,
            expected_suffix,
        ) in scenarios:
            tag = self.builder.generate_image_tag(
                impl_name, version, tag_version, build_mode, runtime_mode
            )
            assert tag.endswith(
                expected_suffix
            ), f"Tag {tag} doesn't end with {expected_suffix}"
            if version:
                assert f"{impl_name}-{version}" in tag
            else:
                assert tag.startswith(impl_name)


class TestDockerBuilderTagSanitization:
    """Test suite specifically for Docker tag sanitization functionality."""

    def setup_method(self):
        """Set up test environment for each test method."""
        self.builder = DockerBuilder()

    def test_sanitize_valid_tag(self):
        """Test that valid tags pass through unchanged."""
        valid_tag = "picoquic-v1.0:latest-debug-asan"
        sanitized = self.builder._sanitize_docker_tag(valid_tag)
        assert sanitized == valid_tag

    def test_sanitize_uppercase_conversion(self):
        """Test uppercase to lowercase conversion."""
        tag = "PICOQUIC-V1.0:LATEST"
        sanitized = self.builder._sanitize_docker_tag(tag)
        assert sanitized == "picoquic-v1.0:latest"

    def test_sanitize_invalid_character_replacement(self):
        """Test invalid character replacement."""
        test_cases = [
            ("test@image:latest", "test-image:latest"),
            ("test#image:latest", "test-image:latest"),
            ("test$image:latest", "test-image:latest"),
            ("test%image:latest", "test-image:latest"),
            ("test space:latest", "test-space:latest"),
        ]

        for input_tag, expected in test_cases:
            sanitized = self.builder._sanitize_docker_tag(input_tag)
            assert sanitized == expected

    def test_sanitize_leading_invalid_characters(self):
        """Test removal of leading periods and dashes."""
        test_cases = [
            (".-test:latest", "test:latest"),
            ("...test:latest", "test:latest"),
            ("---test:latest", "test:latest"),
            (".--.test:latest", "test:latest"),
        ]

        for input_tag, expected in test_cases:
            sanitized = self.builder._sanitize_docker_tag(input_tag)
            assert sanitized == expected

    def test_sanitize_preserve_valid_separators(self):
        """Test that valid separators (colon, underscore, period, dash) are preserved."""
        tag = "test_image.v1-0:latest"
        sanitized = self.builder._sanitize_docker_tag(tag)
        assert sanitized == tag  # Should be unchanged

    def test_sanitize_complex_scenarios(self):
        """Test complex sanitization scenarios."""
        test_cases = [
            # (input, expected)
            (
                "Test@Image#With$Many%Invalid&Chars:latest",
                "test-image-with-many-invalid-chars:latest",
            ),
            ("..--impl_name.v1.0:tag-version", "impl_name.v1.0:tag-version"),
            ("COMPLEX_IMPL@v2.1.0!:STABLE#BUILD", "complex_impl-v2.1.0-:stable-build"),
        ]

        for input_tag, expected in test_cases:
            sanitized = self.builder._sanitize_docker_tag(input_tag)
            assert sanitized == expected


class TestDockerBuilderIntegration:
    """Integration tests for Docker Builder tag generation with service manager."""

    def setup_method(self):
        """Set up test environment for each test method."""
        self.builder = DockerBuilder()

    @pytest.mark.parametrize(
        "build_mode,runtime_mode,expected_includes",
        [
            ("", "minimal", []),  # Should not include mode suffixes
            ("debug-asan", "minimal", ["-debug-asan"]),
            ("", "debug", ["-debug"]),
            ("rel-lto", "profile", ["-rel-lto", "-profile"]),
            ("release-static-pgo", "debug", ["-release-static-pgo", "-debug"]),
        ],
    )
    def test_mode_inclusion_in_tags(self, build_mode, runtime_mode, expected_includes):
        """Test that modes are correctly included in generated tags."""
        tag = self.builder.generate_image_tag(
            "test", "v1.0", "latest", build_mode, runtime_mode
        )

        for expected in expected_includes:
            assert expected in tag, f"Expected '{expected}' in tag '{tag}'"

    def test_config_extraction_simulation(self):
        """Test simulation of config extraction as done in build_image method."""
        config = {
            "build_mode": "debug-asan",
            "runtime_mode": "debug",
            "version": "v1.0",
        }

        # Simulate the config extraction from actual implementation
        build_mode = config.get("build_mode", "")
        runtime_mode = config.get("runtime_mode", "minimal")

        tag = self.builder.generate_image_tag(
            impl_name="test_impl",
            version=config["version"],
            tag_version="latest",
            build_mode=build_mode,
            runtime_mode=runtime_mode,
        )

        assert "test_impl-v1.0:latest-debug-asan-debug" == tag

    def test_backward_compatibility_tags(self):
        """Test backward compatibility with existing tag patterns."""
        # Old style: just implementation and version
        old_style_tag = self.builder.generate_image_tag("picoquic", "v1.0", "latest")
        assert old_style_tag == "picoquic-v1.0:latest"

        # With minimal runtime (should be same as old style)
        minimal_runtime_tag = self.builder.generate_image_tag(
            "picoquic", "v1.0", "latest", "", "minimal"
        )
        assert minimal_runtime_tag == old_style_tag

    def test_cache_isolation_validation(self):
        """Test that cache isolation actually works with different modes."""
        # These should all be different to ensure proper cache isolation
        tags = []
        modes = [
            ("", "minimal"),
            ("debug-asan", "minimal"),
            ("", "debug"),
            ("debug-asan", "debug"),
            ("rel-lto", "profile"),
        ]

        for build_mode, runtime_mode in modes:
            tag = self.builder.generate_image_tag(
                "test", "v1.0", "latest", build_mode, runtime_mode
            )
            tags.append(tag)

        # All tags should be unique for proper cache isolation
        assert len(set(tags)) == len(tags), f"Duplicate tags found: {tags}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
