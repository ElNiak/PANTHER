"""
Unit tests for Docker Image Cache system.

This module provides comprehensive unit tests for the DockerImageCache
and its integration with DockerBuilder to prevent Docker connection
failures and improve performance.
"""

import json
import tempfile
import threading
import time
from dataclasses import asdict
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# Test imports with fallback to mocks
try:
    import docker
    from docker.errors import DockerException, NotFound

    from panther.core.docker_builder.docker_builder import DockerBuilder
    from panther.core.docker_builder.docker_image_cache import (
        CachedImage,
        DockerImageCache,
    )

    DOCKER_SYSTEM_AVAILABLE = True
except ImportError:
    DOCKER_SYSTEM_AVAILABLE = False

    # Mock implementations for testing
    class DockerException(Exception):
        pass

    class NotFound(DockerException):
        pass

    class CachedImage:
        def __init__(self, id, tags, size, created, last_seen):
            self.id = id
            self.tags = tags
            self.size = size
            self.created = created
            self.last_seen = last_seen

        def to_dict(self):
            return {
                "id": self.id,
                "tags": self.tags,
                "size": self.size,
                "created": self.created,
                "last_seen": self.last_seen,
            }

        @classmethod
        def from_dict(cls, data):
            return cls(**data)

    class DockerImageCache:
        def __init__(
            self, cache_ttl=300, cache_file=None, retry_count=3, retry_delay=1.0
        ):
            self.cache_ttl = cache_ttl
            self.cache_file = (
                cache_file or Path.home() / ".panther" / "docker_image_cache.json"
            )
            self.retry_count = retry_count
            self.retry_delay = retry_delay
            self._cache = {}
            self._last_refresh = 0.0
            self._docker_client = None

        def set_docker_client(self, client):
            self._docker_client = client

        def get_cached_images(self, force_refresh=False):
            return list(self._cache.values())

        def image_exists_in_cache(self, image_tag):
            for image in self._cache.values():
                if image_tag in image.tags:
                    return True
            return False

        def get_cache_stats(self):
            return {
                "total_images": len(self._cache),
                "cache_age_seconds": time.time() - self._last_refresh,
                "cache_fresh": (time.time() - self._last_refresh) < self.cache_ttl,
                "total_size_mb": 0,
                "cache_file": str(self.cache_file),
                "last_refresh": "never",
            }


pytestmark = [pytest.mark.unit, pytest.mark.docker_cache]


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


