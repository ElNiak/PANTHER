"""Docker Builder Module - Container Build System for PANTHER.

Singleton Docker management system providing image building, container
lifecycle management, intelligent caching, and cross-platform support
for protocol testing environments.

Architecture::

    DockerBuilder (singleton)
        │
        ├── BaseImageManagerMixin    ── pre-built base images for common stacks
        ├── DockerBuildCacheMixin    ── layer-aware build caching with TTL
        └── Plugin Integration       ── per-plugin Dockerfile generation
            │
            ├── base_images/         ── shared base image definitions
            ├── caching/             ── build cache management
            ├── plugin_mixin/        ── plugin-specific Docker integration
            └── utils/               ── Docker client utilities

Key Capabilities:
    - **Singleton Pattern**: single Docker client instance per application
    - **Intelligent Caching**: layer-aware build cache with TTL invalidation
    - **Cross-Platform**: resilient fallback mechanisms for ARM/x86 builds
    - **Plugin Integration**: each plugin contributes Dockerfile fragments
      via mixin-based architecture

Example::

    from panther.core.docker_builder import DockerBuilder

    builder = DockerBuilder.get_instance()
    builder.build_image(tag="panther/picoquic:latest", path="./docker")

See Also:
    `panther.core.command_processor` -- command generation for containers
    `panther.plugins.environments` -- environment deployment using Docker
"""

from .docker_builder import DockerBuilder

__all__ = [
    "DockerBuilder",
]
