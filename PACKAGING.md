# PANTHER Packaging Guide

## Overview

PANTHER uses a modern, secure, and extensible packaging system that supports both traditional and cutting-edge Python packaging approaches. This guide covers building, packaging, testing, and publishing PANTHER to PyPI and other distribution channels.

!!! info "Enhanced Packaging System"
    PANTHER now includes an enhanced packaging system with security scanning, dependency management, and modern build backends. The traditional system remains fully supported.

!!! warning "For Maintainers Only"
    This guide is intended for PANTHER maintainers and contributors who need to package and publish releases. Regular users should follow the [Installation Guide](INSTALL.md) instead.

## Quick Start

```bash
# Traditional build (stable)
python panther_builder.py package

# Development installation
python panther_builder.py package-dev
```

## Package Structure

PANTHER follows the [PyOpenSci package structure guidelines](https://www.pyopensci.org/python-package-guide/package-structure-code/python-package-structure.html) with enhancements for plugin support and multi-backend compatibility.

### Key Files

| File | Purpose | Notes |
|------|---------|-------|
| `pyproject.toml` | Primary package configuration | PEP 517/518/621 compliant |
| `pyproject_hatchling.toml` | Modern Hatchling backend config | Alternative build backend |
| `MANIFEST.in` | Source distribution includes | Controls non-Python files |
| `panther_builder.py` | Traditional build script | Cross-platform Makefile replacement |
| `requirements.txt` | Frozen dependencies | Auto-generated, do not edit |

### Directory Structure

```
PANTHER/
├── panther/                    # Main package
│   ├── __init__.py            # Version and public API
│   ├── plugins/               # Plugin system
│   │   ├── services/          # Service implementations
│   │   ├── environments/      # Environment plugins
│   │   └── protocols/         # Protocol definitions
│   └── webapp/                # Web interface
├── tests/                     # Test suite
│   └── test_packaging/        # Packaging-specific tests
├── docs/                      # Documentation
│   └── packaging/             # Packaging guides
└── dist/                      # Built distributions
```

## Build System Architecture

### Traditional Builder

The stable, production-tested build system:

```bash
# Basic operations
python panther_builder.py clean        # Clean artifacts
python panther_builder.py package      # Build and install
python panther_builder.py package-dev  # Development mode
python panther_builder.py package-test # Build and test
python panther_builder.py docs         # Build documentation
```

## Building the Package

### Standard Build Process

```bash
# 1. Ensure clean environment
python panther_builder.py clean

# 2. Install build dependencies
pip install --upgrade pip setuptools wheel build

# 3. Build distributions
python panther_builder.py package
# or manually:
python -m build --wheel --sdist

# 4. Verify outputs
ls -la dist/
python -m zipfile -l dist/*.whl | head -20
```

## Plugin System

### Plugin Discovery

PANTHER uses two plugin discovery mechanisms:

1. **Entry Points** (Recommended for external plugins):
   ```toml
   [project.entry-points."panther.plugins.services"]
   my_service = "my_package.service:MyServiceManager"
   ```

2. **File-based Discovery** (Built-in plugins):
   - Place in `panther/plugins/` directories
   - Follow naming conventions
   - Include in package data

### Packaging Plugins

Ensure plugin files are included:

```toml
[tool.setuptools]
package-data = { panther = [
    "plugins/**/*.py",
    "plugins/**/*.yaml",
    "plugins/**/*.jinja",
    "plugins/**/Dockerfile*",
    "plugins/**/*.sh",
] }
```

Verify inclusion:
```bash
python -m zipfile -l dist/*.whl | grep plugins
```

## Testing the Package

### Local Testing

```bash
# 1. Create test environment
python -m venv test_env
source test_env/bin/activate

# 2. Install built package
pip install dist/panther_net-*.whl

# 3. Run verification
python -c "import panther; print(panther.__version__)"
python -m panther --help
python -m panther --list-plugins

# 4. Run packaging tests
pytest tests/test_packaging/ -v
```

## Publishing to PyPI

### Manual Publishing

```bash
# 1. Install twine
pip install twine

# 2. Check distributions
twine check dist/*

# 3. Upload to Test PyPI (optional)
twine upload --repository testpypi dist/*

# 4. Upload to PyPI
twine upload dist/*
```

### Automated Publishing

GitHub Actions workflow triggers on tag push:

```yaml
name: Publish to PyPI
on:
  push:
    tags:
      - 'v*'

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build distributions
        run: python -m build
      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
        with:
          password: ${{ secrets.PYPI_API_TOKEN }}
```

## Docker Integration

### Building Docker Images

```bash
# Build with Docker support
docker-compose -f docker-compose.yml build

# Clean Docker artifacts
python panther_builder.py remove-images-all
python panther_builder.py remove-volume
```

### Optimizing Images

```bash
# Install slim tool
python panther_builder.py install-slim

# Optimize images
slim build --target panther-base
```

## Troubleshooting

Common issues and solutions:

| Issue | Solution |
|-------|----------|
| Import errors | `pip install -e .` |
| Missing plugins | Check `MANIFEST.in` |
| Build failures | `python panther_builder.py clean` |
| Security failures | Update vulnerable packages |
| Slow builds | Enable caching |

For detailed troubleshooting, see [Troubleshooting Guide](docs/packaging/troubleshooting.md).

## Best Practices

1. **Always use virtual environments**
2. **Run security scans before releases**
3. **Generate lock files for reproducibility**
4. **Test on multiple Python versions**
5. **Validate plugin inclusion**
6. **Document breaking changes**
7. **Use semantic versioning**
8. **Keep dependencies up to date**

## Migration Path

For existing installations:

1. **Phase 1**: Enable security scanning
   ```bash
   export PANTHER_SECURITY_SCAN=true
   ```

2. **Phase 2**: Add dependency locks
   ```bash
   export PANTHER_USE_DEP_LOCKS=true
   ```

3. **Phase 3**: Switch to modern backend
   ```bash
   export PANTHER_USE_MODERN_BACKEND=true
   ```

See [Migration Guide](docs/packaging/migration-guide.md) for details.

## Additional Resources

- [User Guide](docs/packaging/user-guide.md) - Day-to-day usage
- [Developer Guide](docs/packaging/developer-guide.md) - Extending the system
- [API Reference](docs/packaging/api-reference.md) - Command reference
- [Migration Guide](docs/packaging/migration-guide.md) - Upgrading guide
- [Troubleshooting](docs/packaging/troubleshooting.md) - Common issues

## Contributing

When contributing packaging improvements:

1. Maintain backward compatibility
2. Add tests for new features
3. Update documentation
4. Follow the feature flag pattern
5. Test on multiple platforms

For questions or issues, please open a GitHub issue or contact the maintainers.