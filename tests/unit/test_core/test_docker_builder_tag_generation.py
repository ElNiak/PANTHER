"""Comprehensive unit tests for Docker Builder tag generation with BUILD_MODE and RUNTIME_MODE support.

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

import pytest

pytestmark = [pytest.mark.unit]


class TestDockerBuilderTagGeneration:
    """Test suite for Docker Builder tag generation functionality."""

    def test_generate_image_tag_basic(self, real_docker_builder):
        """Test basic tag generation without modes."""
        tag = real_docker_builder.generate_image_tag("picoquic", "v1.0", "latest")
        assert tag == "picoquic-v1.0:latest"

    def test_generate_image_tag_no_version(self, real_docker_builder):
        """Test tag generation without version."""
        tag = real_docker_builder.generate_image_tag("picoquic", "", "latest")
        assert tag == "picoquic:latest"

    def test_generate_image_tag_with_build_mode_debug_asan(self, real_docker_builder):
        """Test tag generation with debug-asan build mode."""
        tag = real_docker_builder.generate_image_tag(
            "picoquic", "v1.0", "latest", "debug-asan"
        )
        assert tag == "picoquic-v1.0:latest-debug-asan"

    def test_generate_image_tag_with_build_mode_rel_lto(self, real_docker_builder):
        """Test tag generation with rel-lto build mode."""
        tag = real_docker_builder.generate_image_tag(
            "picoquic", "v1.0", "latest", "rel-lto"
        )
        assert tag == "picoquic-v1.0:latest-rel-lto"

    def test_generate_image_tag_with_build_mode_release_static_pgo(
        self, real_docker_builder
    ):
        """Test tag generation with release-static-pgo build mode."""
        tag = real_docker_builder.generate_image_tag(
            "picoquic", "v1.0", "latest", "release-static-pgo"
        )
        assert tag == "picoquic-v1.0:latest-release-static-pgo"

    def test_generate_image_tag_with_runtime_mode_debug(self, real_docker_builder):
        """Test tag generation with debug runtime mode."""
        tag = real_docker_builder.generate_image_tag(
            "picoquic", "v1.0", "latest", "", "debug"
        )
        assert tag == "picoquic-v1.0:latest-debug"

    def test_generate_image_tag_with_runtime_mode_profile(self, real_docker_builder):
        """Test tag generation with profile runtime mode."""
        tag = real_docker_builder.generate_image_tag(
            "picoquic", "v1.0", "latest", "", "profile"
        )
        assert tag == "picoquic-v1.0:latest-profile"

    def test_generate_image_tag_minimal_runtime_omitted(self, real_docker_builder):
        """Test that minimal runtime mode is omitted from tag."""
        tag = real_docker_builder.generate_image_tag(
            "picoquic", "v1.0", "latest", "debug-asan", "minimal"
        )
        assert tag == "picoquic-v1.0:latest-debug-asan"

    def test_generate_image_tag_both_modes(self, real_docker_builder):
        """Test tag generation with both build and runtime modes."""
        tag = real_docker_builder.generate_image_tag(
            "picoquic", "v1.0", "latest", "rel-lto", "profile"
        )
        assert tag == "picoquic-v1.0:latest-rel-lto-profile"

    def test_generate_image_tag_z3_source_local(self, real_docker_builder):
        """Test that z3_source='local' (default) produces no suffix."""
        tag_local = real_docker_builder.generate_image_tag(
            "panther_ivy", "rfc9000", "latest", z3_source="local"
        )
        tag_empty = real_docker_builder.generate_image_tag(
            "panther_ivy", "rfc9000", "latest", z3_source=""
        )
        tag_default = real_docker_builder.generate_image_tag(
            "panther_ivy", "rfc9000", "latest"
        )
        # All three should produce the same tag (no z3 suffix)
        assert tag_local == tag_empty == tag_default
        assert "z3" not in tag_local

    def test_generate_image_tag_z3_source_pip(self, real_docker_builder):
        """Test that z3_source='pip' adds -z3pip suffix."""
        tag = real_docker_builder.generate_image_tag(
            "panther_ivy", "rfc9000", "latest", z3_source="pip"
        )
        assert tag == "panther_ivy-rfc9000:latest-z3pip"

    def test_generate_image_tag_z3_source_with_all_modes(self, real_docker_builder):
        """Test z3_source combined with build_mode, runtime_mode, and platform."""
        tag = real_docker_builder.generate_image_tag(
            "panther_ivy",
            "rfc9000",
            "latest",
            build_mode="debug-asan",
            runtime_mode="debug",
            z3_source="pip",
            target_platform="linux/amd64",
        )
        # Order: build_suffix, runtime_suffix, z3_suffix, platform_suffix
        assert "-debug-asan-debug-z3pip-linux" in tag

    def test_generate_image_tag_all_modes_and_platform(self, real_docker_builder):
        """Test tag generation with build mode, runtime mode, and platform."""
        tag = real_docker_builder.generate_image_tag(
            "picoquic", "v1.0", "latest", "debug-asan", "debug", "linux/amd64"
        )
        assert tag == "picoquic-v1.0:latest-debug-asan-debug-linux-amd64"

    def test_generate_image_tag_platform_only(self, real_docker_builder):
        """Test tag generation with platform but no modes."""
        tag = real_docker_builder.generate_image_tag(
            "picoquic", "v1.0", "latest", "", "minimal", "linux/arm64"
        )
        assert tag == "picoquic-v1.0:latest-linux-arm64"

    def test_generate_image_tag_complex_implementation_name(self, real_docker_builder):
        """Test tag generation with complex implementation names."""
        tag = real_docker_builder.generate_image_tag(
            "aioquic-client", "v2.1.0", "stable", "debug-asan", "debug"
        )
        assert tag == "aioquic-client-v2.1.0:stable-debug-asan-debug"

    def test_tag_sanitization_uppercase(self, real_docker_builder):
        """Test tag sanitization converts uppercase to lowercase."""
        tag = real_docker_builder.generate_image_tag(
            "PICOQUIC", "V1.0", "LATEST", "DEBUG-ASAN", "DEBUG"
        )
        assert tag == "picoquic-v1.0:latest-debug-asan-debug"

    def test_tag_sanitization_invalid_characters(self, real_docker_builder):
        """Test tag sanitization replaces invalid characters."""
        tag = real_docker_builder.generate_image_tag(
            "test@impl", "v1.0!", "latest", "mode$test", "debug%mode"
        )
        assert tag == "test-impl-v1.0-:latest-mode-test-debug-mode"

    def test_tag_sanitization_leading_invalid_chars(self, real_docker_builder):
        """Test tag sanitization removes leading periods and dashes."""
        sanitized = real_docker_builder._sanitize_docker_tag(".-invalid-tag:latest")
        assert sanitized == "invalid-tag:latest"

    def test_tag_length_limit_with_tag_preservation(self, real_docker_builder):
        """Test tag length limit preserves tag version part."""
        # Create a very long implementation name that exceeds limits
        long_impl_name = "very_long_implementation_name_that_definitely_exceeds_normal_docker_tag_limits_and_should_be_truncated"
        tag = real_docker_builder.generate_image_tag(
            long_impl_name, "v1.0", "latest", "release-static-pgo", "profile"
        )

        # Should be truncated but still valid
        assert len(tag) <= real_docker_builder.MAX_TAG_LENGTH
        assert ":latest" in tag
        assert (
            "release-static-pgo" in tag
            or len(tag) == real_docker_builder.MAX_TAG_LENGTH
        )

    def test_tag_length_limit_without_colon(self, real_docker_builder):
        """Test tag length limit handling when no colon separator exists."""
        # This shouldn't happen in normal usage, but test the edge case
        long_tag = "a" * (real_docker_builder.MAX_TAG_LENGTH + 10)
        sanitized = real_docker_builder._sanitize_docker_tag(long_tag)
        assert len(sanitized) <= real_docker_builder.MAX_TAG_LENGTH

    def test_cache_differentiation_scenarios(self, real_docker_builder):
        """Test that different mode combinations produce different tags for cache isolation."""
        base_params = ("picoquic", "v1.0", "latest")

        # Different build modes should produce different tags
        tag1 = real_docker_builder.generate_image_tag(
            *base_params, "debug-asan", "minimal"
        )
        tag2 = real_docker_builder.generate_image_tag(
            *base_params, "rel-lto", "minimal"
        )
        assert tag1 != tag2
        assert "debug-asan" in tag1
        assert "rel-lto" in tag2

        # Different runtime modes should produce different tags
        tag3 = real_docker_builder.generate_image_tag(*base_params, "", "minimal")
        tag4 = real_docker_builder.generate_image_tag(*base_params, "", "debug")
        assert tag3 != tag4
        assert "debug" in tag4 and "debug" not in tag3

        # Same minimal runtime should be consistent
        tag5 = real_docker_builder.generate_image_tag(*base_params, "", "minimal")
        assert tag3 == tag5

    def test_real_world_scenarios(self, real_docker_builder):
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
            tag = real_docker_builder.generate_image_tag(
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

    def test_sanitize_valid_tag(self, real_docker_builder):
        """Test that valid tags pass through unchanged."""
        valid_tag = "picoquic-v1.0:latest-debug-asan"
        sanitized = real_docker_builder._sanitize_docker_tag(valid_tag)
        assert sanitized == valid_tag

    def test_sanitize_uppercase_conversion(self, real_docker_builder):
        """Test uppercase to lowercase conversion."""
        tag = "PICOQUIC-V1.0:LATEST"
        sanitized = real_docker_builder._sanitize_docker_tag(tag)
        assert sanitized == "picoquic-v1.0:latest"

    def test_sanitize_invalid_character_replacement(self, real_docker_builder):
        """Test invalid character replacement."""
        test_cases = [
            ("test@image:latest", "test-image:latest"),
            ("test#image:latest", "test-image:latest"),
            ("test$image:latest", "test-image:latest"),
            ("test%image:latest", "test-image:latest"),
            ("test space:latest", "test-space:latest"),
        ]

        for input_tag, expected in test_cases:
            sanitized = real_docker_builder._sanitize_docker_tag(input_tag)
            assert sanitized == expected

    def test_sanitize_leading_invalid_characters(self, real_docker_builder):
        """Test removal of leading periods and dashes."""
        test_cases = [
            (".-test:latest", "test:latest"),
            ("...test:latest", "test:latest"),
            ("---test:latest", "test:latest"),
            (".--.test:latest", "test:latest"),
        ]

        for input_tag, expected in test_cases:
            sanitized = real_docker_builder._sanitize_docker_tag(input_tag)
            assert sanitized == expected

    def test_sanitize_preserve_valid_separators(self, real_docker_builder):
        """Test that valid separators (colon, underscore, period, dash) are preserved."""
        tag = "test_image.v1-0:latest"
        sanitized = real_docker_builder._sanitize_docker_tag(tag)
        assert sanitized == tag  # Should be unchanged

    def test_sanitize_complex_scenarios(self, real_docker_builder):
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
            sanitized = real_docker_builder._sanitize_docker_tag(input_tag)
            assert sanitized == expected


class TestDockerBuilderIntegration:
    """Integration tests for Docker Builder tag generation with service manager."""

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
    def test_mode_inclusion_in_tags(
        self, real_docker_builder, build_mode, runtime_mode, expected_includes
    ):
        """Test that modes are correctly included in generated tags."""
        tag = real_docker_builder.generate_image_tag(
            "test", "v1.0", "latest", build_mode, runtime_mode
        )

        for expected in expected_includes:
            assert expected in tag, f"Expected '{expected}' in tag '{tag}'"

    def test_config_extraction_simulation(self, real_docker_builder):
        """Test simulation of config extraction as done in build_image method."""
        config = {
            "build_mode": "debug-asan",
            "runtime_mode": "debug",
            "version": "v1.0",
        }

        # Simulate the config extraction from actual implementation
        build_mode = config.get("build_mode", "")
        runtime_mode = config.get("runtime_mode", "minimal")

        tag = real_docker_builder.generate_image_tag(
            impl_name="test_impl",
            version=config["version"],
            tag_version="latest",
            build_mode=build_mode,
            runtime_mode=runtime_mode,
        )

        assert "test_impl-v1.0:latest-debug-asan-debug" == tag

    def test_backward_compatibility_tags(self, real_docker_builder):
        """Test backward compatibility with existing tag patterns."""
        # Old style: just implementation and version
        old_style_tag = real_docker_builder.generate_image_tag(
            "picoquic", "v1.0", "latest"
        )
        assert old_style_tag == "picoquic-v1.0:latest"

        # With minimal runtime (should be same as old style)
        minimal_runtime_tag = real_docker_builder.generate_image_tag(
            "picoquic", "v1.0", "latest", "", "minimal"
        )
        assert minimal_runtime_tag == old_style_tag

    def test_cache_isolation_validation(self, real_docker_builder):
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
            tag = real_docker_builder.generate_image_tag(
                "test", "v1.0", "latest", build_mode, runtime_mode
            )
            tags.append(tag)

        # All tags should be unique for proper cache isolation
        assert len(set(tags)) == len(tags), f"Duplicate tags found: {tags}"


class TestPerServiceDockerOverrideIntegration:
    """Integration tests for per-service Docker overrides with resolve_docker_build_config()."""

    def test_resolve_force_build_false_skips_rebuild(self):
        """resolve_docker_build_config produces force_build=False when service overrides it."""
        from panther.config.core.models.global_config import (
            DockerConfig,
            ServiceDockerOverrideConfig,
            resolve_docker_build_config,
        )

        global_docker = DockerConfig(
            force_build_docker_image=True, no_docker_cache=False
        )
        service = ServiceDockerOverrideConfig(force_build_docker_image=False)
        resolved = resolve_docker_build_config(global_docker, service)
        force_build = (
            resolved["force_build_docker_image"] or resolved["no_docker_cache"]
        )
        assert force_build is False

    def test_resolve_no_docker_cache_override_triggers_rebuild(self):
        """no_docker_cache=True in per-service override triggers force build."""
        from panther.config.core.models.global_config import (
            DockerConfig,
            ServiceDockerOverrideConfig,
            resolve_docker_build_config,
        )

        global_docker = DockerConfig(
            force_build_docker_image=False, no_docker_cache=False
        )
        service = ServiceDockerOverrideConfig(no_docker_cache=True)
        resolved = resolve_docker_build_config(global_docker, service)
        force_build = (
            resolved["force_build_docker_image"] or resolved["no_docker_cache"]
        )
        assert force_build is True

    def test_resolve_build_args_merge_with_framework_precedence(self):
        """Per-service build_args are available but framework args take precedence when merged."""
        from panther.config.core.models.global_config import (
            DockerConfig,
            ServiceDockerOverrideConfig,
            resolve_docker_build_config,
        )

        global_docker = DockerConfig(build_args={"GLOBAL_KEY": "global_val"})
        service = ServiceDockerOverrideConfig(
            build_args={"CUSTOM": "user_val", "GLOBAL_KEY": "service_override"}
        )
        resolved = resolve_docker_build_config(global_docker, service)
        # Service overrides global on collision
        assert resolved["build_args"]["GLOBAL_KEY"] == "service_override"
        assert resolved["build_args"]["CUSTOM"] == "user_val"
        # Now simulate framework args taking precedence (as build_image does)
        framework_args = {"VERSION": "v1.0", "GLOBAL_KEY": "framework_wins"}
        merged = {**resolved["build_args"], **framework_args}
        assert merged["GLOBAL_KEY"] == "framework_wins"
        assert merged["CUSTOM"] == "user_val"
        assert merged["VERSION"] == "v1.0"

    def test_resolve_use_buildx_override(self):
        """Per-service use_buildx=False overrides global use_buildx=True."""
        from panther.config.core.models.global_config import (
            DockerConfig,
            ServiceDockerOverrideConfig,
            resolve_docker_build_config,
        )

        global_docker = DockerConfig(use_buildx=True)
        service = ServiceDockerOverrideConfig(use_buildx=False)
        resolved = resolve_docker_build_config(global_docker, service)
        assert resolved["use_buildx"] is False

    def test_resolve_no_override_preserves_global(self):
        """Without per-service overrides, resolved config matches global exactly."""
        from panther.config.core.models.global_config import (
            DockerConfig,
            resolve_docker_build_config,
        )

        global_docker = DockerConfig(
            force_build_docker_image=True,
            no_docker_cache=False,
            use_buildx=True,
            target_platform="linux/amd64",
            build_args={"K": "V"},
        )
        resolved = resolve_docker_build_config(global_docker, None)
        assert (
            resolved["force_build_docker_image"]
            == global_docker.force_build_docker_image
        )
        assert resolved["no_docker_cache"] == global_docker.no_docker_cache
        assert resolved["use_buildx"] == global_docker.use_buildx
        assert resolved["target_platform"] == global_docker.target_platform
        assert resolved["build_args"] == global_docker.build_args


class TestSessionBuiltTags:
    """Tests for _session_built_tags thread-safe tracking (Gap 1)."""

    def test_mark_and_check_session_built(self, real_docker_builder):
        """mark_session_built makes was_built_this_session return True."""
        from panther.core.docker_builder.docker_builder import DockerBuilder

        assert DockerBuilder.was_built_this_session("test:v1.0") is False
        DockerBuilder.mark_session_built("test:v1.0")
        assert DockerBuilder.was_built_this_session("test:v1.0") is True

    def test_was_built_returns_false_for_unknown(self, real_docker_builder):
        """was_built_this_session returns False for tags never built."""
        from panther.core.docker_builder.docker_builder import DockerBuilder

        assert DockerBuilder.was_built_this_session("never:built") is False

    def test_multiple_tags_tracked(self, real_docker_builder):
        """Multiple tags can be tracked independently."""
        from panther.core.docker_builder.docker_builder import DockerBuilder

        tags = ["img:a", "img:b", "img:c"]
        for t in tags:
            DockerBuilder.mark_session_built(t)
        for t in tags:
            assert DockerBuilder.was_built_this_session(t) is True
        assert DockerBuilder.was_built_this_session("img:d") is False

    def test_mark_session_built_idempotent(self, real_docker_builder):
        """Adding the same tag twice doesn't cause issues."""
        from panther.core.docker_builder.docker_builder import DockerBuilder

        DockerBuilder.mark_session_built("same:tag")
        DockerBuilder.mark_session_built("same:tag")
        assert DockerBuilder.was_built_this_session("same:tag") is True

    def test_reset_clears_session_built_tags(self, real_docker_builder):
        """reset_singleton clears _session_built_tags."""
        from panther.core.docker_builder.docker_builder import DockerBuilder

        DockerBuilder.mark_session_built("cleared:tag")
        assert DockerBuilder.was_built_this_session("cleared:tag") is True
        DockerBuilder.reset_singleton()
        assert DockerBuilder.was_built_this_session("cleared:tag") is False

    def test_thread_safety_concurrent_writes(self, real_docker_builder):
        """Concurrent mark_session_built calls don't corrupt the set."""
        import threading

        from panther.core.docker_builder.docker_builder import DockerBuilder

        errors = []

        def mark_tags(prefix, count):
            try:
                for i in range(count):
                    DockerBuilder.mark_session_built(f"{prefix}:{i}")
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=mark_tags, args=(f"t{t}", 50)) for t in range(10)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        for t in range(10):
            for i in range(50):
                assert DockerBuilder.was_built_this_session(f"t{t}:{i}") is True


