"""Docker Registry Management for PANTHER.

This module provides a registry system to track Docker images, containers,
and build cache information for PANTHER experiments.
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from panther.core.utils.logging_mixin import LoggerMixin


class DockerResourceType(Enum):
    """Types of Docker resources tracked."""

    IMAGE = "image"
    CONTAINER = "container"
    VOLUME = "volume"
    NETWORK = "network"
    BUILD_CACHE = "build_cache"


@dataclass
class DockerResource:
    """Represents a Docker resource tracked by PANTHER."""

    resource_id: str
    resource_type: DockerResourceType
    name: str
    created_at: str
    tags: Dict[str, str]
    metadata: Dict[str, Any]
    experiment_id: Optional[str] = None
    service_name: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data["resource_type"] = self.resource_type.value
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> "DockerResource":
        """Create from dictionary."""
        data["resource_type"] = DockerResourceType(data["resource_type"])
        return cls(**data)


@dataclass
class BuildCacheEntry:
    """Represents a Docker build cache entry."""

    cache_key: str
    image_id: str
    image_tag: str
    build_time: str
    dockerfile_hash: str
    context_hash: str
    size_bytes: int
    layers: List[str]
    build_args: Dict[str, str]
    metadata: Dict[str, Any]

    def is_valid(self, dockerfile_hash: str, context_hash: str) -> bool:
        """Check if cache entry is still valid."""
        return (
            self.dockerfile_hash == dockerfile_hash
            and self.context_hash == context_hash
        )


class DockerRegistry(LoggerMixin):
    """Manages Docker resource registry for PANTHER.

    Tracks Docker images, containers, volumes, and build cache
    to provide better resource management and cleanup.

    The DockerRegistry class is the central, persistent store for anything Panther does with Docker. Its core responsibilities are:

    Resource Tracking
    – Keeps a JSON-backed registry of all Docker resources (images, containers, volumes, networks) that Panther creates or caches.
    – Lets you register/unregister resources, query by type, experiment ID or tags, clean up stale entries, and get high-level stats.

    Build Cache Management
    – Maintains a separate “build cache” JSON file of BuildCacheEntry records (keyed by Dockerfile+context hashes and build-args).
    – Supports finding a valid cached build, adding new cache entries after a successful build, and pruning old entries.
    – Exposed in code via the DockerCacheMixin (which under the covers calls DockerRegistry.find_cached_build and add_build_cache) to speed up rebuilds.

    CLI Integration
    – Powers the panther admin commands for:
    • Showing registry stats (_show_docker_registry)
    • Pruning build cache (_prune_docker_cache)
    • Exporting/importing the entire registry (_export_docker_registry / _import_docker_registry)
    """

    def __init__(self, registry_path: Optional[Path] = None):
        """Initialize Docker registry."""
        super().__init__()

        # Set default registry path
        if registry_path is None:
            registry_path = Path.home() / ".panther" / "docker_registry.json"
        self.logger.debug(f"Using registry path: {registry_path}")
        self.registry_path = Path(registry_path)
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)

        # Load or initialize registry
        self.registry: Dict[str, Dict] = self._load_registry()

        # Build cache
        self.build_cache: Dict[str, BuildCacheEntry] = {}
        self._load_build_cache()

        self.logger.info(f"Docker registry initialized at: {self.registry_path}")

    def _load_registry(self) -> Dict[str, Dict]:
        """Load registry from file or create new one."""
        if self.registry_path.exists():
            try:
                with open(self.registry_path, "r") as f:
                    data = json.load(f)
                    # Convert to DockerResource objects
                    registry = {}
                    for resource_id, resource_data in data.get("resources", {}).items():
                        try:
                            registry[resource_id] = DockerResource.from_dict(
                                resource_data
                            )
                        except Exception as e:
                            self.logger.warning(
                                f"Failed to load resource {resource_id}: {e}"
                            )
                    return {"resources": registry, "metadata": data.get("metadata", {})}
            except Exception as e:
                self.logger.error(f"Failed to load registry: {e}")
                return self._create_new_registry()
        else:
            return self._create_new_registry()

    def _create_new_registry(self) -> Dict[str, Dict]:
        """Create a new empty registry."""
        return {
            "resources": {},
            "metadata": {
                "version": "1.0",
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
            },
        }

    def _save_registry(self) -> None:
        """Save registry to file."""
        try:
            # Update last_updated timestamp
            self.registry["metadata"]["last_updated"] = datetime.now().isoformat()

            # Convert DockerResource objects to dicts
            data = {
                "resources": {
                    rid: res.to_dict()
                    for rid, res in self.registry["resources"].items()
                },
                "metadata": self.registry["metadata"],
            }

            with open(self.registry_path, "w") as f:
                json.dump(data, f, indent=2)

            self.logger.debug("Registry saved successfully")
        except Exception as e:
            self.logger.error(f"Failed to save registry: {e}")

    def _load_build_cache(self) -> None:
        """Load build cache from registry."""
        cache_file = self.registry_path.parent / "docker_build_cache.json"
        if cache_file.exists():
            try:
                with open(cache_file, "r") as f:
                    data = json.load(f)
                    for key, entry_data in data.items():
                        self.build_cache[key] = BuildCacheEntry(**entry_data)
            except Exception as e:
                self.logger.warning(f"Failed to load build cache: {e}")

    def _save_build_cache(self) -> None:
        """Save build cache to file."""
        cache_file = self.registry_path.parent / "docker_build_cache.json"
        try:
            data = {key: asdict(entry) for key, entry in self.build_cache.items()}
            with open(cache_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save build cache: {e}")

    def register_resource(self, resource: DockerResource) -> None:
        """Register a Docker resource."""
        self.registry["resources"][resource.resource_id] = resource
        self._save_registry()
        self.logger.info(f"Registered {resource.resource_type.value}: {resource.name}")

    def unregister_resource(self, resource_id: str) -> None:
        """Unregister a Docker resource."""
        if resource_id in self.registry["resources"]:
            resource = self.registry["resources"].pop(resource_id)
            self._save_registry()
            self.logger.info(
                f"Unregistered {resource.resource_type.value}: {resource.name}"
            )

    def get_resources_by_type(
        self, resource_type: DockerResourceType
    ) -> List[DockerResource]:
        """Get all resources of a specific type."""
        return [
            res
            for res in self.registry["resources"].values()
            if res.resource_type == resource_type
        ]

    def get_resources_by_experiment(self, experiment_id: str) -> List[DockerResource]:
        """Get all resources associated with an experiment."""
        return [
            res
            for res in self.registry["resources"].values()
            if res.experiment_id == experiment_id
        ]

    def get_resources_by_tag(
        self, tag_key: str, tag_value: Optional[str] = None
    ) -> List[DockerResource]:
        """Get resources by tag."""
        resources = []
        for res in self.registry["resources"].values():
            if tag_key in res.tags:
                if tag_value is None or res.tags[tag_key] == tag_value:
                    resources.append(res)
        return resources

    def add_build_cache(self, cache_entry: BuildCacheEntry) -> None:
        """Add a build cache entry."""
        self.build_cache[cache_entry.cache_key] = cache_entry
        self._save_build_cache()
        self.logger.info(f"Added build cache entry: {cache_entry.cache_key}")

    def get_build_cache(self, cache_key: str) -> Optional[BuildCacheEntry]:
        """Get a build cache entry."""
        return self.build_cache.get(cache_key)

    def find_cached_build(
        self, dockerfile_hash: str, context_hash: str, build_args: Dict[str, str]
    ) -> Optional[BuildCacheEntry]:
        """Find a cached build matching the given parameters."""
        # Create cache key from parameters
        cache_key = self._generate_cache_key(dockerfile_hash, context_hash, build_args)

        # Check if we have a direct match
        if cache_key in self.build_cache:
            entry = self.build_cache[cache_key]
            if entry.is_valid(dockerfile_hash, context_hash):
                return entry

        # Check for compatible builds (same dockerfile/context, compatible args)
        for entry in self.build_cache.values():
            if entry.is_valid(dockerfile_hash, context_hash):
                # Check if build args are compatible
                if self._are_build_args_compatible(entry.build_args, build_args):
                    return entry

        return None

    def _generate_cache_key(
        self, dockerfile_hash: str, context_hash: str, build_args: Dict[str, str]
    ) -> str:
        """Generate a cache key for a build."""
        import hashlib

        # Sort build args for consistent hashing
        args_str = json.dumps(build_args, sort_keys=True)

        # Create composite hash
        composite = f"{dockerfile_hash}:{context_hash}:{args_str}"
        return hashlib.sha256(composite.encode()).hexdigest()[:16]

    def _are_build_args_compatible(
        self, cached_args: Dict[str, str], requested_args: Dict[str, str]
    ) -> bool:
        """Check if build args are compatible for cache reuse."""
        # For now, require exact match
        # Could be enhanced to allow compatible variations
        return cached_args == requested_args

    def cleanup_stale_resources(self, max_age_days: int = 7) -> List[str]:
        """Clean up stale resources older than max_age_days."""
        cleaned = []
        current_time = datetime.now()

        for resource_id, resource in list(self.registry["resources"].items()):
            try:
                created_time = datetime.fromisoformat(resource.created_at)
                age_days = (current_time - created_time).days

                if age_days > max_age_days:
                    cleaned.append(resource_id)
                    self.unregister_resource(resource_id)
            except Exception as e:
                self.logger.warning(
                    f"Failed to check age of resource {resource_id}: {e}"
                )

        return cleaned

    def get_registry_stats(self) -> Dict[str, Any]:
        """Get statistics about the registry."""
        stats = {
            "total_resources": len(self.registry["resources"]),
            "by_type": {},
            "cache_entries": len(self.build_cache),
            "registry_size_kb": (
                self.registry_path.stat().st_size / 1024
                if self.registry_path.exists()
                else 0
            ),
        }

        # Count by type
        for resource_type in DockerResourceType:
            count = len(self.get_resources_by_type(resource_type))
            if count > 0:
                stats["by_type"][resource_type.value] = count

        return stats
