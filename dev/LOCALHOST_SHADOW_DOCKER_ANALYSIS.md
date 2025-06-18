# Localhost and Shadow Environment Docker Implementation Analysis

## Current State Analysis

### 1. Environment Manager Docker Mixin Issues

The current `environment_manager_docker_mixing.py` has several critical problems:

1. **Copy-paste from service_manager_docker_mixin.py**: The file is essentially a copy with minimal changes, containing service-specific logic that doesn't apply to environments
2. **Incorrect attribute access**: Tries to access `service_config_to_test` and `implementation_name` which don't exist on environment managers
3. **Wrong event notifications**: Uses `notify_environment_event` but the logic is still service-oriented
4. **Misaligned Docker build workflow**: Doesn't match the actual needs of localhost/shadow environments

### 2. Localhost Single Container Workflow

Based on the code and docstring analysis, the expected workflow is:

```
1. Build base service image (panther/plugins/services/Dockerfile)
   └─> Tagged as: localhost_single_container_v1

2. Generate configuration files:
   ├─> run.sh (from run.sh.jinja template)
   └─> Dockerfile (from Dockerfile.experience.jinja template)

3. Multi-stage Dockerfile approach:
   ├─> FROM base_image AS shadow_base
   ├─> FROM service1_image AS service1_stage  
   ├─> FROM service2_image AS service2_stage
   └─> FROM base_image (final stage with COPY --from stages)

4. Build final container image
   └─> Tagged as: localhost_<test_name>:latest

5. Run container with all services
```

### 3. Template Parameter Issues

Current problems with template rendering:

1. **Dockerfile.jinja**: Expects `base_image` but receives empty/null
2. **Dockerfile.experience.jinja**: Expects `base_image` in `additional_param`
3. **Parameter passing**: Inconsistent between different environment types

## Implementation Plan

### Phase 1: Fix Environment Manager Docker Mixin

#### 1.1 Create Proper Environment Docker Mixin

```python
class EnvironmentManagerDockerMixin(DockerComposeOperationsMixin, CommandEventMixin):
    """
    Docker mixin specifically for environment managers (localhost, shadow).
    
    Handles:
    - Building base service images
    - Building environment-specific images from generated Dockerfiles
    - Managing multi-stage builds that reference service images
    """
    
    # Use different class variable to avoid conflicts
    _env_base_service_image_built = False
    _env_base_service_lock = None
    
    def build_base_service_image(self, plugin_manager: "PluginManager") -> str:
        """
        Build the base service image from panther/plugins/services/Dockerfile.
        
        Returns:
            str: Image tag of built base image
        """
        with self._env_base_service_lock:
            if not self._env_base_service_image_built:
                # Build panther/plugins/services/Dockerfile
                # Tag as panther_base_services:latest
                pass
                
    def ensure_service_images_available(self, services: List[IServiceManager]) -> Dict[str, str]:
        """
        Ensure all required service images are available.
        
        Returns:
            Dict[str, str]: Mapping of service_name to image_tag
        """
        service_images = {}
        for service in services:
            image_tag = f"{service.implementation_name}_{service.service_protocol.version.name}:latest"
            # Check if image exists, build if needed
            service_images[service.service_name] = image_tag
        return service_images
        
    def build_environment_image(self, dockerfile_path: Path, image_name: str) -> None:
        """
        Build environment-specific Docker image from generated Dockerfile.
        Handles multi-stage builds properly.
        """
        # Build with proper context and build args
        pass
```

#### 1.2 Key Differences from Service Mixin

1. **No service attributes**: Remove all references to service_config_to_test, implementation_name
2. **Environment-specific events**: Use notify_environment_event consistently
3. **Different build workflow**: Focus on orchestrating multiple service images rather than building a single service
4. **Base image management**: Track base service image separately from service-specific images

### Phase 2: Update Localhost Single Container

#### 2.1 Inherit from Environment Docker Mixin

```python
class LocalhostSingleContainerEnvironment(
    BaseNetworkEnvironment,
    EnvironmentManagerDockerMixin,  # Add this
    SubprocessExecutorMixin,
    # ... other mixins
):
```

#### 2.2 Fix generate_environment_services Method

