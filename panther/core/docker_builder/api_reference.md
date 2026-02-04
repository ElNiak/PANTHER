# Docker Builder API Reference

## Module: panther.core.docker_builder

### Classes

#### DockerBuilder

```python
class DockerBuilder(DockerBuildCacheMixin, LoggerMixin, ErrorHandlerMixin)
```

**Manage Docker operations with singleton pattern and advanced caching.**

A singleton Docker management system that provides comprehensive Docker operations including image building, container management, and network configuration. Implements intelligent caching, cross-platform builds, and resilient fallback mechanisms.

The singleton pattern ensures single Docker client connection per application, shared Docker build cache across components, and consistent configuration.

**Attributes:**
- `_instance`: Singleton instance holder
- `_initialized`: Singleton initialization flag
- `MAX_TAG_LENGTH`: Maximum Docker tag length (100 chars)
- `client`: Docker client connection
- `image_cache`: Docker image cache manager
- `docker_logger`: Docker output parser for build logs

**Examples:**

Basic usage:
```python
# All return same singleton instance
builder = DockerBuilder()
builder_alt = DockerBuilder.get_instance()

# Build image with configuration
tag = builder.build_image(
    impl_name="my_service",
    version="v1.0",
    dockerfile_path=Path("Dockerfile"),
    context_path=Path("."),
    config={"build_mode": "release"}
)
```

Cross-platform builds:
```python
# Automatic buildx for cross-platform
builder.global_config.docker.multi_platform = True
tag = builder.build_image(...)  # Uses buildx automatically
```

**Requires:**
- Docker daemon running and accessible
- docker Python package available
- Build context directory must exist

**Ensures:**
- Single Docker client connection maintained
- Build cache persisted across operations
- Graceful fallback if Docker unavailable
- Thread-safe singleton access

**Complexity:** O(1) for cached operations, O(n) for builds where n is context size
**Concurrency:** Thread-safe singleton, operations may block on Docker I/O

### Methods

#### \_\_init\_\_

```python
def __init__(
    self,
    build_log_file: bool = True,
    enable_cache: bool = True,
    global_config=None,
    experiment_context=None,
) -> None
```

**Initialize DockerBuilder singleton with configuration options.**

Creates or updates the singleton DockerBuilder instance with Docker daemon connection, cache configuration, and logging setup. Subsequent calls update existing instance parameters rather than creating new instances.

**Args:**
- `build_log_file`: Enable Docker build log file creation. Logs saved to experiment-specific directories when experiment_context provided.
- `enable_cache`: Enable Docker build caching for faster rebuilds. Disabled automatically when global_config.docker.force_build_docker_image=True.
- `global_config`: Global configuration object containing Docker settings including buildx preferences, platform targets, and build modes.
- `experiment_context`: Experiment context for organizing build logs in test-specific directory structures.

**Raises:**
- `DockerException`: If Docker daemon connection fails (graceful fallback enabled)

**Examples:**

Basic initialization:
```python
builder = DockerBuilder()  # Uses defaults
```

With configuration:
```python
builder = DockerBuilder(
    build_log_file=True,
    enable_cache=False,  # Force rebuild
    global_config=config_obj
)
```

**Note:** Configuration parameters update existing singleton instance on subsequent calls. Docker daemon unavailability triggers cache-only mode for resilient operation.

#### build_image

```python
def build_image(
    self,
    impl_name: str,
    version: str,
    dockerfile_path: Path,
    context_path: Path,
    config: Dict[str, Any],
    tag_version: str = "latest",
    remove_dangling: bool = False,
    experiment_id: Optional[str] = None,
) -> Optional[str]
```

**Build Docker image with intelligent caching and cross-platform support.**

Builds Docker image using regular Docker API or BuildX for cross-platform builds. Automatically selects build method based on Dockerfile requirements, target platform, and configuration. Supports intelligent caching, build mode validation, and comprehensive error handling with graceful fallbacks.

**Args:**
- `impl_name`: Implementation name for image tagging (e.g., 'my_service')
- `version`: Version string for image tagging (e.g., 'v1.0', 'latest')
- `dockerfile_path`: Absolute path to Dockerfile
- `context_path`: Absolute path to build context directory
- `config`: Build configuration containing:
  - build_mode: Build optimization ('', 'debug-asan', 'rel-lto')
  - runtime_mode: Runtime configuration ('minimal', 'debug', 'profile')
  - dependencies: Dict of service dependencies
  - commit: Git commit or version identifier
  - BASE_IMAGE: Base image name for Dockerfile
