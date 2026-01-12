
# CLI

```bash
# Check system readiness
panther tools doctor
```

#### Click-based CLI (*In Progress*)

PANTHER now features a modern, user-friendly CLI built with Click that provides:

- **Colored output** with emojis for visual feedback
- **Progress bars** for long-running operations
- **Enhanced error messages** with contextual suggestions
- **Bash completion** for improved productivity
- **Interactive tutorials** for learning
- **Comprehensive help** with examples


#### UV package manager (*TODO*)

"[An extremely fast Python package and project manager, written in Rust.](https://github.com/astral-sh/uv)" 
- Faster
- Better version management
- Remote usage possible 

### Interactive Learning 

Explore PANTHER through interactive tutorials:

```bash
# Start interactive tutorial system
panther tutorial interactive

# Or run specific tutorials
panther tutorial run service --mode guided
panther tutorial run configuration --mode quick
```

### Plugin Management  (*In Progress*)

Discover and manage plugins easily:

```bash
# List available plugins
panther plugins list

# Get information about a specific plugin
panther plugins info picoquic --verbose

# Check plugin parameters
panther plugins params picoquic --type iut
```

For comprehensive CLI documentation, see [CLI Documentation](docs/cli_click.md).

# QUICK START GUIDE

```bash
# First, validate your configuration (recommended)
panther config validate --config quic_demo.yaml --explain
```

- ```--enable-metrics```

# Documentation

# Packaging and Distribution


### Enhanced Builder

Modern features with gradual adoption:

```bash
# Show configuration
python panther_builder_enhanced.py show-config

# Build with features
python panther_builder_enhanced.py build

# Security operations
python panther_builder_enhanced.py security-scan
python panther_builder_enhanced.py generate-locks
python panther_builder_enhanced.py generate-sbom
```

### Feature Flags

Control packaging behavior with environment variables:

```bash
# Enable modern backend (Hatchling)
export PANTHER_USE_MODERN_BACKEND=true

# Enable dependency lock files
export PANTHER_USE_DEP_LOCKS=true

# Enable security scanning (default: true)
export PANTHER_SECURITY_SCAN=true

# Enable build caching
export PANTHER_BUILD_CACHE=true
```



### Enhanced Build Process

```bash
# 1. Run security scan
python panther_builder_enhanced.py security-scan

# 2. Generate lock files
python panther_builder_enhanced.py generate-locks

# 3. Build with all features
PANTHER_USE_MODERN_BACKEND=true \
PANTHER_USE_DEP_LOCKS=true \
python panther_builder_enhanced.py build

# 4. Generate SBOM
python panther_builder_enhanced.py generate-sbom
```

### Build Backends

PANTHER supports multiple build backends:

#### Setuptools (Default)
- Stable and widely compatible
- Extensive plugin ecosystem
- Configuration in `pyproject.toml`

#### Hatchling (Modern)
- Faster builds
- Better error messages
- Built-in versioning from Git
- Configuration in `pyproject_hatchling.toml`

To switch backends:
```bash
# Use Hatchling
cp pyproject_hatchling.toml pyproject.toml
export PANTHER_USE_MODERN_BACKEND=true
python panther_builder_enhanced.py build
```

## Dependency Management

### Version Constraints

Dependencies use semantic versioning ranges:

```toml
dependencies = [
    "omegaconf>=2.3.0,<3.0",    # Minor version constraint
    "docker>=6.0.0,<8.0",       # Major version range
    "psutil>=5.9.0,<6.0",       # Tight constraint
]
```

### Lock Files

Generate reproducible builds:

```bash
# Generate lock files
python panther_builder_enhanced.py generate-locks

# Files created:
# - locks/requirements-default.lock
# - locks/requirements-dev.lock
# - locks/requirements-tests.lock

# Use lock files
export PANTHER_USE_DEP_LOCKS=true
python panther_builder_enhanced.py build
```

### Security Scanning

Integrated vulnerability detection:

```bash
# Run all security scans
python panther_builder_enhanced.py security-scan

# Individual tools:
safety check                    # Known vulnerabilities
bandit -r panther/             # Code security
pip-audit                      # Dependency audit
semgrep --config=auto panther/ # Security patterns
```


### Migration Validation

Compare different build backends:

```bash
python tests/test_packaging/test_migration_validator.py \
    --compare-backends setuptools hatchling \
    --output comparison_report.json
```

### CI/CD Testing

Automated testing in GitHub Actions:

```yaml
# .github/workflows/packaging-modern.yml
- Multi-backend testing (setuptools, hatchling)
- Cross-platform validation (Linux, macOS)
- Python version matrix (3.10, 3.11, 3.12)
- Security scanning
- Performance benchmarking
```

## Version Management

### Single-Source Versioning

1. **Primary source**: `pyproject.toml`
   ```toml
   [project]
   version = "1.1.3"
   ```

2. **Runtime access**: `panther.__version__`

3. **Git-based versioning** (Hatchling):
   ```toml
   [tool.hatch.version]
   source = "vcs"
   ```

### Release Process

```bash
# 1. Update version
# Edit pyproject.toml

# 2. Update changelog
# Edit CHANGELOG.md

# 3. Run tests
python panther_builder_enhanced.py comprehensive-test

# 4. Create git tag
git tag -a v1.2.3 -m "Release version 1.2.3"
git push origin v1.2.3

# 5. Build release
python panther_builder_enhanced.py build

# 6. Upload to PyPI
twine upload dist/*
```


## Performance Optimization

### Build Caching

```bash
# Enable caching
export PANTHER_BUILD_CACHE=true
export PANTHER_CACHE_DIR=~/.cache/panther

# Build with cache
python panther_builder_enhanced.py build
```

### Parallel Builds

```bash
# Enable parallel operations
export PANTHER_PARALLEL_BUILDS=true

# Build with parallelism
python panther_builder_enhanced.py build
```

### Benchmarking

```bash
# Compare build times
time python panther_builder.py package
time PANTHER_USE_MODERN_BACKEND=true python panther_builder_enhanced.py build
```