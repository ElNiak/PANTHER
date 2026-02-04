# Docker Builder Quickstart Tutorial

## Getting Started with Docker Builder

This tutorial walks you through the essential features of the PANTHER Docker Builder module. You'll learn how to build Docker images, configure caching, and leverage cross-platform build capabilities.

### Prerequisites

Before starting, ensure you have:
- Docker Desktop installed and running
- PANTHER framework installed
- Python 3.8+ environment

Verify your setup:
```bash
docker version
python -c "import panther; print('PANTHER available')"
```

## Step 1: Basic Image Building

Let's start with building a simple Docker image using the Docker Builder singleton.

### Create a Simple Dockerfile

First, create a test directory with a basic Dockerfile:

```bash
mkdir docker_tutorial
cd docker_tutorial
```

Create a `Dockerfile`:
```dockerfile
FROM alpine:latest
RUN apk add --no-cache python3
COPY app.py /app/
WORKDIR /app
CMD ["python3", "app.py"]
```

Create a simple `app.py`:
```python
print("Hello from PANTHER Docker Builder!")
```

### Build Your First Image

Now let's use Docker Builder to build this image:

```python
from pathlib import Path
from panther.core.docker_builder import DockerBuilder

# Get the singleton instance
builder = DockerBuilder(
    build_log_file=True,  # Enable build logging
    enable_cache=True     # Enable caching for faster rebuilds
)

# Configure build settings
config = {
    "build_mode": "",           # Default build mode
    "runtime_mode": "minimal",  # Minimal runtime
    "commit": "tutorial-v1",    # Version identifier
    "dependencies": {}          # No dependencies for this example
}

# Build the image
image_tag = builder.build_image(
    impl_name="hello_app",
    version="v1.0",
    dockerfile_path=Path("Dockerfile"),
    context_path=Path("."),
    config=config
)

print(f"Built image: {image_tag}")
```

**Expected Output:**
```
Built image: hello_app-v1.0:latest-linux-amd64
```

## Step 2: Working with Cache

Docker Builder provides intelligent caching to speed up repeated builds.

### Check Cache Status

```python
# Check if our image exists
exists = builder.image_exists(image_tag)
print(f"Image exists: {exists}")

# Get cache statistics
cache_stats = builder.get_cache_stats()
print(f"Cache entries: {cache_stats['total_images']}")
print(f"Cache fresh: {cache_stats['cache_fresh']}")
```

### Force Rebuild vs Cache Reuse

```python
# Configure for force rebuild
force_config = config.copy()
# This would normally force rebuild, but we'll show cache reuse first

# Rebuild same image (should use cache)
start_time = time.time()
cached_tag = builder.build_image(
    impl_name="hello_app",
    version="v1.0",
    dockerfile_path=Path("Dockerfile"),
    context_path=Path("."),
    config=config
)
cache_time = time.time() - start_time

print(f"Cached build time: {cache_time:.2f} seconds")
```

## Step 3: Advanced Build Modes

Docker Builder supports different build and runtime modes for optimization.

### Debug Build Mode

```python
debug_config = {
    "build_mode": "debug-asan",     # Address sanitizer build (x86 only)
    "runtime_mode": "debug",        # Debug runtime with symbols
    "commit": "tutorial-debug",
    "dependencies": {}
}

# Note: This will fallback to default mode on non-x86 architectures
debug_tag = builder.build_image(
    impl_name="hello_app",
    version="debug",
    dockerfile_path=Path("Dockerfile"),
    context_path=Path("."),
    config=debug_config
)

print(f"Debug image: {debug_tag}")
```

### Production Optimized Build

```python
production_config = {
    "build_mode": "rel-lto",         # Link-time optimization (x86 only)
    "runtime_mode": "minimal",       # Minimal runtime footprint
    "commit": "tutorial-prod",
    "dependencies": {}
}

prod_tag = builder.build_image(
    impl_name="hello_app",
    version="prod",
    dockerfile_path=Path("Dockerfile"),
    context_path=Path("."),
    config=production_config
)

print(f"Production image: {prod_tag}")
```

## Step 4: Cross-Platform Builds

Docker Builder automatically handles cross-platform builds using BuildX when needed.

### Create BuildKit-Enhanced Dockerfile

Create `Dockerfile.buildkit` with BuildKit features:
```dockerfile
# syntax=docker/dockerfile:1
FROM alpine:latest

# Use BuildKit cache mount for package manager
RUN --mount=type=cache,target=/var/cache/apk \
    apk add --no-cache python3

# Use build arguments for platform info
ARG TARGETPLATFORM
ARG BUILDPLATFORM
RUN echo "Building on $BUILDPLATFORM for $TARGETPLATFORM"

COPY app.py /app/
WORKDIR /app
CMD ["python3", "app.py"]
```

### Build for Multiple Platforms