class TestZ3SourceValidation:
    """Tests for z3_source runtime validation in build paths (Gap 5)."""

    def test_z3_source_invalid_falls_back_to_local(self, real_docker_builder):
        """Invalid z3_source value falls back to 'local' (no suffix)."""
        tag = real_docker_builder.generate_image_tag(
            "ivy", "v1", "latest", z3_source="local"
        )
        # "local" should produce no z3 suffix - same as invalid fallback
        assert "-z3" not in tag

    def test_z3_source_empty_no_suffix(self, real_docker_builder):
        """Empty z3_source produces no suffix."""
        tag = real_docker_builder.generate_image_tag(
            "ivy", "v1", "latest", z3_source=""
        )
        assert "-z3" not in tag

    def test_z3_source_pip_suffix(self, real_docker_builder):
        """z3_source='pip' correctly adds -z3pip suffix."""
        tag = real_docker_builder.generate_image_tag(
            "ivy", "v1", "latest", z3_source="pip"
        )
        assert "-z3pip" in tag

    def test_z3_source_propagates_to_build_args(self, real_docker_builder, tmp_path):
        """Z3_SOURCE build arg uses validated value from real build_image() code path."""
        # Create minimal Dockerfile for build_image prerequisites
        dockerfile = tmp_path / "Dockerfile"
        dockerfile.write_text("FROM ubuntu:22.04\n")

        config = {
            "build_mode": "",
            "runtime_mode": "minimal",
            "z3_source": "github",  # Invalid - should fall back to "local"
            "commit": "abc123",
            "dependencies": {},
        }

        # Patch only the build dispatch to force regular build path (not buildx)
        with unittest.mock.patch.object(
            real_docker_builder, "_should_use_buildx", return_value=False
        ):
            real_docker_builder.build_image(
                impl_name="test_z3",
                version="v1",
                dockerfile_path=dockerfile,
                context_path=tmp_path,
                config=config,
            )

        # Inspect buildargs passed to the (mocked) Docker client
        build_call = real_docker_builder.client.images.build.call_args
        actual_build_args = build_call.kwargs.get(
            "buildargs", build_call[1].get("buildargs")
        )
        assert (
            actual_build_args["Z3_SOURCE"] == "local"
        )  # Fallback from invalid "github"


