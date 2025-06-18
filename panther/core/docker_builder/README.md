# Docker Builder System

The Docker Builder system provides a unified approach to building and managing Docker images across PANTHER's plugin architecture. It separates environment-specific and service-specific Docker operations through dedicated mixins.

## Architecture Overview

The Docker builder system is organized into specialized components:

```
docker_builder/
├── docker_builder.py                    # Core Docker builder implementation
├── docker_operations_mixin.py          # Common Docker operations
├── service_manager_docker_mixin.py     # Service-specific Docker operations
├── environment_manager_docker_mixing.py # Environment-specific Docker operations
├── docker_compose_operations_mixin.py  # Docker Compose orchestration
├── docker_cache_mixin.py               # Docker layer caching
└── output_parser.py                    # Docker output parsing utilities
```

## Key Components

### DockerBuilder
The main class responsible for building Docker images with proper error handling, caching, and progress tracking.

### Service Manager Docker Mixin
Provides Docker operations specific to service plugins:
- Building service implementation images
- Managing service-specific Dockerfiles
- Handling service deployment configurations

### Environment Manager Docker Mixin
Provides Docker operations specific to network environment plugins:
- Building base service images from `panther/plugins/services/Dockerfile`
- Ensuring service images are available before environment deployment
- Building environment-specific containers (single container, simulator, etc.)

## Separation of Concerns

The system maintains clear separation between:

1. **Service Docker Operations** (via `ServiceManagerDockerMixin`):
   - Build individual service images
   - Generate service-specific Dockerfiles
   - Handle service deployment commands

2. **Environment Docker Operations** (via `EnvironmentManagerDockerMixin`):
   - Build and tag base images
   - Verify service image availability
   - Create multi-stage environment Dockerfiles
   - Build final environment containers

## Usage Examples

### Service Manager Integration
```python
class MyServiceManager(BaseServiceManager, ServiceManagerDockerMixin):
    def build_docker_image(self):
        # Service-specific Docker build
        return self.docker_builder.build_image(
            dockerfile_path=self.dockerfile_path,
            image_name=f"{self.service_name}:{self.version}"
        )
```

### Environment Manager Integration
```python
class MyNetworkEnvironment(BaseNetworkEnvironment, EnvironmentManagerDockerMixin):
    def generate_environment_services(self, paths, timestamp):
        # Build base image first
        base_image_tag = self.build_base_service_image(self.plugin_manager)
        
        # Ensure service images are available
        service_images = self.ensure_service_images_available(self.services_managers)
        
        # Generate environment Dockerfile with proper base image
        self.generate_from_template(
            template_name="Dockerfile.jinja",
            additional_param={
                "base_image": base_image_tag,
                "service_images": service_images
            }
        )
```

## Multi-Stage Build Support

The system fully supports Docker multi-stage builds, commonly used in environment plugins:

```dockerfile
# Base stage with proper image reference
FROM {{ additional_param.base_image }} AS base

# Service stages for each service
{% for service in services %}
FROM {{ additional_param.service_images[service.service_name] }} AS {{ service.service_name }}_stage
{% endfor %}

# Final stage combining everything
FROM base
COPY --from=service1_stage /app /services/service1
```

## Common Issues and Solutions

### Empty FROM Instructions
**Problem**: Generated Dockerfiles have empty FROM instructions
**Solution**: The environment mixin now ensures base_image is always provided through:
- Building and tagging the base service image
- Passing it in the `additional_param` dictionary to templates
- Verifying all required images before building

### Service Image Not Found
**Problem**: Environment build fails because service images aren't available
**Solution**: The `ensure_service_images_available()` method now:
- Checks if each service image exists
- Builds missing images if needed
- Returns a mapping of service names to image tags

## Best Practices

1. **Always use the appropriate mixin** for your plugin type
2. **Build base images once** per experiment to save time
3. **Verify Dockerfile validity** before building
4. **Use multi-stage builds** for complex environments
5. **Tag images properly** for versioning and identification

## Integration Points

The Docker builder system integrates with:
- **Plugin Manager**: For service discovery and image building
- **Template System**: For Dockerfile generation
- **Event System**: For build progress tracking
- **Error Handling**: For proper error reporting and recovery