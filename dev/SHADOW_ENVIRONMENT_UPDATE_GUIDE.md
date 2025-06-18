# Shadow Environment Update Guide

## Overview
This guide explains how to apply the same Docker mixin pattern to the shadow_ns environment that was successfully implemented for localhost_single_container.

## Steps to Update Shadow Environment

### 1. Update shadow_ns.py Class Inheritance
```python
class ShadowNSEnvironment(
    BaseNetworkEnvironment,
    EnvironmentManagerDockerMixin,  # Add this
    # ... other mixins
):
```

### 2. Update generate_environment_services Method
```python
def generate_environment_services(self, paths: Dict[str, str], timestamp: str) -> None:
    """Generate Shadow configuration files."""
    
    # Step 1: Build base service image
    base_image_tag = self.build_base_service_image(self.plugin_manager)
    
    # Step 2: Ensure service images are available
    service_images = self.ensure_service_images_available(self.services_managers)
    
    # Step 3: Generate Shadow configuration with proper parameters
    self.generate_from_template(
        template_name="shadow.yml.jinja",
        paths=paths,
        timestamp=timestamp,
        rendered_out_file=str(self.rendered_shadow_config_path),
        out_file=str(self.shadow_config_path),
        additional_param={
            "base_image": base_image_tag,
            "services": self.services_managers,
            "service_images": service_images,
            # ... other shadow-specific params
        },
    )
    
    # Step 4: Generate Dockerfile if shadow uses one
    if self.uses_dockerfile:
        self.generate_from_template(
            template_name="Dockerfile.jinja",
            paths=paths,
            timestamp=timestamp,
            rendered_out_file=str(self.rendered_dockerfile_path),
            out_file=str(self.dockerfile_path),
            additional_param={
                "base_image": base_image_tag,
                "services": self.services_managers,
                "service_images": service_images,
            },
        )
        
        # Step 5: Verify and build
        if self.verify_dockerfile_ready(self.rendered_dockerfile_path):
            if self.global_config.docker.build_docker_image:
                self.build_environment_image(
                    dockerfile_path=self.rendered_dockerfile_path,
                    image_name=f"{self.shadow_name}:latest"
                )
```

### 3. Remove Duplicate Methods
Remove any methods that are now handled by the mixin:
- `_build_shadow_image()`
- `generate_base_image()`
- Any other Docker build methods

### 4. Update Templates
Ensure shadow templates use the passed parameters:
```jinja2
{# In Dockerfile.jinja or similar #}
FROM {{ additional_param.base_image }}

{# Use service images if staging #}
{% for service in services %}
FROM {{ additional_param.service_images[service.service_name] }} AS {{ service.service_name }}_stage
{% endfor %}
```

### 5. Test the Implementation
Create a test configuration similar to the localhost test but using shadow_ns:
```yaml
tests:
  - name: "Test Shadow Fix"
    network_environment:
      type: shadow_ns
    # ... rest of config
```

## Key Differences for Shadow
1. Shadow uses a shadow.yml configuration file in addition to Dockerfiles
2. Shadow simulator container needs proper base image reference
3. Service staging might be different due to Shadow's architecture

## Benefits
- Consistent Docker operations across all network environments
- Reusable base image building
- Proper multi-stage build support
- Better error handling and validation