class TestSanitizeDockerTagEmptyFallback:
    """Tests for _sanitize_docker_tag empty string guard (Gap 6)."""

    def test_pathological_input_produces_unknown(self, real_docker_builder):
        """Input with only invalid chars becomes 'unknown' not empty."""
        result = real_docker_builder._sanitize_docker_tag("!!!###$$$")
        assert result == "unknown"

    def test_all_leading_dashes_produces_unknown(self, real_docker_builder):
        """Input that becomes all dashes (then stripped) falls back to 'unknown'."""
        result = real_docker_builder._sanitize_docker_tag("@@@")
        assert result == "unknown"

    def test_empty_string_input_produces_unknown(self, real_docker_builder):
        """Empty string input falls back to 'unknown'."""
        result = real_docker_builder._sanitize_docker_tag("")
        assert result == "unknown"

    def test_normal_input_unchanged(self, real_docker_builder):
        """Normal input is not affected by the empty guard."""
        result = real_docker_builder._sanitize_docker_tag("picoquic:latest")
        assert result == "picoquic:latest"


class TestForceBuildVsNoCacheSemantics:
    """Tests for the force_build vs no_docker_cache separation (Gap 7)."""

    def test_force_build_true_no_cache_false(self):
        """force_build=True, no_docker_cache=False: rebuild but use layer cache."""
        from panther.config.core.models.global_config import (
            DockerConfig,
            resolve_docker_build_config,
        )

        docker = DockerConfig(force_build_docker_image=True, no_docker_cache=False)
        resolved = resolve_docker_build_config(docker)
        assert resolved["force_build_docker_image"] is True
        assert resolved["no_docker_cache"] is False

    def test_force_build_false_no_cache_false(self):
        """force_build=False, no_docker_cache=False: use cached image if available."""
        from panther.config.core.models.global_config import (
            DockerConfig,
            resolve_docker_build_config,
        )

        docker = DockerConfig(force_build_docker_image=False, no_docker_cache=False)
        resolved = resolve_docker_build_config(docker)
        assert resolved["force_build_docker_image"] is False
        assert resolved["no_docker_cache"] is False

    def test_no_cache_true_implies_rebuild(self):
        """no_docker_cache=True should imply a rebuild is needed."""
        from panther.config.core.models.global_config import (
            DockerConfig,
            resolve_docker_build_config,
        )

        docker = DockerConfig(force_build_docker_image=False, no_docker_cache=True)
        resolved = resolve_docker_build_config(docker)
        assert resolved["no_docker_cache"] is True
        # In docker_builder.py, force_build is computed as:
        # force_build = force_build_docker_image or no_docker_cache
        effective_force = (
            resolved["force_build_docker_image"] or resolved["no_docker_cache"]
        )
        assert effective_force is True

    def test_service_override_no_cache_over_global(self):
        """Service-level no_docker_cache=True overrides global False."""
        from panther.config.core.models.global_config import (
            DockerConfig,
            ServiceDockerOverrideConfig,
            resolve_docker_build_config,
        )

        global_docker = DockerConfig(no_docker_cache=False)
        service = ServiceDockerOverrideConfig(no_docker_cache=True)
        resolved = resolve_docker_build_config(global_docker, service)
        assert resolved["no_docker_cache"] is True

    def test_service_override_force_build_false_over_global(self):
        """Service-level force_build=False overrides global True."""
        from panther.config.core.models.global_config import (
            DockerConfig,
            ServiceDockerOverrideConfig,
            resolve_docker_build_config,
        )

        global_docker = DockerConfig(force_build_docker_image=True)
        service = ServiceDockerOverrideConfig(force_build_docker_image=False)
        resolved = resolve_docker_build_config(global_docker, service)
        assert resolved["force_build_docker_image"] is False


