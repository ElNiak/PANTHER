# IUT Service Development Guide

## Environment Setup

### Prerequisites

- Docker Engine 20.10+ with BuildKit support
- Python 3.9+ with development headers
- Git for version control
- Access to protocol implementation source repositories

### Local Development Environment

```bash
# Clone PANTHER repository
git clone <panther-repo-url>
cd panther

# Set up Python virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# Install development dependencies
pip install -e ".[dev]"

# Enable Docker BuildKit for multi-stage builds
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1
```

### Verification

```bash
# Verify PANTHER installation
panther --version

# Test Docker integration
docker run --rm hello-world

# Verify plugin discovery
panther plugins list --type iut
```

## Development Workflow

### Creating a New IUT Plugin

1. **Choose the implementation directory structure:**
```
panther/plugins/services/iut/<protocol>/<implementation>/
├── __init__.py              # Plugin module initialization
├── <implementation>.py      # Main service manager class
├── config_schema.py         # Pydantic configuration schema
├── README.md               # Implementation-specific documentation
├── Dockerfile              # Container build definition
├── templates/              # Jinja2 command templates
│   ├── client_command.jinja
│   └── server_command.jinja
└── version_configs/        # Protocol version configurations
    ├── rfc9000.yaml
    └── draft29.yaml
```

2. **Implement the core service manager:**
```python
from panther.plugins.services.iut.iut_service_manager_mixin import IUTServiceManagerMixin
from panther.plugins.core.plugin_decorators import register_plugin

@register_plugin(
    plugin_type=PluginType.IUT,
    name="implementation_name",
    supported_protocols=["protocol_name"],
    capabilities=["feature1", "feature2"]
)
class ImplementationServiceManager(IUTServiceManagerMixin, BaseServiceManager):
    def __init__(self, service_config_to_test, service_type, protocol,
                 implementation_name, event_manager=None, **kwargs):
        super().__init__(
            service_config_to_test=service_config_to_test,
            service_type=service_type,
            protocol=protocol,
            implementation_name=implementation_name,
            event_manager=event_manager,
            **kwargs
        )

        # Use standardized initialization pattern
        self.standard_iut_initialization(plugin_dir=Path(__file__).parent)
```

3. **Define configuration schema:**
```python
from pydantic import BaseModel, Field
from typing import Optional

class ImplementationConfig(BaseModel):
    binary_path: str = Field(description="Path to implementation binary")
    server_port: int = Field(default=4443, description="Server listening port")
    log_level: str = Field(default="info", description="Logging verbosity")

    class Config:
        schema_extra = {
            "example": {
                "binary_path": "/usr/local/bin/implementation",
                "server_port": 4443,
                "log_level": "debug"
            }
        }
```

### Testing Your Plugin

#### Unit Testing
```bash
# Run unit tests for specific implementation
pytest tests/plugins/services/iut/<protocol>/<implementation>/

# Run with coverage
pytest --cov=panther.plugins.services.iut.<protocol>.<implementation> \
       tests/plugins/services/iut/<protocol>/<implementation>/
```

#### Integration Testing
```bash
# Test container build
docker build -t test-implementation \
    panther/plugins/services/iut/<protocol>/<implementation>/

# Test basic functionality
panther test --implementation <protocol>/<implementation> \
            --config tests/configs/basic_test.yaml
```

#### Manual Testing
```bash
# Interactive container testing
docker run -it --rm test-implementation /bin/bash

# Test command generation
panther generate-commands --implementation <protocol>/<implementation> \
                         --role client --version rfc9000
```

### Debugging Common Issues

#### Container Build Failures
```bash
# Enable verbose Docker output
export BUILDKIT_PROGRESS=plain
docker build --progress=plain -t debug-build .

# Check base image availability
docker pull <base-image>

# Validate multi-stage build layers
docker build --target <stage-name> .
```

#### Template Rendering Issues
```bash
# Test template rendering in isolation
python -c "
from panther.core.template.template_renderer import ServiceTemplateRenderer
renderer = ServiceTemplateRenderer('path/to/plugin')
result = renderer.render_template('client_command.jinja', context={'port': 4443})
print(result)
"
```

#### Plugin Discovery Problems
```bash
# Check plugin registration
python -c "
from panther.plugins.plugin_manager import PluginManager
manager = PluginManager()
print(manager.get_available_plugins(plugin_type='iut'))
"

# Verify __init__.py imports
python -c "import panther.plugins.services.iut.<protocol>.<implementation>"
```

## Code Quality Standards

### Code Style
- Follow PEP 8 style guidelines
- Use type hints for all public methods
- Maximum line length: 120 characters
- Use descriptive variable and method names

### Documentation Requirements
- Docstrings for all public classes and methods using Google style
- Inline comments for complex logic
- README.md with usage examples
- Configuration schema documentation

### Testing Standards
- Minimum 80% code coverage for new implementations
- Unit tests for all public methods
- Integration tests for container execution
- Performance regression tests for critical paths

## Pull Request Workflow

### Before Submitting
1. **Run complete test suite:**
```bash
pytest tests/plugins/services/iut/<protocol>/<implementation>/
flake8 panther/plugins/services/iut/<protocol>/<implementation>/
mypy panther/plugins/services/iut/<protocol>/<implementation>/
```

2. **Test container builds:**
```bash
docker build -t test-implementation .
docker run --rm test-implementation --version
```

3. **Update documentation:**
- Add implementation to main IUT README.md
- Create implementation-specific README.md
- Update capability matrices if new features added

### Pull Request Checklist
- [ ] All tests pass locally
- [ ] Container builds successfully
- [ ] Documentation updated
- [ ] Breaking changes documented
- [ ] Security implications reviewed
- [ ] Performance impact assessed

### Review Process
1. Automated CI checks run on all supported platforms
2. Code review by maintainer team
3. Integration testing in isolated environment
4. Performance benchmarking (if applicable)
5. Security review for new protocol implementations

## Troubleshooting

### Common Development Issues

**Plugin not discovered:**
- Verify `@register_plugin` decorator configuration
- Check `__init__.py` imports in plugin directory
- Ensure plugin follows naming conventions

**Container execution fails:**
- Check Dockerfile base image compatibility
- Verify implementation binary installation
- Test command template rendering
- Review container networking configuration

**Template rendering errors:**
- Validate Jinja2 syntax in templates
- Check context variable availability
- Test with minimal example data
- Review template inheritance chains

**Configuration validation fails:**
- Verify Pydantic schema definitions
- Check default value compatibility
- Test with example configurations
- Review field constraint definitions

### Performance Optimization

**Container startup time:**
- Use multi-stage builds to minimize image size
- Pre-install dependencies in base layers
- Cache dependency installations
- Consider init systems for complex setups

**Memory usage:**
- Profile container resource consumption
- Optimize dependency installations
- Use alpine-based images where possible
- Configure proper resource limits

**Test execution speed:**
- Parallelize independent test cases
- Cache container images between runs
- Use Docker layer caching in CI
- Optimize template rendering performance
