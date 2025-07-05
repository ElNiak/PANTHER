# Docker Builder Module

## Overview

The Docker Builder module provides a singleton-based Docker management system for the PANTHER framework, implementing intelligent caching, cross-platform builds, and resilient fallback mechanisms. This module serves as the central orchestrator for all Docker operations within PANTHER, ensuring consistent image building, container management, and network configuration across the framework.

## Architecture

### Core Design Principles

**Singleton Pattern**: The DockerBuilder class implements a singleton pattern to ensure single Docker client connection per application, shared build cache across all components, and consistent Docker configuration throughout the system.

**Intelligent Build Selection**: The module automatically selects between regular Docker builds and BuildX cross-platform builds based on:
- Dockerfile BuildKit feature requirements (RUN --mount, COPY --link)
- Target platform vs host platform compatibility
- Configuration preferences and multi-platform settings
- Builder availability and system capabilities

**Resilient Operations**: Built-in fallback mechanisms handle Docker daemon unavailability through:
- Cache-only mode when Docker daemon unreachable
- Graceful degradation for image existence checks
- Persistent cache across application restarts
- Comprehensive error handling with detailed diagnostics

### Module Structure

```
docker_builder/
├── README.md                   # Module documentation (this file)
├── __init__.py                 # Module exports
├── docker_builder.py          # Core DockerBuilder singleton class
├── caching/                    # Build caching subsystem
│   ├── buildkit_cache_mixin.py     # BuildKit cache management
│   ├── docker_build_cache_mixin.py # Build cache coordination
│   ├── docker_image_cache.py       # Image existence caching
│   └── docker_registry.py          # Registry operations cache
├── plugin_mixin/              # Docker operation mixins
│   ├── docker_operations_mixin.py      # Core Docker operations
│   ├── environment_manager_docker_mixing.py  # Environment management
│   └── service_manager_docker_mixin.py       # Service lifecycle
└── utils/                     # Utility functions
    ├── docker_output_parser.py     # Build log parsing
    └── docker_plateform_mixin.py   # Platform detection
```

### Key Components

**DockerBuilder** (docker_builder.py): Primary interface providing:
- Image building with automatic build method selection
- Container lifecycle management (create, start, stop, remove)
- Network operations (create, configure, manage)
- Build cache coordination and optimization
- Cross-platform build support via BuildX

**Caching Subsystem** (caching/): Performance optimization through:
- Build cache validation and reuse decisions
- Image existence tracking with TTL-based expiration
- Registry operations caching for faster lookups
- BuildKit cache mount management for layer optimization

**Plugin Mixins** (plugin_mixin/): Specialized operation mixins for:
- Environment management integration
- Service manager coordination
- Docker operations abstraction layer

**Utilities** (utils/): Supporting functionality including:
- Docker build output parsing and log management
- Platform detection and architecture validation
- Build log organization and experiment tracking

## Build Strategy Logic

### Regular Docker vs BuildX Selection

The module implements intelligent build method selection based on multiple factors:

1. **BuildKit Feature Detection** (Highest Priority)
   - Scans Dockerfile for BuildKit-specific syntax
   - Forces BuildX when RUN --mount, COPY --link, or platform args detected
   - Ensures compatibility with advanced Dockerfile features

2. **Cross-Platform Requirements**
   - Compares host architecture with target platform
   - Uses BuildX for cross-platform builds (ARM64 → AMD64, etc.)
   - Optimizes for efficiency on cross-architecture scenarios

3. **Configuration Preferences**
   - Respects global_config.docker.use_buildx setting
   - Enables BuildX for multi_platform configuration
   - Provides configuration override capabilities

4. **System Availability**
   - Validates BuildX installation and context compatibility
   - Falls back to regular Docker when BuildX unavailable
   - Handles builder instance creation and management

### Caching Strategy

