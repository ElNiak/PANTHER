"""Docker Image Cache - Resilient Image Management.

This module provides a caching layer for Docker image operations to prevent
frequent Docker daemon connections and handle connection failures gracefully.

Key Features:
- TTL-based image cache to reduce Docker API calls
- Fallback mechanisms when Docker daemon is unavailable
- Retry logic for transient connection failures
- Persistent cache with JSON storage
- Thread-safe operations
"""

import concurrent.futures
import json
import stat
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union

import docker
from docker.errors import DockerException, NotFound

from panther.core.utils.logging_mixin import LoggerMixin


@dataclass
class CachedImage:
    """Represents a cached Docker image with metadata."""

    id: str
    tags: List[str]
    size: int
    created: str
    last_seen: float

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "CachedImage":
        """Create from dictionary."""
        return cls(**data)


class DockerImageCache(LoggerMixin):
    """Thread-safe Docker image cache with TTL and fallback mechanisms.

    Provides resilient Docker image operations that can handle:
    - Docker daemon connection failures
    - Transient network issues
    - High-frequency image list operations
    - Cache persistence across application restarts
    """

    def __init__(
        self,
        cache_ttl: int = 300,  # 5 minutes default TTL
        cache_file: Optional[Path] = None,
        retry_count: int = 3,
        retry_delay: float = 1.0,
        target_platform: Optional[str] = None,
    ):
        """Initialize Docker image cache with platform-aware caching.

        Args:
            cache_ttl: Time-to-live for cached images in seconds
            cache_file: Path to persistent cache file (optional)
            retry_count: Number of retry attempts for Docker operations
            retry_delay: Delay between retry attempts in seconds
            target_platform: Target platform for cache isolation (e.g., 'linux/amd64')
        """
        super().__init__()
        self.__init_logger__("docker_image_cache")

        self.cache_ttl = cache_ttl
        self.target_platform = target_platform or self._detect_host_platform()

        # Generate platform-aware cache file path
        self.cache_file = self._get_platform_cache_file(cache_file)

        self.retry_count = retry_count
        self.retry_delay = retry_delay

        # Thread-safe cache storage
        self._cache: Dict[str, CachedImage] = {}
        self._cache_lock = threading.RLock()
        self._last_refresh = 0.0

        # Docker client (will be set by DockerBuilder)
        self._docker_client: Optional[docker.DockerClient] = None

        # Initialize secure cache file and directory
        self._initialize_secure_cache_file()

        # Load existing cache
        self._load_cache()

        self.logger.info(
            f"Docker image cache initialized with TTL={cache_ttl}s, "
            f"platform={self.target_platform}, cache_file={self.cache_file}"
        )

    def _detect_host_platform(self) -> str:
        """Detect the host platform for platform-aware caching.

        Returns:
            str: Platform string in Docker format (e.g., 'linux/amd64')
        """
        import platform

        # Map Python platform names to Docker platform format
        arch_map = {
            "x86_64": "amd64",
            "amd64": "amd64",
            "aarch64": "arm64",
            "arm64": "arm64",
            "armv7l": "arm/v7",
        }

        system = platform.system().lower()
        machine = platform.machine().lower()

        docker_arch = arch_map.get(machine, machine)
        return f"{system}/{docker_arch}"

    def _get_platform_cache_file(self, cache_file: Optional[Path]) -> Path:
        """Generate platform-specific cache file path.

        Args:
            cache_file: Optional cache file path override

        Returns:
            Path: Platform-specific cache file path
        """
        if cache_file:
            # If explicit cache file provided, add platform suffix
            platform_suffix = self.target_platform.replace("/", "-")
            cache_dir = cache_file.parent
            cache_name = cache_file.stem
            cache_ext = cache_file.suffix
            return cache_dir / f"{cache_name}-{platform_suffix}{cache_ext}"
        else:
            # Default platform-specific cache file
            platform_suffix = self.target_platform.replace("/", "-")
            return (
                Path.home() / ".panther" / f"docker_image_cache-{platform_suffix}.json"
            )

    def set_target_platform(self, platform: str) -> None:
        """Update target platform and reinitialize cache file if needed.

        Args:
            platform: New target platform (e.g., 'linux/arm64')
        """
        if platform != self.target_platform:
            old_platform = self.target_platform
            old_cache_file = self.cache_file

            # Update platform and cache file path
            self.target_platform = platform
            self.cache_file = self._get_platform_cache_file(None)

            # Save current cache before switching
            if self._cache:
                self._save_cache()

            # Clear cache and reload for new platform
            with self._cache_lock:
                self._cache = {}
                self._last_refresh = 0.0

            # Initialize new platform cache
            self._initialize_secure_cache_file()
            self._load_cache()

            self.logger.info(
                f"Switched cache platform: {old_platform} -> {platform}, "
                f"cache_file: {old_cache_file} -> {self.cache_file}"
            )

    def _initialize_secure_cache_file(self) -> None:
        """Initialize cache file and directory with secure permissions.

        Creates cache directory with 700 permissions (owner read/write/execute only)
        and ensures cache file has 600 permissions (owner read/write only).
        """
        try:
            # Create cache directory with secure permissions (700 - owner only)
            self.cache_file.parent.mkdir(parents=True, exist_ok=True, mode=0o700)

            # Ensure directory has correct permissions (in case it already existed)
            self.cache_file.parent.chmod(0o700)

            # If cache file exists, ensure it has secure permissions
            if self.cache_file.exists():
                self.cache_file.chmod(0o600)  # Owner read/write only
                self.logger.debug(
                    "Secured existing cache file permissions: %s", self.cache_file
                )

            self.logger.debug(
                "Cache directory initialized with secure permissions: %s",
                self.cache_file.parent,
            )

        except (OSError, PermissionError) as e:
            self.logger.error(f"Failed to initialize secure cache file: {e}")
            # Don't raise exception - allow cache to work without security if necessary
            self.logger.warning("Cache will operate with default permissions")

    def _validate_cache_file_security(self) -> bool:
        """Validate cache file and directory have secure permissions.

        Returns:
            bool: True if permissions are secure, False otherwise
        """
        try:
            # Check directory permissions (should be 700)
            dir_stat = self.cache_file.parent.stat()
            dir_perms = stat.filemode(dir_stat.st_mode)[1:4]  # Owner perms (chars 1-3)

            if dir_perms != "rwx":
                self.logger.warning(
                    f"Cache directory permissions not secure: {dir_perms} "
                    f"(expected: rwx, path: {self.cache_file.parent})"
                )
                return False

            # Check file permissions if file exists (should be 600)
            if self.cache_file.exists():
                file_stat = self.cache_file.stat()
                file_perms = stat.filemode(file_stat.st_mode)[
                    1:4
                ]  # Owner perms (chars 1-3)

                if file_perms != "rw-":
                    self.logger.warning(
                        f"Cache file permissions not secure: {file_perms} "
                        f"(expected: rw-, path: {self.cache_file})"
                    )
                    return False

            self.logger.debug("Cache file security validation passed")
            return True

        except (OSError, AttributeError) as e:
            self.logger.error(f"Failed to validate cache file security: {e}")
            return False

    def set_docker_client(self, client: docker.DockerClient):
        """Set the Docker client for cache operations."""
        self._docker_client = client
        self.logger.debug("Docker client set for image cache")

    def _load_cache(self):
        """Load cache from persistent storage with security validation."""
        # Validate cache file security
        if not self._validate_cache_file_security():
            self.logger.warning(
                "Cache file security validation failed, proceeding anyway"
            )

        if not self.cache_file.exists():
            self.logger.debug("No cache file found, starting with empty cache")
            return

        try:
            with open(self.cache_file, "r") as f:
                data = json.load(f)

            # Validate cache file version for future compatibility
            cache_version = data.get("version", "unknown")
            if cache_version != "1.0" and cache_version != "unknown":
                self.logger.warning(
                    f"Unknown cache version: {cache_version}, proceeding anyway"
                )

            with self._cache_lock:
                self._cache = {
                    image_id: CachedImage.from_dict(image_data)
                    for image_id, image_data in data.get("images", {}).items()
                }
                self._last_refresh = data.get("last_refresh", 0.0)

            # Clean expired entries
            self._clean_expired_entries()

            self.logger.info(
                f"Loaded {len(self._cache)} cached images from {self.cache_file}"
            )

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            self.logger.warning(f"Failed to load cache file: {e}, starting fresh")
            with self._cache_lock:
                self._cache = {}
                self._last_refresh = 0.0

    def _save_cache(self) -> None:
        """Save cache to persistent storage using atomic writes.

        Uses atomic write pattern (write to temp file, then rename) to prevent
        cache corruption from concurrent access or interrupted writes.
        """
        temp_file = None
        try:
            cache_data = {
                "images": {
                    image_id: image.to_dict() for image_id, image in self._cache.items()
                },
                "last_refresh": self._last_refresh,
                "saved_at": time.time(),
                "version": "1.0",  # Add version for future compatibility
            }

            # Create temporary file in same directory for atomic rename
            temp_file = self.cache_file.with_suffix(".tmp")

            # Write to temporary file with secure permissions
            with open(temp_file, "w") as f:
                json.dump(cache_data, f, indent=2)

            # Set secure permissions on temp file
            temp_file.chmod(0o600)

            # Atomic rename (replaces original file)
            temp_file.replace(self.cache_file)

            self.logger.debug(
                "Atomically saved %d images to cache file", len(self._cache)
            )

        except (OSError, json.JSONEncodeError, PermissionError) as e:
            self.logger.error(f"Failed to save cache file: {e}")

            # Clean up temp file if it exists
            if temp_file and temp_file.exists():
                try:
                    temp_file.unlink()
                    self.logger.debug("Cleaned up temporary cache file after error")
                except OSError as cleanup_error:
                    self.logger.warning(f"Failed to cleanup temp file: {cleanup_error}")

        except Exception as e:
            self.logger.error(f"Unexpected error saving cache: {e}")

            # Clean up temp file if it exists
            if temp_file and temp_file.exists():
                try:
                    temp_file.unlink()
                except OSError:
                    pass  # Best effort cleanup

    def _clean_expired_entries(self):
        """Remove expired entries from cache."""
        current_time = time.time()
        expired_keys = []

        with self._cache_lock:
            for image_id, image in self._cache.items():
                if current_time - image.last_seen > self.cache_ttl:
                    expired_keys.append(image_id)

            for key in expired_keys:
                del self._cache[key]

        if expired_keys:
            self.logger.debug("Cleaned %d expired cache entries", len(expired_keys))

    def _is_cache_fresh(self) -> bool:
        """Check if cache is still within TTL."""
        return (time.time() - self._last_refresh) < self.cache_ttl

    def _refresh_cache_from_docker(self) -> bool:
        """Refresh cache by fetching current images from Docker daemon.

        Returns:
            bool: True if refresh successful, False otherwise
        """
        if not self._docker_client:
            self.logger.warning("No Docker client available for cache refresh")
            return False

        for attempt in range(1, self.retry_count + 1):
            try:
                self.logger.debug(
                    "Refreshing image cache (attempt %d/%d)",
                    attempt,
                    self.retry_count,
                )

                # Use low-level API to avoid per-image inspect_image() calls that hang.
                # self._docker_client.images.list() calls get() per image which does inspect.
                # self._docker_client.api.images() returns raw dicts without inspect.
                # NOTE: Do not use ThreadPoolExecutor as a context manager here.
                # If future.result() times out, __exit__ calls shutdown(wait=True),
                # which blocks indefinitely when Docker is hung.
                executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
                future = executor.submit(self._docker_client.api.images, all=False)
                try:
                    raw_images = future.result(timeout=30)
                except concurrent.futures.TimeoutError:
                    self.logger.error("Docker image list timed out after 30 seconds")
                    executor.shutdown(wait=False, cancel_futures=True)
                    continue
                finally:
                    executor.shutdown(wait=False)

                current_time = time.time()

                with self._cache_lock:
                    # Clear existing cache
                    self._cache.clear()

                    # Populate with current images from raw API response
                    for raw_image in raw_images:
                        image_id = raw_image.get("Id", "")
                        tags = raw_image.get("RepoTags") or []
                        cached_image = CachedImage(
                            id=image_id,
                            tags=tags,
                            size=raw_image.get("Size", 0),
                            created=raw_image.get("Created", ""),
                            last_seen=current_time,
                        )
                        self._cache[image_id] = cached_image

                    self._last_refresh = current_time

                self.logger.info(
                    f"Successfully refreshed cache with {len(self._cache)} images"
                )

                # Save to persistent storage
                self._save_cache()
                return True

            except DockerException as e:
                self.logger.warning(
                    f"Docker connection failed on attempt {attempt}/{self.retry_count}: {e}"
                )
                if attempt < self.retry_count:
                    time.sleep(self.retry_delay * attempt)  # Exponential backoff
                continue

            except Exception as e:
                self.logger.error(f"Unexpected error refreshing cache: {e}")
                break

        self.logger.error("Failed to refresh cache after all retry attempts")
        return False

    def get_cached_images(self, force_refresh: bool = False) -> List[CachedImage]:
        """Get list of cached Docker images.

        Args:
            force_refresh: Force refresh from Docker daemon even if cache is fresh

        Returns:
            List of cached images (may be empty if Docker is unavailable)
        """
        # Clean expired entries first
        self._clean_expired_entries()

        # Check if refresh is needed
        if force_refresh or not self._is_cache_fresh():
            self._refresh_cache_from_docker()

        with self._cache_lock:
            return list(self._cache.values())

    def image_exists_in_cache(self, image_tag: str) -> Optional[bool]:
        """Check if an image exists in the current in-memory cache.

        Does NOT trigger a cache refresh — returns None when cache is stale.

        Args:
            image_tag: Docker image tag to check

        Returns:
            True if found, False if not found in fresh cache,
            None if cache is stale (caller should use Docker API directly)
        """
        with self._cache_lock:
            for image in self._cache.values():
                if image_tag in image.tags:
                    self.logger.debug("Image '%s' found in cache", image_tag)
                    return True

        # If cache is fresh and image not found, it definitively doesn't exist
        if self._is_cache_fresh():
            self.logger.debug("Image '%s' not found in fresh cache", image_tag)
            return False

        # Cache stale — can't determine from cache alone
        self.logger.debug(
            "Cache stale, cannot determine if image '%s' exists from cache",
            image_tag,
        )
        return None

    def get_image_by_tag(self, image_tag: str) -> Optional[CachedImage]:
        """Get cached image by tag.

        Args:
            image_tag: Docker image tag

        Returns:
            CachedImage if found, None otherwise
        """
        with self._cache_lock:
            for image in self._cache.values():
                if image_tag in image.tags:
                    return image
        return None

    def get_images_by_filter(self, **filters) -> List[CachedImage]:
        """Get cached images matching filters.

        Supported filters:
        - dangling: bool (images with no tags)
        - tag_pattern: str (images with tags matching pattern)

        Args:
            **filters: Filter criteria

        Returns:
            List of matching cached images
        """
        results = []

        with self._cache_lock:
            for image in self._cache.values():
                # Filter by dangling status
                if "dangling" in filters:
                    is_dangling = not image.tags or image.tags == ["<none>:<none>"]
                    if filters["dangling"] != is_dangling:
                        continue

                # Filter by tag pattern
                if "tag_pattern" in filters:
                    pattern = filters["tag_pattern"]
                    if not any(pattern in tag for tag in image.tags):
                        continue

                results.append(image)

        return results

    def invalidate_cache(self):
        """Force cache invalidation."""
        with self._cache_lock:
            self._cache.clear()
            self._last_refresh = 0.0
        self.logger.info("Docker image cache invalidated")

    def remove_image(self, image_tag: str) -> bool:
        """Remove a single image entry from the cache.

        Returns True if the image was found and removed, False otherwise.
        """
        with self._cache_lock:
            removed = self._cache.pop(image_tag, None) is not None
        if removed:
            self.logger.info("Removed image '%s' from cache", image_tag)
        else:
            self.logger.debug("Image '%s' was not in cache", image_tag)
        return removed

    def get_cache_stats(self) -> Dict[str, Union[int, float, str, bool]]:
        """Get cache statistics including security status.

        Returns:
            Dictionary with cache statistics and security information
        """
        current_time = time.time()

        with self._cache_lock:
            cache_age = current_time - self._last_refresh
            total_size = sum(image.size for image in self._cache.values())
            security_valid = self._validate_cache_file_security()

            return {
                "total_images": len(self._cache),
                "cache_age_seconds": cache_age,
                "cache_fresh": self._is_cache_fresh(),
                "total_size_mb": total_size / (1024 * 1024),
                "cache_file": str(self.cache_file),
                "cache_secure": security_valid,
                "last_refresh": (
                    datetime.fromtimestamp(self._last_refresh).isoformat()
                    if self._last_refresh
                    else "never"
                ),
            }

    def image_exists(self, image_tag: str, docker_client=None) -> bool:
        """Check if a Docker image with the given tag exists locally.

        Uses cache when fresh, falls back to fast targeted Docker API check.

        :param image_tag: Tag of the Docker image.
        :param docker_client: Docker client instance (optional, uses internal client if available).
        :return: True if exists, else False.
        """
        # Quick check: is it already in our cache?
        cached_result = self.image_exists_in_cache(image_tag)
        if cached_result is not None:
            self.logger.debug(
                "Image '%s' cache lookup: %s",
                image_tag,
                "found" if cached_result else "not found",
            )
            return cached_result

        # Cache stale/miss — do a fast targeted Docker API check (O(1))
        client = docker_client or self._docker_client
        if client is None:
            self.logger.error(
                "Docker client is not available. Cannot check if image exists."
            )
            return False

        self.logger.debug(
            "Cache miss for image '%s', checking with Docker API", image_tag
        )

        try:
            client.images.get(image_tag)
            self.logger.debug("Image '%s' found locally via Docker API.", image_tag)
            return True
        except NotFound:
            self.logger.debug("Image '%s' not found locally.", image_tag)
            return False
        except DockerException as e:
            self.logger.error("Error checking if image exists '%s': %s", image_tag, e)
            return False

    def cleanup_unused_images(self, keep_tags: List[str], docker_client=None):
        """Remove Docker images that are not in the keep_tags list.

        Uses cached image list with fallback to direct Docker API.

        :param keep_tags: List of image tags to retain.
        :param docker_client: Docker client instance (optional, uses internal client if available).
        """
        # Use provided client or internal client
        client = docker_client or self._docker_client
        if client is None:
            self.logger.error(
                "Docker client is not available. Cannot cleanup unused images."
            )
            return

        try:
            # Try to get images from cache first
            cached_images = self.get_cached_images(force_refresh=True)

            if cached_images:
                self.logger.info(
                    f"Using cached image list for cleanup ({len(cached_images)} images)"
                )
                images_to_process = cached_images
            else:
                # Fallback to direct Docker API call
                self.logger.warning(
                    "Cache unavailable, falling back to direct Docker API"
                )
                docker_images = client.images.list()
                # Convert to our format for consistent processing
                images_to_process = []
                for docker_image in docker_images:
                    images_to_process.append(
                        type(
                            "CachedImage",
                            (),
                            {"id": docker_image.id, "tags": docker_image.tags},
                        )()
                    )

            for image in images_to_process:
                image_tags = image.tags
                # If image has no tags, consider it for removal
                if not image_tags:
                    self.logger.info("Removing untagged image '%s'", image.id[:12])
                    client.images.remove(image.id, force=True)
                    continue

                for tag in image_tags:
                    if tag not in keep_tags:
                        self.logger.info("Removing unused Docker image '%s'", tag)
                        client.images.remove(tag, force=True)

            # Invalidate cache after cleanup
            self.invalidate_cache()

        except DockerException as e:
            self.logger.error("Error during Docker image cleanup: %s", e)
        except Exception as e:
            self.logger.error("Unexpected error during Docker image cleanup: %s", e)

    def remove_dangling_images(self, docker_client=None):
        """Remove dangling Docker images (images with <none>:<none> tag).

        Uses cached image list with fallback to direct Docker API.

        These images are typically created when building a new image with the same tag
        as an existing one, causing the original image to lose its tag.

        :param docker_client: Docker client instance (optional, uses internal client if available).
        :return: True if successful, False if an error occurred
        """
        # Use provided client or internal client
        client = docker_client or self._docker_client
        if client is None:
            self.logger.error(
                "Docker client is not available. Cannot remove dangling images."
            )
            return False

        try:
            # Try to get dangling images from cache first
            dangling_images = self.get_images_by_filter(dangling=True)

            if dangling_images:
                self.logger.info(
                    f"Found {len(dangling_images)} dangling images from cache"
                )
            else:
                # Fallback to direct Docker API call
                self.logger.debug("No dangling images in cache, checking Docker API")
                try:
                    docker_dangling = client.images.list(filters={"dangling": True})
                    # Convert to our format
                    dangling_images = []
                    for docker_image in docker_dangling:
                        dangling_images.append(
                            type(
                                "CachedImage",
                                (),
                                {"id": docker_image.id, "tags": docker_image.tags},
                            )()
                        )
                except DockerException as api_error:
                    self.logger.error(f"Docker API call failed: {api_error}")
                    # Try to use any cached data even if stale
                    cached_images = self.get_cached_images(force_refresh=False)
                    dangling_images = [
                        img
                        for img in cached_images
                        if not img.tags or img.tags == ["<none>:<none>"]
                    ]
                    if dangling_images:
                        self.logger.warning(
                            f"Using stale cache data, found {len(dangling_images)} dangling images"
                        )
                    else:
                        self.logger.error(
                            "No cached data available and Docker API failed"
                        )
                        return False

            if not dangling_images:
                self.logger.debug("No dangling images found to remove.")
                return True

            # Remove each dangling image
            for image in dangling_images:
                self.logger.info("Removing dangling image %s", image.id[:12])
                client.images.remove(image.id, force=False)

            self.logger.info(
                "Successfully removed %s dangling images", len(dangling_images)
            )

            # Invalidate cache after cleanup
            self.invalidate_cache()
            return True

        except DockerException as e:
            self.logger.error("Error removing dangling images: %s", e)
            return False
        except OSError as e:
            self.logger.error("Unexpected error removing dangling images: %s", e)
            return False
