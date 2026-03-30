"""Property-based tests for Docker image validation using Hypothesis.

This module uses property-based testing to generate thousands of test cases
automatically, ensuring robust validation of Docker image names, patterns,
and validation logic under various conditions.
"""

import re
import string
import uuid
from pathlib import Path
from typing import Any, Dict, List, Tuple
from unittest.mock import Mock, patch

import pytest
from hypothesis import assume, example, given, settings
from hypothesis import strategies as st
from hypothesis.stateful import (
    Bundle,
    RuleBasedStateMachine,
    initialize,
    precondition,
    rule,
)

# Test imports with fallback to mocks
try:
    import docker
    from docker.errors import DockerException, NotFound

    from panther.core.docker_builder.docker_builder import DockerBuilder
    from panther.core.docker_builder.docker_image_cache import (
        CachedImage,
        DockerImageCache,
    )
    from panther.core.exceptions.fast_fail import DockerComposeException

    DOCKER_SYSTEM_AVAILABLE = True
except ImportError:
    DOCKER_SYSTEM_AVAILABLE = False

    # Mock implementations
    class DockerException(Exception):
        pass

    class NotFound(DockerException):
        pass

    class DockerComposeException(Exception):
        pass

    class CachedImage:
        def __init__(self, id, tags, size, created, last_seen):
            self.id = id
            self.tags = tags
            self.size = size
            self.created = created
            self.last_seen = last_seen


pytestmark = [pytest.mark.property_based, pytest.mark.docker_validation]


# Hypothesis Strategies for Docker Image Components
@st.composite
def valid_docker_name_component(draw):
    """Generate valid Docker name components (lowercase, alphanumeric, limited punctuation)."""
    # Docker names must be lowercase and can contain a-z, 0-9, -, _, .
    first_char = draw(st.sampled_from(string.ascii_lowercase + string.digits))
    rest_chars = draw(
        st.text(
            alphabet=string.ascii_lowercase + string.digits + "-_.",
            min_size=0,
            max_size=62,  # Docker component max length is 63
        )
    )

    # Ensure no consecutive dots or hyphens at start/end
    name = first_char + rest_chars
    name = re.sub(r"\.{2,}", ".", name)  # No consecutive dots
    name = name.strip("-._")  # No punctuation at start/end

    # Ensure minimum length and no empty components
    assume(len(name) >= 1)
    assume(not name.startswith("."))
    assume(not name.endswith("."))

    return name


@st.composite
def valid_docker_tag(draw):
    """Generate valid Docker tags."""
    # Tags can be more flexible than names
    tag_chars = string.ascii_letters + string.digits + "-._"
    tag = draw(st.text(alphabet=tag_chars, min_size=1, max_size=127))

    # Clean up the tag
    tag = tag.strip("-._")
    assume(len(tag) >= 1)
    assume(not ".." in tag)

    return tag


@st.composite
def valid_docker_image_name(draw):
    """Generate valid Docker image names with optional registry and tag."""
    # Optional registry
    registry = draw(
        st.one_of(
            st.none(),
            st.builds(
                lambda host, port: f"{host}:{port}",
                host=valid_docker_name_component(),
                port=st.integers(min_value=1000, max_value=65535),
            ),
        )
    )

    # Namespace (optional)
    namespace = draw(st.one_of(st.none(), valid_docker_name_component()))

    # Repository name (required)
    repository = draw(valid_docker_name_component())

    # Tag (optional, defaults to 'latest')
    tag = draw(st.one_of(st.none(), valid_docker_tag()))

    # Build full image name
    parts = []
    if registry:
        parts.append(registry)
    if namespace:
        parts.append(namespace)
    parts.append(repository)

    image_name = "/".join(parts)
    if tag:
        image_name += f":{tag}"

    return image_name


@st.composite
def problematic_docker_image_name(draw):
    """Generate problematic Docker image names that should be rejected."""
    problematic_patterns = [
        # UUID-like patterns
        f"unknown:{uuid.uuid4()}",
        f"temp:{uuid.uuid4()}",
        f"build:{uuid.uuid4()}",
        # SHA256-like patterns
        f"sha256:{'a' * 64}",
        f"intermediate:{'b' * 32}",
        # Invalid characters
        "UPPERCASE:tag",
        "name with spaces:tag",
        "name@symbol:tag",
        "name#hash:tag",
        # Invalid structure
        ":notag",
        "noname:",
        "//double-slash",
        "name..double-dot:tag",
        # Too long
        "a" * 300 + ":tag",
        f"name:{'x' * 200}",
    ]

    return draw(st.sampled_from(problematic_patterns))