**Multi-Level Cache Architecture**:
- **L1**: In-memory image existence cache with TTL expiration
- **L2**: Build cache validation using dockerfile + context + args hashing
- **L3**: BuildKit cache mounts for layer reuse across builds
- **Registry Cache**: Remote registry operations for faster image pulls

**Cache Invalidation Triggers**:
- Dockerfile content changes (checksum-based detection)
- Build context modifications (timestamp + file hash validation)
- Build arguments changes (configuration hash comparison)
- Force build configuration overrides
- Cache TTL expiration for staleness prevention

## Configuration Integration

### Global Configuration Support

The module integrates with PANTHER's global configuration system:

```python
global_config.docker.force_build_docker_image  # Override cache decisions
global_config.docker.use_buildx                # BuildX preference
global_config.docker.multi_platform            # Multi-platform builds
global_config.docker.target_platform           # Platform override
global_config.docker.buildx_builder            # Builder instance name
```

### Experiment Context Integration

Build operations integrate with experiment tracking:
- Build logs organized by experiment and test context
- Experiment-specific cache isolation
- Test result correlation with build artifacts
- Performance metrics collection per experiment

### Build Mode Support

**Architecture-Aware Build Modes**:
- Standard modes: '' (default), 'debug', 'release'
- Advanced x86 modes: 'rel-lto', 'debug-asan', 'release-static-pgo'
- Automatic fallback for incompatible architecture combinations
- Runtime mode coordination: 'minimal', 'debug', 'profile'

## Performance Characteristics

### Time Complexity
- **Cached Operations**: O(1) for image existence checks, cache hits
- **Build Operations**: O(n) where n = context size + Dockerfile complexity
- **Cache Validation**: O(log n) for hash computation and comparison

### Space Complexity
- **Cache Storage**: O(m) where m = number of unique build configurations
- **Build Context**: O(n) where n = total size of build context files
- **Log Storage**: O(k) where k = number of concurrent experiments

### Concurrency Model
- **Thread-Safe Singleton**: Multiple threads share single instance safely
- **Docker I/O Blocking**: Build operations block on Docker daemon I/O
- **Cache Coordination**: Atomic cache updates prevent race conditions
- **Resource Isolation**: Experiment contexts prevent log interference

## Error Handling Strategy

### Layered Error Management

**Fast-Fail Validation**: Pre-build validation prevents expensive failures:
- Docker daemon connectivity verification
- Dockerfile and context path validation
- Configuration parameter validation
- Architecture compatibility checks

**Graceful Degradation**: Resilient operation under adverse conditions:
- Cache-only mode when Docker daemon unavailable
- Fallback to regular Docker when BuildX fails
- Alternative platform detection when configuration invalid
- Log file creation fallbacks for permission issues

**Comprehensive Diagnostics**: Detailed error context for debugging:
- Build failure analysis with log correlation
- Platform compatibility diagnostic information
- Cache state inspection for troubleshooting
- Configuration validation with specific error details

## Dependencies

### Required Dependencies
- **docker**: Python Docker SDK for daemon communication
- **pathlib**: Modern path handling for cross-platform compatibility
- **subprocess**: BuildX command execution and platform detection
- **json**: Configuration serialization and build argument handling

### Internal Dependencies
- **panther.core.exceptions**: PANTHER exception hierarchy
- **panther.core.utils.logging_mixin**: Structured logging functionality
- **panther.core.exceptions.error_handler_mixin**: Error management coordination

### System Dependencies
- **Docker Daemon**: Must be running and accessible
- **Docker BuildX** (Optional): For cross-platform builds and advanced features
- **Platform Tools**: Native architecture detection utilities

## Thread Safety

The DockerBuilder singleton implementation provides thread-safe access through:
- **Atomic Instance Creation**: Thread-safe singleton pattern implementation
- **Immutable Configuration**: Configuration updates applied atomically
- **Cache Coordination**: Thread-safe cache operations with proper locking
- **Docker Client Sharing**: Single Docker client shared safely across threads

Note: Individual Docker operations may block on I/O but do not compromise thread safety.