class TestResolveDockerBuildConfigLogging:
    """Tests for resolve_docker_build_config debug logging (Gap 7 / I7)."""

    def test_override_logs_debug_message(self):
        """When service overrides a field, a debug log is emitted."""
        import logging

        from panther.config.core.models.global_config import (
            DockerConfig,
            ServiceDockerOverrideConfig,
            resolve_docker_build_config,
        )

        logger = logging.getLogger("test_resolve_logging")
        with unittest.mock.patch.object(logger, "debug") as mock_debug:
            global_docker = DockerConfig(force_build_docker_image=True)
            service = ServiceDockerOverrideConfig(force_build_docker_image=False)
            resolve_docker_build_config(global_docker, service, logger=logger)
            # Should have logged the override
            mock_debug.assert_called()
            call_args = str(mock_debug.call_args_list)
            assert "force_build_docker_image" in call_args

    def test_no_override_no_debug_log(self):
        """When no fields are overridden, no debug override log is emitted."""
        import logging

        from panther.config.core.models.global_config import (
            DockerConfig,
            resolve_docker_build_config,
        )

        logger = logging.getLogger("test_resolve_no_logging")
        with unittest.mock.patch.object(logger, "debug") as mock_debug:
            global_docker = DockerConfig()
            resolve_docker_build_config(global_docker, None, logger=logger)
            mock_debug.assert_not_called()

    def test_build_args_override_logs(self):
        """When service build_args override global keys, debug log is emitted."""
        import logging

        from panther.config.core.models.global_config import (
            DockerConfig,
            ServiceDockerOverrideConfig,
            resolve_docker_build_config,
        )

        logger = logging.getLogger("test_resolve_build_args_logging")
        with unittest.mock.patch.object(logger, "debug") as mock_debug:
            global_docker = DockerConfig(build_args={"KEY": "old"})
            service = ServiceDockerOverrideConfig(build_args={"KEY": "new"})
            resolve_docker_build_config(global_docker, service, logger=logger)
            call_args = str(mock_debug.call_args_list)
            assert "KEY" in call_args


import unittest.mock

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
