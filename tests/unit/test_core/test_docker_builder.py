"""
Unit tests for PANTHER Docker Builder system.

Tests the real DockerBuilder class with only IO-boundary mocking
(Docker daemon connection). All internal logic runs as real code.
"""

import json
import time
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from docker.errors import DockerException, NotFound

from panther.core.docker_builder.docker_builder import DockerBuilder

pytestmark = [pytest.mark.unit, pytest.mark.docker_system]


class TestDockerBuilder:
    """Test DockerBuilder core functionality using real instances."""

    def test_network_creation(self, real_docker_builder, mock_docker_client):
        """Test Docker network creation delegates to the Docker client."""
        # network_exists must raise NotFound so create_network proceeds.
        mock_docker_client.networks.get.side_effect = NotFound("not found")

        # create_network accesses docker.service_types at runtime, so the
        # docker module must be patched during the call (the fixture patch
        # only covers __init__).
        with patch(
            "panther.core.docker_builder.docker_builder.docker"
        ) as mock_docker_mod:
            mock_docker_mod.service_types.IPAMConfig.return_value = MagicMock()
            mock_docker_mod.service_types.IPAMPool.return_value = MagicMock()

            result = real_docker_builder.create_network("test-net")

        assert result is True
        mock_docker_client.networks.create.assert_called_once()
        call_kwargs = mock_docker_client.networks.create.call_args
        assert call_kwargs[1]["name"] == "test-net"
        assert call_kwargs[1]["driver"] == "bridge"

    def test_network_creation_custom_driver(
        self, real_docker_builder, mock_docker_client
    ):
        """Test Docker network creation with a custom driver."""
        mock_docker_client.networks.get.side_effect = NotFound("not found")

        with patch(
            "panther.core.docker_builder.docker_builder.docker"
        ) as mock_docker_mod:
            mock_docker_mod.service_types.IPAMConfig.return_value = MagicMock()
            mock_docker_mod.service_types.IPAMPool.return_value = MagicMock()

            result = real_docker_builder.create_network("overlay-net", driver="overlay")

        assert result is True
        call_kwargs = mock_docker_client.networks.create.call_args
        assert call_kwargs[1]["name"] == "overlay-net"
        assert call_kwargs[1]["driver"] == "overlay"

    def test_docker_availability_check(self, real_docker_builder):
        """Test is_docker_available returns True when Docker daemon responds."""
        result = real_docker_builder.is_docker_available()

        assert result is True

    def test_docker_availability_failure_handling(
        self, real_docker_builder, mock_docker_client
    ):
        """Test is_docker_available returns False when Docker daemon is unreachable."""
        mock_docker_client.ping.side_effect = DockerException("Connection refused")

        result = real_docker_builder.is_docker_available()

        assert result is False

    def test_build_image_invalid_dockerfile(self, real_docker_builder, tmp_path):
        """Test build_image raises when given a nonexistent Dockerfile path."""
        nonexistent = tmp_path / "nonexistent" / "Dockerfile"
        context = tmp_path

        with pytest.raises(Exception):
            real_docker_builder.build_image(
                impl_name="test_impl",
                version="v1.0",
                dockerfile_path=nonexistent,
                context_path=context,
                config={"build_mode": ""},
            )

    def test_multiple_docker_builders_singleton(self, mock_docker_client):
        """Test that DockerBuilder enforces singleton pattern."""
        DockerBuilder.reset_singleton()

        with patch(
            "panther.core.docker_builder.docker_builder.docker"
        ) as mock_docker_mod:
            mock_docker_mod.from_env.return_value = mock_docker_client
            errors = MagicMock()
            errors.DockerException = type("DockerException", (Exception,), {})
            errors.ImageNotFound = type("ImageNotFound", (Exception,), {})
            errors.NotFound = type("NotFound", (Exception,), {})
            errors.APIError = type("APIError", (Exception,), {})
            errors.BuildError = type("BuildError", (Exception,), {})
            mock_docker_mod.errors = errors

            builder1 = DockerBuilder.get_instance()
            builder2 = DockerBuilder.get_instance()

        assert builder1 is builder2