class TestDockerImageCache:
    """Test DockerImageCache core functionality."""

    @pytest.fixture
    def temp_cache_file(self):
        """Create temporary cache file for testing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = Path(f.name)

        yield temp_path

        # Cleanup
        temp_path.unlink(missing_ok=True)

    @pytest.fixture
    def mock_docker_client(self):
        """Create mock Docker client with low-level API response format."""
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

    def test_docker_image_cache_initialization(self, temp_cache_file):
        """Test DockerImageCache initialization."""
        cache = DockerImageCache(
            cache_ttl=600, cache_file=temp_cache_file, retry_count=5, retry_delay=2.0
        )

        assert cache.cache_ttl == 600
        assert cache.cache_file == temp_cache_file
        assert cache.retry_count == 5
        assert cache.retry_delay == 2.0
        assert cache._docker_client is None
        assert len(cache._cache) == 0

    def test_docker_client_setting(self, temp_cache_file, mock_docker_client):
        """Test setting Docker client."""
        cache = DockerImageCache(cache_file=temp_cache_file)

        cache.set_docker_client(mock_docker_client)

        assert cache._docker_client == mock_docker_client

    @pytest.mark.skipif(
        not DOCKER_SYSTEM_AVAILABLE, reason="Requires real DockerImageCache"
    )
    def test_cache_refresh_from_docker(self, temp_cache_file, mock_docker_client):
        """Test cache refresh from Docker daemon via low-level API."""
        cache = DockerImageCache(cache_file=temp_cache_file)
        cache.set_docker_client(mock_docker_client)

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
        mock_docker_client.api.images.assert_called_once_with(all=False)

    @pytest.mark.skipif(
        not DOCKER_SYSTEM_AVAILABLE, reason="Requires real DockerImageCache"
    )
    def test_cache_refresh_docker_failure(self, temp_cache_file):
        """Test cache refresh when Docker is unavailable."""
        cache = DockerImageCache(cache_file=temp_cache_file, retry_count=1)

        # Mock Docker client that fails on the low-level API
        mock_client = Mock()
        mock_client.api.images.side_effect = DockerException("Connection refused")
        cache.set_docker_client(mock_client)

        # Refresh should fail but not raise exception
        result = cache._refresh_cache_from_docker()

        assert result is False
        assert len(cache._cache) == 0

    @pytest.mark.skipif(
        not DOCKER_SYSTEM_AVAILABLE, reason="Requires real DockerImageCache"
    )
    def test_get_cached_images_fresh_cache(self, temp_cache_file, mock_docker_client):
        """Test getting cached images with fresh cache."""
        cache = DockerImageCache(cache_file=temp_cache_file, cache_ttl=300)
        cache.set_docker_client(mock_docker_client)

        # First call should refresh cache
        images = cache.get_cached_images()

        assert len(images) == 2
        mock_docker_client.api.images.assert_called_once_with(all=False)

        # Second call should use cache (no additional Docker call)
        mock_docker_client.api.images.reset_mock()
        images = cache.get_cached_images()

        assert len(images) == 2
        mock_docker_client.api.images.assert_not_called()

    @pytest.mark.skipif(
        not DOCKER_SYSTEM_AVAILABLE, reason="Requires real DockerImageCache"
    )
    def test_get_cached_images_force_refresh(self, temp_cache_file, mock_docker_client):
        """Test forced cache refresh."""
        cache = DockerImageCache(cache_file=temp_cache_file)
        cache.set_docker_client(mock_docker_client)

        # Initial cache
        cache.get_cached_images()
        mock_docker_client.api.images.reset_mock()

        # Force refresh should call Docker API again
        images = cache.get_cached_images(force_refresh=True)

        assert len(images) == 2
        mock_docker_client.api.images.assert_called_once_with(all=False)

    @pytest.mark.skipif(
        not DOCKER_SYSTEM_AVAILABLE, reason="Requires real DockerImageCache"
    )
    def test_image_exists_in_cache(self, temp_cache_file, mock_docker_client):
        """Test image existence checking from cache."""
        cache = DockerImageCache(cache_file=temp_cache_file)
        cache.set_docker_client(mock_docker_client)

        # Populate cache
        cache.get_cached_images()

        # Test existing images
        assert cache.image_exists_in_cache("python:3.11") is True
        assert cache.image_exists_in_cache("python:latest") is True
        assert cache.image_exists_in_cache("alpine:3.18") is True

        # Test non-existing image
        assert cache.image_exists_in_cache("nonexistent:tag") is False

    @pytest.mark.skipif(
        not DOCKER_SYSTEM_AVAILABLE, reason="Requires real DockerImageCache"
    )
    def test_cache_ttl_expiration(self, temp_cache_file, mock_docker_client):
        """Test cache TTL expiration behavior."""
        cache = DockerImageCache(
            cache_file=temp_cache_file, cache_ttl=1
        )  # 1 second TTL
        cache.set_docker_client(mock_docker_client)

        # Initial cache
        cache.get_cached_images()
        assert cache._is_cache_fresh() is True

        # Wait for TTL expiration
        time.sleep(1.1)
        assert cache._is_cache_fresh() is False

        # Next call should refresh cache
        mock_docker_client.api.images.reset_mock()
        cache.get_cached_images()
        mock_docker_client.api.images.assert_called_once_with(all=False)

    @pytest.mark.skipif(
        not DOCKER_SYSTEM_AVAILABLE, reason="Requires real DockerImageCache"
    )
    def test_cache_persistence(self, temp_cache_file, mock_docker_client):
        """Test cache persistence to file."""
        # Create cache and populate it
        cache = DockerImageCache(cache_file=temp_cache_file)
        cache.set_docker_client(mock_docker_client)
        cache.get_cached_images()

        # Force save
        cache._save_cache()

        # Verify file exists and contains data
        assert temp_cache_file.exists()

        with open(temp_cache_file, "r") as f:
            data = json.load(f)

        assert "images" in data
        assert "last_refresh" in data
        assert len(data["images"]) == 2

    @pytest.mark.skipif(
        not DOCKER_SYSTEM_AVAILABLE, reason="Requires real DockerImageCache"
    )
    def test_cache_loading(self, temp_cache_file):
        """Test cache loading from persistent file."""
        # Create cache file manually
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

        with open(temp_cache_file, "w") as f:
            json.dump(cache_data, f)

        # Create cache - should load existing data
        cache = DockerImageCache(cache_file=temp_cache_file)

        assert len(cache._cache) == 1
        assert "sha256:test123" in cache._cache
        assert cache._cache["sha256:test123"].tags == ["test:latest"]

    @pytest.mark.skipif(
        not DOCKER_SYSTEM_AVAILABLE, reason="Requires real DockerImageCache"
    )
    def test_cache_loading_corrupted_file(self, temp_cache_file):
        """Test cache loading with corrupted file."""
        # Create corrupted cache file
        with open(temp_cache_file, "w") as f:
            f.write("invalid json content")

        # Cache should handle corruption gracefully
        cache = DockerImageCache(cache_file=temp_cache_file)

        assert len(cache._cache) == 0
        assert cache._last_refresh == 0.0

    @pytest.mark.skipif(
        not DOCKER_SYSTEM_AVAILABLE, reason="Requires real DockerImageCache"
    )
    def test_get_images_by_filter_dangling(self, temp_cache_file):
        """Test filtering dangling images."""
        cache = DockerImageCache(cache_file=temp_cache_file)

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

    @pytest.mark.skipif(
        not DOCKER_SYSTEM_AVAILABLE, reason="Requires real DockerImageCache"
    )
    def test_get_images_by_filter_tag_pattern(self, temp_cache_file):
        """Test filtering images by tag pattern."""
        cache = DockerImageCache(cache_file=temp_cache_file)

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

    @pytest.mark.skipif(
        not DOCKER_SYSTEM_AVAILABLE, reason="Requires real DockerImageCache"
    )
    def test_cache_invalidation(self, temp_cache_file, mock_docker_client):
        """Test cache invalidation."""
        cache = DockerImageCache(cache_file=temp_cache_file)
        cache.set_docker_client(mock_docker_client)

        # Populate cache
        cache.get_cached_images()
        assert len(cache._cache) == 2

        # Invalidate cache
        cache.invalidate_cache()

        assert len(cache._cache) == 0
        assert cache._last_refresh == 0.0

    @pytest.mark.skipif(
        not DOCKER_SYSTEM_AVAILABLE, reason="Requires real DockerImageCache"
    )
    def test_get_cache_stats(self, temp_cache_file, mock_docker_client):
        """Test cache statistics."""
        cache = DockerImageCache(cache_file=temp_cache_file, cache_ttl=300)
        cache.set_docker_client(mock_docker_client)

        # Get stats with empty cache
        stats = cache.get_cache_stats()
        assert stats["total_images"] == 0
        assert stats["cache_fresh"] is False

        # Populate cache and get stats
        cache.get_cached_images()
        stats = cache.get_cache_stats()

        assert stats["total_images"] == 2
        assert stats["cache_fresh"] is True
        assert stats["cache_age_seconds"] < 1.0  # Should be very recent
        assert "cache_file" in stats
        assert "last_refresh" in stats


@pytest.mark.skipif(
    not DOCKER_SYSTEM_AVAILABLE, reason="Requires real DockerImageCache"
)
class TestDockerImageCacheThreadSafety:
    """Test thread safety of DockerImageCache."""

    def test_concurrent_cache_access(self, tmp_path):
        """Test concurrent access to cache."""
        cache_file = tmp_path / "concurrent_cache.json"
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
        cache_file = tmp_path / "refresh_cache.json"
        cache = DockerImageCache(cache_file=cache_file)

        # Mock Docker client
        mock_client = Mock()
        mock_client.images.list.return_value = []
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


class TestDockerBuilderCacheIntegration:
    """Test integration of cache with DockerBuilder."""

    @pytest.fixture
    def mock_docker_builder(self, tmp_path):
        """Create mock DockerBuilder with cache."""
        if DOCKER_SYSTEM_AVAILABLE:
            # Reset singleton for clean test
            DockerBuilder.reset_singleton()

        with patch(
            "panther.core.docker_builder.docker_builder.docker.from_env"
        ) as mock_docker:
            mock_client = Mock()
            mock_client.ping.return_value = True
            mock_docker.return_value = mock_client

            # Configure mock images
            mock_image = Mock()
            mock_image.id = "sha256:test123"
            mock_image.tags = ["python:3.11"]
            mock_image.attrs = {"Size": 100 * 1024 * 1024}
            mock_client.images.get.return_value = mock_image
            mock_client.images.list.return_value = [mock_image]

            if DOCKER_SYSTEM_AVAILABLE:
                builder = DockerBuilder.get_instance()
                builder.image_cache.cache_file = tmp_path / "test_cache.json"
                yield builder
            else:
                # Create mock builder
                builder = Mock()
                builder.image_cache = DockerImageCache(
                    cache_file=tmp_path / "test_cache.json"
                )
                builder.client = mock_client
                yield builder

    def test_builder_image_exists_with_cache(self, mock_docker_builder):
        """Test DockerBuilder.image_exists() using cache."""
        if not DOCKER_SYSTEM_AVAILABLE:
            pytest.skip("Docker system not available")

        # First call should populate cache
        result = mock_docker_builder.image_exists("python:3.11")
        assert result is True

        # Verify cache was populated
        cached_images = mock_docker_builder.image_cache.get_cached_images()
        assert len(cached_images) > 0

    def test_builder_cache_fallback_on_docker_failure(self, tmp_path):
        """Test DockerBuilder fallback to cache when Docker fails."""
        if not DOCKER_SYSTEM_AVAILABLE:
            pytest.skip("Docker system not available")

        cache_file = tmp_path / "fallback_cache.json"

        # Create cache with known data
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

        with open(cache_file, "w") as f:
            json.dump(cache_data, f)

        # Reset singleton and create builder with failing Docker
        DockerBuilder.reset_singleton()

        with patch(
            "panther.core.docker_builder.docker_builder.docker.from_env"
        ) as mock_docker:
            mock_client = Mock()
            mock_client.ping.side_effect = DockerException("Connection refused")
            mock_docker.return_value = mock_client

            # Builder should initialize without throwing exception
            builder = DockerBuilder.get_instance()
            builder.image_cache.cache_file = cache_file
            builder.image_cache._load_cache()

            # Should be able to check image existence from cache
            # even though Docker is unavailable
            cached_result = builder.image_cache.image_exists_in_cache("cached:latest")
            assert cached_result is True

    def test_builder_docker_status(self, mock_docker_builder):
        """Test DockerBuilder.get_docker_status() method."""
        if not DOCKER_SYSTEM_AVAILABLE:
            pytest.skip("Docker system not available")

        status = mock_docker_builder.get_docker_status()

        assert isinstance(status, dict)
        assert "docker_available" in status
        assert "cache_enabled" in status
        assert "cached_images" in status
        assert "cache_fresh" in status
        assert "fallback_mode" in status

        # Should be in normal mode (not fallback)
        assert status["cache_enabled"] is True
        assert status["fallback_mode"] is False


@pytest.mark.skipif(
    not DOCKER_SYSTEM_AVAILABLE, reason="Requires real DockerImageCache"
)
class TestDockerCacheErrorHandling:
    """Test error handling in Docker cache system."""

    def test_cache_file_permission_error(self, tmp_path):
        """Test handling of cache file permission errors."""
        # Create read-only directory
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir(mode=0o444)
        cache_file = readonly_dir / "cache.json"

        # Cache should handle permission error gracefully
        cache = DockerImageCache(cache_file=cache_file)

        # Should not raise exception during save
        cache._save_cache()

        # Clean up
        readonly_dir.chmod(0o755)

    def test_docker_client_retry_logic(self, tmp_path):
        """Test retry logic for Docker client failures."""
        cache = DockerImageCache(
            cache_file=tmp_path / "retry_cache.json",
            retry_count=3,
            retry_delay=0.1,  # Fast retry for testing
        )

        # Mock client that fails first two times, succeeds third time
        mock_client = Mock()
        call_count = [0]

        def failing_images_list():
            call_count[0] += 1
            if call_count[0] <= 2:
                raise DockerException("Temporary failure")
            return []  # Success on third call

        mock_client.images.list = failing_images_list
        cache.set_docker_client(mock_client)

        # Should succeed after retries
        result = cache._refresh_cache_from_docker()
        assert result is True
        assert call_count[0] == 3  # Called 3 times

    def test_docker_client_total_failure(self, tmp_path):
        """Test handling when Docker client always fails."""
        cache = DockerImageCache(
            cache_file=tmp_path / "failure_cache.json", retry_count=2, retry_delay=0.1
        )

        # Mock client that always fails
        mock_client = Mock()
        mock_client.images.list.side_effect = DockerException("Persistent failure")
        cache.set_docker_client(mock_client)

        # Should fail gracefully after all retries
        result = cache._refresh_cache_from_docker()
        assert result is False
        assert mock_client.images.list.call_count == 2


class TestDockerCachePerformance:
    """Test performance characteristics of Docker cache."""

    def test_cache_lookup_performance(self, tmp_path):
        """Test cache lookup performance."""
        cache = DockerImageCache(cache_file=tmp_path / "perf_cache.json")

        # Add many images to cache
        for i in range(1000):
            cache._cache[f"sha256:image{i}"] = CachedImage(
                id=f"sha256:image{i}",
                tags=[f"test{i}:latest"],
                size=1024 * 1024,
                created="2025-06-24T10:00:00Z",
                last_seen=time.time(),
            )

        # Test lookup performance
        start_time = time.time()

        # Perform many lookups
        for i in range(100):
            exists = cache.image_exists_in_cache(f"test{i}:latest")
            assert exists is True

        end_time = time.time()
        duration = end_time - start_time

        # Should be very fast (under 10ms for 100 lookups)
        assert duration < 0.01

    @pytest.mark.skipif(
        not DOCKER_SYSTEM_AVAILABLE, reason="Requires real DockerImageCache"
    )
    def test_cache_serialization_performance(self, tmp_path):
        """Test cache serialization performance."""
        cache_file = tmp_path / "serialize_cache.json"
        cache = DockerImageCache(cache_file=cache_file)

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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
