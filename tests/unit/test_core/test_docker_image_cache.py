"""Unit tests for Docker Image Cache system.

Tests the real CachedImage dataclass, DockerImageCache, and integration
with DockerBuilder. All PANTHER classes are imported directly -- no fake
class fallbacks.

IO boundaries mocked: Docker daemon (docker.from_env, client.api.images),
filesystem writes (via tmp_path).
"""

import json
import threading
import time
from unittest.mock import MagicMock, Mock, patch

import pytest
from docker.errors import DockerException

from panther.core.docker_builder.caching.docker_image_cache import (
    CachedImage,
    DockerImageCache,
)
from panther.core.docker_builder.docker_builder import DockerBuilder

pytestmark = [pytest.mark.unit, pytest.mark.docker_cache]


def _make_docker_errors_module():
    """Create a mock docker.errors module with real exception types."""
    errors = MagicMock()
    errors.DockerException = type("DockerException", (Exception,), {})
    errors.ImageNotFound = type("ImageNotFound", (Exception,), {})
    errors.NotFound = type("NotFound", (Exception,), {})
    errors.APIError = type("APIError", (Exception,), {})
    errors.BuildError = type("BuildError", (Exception,), {})
    return errors


# ---------------------------------------------------------------------------
# TestCachedImage -- pure dataclass, no IO
# ---------------------------------------------------------------------------


class TestCachedImage:
    """Test CachedImage data class functionality."""

    def test_cached_image_creation(self):
        """Test CachedImage creation with valid data."""
        image = CachedImage(
            id="sha256:abc123",
            tags=["python:3.11", "python:latest"],
            size=1024 * 1024 * 500,  # 500MB
            created="2025-06-24T10:00:00Z",
            last_seen=time.time(),
        )

        assert image.id == "sha256:abc123"
        assert "python:3.11" in image.tags
        assert "python:latest" in image.tags
        assert image.size == 1024 * 1024 * 500
        assert isinstance(image.last_seen, float)

    def test_cached_image_to_dict(self):
        """Test CachedImage serialization to dictionary."""
        timestamp = time.time()
        image = CachedImage(
            id="sha256:def456",
            tags=["alpine:3.18"],
            size=5 * 1024 * 1024,  # 5MB
            created="2025-06-24T09:00:00Z",
            last_seen=timestamp,
        )

        image_dict = image.to_dict()

        assert isinstance(image_dict, dict)
        assert image_dict["id"] == "sha256:def456"
        assert image_dict["tags"] == ["alpine:3.18"]
        assert image_dict["size"] == 5 * 1024 * 1024
        assert image_dict["last_seen"] == timestamp

    def test_cached_image_from_dict(self):
        """Test CachedImage deserialization from dictionary."""
        timestamp = time.time()
        image_data = {
            "id": "sha256:ghi789",
            "tags": ["ubuntu:20.04", "ubuntu:focal"],
            "size": 72 * 1024 * 1024,  # 72MB
            "created": "2025-06-24T08:00:00Z",
            "last_seen": timestamp,
        }

        image = CachedImage.from_dict(image_data)

        assert image.id == "sha256:ghi789"
        assert image.tags == ["ubuntu:20.04", "ubuntu:focal"]
        assert image.size == 72 * 1024 * 1024
        assert image.last_seen == timestamp


# ---------------------------------------------------------------------------
# TestDockerImageCache -- core cache functionality
# ---------------------------------------------------------------------------