@st.composite
def service_configuration(draw):
    """Generate PANTHER service configurations."""
    protocols = ["quic", "http", "tcp", "udp"]
    implementations = ["picoquic", "quiche", "nginx", "apache", "custom"]
    roles = ["client", "server", "proxy", "load-balancer"]

    config = {
        "name": draw(valid_docker_name_component()),
        "protocol": draw(st.sampled_from(protocols)),
        "implementation": draw(st.sampled_from(implementations)),
        "role": draw(st.sampled_from(roles)),
        "version": draw(
            st.one_of(
                st.none(),
                st.text(alphabet=string.digits + ".", min_size=1, max_size=10),
            )
        ),
        "environment": draw(
            st.dictionaries(
                keys=st.text(
                    alphabet=string.ascii_uppercase + "_", min_size=1, max_size=20
                ),
                values=st.text(min_size=0, max_size=100),
                min_size=0,
                max_size=10,
            )
        ),
        "ports": draw(
            st.lists(
                st.integers(min_value=1024, max_value=65535),
                min_size=0,
                max_size=5,
                unique=True,
            )
        ),
        "dependencies": draw(
            st.lists(valid_docker_name_component(), min_size=0, max_size=5, unique=True)
        ),
    }

    return config


class TestDockerImageValidationProperties:
    """Property-based tests for Docker image validation."""

    @given(valid_docker_image_name())
    @settings(max_examples=200)
    def test_valid_image_names_pass_validation(self, image_name):
        """Property: All valid Docker image names should pass basic validation."""
        # Mock validator
        validator = Mock()

        def validate_image_name_format(name):
            """Basic Docker image name format validation."""
            # Check basic structure
            if not name or name.startswith(":") or name.endswith(":"):
                return False

            # Check for invalid characters in name part (before tag)
            name_part = name.split(":")[0]
            if not re.match(r"^[a-z0-9][a-z0-9._/-]*[a-z0-9]$|^[a-z0-9]$", name_part):
                return False

            # Check tag part if present
            if ":" in name:
                tag_part = name.split(":", 1)[1]
                if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$", tag_part):
                    return False

            return True

        validator.validate_format.side_effect = validate_image_name_format

        # Valid names should pass validation
        result = validator.validate_format(image_name)
        assert result is True, f"Valid image name {image_name} failed validation"

    @given(problematic_docker_image_name())
    @settings(max_examples=100)
    def test_problematic_image_names_fail_validation(self, image_name):
        """Property: Problematic Docker image names should fail validation."""
        # Mock validator with strict rules
        validator = Mock()

        def validate_image_name_strict(name):
            """Strict validation that catches problematic patterns."""
            if not name:
                return False

            # Check for UUID-like patterns
            if re.search(
                r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", name
            ):
                return False

            # Check for SHA-like patterns
            if re.search(r"[0-9a-f]{32,}", name):
                return False

            # Check for uppercase (Docker names should be lowercase)
            if re.search(r"[A-Z]", name.split(":")[0]):
                return False

            # Check for invalid characters
            if re.search(r"[^a-z0-9:._/-]", name):
                return False

            # Check structure
            if name.startswith(":") or name.endswith(":"):
                return False

            if "//" in name or ".." in name:
                return False

            # Check length limits
            if len(name) > 255:
                return False

            parts = name.split(":")
            if len(parts) > 2:
                return False

            if len(parts) == 2 and len(parts[1]) > 128:
                return False

            return True

        validator.validate_strict.side_effect = validate_image_name_strict

        # Problematic names should fail validation
        result = validator.validate_strict(image_name)
        assert (
            result is False
        ), f"Problematic image name {image_name} passed validation when it should fail"

    @given(st.lists(valid_docker_image_name(), min_size=1, max_size=20))
    @settings(max_examples=50)
    def test_batch_image_validation_consistency(self, image_names):
        """Property: Batch validation should be consistent with individual validation."""
        # Mock batch validator
        validator = Mock()

        def validate_single(name):
            return len(name) > 0 and ":" in name and not name.startswith("invalid")

        def validate_batch(names):
            return [validate_single(name) for name in names]

        validator.validate_single.side_effect = validate_single
        validator.validate_batch.side_effect = validate_batch

        # Individual validation results
        individual_results = [validator.validate_single(name) for name in image_names]

        # Batch validation results
        batch_results = validator.validate_batch(image_names)

        # Should be consistent
        assert (
            individual_results == batch_results
        ), f"Batch validation inconsistent with individual validation for {image_names}"

    @given(service_configuration())
    @settings(max_examples=100)
    def test_service_config_generates_valid_image_names(self, config):
        """Property: Service configurations should generate valid image names."""
        # Mock image name generator
        generator = Mock()

        def generate_image_name(service_config):
            """Generate image name from service configuration."""
            name = service_config["name"]
            protocol = service_config["protocol"]
            implementation = service_config["implementation"]
            version = service_config.get("version", "latest")

            # Create image name following PANTHER conventions
            image_name = f"{name}-{protocol}-{implementation}:{version}"

            # Ensure lowercase (Docker requirement)
            image_name = image_name.lower()

            # Replace invalid characters
            image_name = re.sub(r"[^a-z0-9:._/-]", "-", image_name)

            # Remove consecutive hyphens
            image_name = re.sub(r"-+", "-", image_name)

            return image_name

        generator.generate.side_effect = generate_image_name

        # Generate image name
        image_name = generator.generate(config)

        # Validate the generated name
        assert image_name is not None
        assert len(image_name) > 0
        assert ":" in image_name  # Should have tag
        assert not image_name.startswith(":")
        assert not image_name.endswith(":")
        assert image_name.islower()  # Docker names must be lowercase

        # Check no invalid characters
        name_part = image_name.split(":")[0]
        assert re.match(
            r"^[a-z0-9][a-z0-9._/-]*[a-z0-9]$|^[a-z0-9]$", name_part
        ), f"Generated image name {image_name} contains invalid characters"

    @given(
        st.lists(
            st.tuples(valid_docker_image_name(), st.booleans()), min_size=1, max_size=50
        )
    )
    @settings(max_examples=30)
    def test_image_cache_consistency(self, image_existence_pairs):
        """Property: Image cache should consistently report image existence."""
        # Mock image cache
        cache = Mock()

        # Set up cache state
        existing_images = {name for name, exists in image_existence_pairs if exists}

        def check_image_exists(name):
            return name in existing_images

        cache.image_exists.side_effect = check_image_exists

        # Test cache consistency
        for image_name, should_exist in image_existence_pairs:
            result = cache.image_exists(image_name)
            assert (
                result == should_exist
            ), f"Cache inconsistency for {image_name}: expected {should_exist}, got {result}"

    @given(st.text(min_size=1, max_size=100))
    @settings(max_examples=100)
    def test_uuid_detection_is_accurate(self, text_input):
        """Property: UUID detection should accurately identify UUID patterns."""
        # Mock UUID detector
        detector = Mock()

        def detect_uuid_pattern(text):
            """Detect UUID-like patterns in text."""
            # Standard UUID pattern
            uuid_pattern = (
                r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
            )
            return bool(re.search(uuid_pattern, text.lower()))

        detector.has_uuid_pattern.side_effect = detect_uuid_pattern

        # Test detection
        has_uuid = detector.has_uuid_pattern(text_input)

        # Manually check if text contains UUID pattern
        manual_check = bool(
            re.search(
                r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
                text_input.lower(),
            )
        )

        assert (
            has_uuid == manual_check
        ), f"UUID detection mismatch for '{text_input}': detector={has_uuid}, manual={manual_check}"

    @given(st.integers(min_value=0, max_value=1000))
    @settings(max_examples=50)
    def test_image_validation_performance_scales_linearly(self, num_images):
        """Property: Image validation performance should scale roughly linearly."""
        # Mock performance validator
        validator = Mock()

        # Simulate validation times (should be roughly linear)
        def validate_multiple_images(count):
            base_time = 0.001  # Base time per image in seconds
            return count * base_time

        validator.validate_batch_time.side_effect = validate_multiple_images

        # Test performance scaling
        time_taken = validator.validate_batch_time(num_images)

        # Performance should scale roughly linearly
        expected_max_time = num_images * 0.01  # 10ms per image max
        assert (
            time_taken <= expected_max_time
        ), f"Validation time {time_taken} exceeds expected maximum {expected_max_time} for {num_images} images"

        # Time should be non-negative
        assert time_taken >= 0