- `tag_version`: Docker tag version suffix (default: 'latest')
- `remove_dangling`: Remove dangling images after build (default: False)
- `experiment_id`: Optional experiment identifier for tracking

**Returns:**
Generated Docker image tag on success, None if build failed or skipped

**Raises:**
- `DockerBuildException`: Build operation failed with detailed context
- `PantherException`: Validation error or Docker daemon unavailable

**Examples:**

Basic build:
```python
tag = builder.build_image(
    impl_name="web_service",
    version="v2.1.0",
    dockerfile_path=Path("docker/Dockerfile"),
    context_path=Path("."),
    config={"build_mode": "release"}
)
```

Cross-platform build:
```python
config = {
    "build_mode": "rel-lto",
    "runtime_mode": "debug",
    "dependencies": {"auth": "v1.0"}
}
tag = builder.build_image("api", "latest", dockerfile, context, config)
```

**Requires:**
- Docker daemon accessible and responsive
- Dockerfile exists and readable
- Build context directory accessible
- Sufficient disk space for image layers

**Ensures:**
- Build cache updated with timing and metadata
- Build logs written to experiment-specific directories
- Platform-appropriate build method selected automatically
- Graceful error handling with detailed diagnostics

**Complexity:** O(n) where n is build context size + Dockerfile complexity
**Concurrency:** Blocks on Docker daemon I/O, thread-safe for singleton access

#### image_exists

```python
def image_exists(self, image_tag: str) -> bool
```

**Check if Docker image exists locally with cache-aware lookup.**

Verifies image existence using DockerImageCache for resilient checking with fallback mechanisms when Docker daemon unavailable.

**Args:**
- `image_tag`: Docker image tag to check (e.g., 'nginx:latest')

**Returns:**
True if image exists locally, False otherwise

**Examples:**

Check image existence:
```python
if builder.image_exists('my_app:v1.0'):
    print("Image available")
```

**Complexity:** O(1) cached lookup, O(log n) for cache miss

#### find_dockerfiles

```python
def find_dockerfiles(self, plugins_dir: str) -> Dict[str, Path]
```

**Scan plugins directory for Dockerfiles and return implementation mapping.**

Scans the specified plugins directory and its subdirectories for Dockerfiles in three main locations: services/iut, services/testers, and environments. Returns a dictionary mapping implementation names to Dockerfile paths.

**Args:**
- `plugins_dir`: Path to the plugins directory to scan for Dockerfiles

**Returns:**
Dictionary where keys are implementation names and values are paths to Dockerfiles

**Raises:**
- `ServicePluginNotFound`: If the 'services/iut' directory does not exist
- `EnvironmentPluginNotFound`: If the 'environments' directory does not exist

#### container_exists

```python
def container_exists(self, container_name: str) -> bool
```

**Check if a Docker container with the given name exists.**

**Args:**
- `container_name`: The name of the Docker container to check

**Returns:**
True if the container exists, False otherwise

**Raises:**
- `DockerException`: If there is an error while checking the container existence

#### get_container_ip

```python
def get_container_ip(self, container_name: str) -> Optional[str]
```

**Retrieve the IP address of a Docker container by its name.**

**Args:**
- `container_name`: The name of the Docker container

**Returns:**
The IP address of the container if found, otherwise None

#### create_network

```python
def create_network(
    self,
    network_name: str,
    driver: str = "bridge",
    subnet: str = "172.27.1.0/24",
    gateway: str = "172.27.1.1",
) -> bool
```

**Create a Docker network with the specified parameters.**

**Args:**
- `network_name`: The name of the network to create
- `driver`: The network driver to use (default: "bridge")
- `subnet`: The subnet for the network (default: "172.27.1.0/24")
- `gateway`: The gateway for the network (default: "172.27.1.1")

**Returns:**
True if the network was created successfully or already exists, False otherwise

**Raises:**
- `DockerException`: If there is an error creating the network
- `Exception`: If there is an unexpected error

#### stop_and_remove_container

```python
def stop_and_remove_container(self, container_name: str) -> bool
```

**Stop and remove a Docker container.**

**Args:**
- `container_name`: Name of the Docker container

**Returns:**
True if successful, False otherwise

#### cleanup_unused_images

```python
def cleanup_unused_images(self, keep_tags: List[str]) -> None
```

**Remove Docker images that are not in the keep_tags list.**

Delegates to DockerImageCache for cache-aware cleanup.