class TestDockerImageCache:
    """Test DockerImageCache core functionality."""

    @pytest.fixture
    def cache_dir(self, tmp_path):
        """Provide a writable directory for cache files."""
        d = tmp_path / "cache_dir"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @pytest.fixture
    def mock_cache_docker_client(self):
        """Create mock Docker client with low-level API response format.

        Named to avoid shadowing conftest's mock_docker_client.
        Uses client.api.images() which is the real cache's API path.
        """
        client = Mock()

        # Mock api.images() return value (raw dicts from low-level Docker API)
        raw_images = [
            {
                "Id": "sha256:abc123",
                "RepoTags": ["python:3.11", "python:latest"],
                "Size": 500 * 1024 * 1024,
                "Created": "2025-06-24T10:00:00Z",
            },
            {
                "Id": "sha256:def456",
                "RepoTags": ["alpine:3.18"],
                "Size": 5 * 1024 * 1024,
                "Created": "2025-06-24T09:00:00Z",
            },
        ]

        client.api.images.return_value = raw_images
        client.ping.return_value = True

        return client

    def _make_cache(self, cache_dir, **kwargs):
        """Helper to create a DockerImageCache rooted in cache_dir.

        The real __init__ appends a platform suffix to the cache file
        name, so we cannot assert cache.cache_file == original_path.
        Instead, callers use cache.cache_file for subsequent checks.
        """
        cache_file = cache_dir / "test_cache.json"
        return DockerImageCache(cache_file=cache_file, **kwargs)

    def test_docker_image_cache_initialization(self, cache_dir):
        """Test DockerImageCache initialization with custom parameters."""
        cache = self._make_cache(
            cache_dir, cache_ttl=600, retry_count=5, retry_delay=2.0
        )

        assert cache.cache_ttl == 600
        assert cache.retry_count == 5
        assert cache.retry_delay == 2.0
        assert cache._docker_client is None
        assert len(cache._cache) == 0
        # cache_file gets a platform suffix, but should be inside cache_dir
        assert cache.cache_file.parent == cache_dir

    def test_docker_client_setting(self, cache_dir, mock_cache_docker_client):
        """Test setting Docker client."""
        cache = self._make_cache(cache_dir)

        cache.set_docker_client(mock_cache_docker_client)

        assert cache._docker_client == mock_cache_docker_client

    def test_cache_refresh_from_docker(self, cache_dir, mock_cache_docker_client):
        """Test cache refresh from Docker daemon via low-level API."""
        cache = self._make_cache(cache_dir)
        cache.set_docker_client(mock_cache_docker_client)

        # Refresh cache
        result = cache._refresh_cache_from_docker()

        assert result is True
        assert len(cache._cache) == 2
        assert "sha256:abc123" in cache._cache
        assert "sha256:def456" in cache._cache

        # Verify image data parsed from raw API dict format
        python_image = cache._cache["sha256:abc123"]
        assert "python:3.11" in python_image.tags
        assert python_image.size == 500 * 1024 * 1024

        # Verify the low-level API was used (not images.list)
        mock_cache_docker_client.api.images.assert_called_with(all=False)

    def test_cache_refresh_docker_failure(self, cache_dir):
        """Test cache refresh when Docker is unavailable."""
        cache = self._make_cache(cache_dir, retry_count=1, retry_delay=0.01)

        # Mock Docker client that fails on the low-level API
        mock_client = Mock()
        mock_client.api.images.side_effect = DockerException("Connection refused")
        cache.set_docker_client(mock_client)

        # Refresh should fail but not raise exception
        result = cache._refresh_cache_from_docker()

        assert result is False
        assert len(cache._cache) == 0

    def test_get_cached_images_fresh_cache(self, cache_dir, mock_cache_docker_client):
        """Test getting cached images with fresh cache."""
        cache = self._make_cache(cache_dir, cache_ttl=300)
        cache.set_docker_client(mock_cache_docker_client)

        # First call should refresh cache
        images = cache.get_cached_images()

        assert len(images) == 2
        mock_cache_docker_client.api.images.assert_called_with(all=False)

        # Second call should use cache (no additional Docker call)
        mock_cache_docker_client.api.images.reset_mock()
        images = cache.get_cached_images()

        assert len(images) == 2
        mock_cache_docker_client.api.images.assert_not_called()

    def test_get_cached_images_force_refresh(self, cache_dir, mock_cache_docker_client):
        """Test forced cache refresh."""
        cache = self._make_cache(cache_dir)
        cache.set_docker_client(mock_cache_docker_client)

        # Initial cache
        cache.get_cached_images()
        mock_cache_docker_client.api.images.reset_mock()

        # Force refresh should call Docker API again
        images = cache.get_cached_images(force_refresh=True)

        assert len(images) == 2
        mock_cache_docker_client.api.images.assert_called_with(all=False)

    def test_image_exists_in_cache(self, cache_dir, mock_cache_docker_client):
        """Test image existence checking from cache."""
        cache = self._make_cache(cache_dir)
        cache.set_docker_client(mock_cache_docker_client)

        # Populate cache (makes it fresh)
        cache.get_cached_images()

        # Test existing images -- returns True when found in fresh cache
        assert cache.image_exists_in_cache("python:3.11") is True
        assert cache.image_exists_in_cache("python:latest") is True
        assert cache.image_exists_in_cache("alpine:3.18") is True

        # Test non-existing image -- returns False when fresh cache has no match
        assert cache.image_exists_in_cache("nonexistent:tag") is False

    def test_cache_ttl_expiration(self, cache_dir, mock_cache_docker_client):
        """Test cache TTL expiration behavior."""
        cache = self._make_cache(cache_dir, cache_ttl=1)  # 1 second TTL
        cache.set_docker_client(mock_cache_docker_client)

        # Initial cache
        cache.get_cached_images()
        assert cache._is_cache_fresh() is True

        # Wait for TTL expiration
        time.sleep(1.1)
        assert cache._is_cache_fresh() is False

        # Next call should refresh cache
        mock_cache_docker_client.api.images.reset_mock()
        cache.get_cached_images()
        mock_cache_docker_client.api.images.assert_called_with(all=False)

    def test_cache_persistence(self, cache_dir, mock_cache_docker_client):
        """Test cache persistence to file."""
        # Create cache and populate it
        cache = self._make_cache(cache_dir)
        cache.set_docker_client(mock_cache_docker_client)
        cache.get_cached_images()

        # Force save
        cache._save_cache()

        # Verify file exists and contains data
        assert cache.cache_file.exists()

        with open(cache.cache_file, "r") as f:
            data = json.load(f)

        assert "images" in data
        assert "last_refresh" in data
        assert len(data["images"]) == 2

    def test_cache_loading(self, cache_dir):
        """Test cache loading from persistent file."""
        # We must create the cache file at the platform-specific path.
        # Create a temporary cache first just to discover the actual file path.
        probe_cache = self._make_cache(cache_dir)
        actual_cache_file = probe_cache.cache_file

        # Create cache file manually at the correct platform-aware path
        cache_data = {
            "images": {
                "sha256:test123": {
                    "id": "sha256:test123",
                    "tags": ["test:latest"],
                    "size": 1024 * 1024,
                    "created": "2025-06-24T10:00:00Z",
                    "last_seen": time.time(),
                }
            },
            "last_refresh": time.time(),
            "saved_at": time.time(),
        }

        with open(actual_cache_file, "w") as f:
            json.dump(cache_data, f)

        # Create new cache instance -- should load existing data
        cache = self._make_cache(cache_dir)

        assert len(cache._cache) == 1
        assert "sha256:test123" in cache._cache
        assert cache._cache["sha256:test123"].tags == ["test:latest"]

    def test_cache_loading_corrupted_file(self, cache_dir):
        """Test cache loading with corrupted file."""
        # Discover the platform-aware cache file path
        probe_cache = self._make_cache(cache_dir)
        actual_cache_file = probe_cache.cache_file

        # Create corrupted cache file
        with open(actual_cache_file, "w") as f:
            f.write("invalid json content")

        # Cache should handle corruption gracefully
        cache = self._make_cache(cache_dir)

        assert len(cache._cache) == 0
        assert cache._last_refresh == 0.0

    def test_get_images_by_filter_dangling(self, cache_dir):
        """Test filtering dangling images."""
        cache = self._make_cache(cache_dir)

        # Add test images to cache
        cache._cache["dangling1"] = CachedImage(
            id="sha256:dangling1",
            tags=[],  # No tags = dangling
            size=1024,
            created="2025-06-24T10:00:00Z",
            last_seen=time.time(),
        )

        cache._cache["dangling2"] = CachedImage(
            id="sha256:dangling2",
            tags=["<none>:<none>"],  # Explicit dangling
            size=2048,
            created="2025-06-24T10:00:00Z",
            last_seen=time.time(),
        )

        cache._cache["normal"] = CachedImage(
            id="sha256:normal",
            tags=["python:3.11"],
            size=4096,
            created="2025-06-24T10:00:00Z",
            last_seen=time.time(),
        )

        # Test dangling filter
        dangling_images = cache.get_images_by_filter(dangling=True)
        assert len(dangling_images) == 2

        # Test non-dangling filter
        normal_images = cache.get_images_by_filter(dangling=False)
        assert len(normal_images) == 1
        assert normal_images[0].tags == ["python:3.11"]

    def test_get_images_by_filter_tag_pattern(self, cache_dir):
        """Test filtering images by tag pattern."""
        cache = self._make_cache(cache_dir)

        # Add test images
        cache._cache["python1"] = CachedImage(
            id="sha256:python1",
            tags=["python:3.11", "python:latest"],
            size=1024,
            created="2025-06-24T10:00:00Z",
            last_seen=time.time(),
        )

        cache._cache["alpine1"] = CachedImage(
            id="sha256:alpine1",
            tags=["alpine:3.18"],
            size=512,
            created="2025-06-24T10:00:00Z",
            last_seen=time.time(),
        )

        # Test pattern filter
        python_images = cache.get_images_by_filter(tag_pattern="python")
        assert len(python_images) == 1
        assert "python:3.11" in python_images[0].tags

        alpine_images = cache.get_images_by_filter(tag_pattern="alpine")
        assert len(alpine_images) == 1
        assert "alpine:3.18" in alpine_images[0].tags

    def test_cache_invalidation(self, cache_dir, mock_cache_docker_client):
        """Test cache invalidation."""
        cache = self._make_cache(cache_dir)
        cache.set_docker_client(mock_cache_docker_client)

        # Populate cache
        cache.get_cached_images()
        assert len(cache._cache) == 2

        # Invalidate cache
        cache.invalidate_cache()

        assert len(cache._cache) == 0
        assert cache._last_refresh == 0.0

    def test_get_cache_stats(self, cache_dir, mock_cache_docker_client):
        """Test cache statistics."""
        cache = self._make_cache(cache_dir, cache_ttl=300)
        cache.set_docker_client(mock_cache_docker_client)

        # Get stats with empty cache
        stats = cache.get_cache_stats()
        assert stats["total_images"] == 0
        assert stats["cache_fresh"] is False

        # Populate cache and get stats
        cache.get_cached_images()
        stats = cache.get_cache_stats()

        assert stats["total_images"] == 2
        assert stats["cache_fresh"] is True
        assert stats["cache_age_seconds"] < 2.0  # Should be very recent
        assert "cache_file" in stats
        assert "last_refresh" in stats
        # Real implementation also includes cache_secure
        assert "cache_secure" in stats