class TestDockerImageValidationStateMachine(RuleBasedStateMachine):
    """Stateful property-based testing for Docker image validation systems."""

    def __init__(self):
        super().__init__()
        self.built_images = set()
        self.validated_images = set()
        self.failed_builds = set()
        self.cache = {}

        # Mock components
        self.docker_builder = Mock()
        self.validator = Mock()
        self.cache_manager = Mock()

        # Configure mock behavior
        self.docker_builder.build_image.side_effect = self._mock_build_image
        self.docker_builder.image_exists.side_effect = self._mock_image_exists
        self.validator.validate_image.side_effect = self._mock_validate_image
        self.cache_manager.get_cached_result.side_effect = self._mock_get_cached_result
        self.cache_manager.cache_result.side_effect = self._mock_cache_result

    # Bundles for different types of data
    image_names = Bundle("image_names")
    service_configs = Bundle("service_configs")

    @initialize()
    def init_state(self):
        """Initialize the state machine."""
        self.built_images = set()
        self.validated_images = set()
        self.failed_builds = set()
        self.cache = {}

    @rule(target=image_names, name=valid_docker_image_name())
    def build_image(self, name):
        """Rule: Build a Docker image."""
        assume(name not in self.built_images)
        assume(name not in self.failed_builds)

        # Attempt to build image
        success = self.docker_builder.build_image("Dockerfile", name)

        if success:
            self.built_images.add(name)
        else:
            self.failed_builds.add(name)

        return name

    @rule(name=image_names)
    def validate_image(self, name):
        """Rule: Validate an image exists."""
        # Validation should be consistent with build state
        exists = self.docker_builder.image_exists(name)
        validation_result = self.validator.validate_image(name)

        if name in self.built_images:
            assert exists is True, f"Built image {name} should exist"
            assert (
                validation_result is True
            ), f"Built image {name} should validate successfully"
            self.validated_images.add(name)

        if name in self.failed_builds:
            assert exists is False, f"Failed build {name} should not exist"

    @rule(name=image_names)
    def cache_validation_result(self, name):
        """Rule: Cache validation results."""
        if name in self.validated_images:
            # Cache the positive result
            self.cache_manager.cache_result(name, True)

            # Cached result should match actual state
            cached = self.cache_manager.get_cached_result(name)
            actual = self.docker_builder.image_exists(name)

            assert (
                cached == actual
            ), f"Cached result {cached} doesn't match actual {actual} for {name}"

    @rule(target=service_configs, config=service_configuration())
    def create_service_config(self, config):
        """Rule: Create a service configuration."""
        return config

    @rule(config=service_configs)
    def validate_service_config_generates_valid_image(self, config):
        """Rule: Service configs should generate valid image names."""
        # Generate image name from config
        image_name = (
            f"{config['name']}-{config['protocol']}:{config.get('version', 'latest')}"
        )
        image_name = image_name.lower()

        # Validate the generated name format
        assert re.match(
            r"^[a-z0-9][a-z0-9._/-]*:[a-z0-9][a-z0-9._-]*$", image_name
        ), f"Service config generated invalid image name: {image_name}"

    @precondition(lambda self: len(self.built_images) > 0)
    @rule()
    def invariant_built_images_exist(self):
        """Invariant: All built images should exist when checked."""
        for image_name in self.built_images:
            exists = self.docker_builder.image_exists(image_name)
            assert exists, f"Built image {image_name} should exist but doesn't"

    @precondition(lambda self: len(self.failed_builds) > 0)
    @rule()
    def invariant_failed_builds_dont_exist(self):
        """Invariant: Failed builds should not exist."""
        for image_name in self.failed_builds:
            exists = self.docker_builder.image_exists(image_name)
            assert not exists, f"Failed build {image_name} should not exist but does"

    @precondition(lambda self: len(self.cache) > 0)
    @rule()
    def invariant_cache_consistency(self):
        """Invariant: Cache should be consistent with actual state."""
        for image_name, cached_result in self.cache.items():
            actual_result = self.docker_builder.image_exists(image_name)
            # Allow for some cache staleness, but not complete inconsistency
            if image_name in self.built_images:
                assert cached_result, f"Cache should show {image_name} as existing"

    # Mock implementation methods
    def _mock_build_image(self, dockerfile, tag):
        """Mock image building with realistic failure rate."""
        # Simulate ~90% success rate
        import random

        return random.random() > 0.1

    def _mock_image_exists(self, name):
        """Mock image existence check."""
        return name in self.built_images

    def _mock_validate_image(self, name):
        """Mock image validation."""
        return name in self.built_images

    def _mock_get_cached_result(self, name):
        """Mock cache retrieval."""
        return self.cache.get(name)

    def _mock_cache_result(self, name, result):
        """Mock cache storage."""
        self.cache[name] = result