**Args:**
- `keep_tags`: List of image tags to retain

#### remove_dangling_images

```python
def remove_dangling_images(self) -> bool
```

**Remove dangling Docker images (images with <none>:<none> tag).**

Delegates to DockerImageCache for cache-aware dangling image removal.

**Returns:**
True if successful, False if an error occurred

### Class Methods

#### get_instance

```python
@classmethod
def get_instance(
    cls,
    build_log_file: bool = True,
    enable_cache: bool = True,
    global_config=None,
    experiment_context=None,
) -> "DockerBuilder"
```

**Get the singleton instance of DockerBuilder.**

This method returns the singleton instance and allows updating configuration parameters even if the instance already exists.

**Args:**
- `build_log_file`: Whether to create log files for Docker builds
- `enable_cache`: Whether to enable Docker build caching
- `global_config`: Global configuration object containing Docker settings
- `experiment_context`: Optional experiment context for organizing build logs

**Returns:**
The singleton DockerBuilder instance (with updated parameters if provided)

#### reset_singleton

```python
@classmethod
def reset_singleton(cls) -> None
```

**Reset the singleton instance.**

This method should only be used in testing scenarios where a fresh instance is needed.

### Utility Methods

#### generate_image_tag

```python
def generate_image_tag(
    self,
    impl_name: str,
    version: str,
    tag_version: str,
    build_mode: str = "",
    runtime_mode: str = "minimal",
    target_platform: str = "",
) -> str
```

**Generate Docker image tag with build and runtime mode differentiation.**

**Args:**
- `impl_name`: Implementation name (e.g., 'picoquic')
- `version`: Version string (e.g., 'v1.0' or 'latest')
- `tag_version`: Tag version (e.g., 'latest', 'stable')
- `build_mode`: Build mode ('', 'debug-asan', 'rel-lto', 'release-static-pgo')
- `runtime_mode`: Runtime mode ('minimal', 'debug', 'profile')
- `target_platform`: Target platform (e.g., 'linux/amd64', 'linux/arm64')

**Returns:**
Complete image tag

**Examples:**
- picoquic-v1.0:latest-debug-asan-debug-linux/amd64 (build_mode + runtime_mode + platform)
- picoquic-v1.0:latest-linux/amd64 (empty build_mode, minimal runtime + platform)
- picoquic-v1.0:latest-rel-lto-profile-linux/amd64 (both modes specified + platform)
- picoquic:latest (no version, minimal runtime, no platform)

#### is_docker_available

```python
def is_docker_available(self) -> bool
```

**Check if Docker daemon is available and responsive.**

**Returns:**
True if Docker is available, False otherwise

#### get_docker_status

```python
def get_docker_status(self) -> Dict[str, Union[bool, str, int]]
```

**Get comprehensive Docker status including cache information.**

**Returns:**
Dictionary with Docker and cache status

#### validate_build_mode_for_architecture

```python
def validate_build_mode_for_architecture(self, build_mode: str) -> str
```

**Validate BUILD_MODE compatibility with host architecture.**

Advanced build modes (rel-lto, debug-asan, release-static-pgo) require x86 architecture. Non-x86 architectures fall back to empty BUILD_MODE for compatibility.

**Args:**
- `build_mode`: The requested build mode

**Returns:**
Validated build mode (empty string if incompatible with architecture)

## Module Exports

The module exports the following public interfaces:

```python
from panther.core.docker_builder import DockerBuilder

# Available classes and functions
__all__ = [
    "DockerBuilder",
]
```

## Dependencies

### External Dependencies
- `docker`: Python Docker SDK for daemon communication
- `pathlib`: Modern path handling utilities
- `subprocess`: System command execution
- `json`: Configuration serialization

### Internal Dependencies
- `panther.core.exceptions`: PANTHER exception hierarchy
- `panther.core.utils.logging_mixin`: Structured logging
- `panther.core.exceptions.error_handler_mixin`: Error management

## Exception Classes

### DockerBuildException
Raised when Docker build operations fail with detailed context.

### PantherException
Base exception for PANTHER framework errors including validation failures.

## Thread Safety

All public methods are thread-safe due to the singleton pattern implementation. Individual operations may block on Docker I/O but maintain thread safety guarantees.

## Performance Notes

- **Cached Operations**: O(1) complexity for cache hits
- **Build Operations**: O(n) complexity where n is context size
- **Memory Usage**: Bounded by cache size and active build contexts
- **I/O Blocking**: Docker operations block but don't affect thread safety