```python
# Configure for cross-platform build
cross_config = {
    "build_mode": "",
    "runtime_mode": "minimal",
    "commit": "tutorial-cross",
    "dependencies": {}
}

# The builder will automatically detect BuildKit features
# and use BuildX for cross-platform capabilities
cross_tag = builder.build_image(
    impl_name="hello_app",
    version="cross",
    dockerfile_path=Path("Dockerfile.buildkit"),
    context_path=Path("."),
    config=cross_config
)

print(f"Cross-platform image: {cross_tag}")
```

## Step 5: Container Management

Docker Builder also provides container lifecycle management.

### Check Container Operations

```python
# Check if container exists
container_name = "hello_app_container"
exists = builder.container_exists(container_name)
print(f"Container '{container_name}' exists: {exists}")

# List PANTHER-related containers
panther_containers = builder.get_panther_containers()
print(f"PANTHER containers: {panther_containers}")
```

### Network Management

```python
# Create a custom network
network_created = builder.create_network(
    network_name="tutorial_network",
    subnet="172.28.1.0/24",
    gateway="172.28.1.1"
)

print(f"Network created: {network_created}")

# Check if network exists
network_exists = builder.network_exists("tutorial_network")
print(f"Network exists: {network_exists}")
```

## Step 6: Error Handling and Diagnostics

Docker Builder provides comprehensive error handling and diagnostics.

### Check Docker Status

```python
# Get comprehensive Docker status
status = builder.get_docker_status()
print("Docker Status:")
for key, value in status.items():
    print(f"  {key}: {value}")
```

### Handle Build Failures

```python
try:
    # Attempt to build with invalid Dockerfile
    invalid_tag = builder.build_image(
        impl_name="invalid_app",
        version="v1.0",
        dockerfile_path=Path("nonexistent_dockerfile"),
        context_path=Path("."),
        config=config
    )
except Exception as e:
    print(f"Build failed as expected: {e}")
    # Builder provides detailed error context
```

### Validate Prerequisites

```python
# Check Docker availability
if builder.is_docker_available():
    print("Docker daemon is responsive")
else:
    print("Docker daemon unavailable - using cache-only mode")
```

## Step 7: Experiment Integration

Docker Builder integrates with PANTHER's experiment tracking system.

### Configure Experiment Context

```python
# Simulate experiment context (normally provided by PANTHER)
class MockExperimentContext:
    def __init__(self):
        self.experiment_dir = Path("experiment_logs")
        self.test_name = "tutorial_test"

    @property
    def test_experiment_dir(self):
        return self.experiment_dir / self.test_name

# Set experiment context
experiment_context = MockExperimentContext()
builder.set_experiment_context(experiment_context)

# Build with experiment tracking
experiment_config = config.copy()
tracked_tag = builder.build_image(
    impl_name="hello_app",
    version="tracked",
    dockerfile_path=Path("Dockerfile"),
    context_path=Path("."),
    config=experiment_config,
    experiment_id="tutorial_experiment_001"
)

print(f"Tracked build: {tracked_tag}")
print(f"Logs in: {experiment_context.test_experiment_dir / 'docker_builds'}")
```

## Step 8: Cleanup and Maintenance

Learn how to maintain your Docker environment.

### Image Cleanup

```python
# Get list of current images
import docker
client = docker.from_env()
images_before = len(client.images.list())

# Remove dangling images
removed = builder.remove_dangling_images()
print(f"Dangling images removed: {removed}")

# Clean up specific images (keep important ones)
keep_tags = ["hello_app-v1.0:latest-linux-amd64"]
builder.cleanup_unused_images(keep_tags)

images_after = len(client.images.list())
print(f"Images before/after cleanup: {images_before}/{images_after}")
```

### Reset for Fresh Start

```python
# Reset singleton for clean state (testing only)
DockerBuilder.reset_singleton()

# Create fresh instance
fresh_builder = DockerBuilder()
print("Fresh builder instance created")
```

## Best Practices Summary

Based on this tutorial, here are key best practices:

### 1. Leverage Caching
- Enable caching for development workflows
- Use force builds sparingly for production
- Monitor cache hit ratios for optimization

### 2. Choose Appropriate Build Modes
- Use default mode for development
- Use debug modes for troubleshooting
- Use optimized modes for production (x86 only)

### 3. Handle Cross-Platform Builds
- Let Docker Builder automatically select build method
- Use BuildKit features when beneficial
- Test on target platforms when possible

### 4. Integrate with Experiments
- Use experiment context for organized logging
- Track builds with experiment IDs
- Review build logs for optimization opportunities

### 5. Monitor System Health
- Check Docker daemon status regularly
- Monitor cache performance and size
- Handle failures gracefully with fallbacks

## Next Steps

Now that you've completed the quickstart tutorial:

1. **Explore Advanced Features**: Review the API reference for specialized methods
2. **Integrate with Your Project**: Adapt the patterns to your specific use case
3. **Optimize Performance**: Tune cache settings and build modes for your workflow
4. **Contribute**: Consider contributing improvements to the Docker Builder module

For more detailed information, see:
- [Module README](../README.md) for architecture overview
- [Developer Guide](../DEVELOPER_GUIDE.md) for development workflows
- [API Reference](../api_reference.md) for complete method documentation
