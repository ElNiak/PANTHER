# Docker Builder Developer Guide

## Development Environment Setup

### Prerequisites

Ensure the following are installed and configured:

- **Python 3.8+** with pip package manager
- **Docker Desktop** or Docker daemon running
- **Docker BuildX** plugin for cross-platform builds (optional but recommended)
- **Git** for version control and dependency management

### Installation

```bash
# Clone PANTHER repository
git clone <panther-repo-url>
cd panther

# Install Python dependencies
pip install -r requirements.txt

# Verify Docker daemon is running
docker version

# Verify BuildX availability (optional)
docker buildx version
```

### Docker Configuration

Configure Docker for optimal development:

```bash
# Enable BuildKit for enhanced features
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

# Configure Docker daemon settings (optional)
# Edit ~/.docker/daemon.json:
{
  "experimental": true,
  "features": {
    "buildkit": true
  }
}
```

## Running Tests

### Unit Tests

```bash
# Run docker_builder module tests
python -m pytest tests/core/docker_builder/ -v

# Run specific test class
python -m pytest tests/core/docker_builder/test_docker_builder.py::TestDockerBuilder -v

# Run with coverage
python -m pytest tests/core/docker_builder/ --cov=panther.core.docker_builder --cov-report=html
```

### Integration Tests

```bash
# Run integration tests (requires Docker daemon)
python -m pytest tests/integration/docker_builder/ -v

# Run cross-platform build tests
python -m pytest tests/integration/docker_builder/test_buildx_integration.py -v
```

### Doctests

```bash
# Run doctests in module files
python -m doctest panther/core/docker_builder/docker_builder.py -v

# Run all doctests in module
find panther/core/docker_builder -name "*.py" -exec python -m doctest {} \;
```

## Development Workflow

### Code Style and Linting

```bash
# Format code with black
black panther/core/docker_builder/

# Sort imports with isort
isort panther/core/docker_builder/

# Lint with flake8
flake8 panther/core/docker_builder/

# Type checking with mypy
mypy panther/core/docker_builder/
```

### Documentation Linting

```bash
# Install documentation tools
pip install markdownlint-cli vale

# Lint markdown files
markdownlint panther/core/docker_builder/**/*.md

# Check writing style with Vale
vale panther/core/docker_builder/README.md
```

## Debugging

### Debug Mode Setup

```bash
# Enable verbose Docker logging
export DOCKER_PY_VERBOSE=1

# Enable debug logging in PANTHER
export PANTHER_LOG_LEVEL=DEBUG

# Run with debug configuration
python -m panther.core.docker_builder.docker_builder
```

### Common Debug Scenarios

**Build Failures**:
```bash
# Check Docker daemon status
docker system info

# Inspect build logs
ls -la docker_builds/  # Check experiment log directory
tail -f docker_builds/latest_build.log

# Test BuildX availability
docker buildx inspect default
```

**Cache Issues**:
```python
# In Python REPL
from panther.core.docker_builder import DockerBuilder

builder = DockerBuilder()
stats = builder.get_cache_stats()
print(f"Cache stats: {stats}")

# Clear cache if needed
builder.clear_cache()
```

**Platform Issues**:
```bash
# Check platform detection
python -c "from panther.core.docker_builder.docker_builder import DockerBuilder; print(DockerBuilder()._get_target_platform())"

# Test cross-platform builds
docker buildx ls
docker buildx create --name test-builder --use
```

### Logging Configuration

Configure detailed logging for debugging:

```python
import logging
logging.getLogger("docker").setLevel(logging.DEBUG)
logging.getLogger("panther.core.docker_builder").setLevel(logging.DEBUG)
```

## Adding New Features

### Creating New Mixins

1. **Create mixin file** in appropriate subdirectory:
   ```bash
   touch panther/core/docker_builder/plugin_mixin/new_feature_mixin.py
   ```

2. **Implement mixin class** with proper inheritance:
   ```python
   from panther.core.utils.logging_mixin import LoggerMixin

   class NewFeatureMixin(LoggerMixin):
       """Provide new feature functionality for Docker operations."""

       def new_feature_method(self):
           """Implement new feature with proper docstring."""
           pass
   ```

3. **Add tests** for new functionality:
   ```bash
   touch tests/core/docker_builder/test_new_feature_mixin.py
   ```

### Extending Build Logic

1. **Identify extension point** in `DockerBuilder` class
2. **Add configuration support** in global config integration
3. **Implement feature detection** if needed
4. **Add comprehensive error handling**
5. **Update cache logic** if build behavior changes

### Cache System Extensions

1. **Understand cache architecture** (L1/L2/L3 levels)
2. **Implement cache-aware operations**
3. **Add cache invalidation triggers**
4. **Test cache isolation between different configurations**

## Testing Guidelines

### Test Structure

Organize tests by functionality:
```
tests/core/docker_builder/
├── test_docker_builder.py         # Core class tests
├── test_build_logic.py            # Build method tests
├── test_caching.py                # Cache functionality
├── test_platform_detection.py     # Platform/architecture tests
├── integration/
│   ├── test_buildx_integration.py # BuildX integration
│   └── test_docker_daemon.py      # Docker daemon integration
└── fixtures/
    ├── Dockerfile.test            # Test Dockerfiles
    └── test_configs.py            # Test configurations
```