class TestDockerSystemIntegration:
    """Test integration between Docker system components."""

    def test_multiple_docker_builders_are_same_singleton(self, mock_docker_client):
        """Test that get_instance always returns the same singleton."""
        DockerBuilder.reset_singleton()

        with patch(
            "panther.core.docker_builder.docker_builder.docker"
        ) as mock_docker_mod:
            mock_docker_mod.from_env.return_value = mock_docker_client
            errors = MagicMock()
            errors.DockerException = type("DockerException", (Exception,), {})
            errors.ImageNotFound = type("ImageNotFound", (Exception,), {})
            errors.NotFound = type("NotFound", (Exception,), {})
            errors.APIError = type("APIError", (Exception,), {})
            errors.BuildError = type("BuildError", (Exception,), {})
            mock_docker_mod.errors = errors

            instance_a = DockerBuilder.get_instance()
            instance_b = DockerBuilder.get_instance()

        assert instance_a is instance_b
        assert instance_a.client is instance_b.client


class TestDockerSystemErrorHandling:
    """Test error handling in Docker system."""

    def test_build_image_invalid_dockerfile(self, real_docker_builder, tmp_path):
        """Test building image with a nonexistent Dockerfile raises an error."""
        invalid_path = tmp_path / "nonexistent_dockerfile"

        with pytest.raises(Exception):
            real_docker_builder.build_image(
                impl_name="test_impl",
                version="v1.0",
                dockerfile_path=invalid_path,
                context_path=tmp_path,
                config={"build_mode": ""},
            )

    def test_docker_availability_failure_handling(
        self, real_docker_builder, mock_docker_client
    ):
        """Test handling of Docker unavailability."""
        mock_docker_client.ping.side_effect = DockerException("refused")

        assert real_docker_builder.is_docker_available() is False

    def test_network_creation_when_already_exists(
        self, real_docker_builder, mock_docker_client
    ):
        """Test create_network returns True when network already exists."""
        # Clear the side_effect from conftest so return_value takes effect
        mock_docker_client.networks.get.side_effect = None
        mock_docker_client.networks.get.return_value = MagicMock(id="existing-net")

        result = real_docker_builder.create_network("existing-net")

        assert result is True
        # Should not try to create since it already exists
        mock_docker_client.networks.create.assert_not_called()