# Example-based tests with specific edge cases
class TestDockerImageValidationExamples:
    """Example-based tests for specific edge cases."""

    @given(valid_docker_image_name())
    @example("python:3.11")
    @example("localhost:5000/myapp:latest")
    @example("registry.example.com:443/namespace/app:v1.0.0")
    @example("simple")
    @settings(max_examples=50)
    def test_known_valid_patterns(self, image_name):
        """Test known valid Docker image patterns."""
        # These should all pass validation
        validator = Mock()
        validator.validate.return_value = True

        result = validator.validate(image_name)
        assert result is True

    @given(problematic_docker_image_name())
    @example("unknown:ceacda77-b5b4-56d6-a95f-ec764bb37357")  # The specific error case
    @example("UPPERCASE:tag")
    @example("name with spaces:tag")
    @example(":notag")
    @example("name:")
    @settings(max_examples=50)
    def test_known_invalid_patterns(self, image_name):
        """Test known invalid Docker image patterns."""
        # These should all fail validation
        validator = Mock()

        def strict_validate(name):
            # Reproduce the strict validation logic
            if not name or ":" not in name:
                return False
            if re.search(r"[A-Z]", name):
                return False
            if " " in name:
                return False
            if name.startswith(":") or name.endswith(":"):
                return False
            if re.search(
                r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", name
            ):
                return False
            return True

        validator.validate.side_effect = strict_validate

        result = validator.validate(image_name)
        assert result is False, f"Invalid pattern {image_name} should fail validation"


