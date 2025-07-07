"""
Docker Cache Mixin for Build Optimization

This mixin provides caching functionality for Docker builds in PANTHER.
"""

import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from panther.core.docker_builder.caching.docker_registry import (
    BuildCacheEntry,
    DockerRegistry,
    DockerResource,
    DockerResourceType,
)
from panther.core.utils.logging_mixin import LoggerMixin


class DockerBuildCacheMixin(LoggerMixin):
    """
    Mixin that provides Docker caching functionality.

    This mixin integrates with the Docker registry to provide:
    - Build cache management
    - Image layer caching
    - Resource tracking
    """

    def __init__(self, *args, **kwargs):
        """Initialize Docker cache mixin."""
        super().__init__(*args, **kwargs)
        self._docker_registry: Optional[DockerRegistry] = None
        self._cache_enabled = False
        self._cache_hits = 0
        self._cache_misses = 0

    @property
    def docker_registry(self) -> DockerRegistry:
        """Get or create Docker registry instance."""
        if self._docker_registry is None:
            self._docker_registry = DockerRegistry()
        return self._docker_registry

    def enable_cache(self, enabled: bool = True, reason: str = "manual") -> None:
        """Enable or disable Docker build caching.

        Args:
            enabled: Whether to enable caching
            reason: Context for why cache state is changing (for logging)
        """
        # Only log if cache state actually changed
        if not hasattr(self, "_cache_enabled") or self._cache_enabled != enabled:
            self._cache_enabled = enabled
            self.logger.debug(
                f"Docker build cache {'enabled' if enabled else 'disabled'} ({reason})"
            )
        else:
            self._cache_enabled = enabled

    def _calculate_dockerfile_hash(self, dockerfile_path: Path) -> str:
        """Calculate hash of Dockerfile content."""
        try:
            with open(dockerfile_path, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception as e:
            self.logger.warning(f"Failed to hash Dockerfile: {e}")
            return "unknown"

    def _calculate_context_hash(
        self, context_path: Path, exclude_patterns: Optional[List[str]] = None
    ) -> str:
        """Calculate hash of build context."""
        hasher = hashlib.sha256()
        exclude_patterns = exclude_patterns or [".git", "__pycache__", "*.pyc"]

        try:
            # Get all files in context
            files = []
            for item in context_path.rglob("*"):
                if item.is_file():
                    # Check exclusion patterns
                    excluded = False
                    for pattern in exclude_patterns:
                        if pattern in str(item):
                            excluded = True
                            break

                    if not excluded:
                        files.append(item)

            # Sort files for consistent hashing
            files.sort()

            # Hash file paths and contents
            for file_path in files[:100]:  # Limit to first 100 files for performance
                relative_path = file_path.relative_to(context_path)
                hasher.update(str(relative_path).encode())

                # Hash file content (first 1KB)
                try:
                    with open(file_path, "rb") as f:
                        hasher.update(f.read(1024))
                except:
                    pass

            return hasher.hexdigest()
        except Exception as e:
            self.logger.warning(f"Failed to hash build context: {e}")
            return "unknown"

    def check_build_cache(
        self, dockerfile_path: Path, context_path: Path, build_args: Dict[str, str]
    ) -> Optional[str]:
        """
        Check if a cached build exists.

        TODO - Implement more sophisticated cache lookup logic,
        Check if the base configuration of the Dockerfile has changed,
        and if so, invalidate the cache.

        Returns:
            Image ID if cached build exists, None otherwise
        """
        if not self._cache_enabled:
            return None

        # Calculate hashes
        dockerfile_hash = self._calculate_dockerfile_hash(dockerfile_path)
        context_hash = self._calculate_context_hash(context_path)

        # Check registry for cached build
        cached_entry = self.docker_registry.find_cached_build(
            dockerfile_hash, context_hash, build_args
        )

        if cached_entry:
            # Verify image still exists
            try:
                result = subprocess.run(
                    ["docker", "images", "-q", cached_entry.image_id],
                    capture_output=True,
                    text=True,
                )

                if result.returncode == 0 and result.stdout.strip():
                    self._cache_hits += 1
                    self.logger.info(
                        f"Cache hit! Using image: {cached_entry.image_tag}"
                    )
                    return cached_entry.image_id
            except Exception as e:
                self.logger.warning(f"Failed to verify cached image: {e}")

        self._cache_misses += 1
        return None

    def should_use_cached_build(
        self,
        dockerfile_path: Path,
        context_path: Path,
        build_args: Dict[str, str],
        image_tag: str,
        force_build: bool = False,
    ) -> Optional[str]:
        """
        Complete cache checking and decision logic for build operations.

        Args:
            dockerfile_path: Path to Dockerfile
            context_path: Build context path
            build_args: Build arguments for cache key
            image_tag: Target image tag
            docker_client: Docker client for image operations
            force_build: Whether to force rebuild even if cache exists

        Returns:
            Image tag if cache should be used, None if build is needed
        """
        # Check build cache first
        cached_image_id = self.check_build_cache(
            dockerfile_path=dockerfile_path,
            context_path=context_path,
            build_args=build_args,
        )

        if not cached_image_id:
            self.logger.debug(
                f"No cached build found for {image_tag}, proceeding with build."
            )
            self._cache_misses += 1
            return None

        self.logger.info(f"Using cached image for {image_tag}: {cached_image_id}")

        if force_build:
            self.logger.info(
                f"Force build enabled, rebuilding image {image_tag} even if cache exists."
            )
            return None

        try:
            # Extract version from image tag
            tag_version = image_tag.split(":")[-1] if ":" in image_tag else "latest"

            # Tag the cached image with the requested tag
            cached_image = self.client.images.get(cached_image_id)
            cached_image.tag(image_tag.split(":")[0], tag_version)
            return image_tag
        except Exception as e:
            self.logger.warning(f"Failed to use cached image: {e}")
            # Continue with build if cache fails
            return None

    def register_build(
        self,
        image_id: str,
        image_tag: str,
        dockerfile_path: Path,
        context_path: Path,
        build_args: Dict[str, str],
        build_time_seconds: float,
        experiment_id: Optional[str] = None,
    ) -> None:
        """Register a successful build in the cache."""
        if not self._cache_enabled:
            return

        try:
            # Calculate hashes
            dockerfile_hash = self._calculate_dockerfile_hash(dockerfile_path)
            context_hash = self._calculate_context_hash(context_path)

            # Get image details
            image_info = self._get_image_info(image_id)

            # Create cache entry
            cache_key = self.docker_registry._generate_cache_key(
                dockerfile_hash, context_hash, build_args
            )

            cache_entry = BuildCacheEntry(
                cache_key=cache_key,
                image_id=image_id,
                image_tag=image_tag,
                build_time=datetime.now().isoformat(),
                dockerfile_hash=dockerfile_hash,
                context_hash=context_hash,
                size_bytes=image_info.get("size", 0),
                layers=image_info.get("layers", []),
                build_args=build_args,
                metadata={
                    "build_time_seconds": build_time_seconds,
                    "dockerfile_path": str(dockerfile_path),
                    "context_path": str(context_path),
                },
            )

            # Add to registry
            self.docker_registry.add_build_cache(cache_entry)

            # Register as Docker resource
            resource = DockerResource(
                resource_id=image_id,
                resource_type=DockerResourceType.IMAGE,
                name=image_tag,
                created_at=datetime.now().isoformat(),
                tags={"panther": "true", "cached": "true", "cache_key": cache_key},
                metadata={
                    "size_bytes": image_info.get("size", 0),
                    "build_time_seconds": build_time_seconds,
                },
                experiment_id=experiment_id,
            )

            self.docker_registry.register_resource(resource)

            self.logger.info(f"Build cached: {image_tag} (key: {cache_key})")

        except Exception as e:
            self.logger.error(f"Failed to register build in cache: {e}")

    def _get_image_info(self, image_id: str) -> Dict[str, Any]:
        """Get detailed information about a Docker image."""
        try:
            # Get image size
            size_result = subprocess.run(
                ["docker", "image", "inspect", image_id, "--format", "{{.Size}}"],
                capture_output=True,
                text=True,
            )

            size = int(size_result.stdout.strip()) if size_result.returncode == 0 else 0

            # Get layer info
            layers_result = subprocess.run(
                [
                    "docker",
                    "image",
                    "inspect",
                    image_id,
                    "--format",
                    "{{json .RootFS.Layers}}",
                ],
                capture_output=True,
                text=True,
            )

            layers = []
            if layers_result.returncode == 0:
                try:
                    layers = json.loads(layers_result.stdout.strip())
                except:
                    pass

            return {"size": size, "layers": layers}
        except Exception as e:
            self.logger.warning(f"Failed to get image info: {e}")
            return {"size": 0, "layers": []}

    def register_container(
        self,
        container_id: str,
        container_name: str,
        image_id: str,
        service_name: Optional[str] = None,
        experiment_id: Optional[str] = None,
    ) -> None:
        """Register a container in the registry."""
        try:
            resource = DockerResource(
                resource_id=container_id,
                resource_type=DockerResourceType.CONTAINER,
                name=container_name,
                created_at=datetime.now().isoformat(),
                tags={"panther": "true", "image_id": image_id},
                metadata={"image_id": image_id, "status": "running"},
                experiment_id=experiment_id,
                service_name=service_name,
            )

            self.docker_registry.register_resource(resource)

        except Exception as e:
            self.logger.error(f"Failed to register container: {e}")

    def cleanup_experiment_resources(self, experiment_id: str) -> Dict[str, int]:
        """Clean up all Docker resources for an experiment."""
        cleaned = {"containers": 0, "images": 0, "volumes": 0, "networks": 0}

        try:
            resources = self.docker_registry.get_resources_by_experiment(experiment_id)

            for resource in resources:
                try:
                    if resource.resource_type == DockerResourceType.CONTAINER:
                        # Stop and remove container
                        subprocess.run(
                            ["docker", "stop", resource.resource_id],
                            capture_output=True,
                        )
                        subprocess.run(
                            ["docker", "rm", resource.resource_id], capture_output=True
                        )
                        cleaned["containers"] += 1

                    elif resource.resource_type == DockerResourceType.IMAGE:
                        # Remove image
                        subprocess.run(
                            ["docker", "rmi", resource.resource_id], capture_output=True
                        )
                        cleaned["images"] += 1

                    elif resource.resource_type == DockerResourceType.VOLUME:
                        # Remove volume
                        subprocess.run(
                            ["docker", "volume", "rm", resource.resource_id],
                            capture_output=True,
                        )
                        cleaned["volumes"] += 1

                    elif resource.resource_type == DockerResourceType.NETWORK:
                        # Remove network
                        subprocess.run(
                            ["docker", "network", "rm", resource.resource_id],
                            capture_output=True,
                        )
                        cleaned["networks"] += 1

                    # Unregister from registry
                    self.docker_registry.unregister_resource(resource.resource_id)

                except Exception as e:
                    self.logger.warning(
                        f"Failed to clean resource {resource.resource_id}: {e}"
                    )

            self.logger.info(f"Cleaned experiment {experiment_id}: {cleaned}")

        except Exception as e:
            self.logger.error(f"Failed to cleanup experiment resources: {e}")

        return cleaned

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = {
            "enabled": self._cache_enabled,
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "hit_rate": (
                self._cache_hits / (self._cache_hits + self._cache_misses)
                if (self._cache_hits + self._cache_misses) > 0
                else 0
            ),
            "registry_stats": self.docker_registry.get_registry_stats(),
        }

        return stats

    def prune_cache(
        self, max_age_days: int = 0, max_size_gb: float = 0.0
    ) -> Dict[str, int]:
        """Prune old cache entries and images."""
        pruned = {"cache_entries": 0, "images": 0, "size_freed_mb": 0}

        try:
            # Clean stale resources from registry
            stale_resources = self.docker_registry.cleanup_stale_resources(max_age_days)

            # Remove old cache entries
            current_time = datetime.now()
            entries_to_remove = []

            for key, entry in self.docker_registry.build_cache.items():
                try:
                    created_time = datetime.fromisoformat(entry.build_time)
                    age_days = (current_time - created_time).days

                    if age_days > max_age_days:
                        entries_to_remove.append(key)

                        # Try to remove the image
                        try:
                            subprocess.run(
                                ["docker", "rmi", entry.image_id], capture_output=True
                            )
                            pruned["images"] += 1
                            pruned["size_freed_mb"] += entry.size_bytes / (1024 * 1024)
                        except:
                            pass

                except Exception as e:
                    self.logger.warning(f"Failed to check cache entry {key}: {e}")

            # Remove entries from cache
            for key in entries_to_remove:
                del self.docker_registry.build_cache[key]
                pruned["cache_entries"] += 1

            # Save updated cache
            self.docker_registry._save_build_cache()

            self.logger.info(f"Cache pruned: {pruned}")

        except Exception as e:
            self.logger.error(f"Failed to prune cache: {e}")

        return pruned