```python
def generate_environment_services(self, paths: Dict[str, str], timestamp: str) -> None:
    """Generate run script and Dockerfile for single container."""
    
    # Step 1: Build base service image using mixin
    base_image_tag = self.build_base_service_image(self.plugin_manager)
    
    # Step 2: Ensure all service images are available
    service_images = self.ensure_service_images_available(self.services_managers)
    
    # Step 3: Generate run.sh with proper parameters
    self.generate_from_template(
        template_name="run.sh.jinja",
        paths=paths,
        timestamp=timestamp,
        rendered_out_file=str(self.rendered_services_network_config_file_path),
        out_file=str(self.services_network_config_file_path),
        additional_param={
            "container_name": self.docker_name,
            "services": self.services_managers,
            "services_with_outputs": services_with_outputs,
        },
    )
    
    # Step 4: Generate Dockerfile with base_image properly set
    self.generate_from_template(
        template_name="Dockerfile.experience.jinja",
        paths=paths,
        timestamp=timestamp,
        rendered_out_file=str(self.rendered_services_network_docker_file_path),
        out_file=str(self.services_network_docker_file_path),
        additional_param={
            "base_image": base_image_tag,  # Now properly set!
            "services": self.services_managers,
            "service_images": service_images,  # Add mapping for FROM instructions
        },
    )
    
    # Step 5: Build final environment image using mixin
    if self.global_config.docker.build_docker_image:
        self.build_environment_image(
            dockerfile_path=self.rendered_services_network_docker_file_path,
            image_name=f"{self.docker_name}:latest"
        )
```

#### 2.3 Remove Duplicate Methods

Remove these methods as they'll be handled by the mixin:
- `generate_base_image()` 
- `_build_container_image()`

### Phase 3: Update Shadow Environment

Shadow environment should follow similar pattern:

```python
class ShadowNSEnvironment(
    BaseNetworkEnvironment,
    EnvironmentManagerDockerMixin,  # Add this
    # ... other mixins
):
    def generate_environment_services(self, paths: Dict[str, str], timestamp: str) -> None:
        # Similar pattern to localhost but with Shadow-specific configuration
        base_image_tag = self.build_base_service_image(self.plugin_manager)
        
        # Generate Shadow configuration files
        # Use base_image_tag in templates
```

### Phase 4: Fix Templates

#### 4.1 Update Dockerfile.experience.jinja

```jinja2
{# Use base_image from additional_param #}
FROM {{ additional_param.base_image }} AS shadow_base

{% for service in services %}
{# Use service image mapping if provided #}
{% set service_image = additional_param.service_images.get(service.service_name, service.implementation_name + '_' + service.service_protocol.version.name + ':latest') %}
FROM {{ service_image }} AS {{ service.service_name }}_stage

{# Rest of service staging logic #}
{% endfor %}

{# Final stage #}
FROM {{ additional_param.base_image }}
{# Copy from stages and setup final image #}
```

#### 4.2 Ensure Consistent Parameter Access

All templates should access base_image consistently:
- `{{ additional_param.base_image }}`
- With fallback: `{{ additional_param.base_image if additional_param and additional_param.base_image else "ubuntu:20.04" }}`

## Implementation Priority

1. **Immediate (Critical)**:
   - Fix environment_manager_docker_mixing.py to be environment-specific
   - Update localhost_single_container to properly pass base_image
   - Fix Dockerfile templates to use consistent parameter access

2. **Short-term (Important)**:
   - Add proper service image verification
   - Implement multi-stage build error handling
   - Update shadow environment similarly

3. **Long-term (Enhancement)**:
   - Add image caching strategies
   - Implement parallel service image builds
   - Add build progress reporting

## Testing Strategy

### 1. Unit Tests
- Test environment Docker mixin methods in isolation
- Verify base image building logic
- Test service image verification

### 2. Integration Tests
- Test full localhost environment setup with multiple services
- Verify multi-stage Dockerfile generation
- Test shadow environment setup

### 3. Validation Points
- [ ] Base service image builds correctly
- [ ] Service images are properly referenced in multi-stage builds
- [ ] FROM instructions are never empty
- [ ] Container runs with all services properly staged
- [ ] Shadow environment works with same pattern

## Common Pitfalls to Avoid

1. **Don't mix service and environment concerns** - Keep clear separation
2. **Always verify service images exist** before referencing in multi-stage builds
3. **Use consistent parameter naming** across all templates
4. **Handle missing images gracefully** with clear error messages
5. **Track build state properly** to avoid redundant builds

## Expected Outcome

After implementation:
1. Localhost environment builds reliably with proper base images
2. Multi-stage Dockerfiles have all FROM instructions populated
3. Service images are properly staged and available
4. Shadow environment follows same reliable pattern
5. Clear separation between service and environment Docker operations