### Test Best Practices

1. **Use pytest fixtures** for common setup:
   ```python
   @pytest.fixture
   def docker_builder():
       builder = DockerBuilder()
       yield builder
       builder.reset_singleton()  # Cleanup
   ```

2. **Mock Docker operations** when testing logic:
   ```python
   @patch('docker.from_env')
   def test_build_logic(mock_docker):
       # Test without actual Docker calls
   ```

3. **Test error conditions** comprehensively:
   ```python
   def test_docker_unavailable():
       with patch('docker.from_env', side_effect=DockerException):
           # Test graceful degradation
   ```

4. **Use temporary directories** for test contexts:
   ```python
   def test_build_with_context(tmp_path):
       dockerfile = tmp_path / "Dockerfile"
       dockerfile.write_text("FROM alpine")
       # Test with real file structure
   ```

## Pull Request Process

### Pre-submission Checklist

- [ ] All tests pass (`pytest tests/core/docker_builder/`)
- [ ] Code formatted (`black`, `isort`)
- [ ] Linting passes (`flake8`, `mypy`)
- [ ] Documentation updated (docstrings, README, etc.)
- [ ] Doctests pass (`python -m doctest`)
- [ ] Integration tests pass (requires Docker)
- [ ] Change log entry added if needed

### Code Review Guidelines

**For Reviewers**:
- Verify Docker operations are safe and don't affect host system
- Check cache invalidation logic for correctness
- Ensure cross-platform compatibility considerations
- Validate error handling covers edge cases
- Review performance implications of changes

**For Authors**:
- Include test dockerfile/context in PR for complex builds
- Document any new configuration options
- Explain cache behavior changes
- Provide before/after performance comparison if relevant

### CI/CD Integration

The module integrates with PANTHER's CI/CD pipeline:

```yaml
# .github/workflows/docker_builder.yml example
name: Docker Builder Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      docker:
        image: docker:dind
    steps:
      - uses: actions/checkout@v3
      - name: Setup Docker Buildx
        uses: docker/setup-buildx-action@v2
      - name: Run Tests
        run: |
          pytest tests/core/docker_builder/ --cov
          python -m doctest panther/core/docker_builder/*.py
```

## Performance Optimization

### Profiling Build Operations

```python
import cProfile
import pstats

def profile_build():
    builder = DockerBuilder()
    # Profile build operation
    cProfile.run('builder.build_image(...)', 'build_profile.stats')

    # Analyze results
    stats = pstats.Stats('build_profile.stats')
    stats.sort_stats('cumulative').print_stats(10)
```

### Cache Optimization

Monitor cache effectiveness:
```python
# Get cache statistics
stats = builder.get_cache_stats()
print(f"Cache hit ratio: {stats['hit_ratio']:.2%}")
print(f"Cache size: {stats['cache_size']} entries")

# Optimize cache TTL based on build frequency
builder.image_cache.configure(cache_ttl=600)  # 10 minutes
```

### BuildX Performance

Optimize BuildX for development:
```bash
# Create optimized builder
docker buildx create \
  --name dev-builder \
  --driver docker-container \
  --driver-opt network=host \
  --use

# Configure BuildKit cache
export BUILDKIT_INLINE_CACHE=1
```

## Troubleshooting

### Common Issues

**"Docker daemon not available"**:
- Check Docker Desktop is running
- Verify Docker socket permissions
- Test with `docker version`

**"BuildX builder not found"**:
- Install BuildX plugin: `docker buildx install`
- Create default builder: `docker buildx create --use`
- Check builder status: `docker buildx ls`

**"Platform not supported"**:
- Verify target platform format (`linux/amd64`, `linux/arm64`)
- Check BuildX supports target platform
- Review platform detection logic

**"Cache corruption"**:
- Clear image cache: `builder.image_cache.clear()`
- Reset singleton: `DockerBuilder.reset_singleton()`
- Check cache file permissions

### Debug Tools

```bash
# Docker system information
docker system info
docker system df  # Disk usage

# BuildX debugging
docker buildx ls
docker buildx inspect default

# PANTHER debugging
python -c "
from panther.core.docker_builder import DockerBuilder
builder = DockerBuilder()
print('Docker available:', builder.is_docker_available())
print('Cache stats:', builder.get_cache_stats())
print('Platform:', builder._get_target_platform())
"
```

## Documentation Maintenance

### Updating Documentation

When modifying the module:

1. **Update docstrings** with Google style format
2. **Run doctests** to verify examples work
3. **Update README.md** for architectural changes
4. **Update this guide** for new development procedures
5. **Generate API reference** if public interface changes

### Documentation Standards

- Use present tense for descriptions
- Include executable examples in docstrings
- Document complexity and concurrency characteristics
- Provide troubleshooting information for new features
- Follow Diátaxis structure for organizing information