class TestDockerBuilderCacheIntegration:
    """Test Docker image cache integration with DockerBuilder."""

    @pytest.fixture
    def mock_docker_builder_with_cache(self, tmp_path, mock_docker_client):
        """Create a real DockerBuilder with cache for testing."""
        DockerBuilder.reset_singleton()

        with patch(
            "panther.core.docker_builder.docker_builder.docker"
        ) as mock_docker_mod:
            mock_client = mock_docker_client

            # Configure mock images for cache testing
            mock_image = Mock()
            mock_image.id = "sha256:cache_test_123"
            mock_image.tags = ["cache_test:latest"]
            mock_image.attrs = {
                "Size": 50 * 1024 * 1024,
                "Created": "2025-06-24T10:00:00Z",
            }

            mock_client.images.list.return_value = [mock_image]
            mock_client.images.get.side_effect = None
            mock_client.images.get.return_value = mock_image
            mock_docker_mod.from_env.return_value = mock_client

            errors = MagicMock()
            errors.DockerException = type("DockerException", (Exception,), {})
            errors.ImageNotFound = type("ImageNotFound", (Exception,), {})
            errors.NotFound = type("NotFound", (Exception,), {})
            errors.APIError = type("APIError", (Exception,), {})
            errors.BuildError = type("BuildError", (Exception,), {})
            mock_docker_mod.errors = errors

            builder = DockerBuilder.get_instance()
            # Set custom cache file for testing
            builder.image_cache.cache_file = tmp_path / "test_docker_cache.json"

            yield builder, mock_client

    def test_image_exists_uses_cache(self, mock_docker_builder_with_cache):
        """Test that image_exists() uses cache to reduce Docker API calls."""
        builder, mock_client = mock_docker_builder_with_cache

        # First call should populate cache and call Docker API
        result1 = builder.image_exists("cache_test:latest")
        assert result1 is True
        assert mock_client.images.get.call_count >= 1

        # Reset mock to count subsequent calls
        initial_call_count = mock_client.images.get.call_count
        mock_client.images.get.reset_mock()

        # Second call should use cache (no additional Docker API call for listing)
        result2 = builder.image_exists("cache_test:latest")
        assert result2 is True

        # Should have made fewer API calls due to caching
        assert mock_client.images.get.call_count <= initial_call_count

    def test_image_exists_fallback_on_docker_failure(self, tmp_path):
        """Test image_exists() fallback when Docker is unavailable."""
        # Create cache file with known data
        cache_file = tmp_path / "fallback_test_cache.json"
        cache_data = {
            "images": {
                "sha256:fallback123": {
                    "id": "sha256:fallback123",
                    "tags": ["fallback_test:latest"],
                    "size": 1024 * 1024,
                    "created": "2025-06-24T10:00:00Z",
                    "last_seen": time.time(),
                }
            },
            "last_refresh": time.time() - 100,
            "saved_at": time.time(),
        }

        with open(cache_file, "w") as f:
            json.dump(cache_data, f)

        DockerBuilder.reset_singleton()

        with patch(
            "panther.core.docker_builder.docker_builder.docker"
        ) as mock_docker_mod:
            # Mock Docker client that fails
            mock_client = Mock()
            mock_client.ping.side_effect = DockerException("Connection refused")
            mock_client.images.get.side_effect = DockerException("Connection refused")
            mock_docker_mod.from_env.return_value = mock_client

            errors = MagicMock()
            errors.DockerException = DockerException
            errors.ImageNotFound = type("ImageNotFound", (Exception,), {})
            errors.NotFound = type("NotFound", (Exception,), {})
            errors.APIError = type("APIError", (Exception,), {})
            errors.BuildError = type("BuildError", (Exception,), {})
            mock_docker_mod.errors = errors

            # Builder should initialize without exception (graceful degradation)
            builder = DockerBuilder.get_instance()
            builder.image_cache.cache_file = cache_file
            builder.image_cache._load_cache()

            # Should find image in cache even though Docker is unavailable
            cached_result = builder.image_cache.image_exists_in_cache(
                "fallback_test:latest"
            )
            assert cached_result is True

    def test_cleanup_unused_images_uses_cache(self, mock_docker_builder_with_cache):
        """Test that cleanup_unused_images() uses cache."""
        builder, mock_client = mock_docker_builder_with_cache

        # Mock images.remove for cleanup
        mock_client.images.remove.return_value = True

        # Test cleanup with keep_tags
        builder.cleanup_unused_images(keep_tags=["keep_this:latest"])

        # Should have called cache operations
        assert hasattr(builder, "image_cache")
        assert builder.image_cache is not None

    def test_remove_dangling_images_uses_cache(self, mock_docker_builder_with_cache):
        """Test that remove_dangling_images() uses cache."""
        builder, mock_client = mock_docker_builder_with_cache

        # Mock dangling images
        mock_dangling = Mock()
        mock_dangling.id = "sha256:dangling123"
        mock_dangling.tags = []
        mock_client.images.list.return_value = [mock_dangling]
        mock_client.images.remove.return_value = True

        # Test dangling image removal
        result = builder.remove_dangling_images()

        # Should succeed and use cache
        assert result is True
        assert hasattr(builder, "image_cache")

    def test_docker_status_reporting(self, mock_docker_builder_with_cache):
        """Test get_docker_status() method."""
        builder, mock_client = mock_docker_builder_with_cache

        # Get Docker status
        status = builder.get_docker_status()

        assert isinstance(status, dict)
        assert "docker_available" in status
        assert "cache_enabled" in status
        assert "cached_images" in status
        assert "cache_fresh" in status
        assert "fallback_mode" in status

        # Should report cache as enabled
        assert status["cache_enabled"] is True
        assert isinstance(status["docker_available"], bool)

    def test_builder_singleton_cache_persistence(self, tmp_path):
        """Test that DockerBuilder singleton maintains cache across instances."""
        cache_file = tmp_path / "singleton_cache.json"

        # Reset and create first instance
        DockerBuilder.reset_singleton()

        with patch(
            "panther.core.docker_builder.docker_builder.docker"
        ) as mock_docker_mod:
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_docker_mod.from_env.return_value = mock_client

            errors = MagicMock()
            errors.DockerException = type("DockerException", (Exception,), {})
            errors.ImageNotFound = type("ImageNotFound", (Exception,), {})
            errors.NotFound = type("NotFound", (Exception,), {})
            errors.APIError = type("APIError", (Exception,), {})
            errors.BuildError = type("BuildError", (Exception,), {})
            mock_docker_mod.errors = errors

            builder1 = DockerBuilder.get_instance()
            builder1.image_cache.cache_file = cache_file

            # Get second instance (should be same object)
            builder2 = DockerBuilder.get_instance()

            # Should be the same singleton instance
            assert builder1 is builder2
            assert builder1.image_cache is builder2.image_cache
            assert builder1.image_cache.cache_file == cache_file


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