# ---------------------------------------------------------------------------
# TestDockerImageCacheThreadSafety
# ---------------------------------------------------------------------------


class TestDockerImageCacheThreadSafety:
    """Test thread safety of DockerImageCache."""

    def test_concurrent_cache_access(self, tmp_path):
        """Test concurrent access to cache."""
        cache_dir = tmp_path / "concurrent"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / "concurrent_cache.json"
        cache = DockerImageCache(cache_file=cache_file)

        results = []
        errors = []

        def cache_operation(thread_id):
            try:
                # Simulate various cache operations
                cache.invalidate_cache()
                cache.get_cached_images()
                stats = cache.get_cache_stats()
                results.append(f"Thread {thread_id}: {stats['total_images']} images")
            except Exception as e:
                errors.append(f"Thread {thread_id}: {e}")

        # Run multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=cache_operation, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Check results
        assert len(errors) == 0, f"Thread safety errors: {errors}"
        assert len(results) == 5

    def test_concurrent_cache_refresh(self, tmp_path):
        """Test concurrent cache refresh operations."""
        cache_dir = tmp_path / "refresh"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / "refresh_cache.json"
        cache = DockerImageCache(cache_file=cache_file)

        # Mock Docker client using the real API path (api.images)
        mock_client = Mock()
        mock_client.api.images.return_value = []
        cache.set_docker_client(mock_client)

        refresh_results = []

        def refresh_cache(thread_id):
            result = cache._refresh_cache_from_docker()
            refresh_results.append(result)

        # Run multiple refresh operations concurrently
        threads = []
        for i in range(3):
            thread = threading.Thread(target=refresh_cache, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All refreshes should succeed (though some may be redundant)
        assert len(refresh_results) == 3


# ---------------------------------------------------------------------------
# TestDockerBuilderCacheIntegration
# ---------------------------------------------------------------------------


class TestDockerBuilderCacheIntegration:
    """Test integration of cache with DockerBuilder."""

    @pytest.fixture
    def cache_builder(self, mock_docker_client, tmp_path):
        """Create a real DockerBuilder with cache file in tmp_path.

        Uses conftest's mock_docker_client (images.get/list based).
        Configures the builder's image_cache to use a tmp_path file.
        """
        DockerBuilder.reset_singleton()

        with patch(
            "panther.core.docker_builder.docker_builder.docker"
        ) as mock_docker_mod:
            mock_docker_mod.from_env.return_value = mock_docker_client
            mock_docker_mod.errors = _make_docker_errors_module()

            # Configure mock images for the high-level API path
            mock_image = Mock()
            mock_image.id = "sha256:test123"
            mock_image.tags = ["python:3.11"]
            mock_image.attrs = {"Size": 100 * 1024 * 1024}
            mock_docker_client.images.get.side_effect = None
            mock_docker_client.images.get.return_value = mock_image
            mock_docker_client.images.list.return_value = [mock_image]

            # Also configure the low-level API for cache refresh
            mock_docker_client.api.images.return_value = [
                {
                    "Id": "sha256:test123",
                    "RepoTags": ["python:3.11"],
                    "Size": 100 * 1024 * 1024,
                    "Created": "2025-06-24T10:00:00Z",
                },
            ]

            builder = DockerBuilder(
                build_log_file=False,
                enable_cache=True,
            )

        # Redirect cache file to tmp_path
        cache_dir = tmp_path / "builder_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / "test_cache.json"
        builder.image_cache.cache_file = builder.image_cache._get_platform_cache_file(
            cache_file
        )

        return builder

    def test_builder_image_exists_with_cache(self, cache_builder, mock_docker_client):
        """Test DockerBuilder.image_exists() using cache."""
        result = cache_builder.image_exists("python:3.11")
        assert result is True

    def test_builder_cache_fallback_on_docker_failure(self, tmp_path):
        """Test DockerBuilder fallback to cache when Docker fails."""
        cache_dir = tmp_path / "fallback_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)

        DockerBuilder.reset_singleton()

        with patch(
            "panther.core.docker_builder.docker_builder.docker"
        ) as mock_docker_mod:
            mock_client = Mock()
            mock_client.ping.side_effect = DockerException("Connection refused")
            mock_docker_mod.from_env.return_value = mock_client
            mock_docker_mod.errors = _make_docker_errors_module()

            # Builder should initialize without throwing exception
            builder = DockerBuilder(
                build_log_file=False,
                enable_cache=True,
            )

        # Write a pre-populated cache file at the platform-aware path
        cache_file_base = cache_dir / "fallback.json"
        actual_cache_file = builder.image_cache._get_platform_cache_file(
            cache_file_base
        )
        cache_data = {
            "images": {
                "sha256:cached123": {
                    "id": "sha256:cached123",
                    "tags": ["cached:latest"],
                    "size": 1024 * 1024,
                    "created": "2025-06-24T10:00:00Z",
                    "last_seen": time.time(),
                }
            },
            "last_refresh": time.time() - 100,  # Slightly stale but usable
            "saved_at": time.time(),
        }

        with open(actual_cache_file, "w") as f:
            json.dump(cache_data, f)

        # Point cache to our prepared file and reload
        builder.image_cache.cache_file = actual_cache_file
        builder.image_cache._load_cache()

        # Should be able to check image existence from cache
        cached_result = builder.image_cache.image_exists_in_cache("cached:latest")
        assert cached_result is True


# ---------------------------------------------------------------------------
# TestDockerCacheErrorHandling
# ---------------------------------------------------------------------------


class TestDockerCacheErrorHandling:
    """Test error handling in Docker cache system."""

    def test_cache_file_permission_error(self, tmp_path):
        """Test handling of cache file permission errors."""
        # Create read-only directory
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir(mode=0o444)
        cache_file = readonly_dir / "cache.json"

        # Cache should handle permission error gracefully during init
        # (the real __init__ calls _initialize_secure_cache_file which
        # catches PermissionError)
        cache = DockerImageCache(cache_file=cache_file)

        # Should not raise exception during save
        cache._save_cache()

        # Clean up
        readonly_dir.chmod(0o755)

    def test_docker_client_retry_logic(self, tmp_path):
        """Test retry logic for Docker client failures.

        Real _refresh_cache_from_docker uses client.api.images() via
        ThreadPoolExecutor, and retries on DockerException.
        """
        cache_dir = tmp_path / "retry"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache = DockerImageCache(
            cache_file=cache_dir / "retry_cache.json",
            retry_count=3,
            retry_delay=0.01,  # Fast retry for testing
        )

        # Mock client that fails first two times, succeeds third time
        mock_client = Mock()
        call_count = [0]

        def failing_api_images(**kwargs):
            call_count[0] += 1
            if call_count[0] <= 2:
                raise DockerException("Temporary failure")
            return []  # Success on third call

        mock_client.api.images = failing_api_images
        cache.set_docker_client(mock_client)

        # Should succeed after retries
        result = cache._refresh_cache_from_docker()
        assert result is True
        assert call_count[0] == 3  # Called 3 times

    def test_docker_client_total_failure(self, tmp_path):
        """Test handling when Docker client always fails."""
        cache_dir = tmp_path / "failure"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache = DockerImageCache(
            cache_file=cache_dir / "failure_cache.json",
            retry_count=2,
            retry_delay=0.01,
        )

        # Mock client that always fails via low-level API
        mock_client = Mock()
        mock_client.api.images.side_effect = DockerException("Persistent failure")
        cache.set_docker_client(mock_client)

        # Should fail gracefully after all retries
        result = cache._refresh_cache_from_docker()
        assert result is False
        assert mock_client.api.images.call_count == 2


# ---------------------------------------------------------------------------
# TestDockerCachePerformance
# ---------------------------------------------------------------------------


class TestDockerCachePerformance:
    """Test performance characteristics of Docker cache."""

    def test_cache_lookup_performance(self, tmp_path):
        """Test cache lookup performance."""
        cache_dir = tmp_path / "perf"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache = DockerImageCache(cache_file=cache_dir / "perf_cache.json")

        # Add many images to cache and mark cache as fresh
        current_time = time.time()
        for i in range(1000):
            cache._cache[f"sha256:image{i}"] = CachedImage(
                id=f"sha256:image{i}",
                tags=[f"test{i}:latest"],
                size=1024 * 1024,
                created="2025-06-24T10:00:00Z",
                last_seen=current_time,
            )
        cache._last_refresh = current_time

        # Test lookup performance
        start_time = time.time()

        # Perform many lookups
        for i in range(100):
            exists = cache.image_exists_in_cache(f"test{i}:latest")
            assert exists is True

        end_time = time.time()
        duration = end_time - start_time

        # Should be very fast (under 100ms for 100 lookups to be safe in CI)
        assert duration < 0.1

    def test_cache_serialization_performance(self, tmp_path):
        """Test cache serialization performance."""
        cache_dir = tmp_path / "serialize"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache = DockerImageCache(cache_file=cache_dir / "serialize_cache.json")

        # Add many images to cache
        for i in range(500):
            cache._cache[f"sha256:large{i}"] = CachedImage(
                id=f"sha256:large{i}",
                tags=[f"large{i}:v1", f"large{i}:latest"],
                size=1024 * 1024 * 100,  # 100MB each
                created="2025-06-24T10:00:00Z",
                last_seen=time.time(),
            )

        # Test save performance
        start_time = time.time()
        cache._save_cache()
        save_duration = time.time() - start_time

        # Test load performance
        cache._cache.clear()
        start_time = time.time()
        cache._load_cache()
        load_duration = time.time() - start_time

        # Should be reasonably fast (under 1 second each)
        assert save_duration < 1.0
        assert load_duration < 1.0
        assert len(cache._cache) == 500


if __name__ in {"__main__", "__mp_main__"}:
    pytest.main([__file__, "-v"])