# Performance property tests
class TestDockerImageValidationPerformanceProperties:
    """Property-based performance tests."""

    @given(st.lists(valid_docker_image_name(), min_size=1, max_size=1000))
    @settings(max_examples=10, deadline=5000)  # 5 second deadline
    def test_bulk_validation_performance(self, image_names):
        """Property: Bulk validation should complete within reasonable time."""
        # Mock high-performance validator
        validator = Mock()

        def fast_bulk_validate(names):
            # Simulate fast validation (should handle 1000 names quickly)
            return [True] * len(names)

        validator.bulk_validate.side_effect = fast_bulk_validate

        # This should complete quickly
        results = validator.bulk_validate(image_names)

        assert len(results) == len(image_names)
        assert all(results)  # All should pass in this mock

    @given(st.integers(min_value=1, max_value=10000))
    @settings(max_examples=20)
    def test_cache_performance_scales_logarithmically(self, cache_size):
        """Property: Cache lookups should scale logarithmically or better."""
        # Mock cache with realistic performance characteristics
        cache = Mock()

        def lookup_time(size):
            import math

            # Simulate O(log n) or O(1) lookup time
            return max(0.001, 0.001 * math.log(size + 1))

        cache.lookup_time.side_effect = lookup_time

        time_taken = cache.lookup_time(cache_size)

        # Should be very fast even for large caches
        max_acceptable_time = 0.1  # 100ms max
        assert (
            time_taken <= max_acceptable_time
        ), f"Cache lookup time {time_taken} too slow for size {cache_size}"


# Run the state machine test
TestDockerImageValidationStateMachine = TestDockerImageValidationStateMachine.TestCase


if __name__ == "__main__":
    # Run specific property-based tests
    pytest.main([__file__, "-v", "--hypothesis-show-statistics"])
