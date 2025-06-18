# Network Environment Docker Build Integration Plan

## 🔍 Current State Analysis

### How Network Environments Currently Build Docker Images

#### 1. Shadow NS (`shadow_ns.py`)
```python
def _build_shadow_image(self) -> None:
    """Build Shadow Docker image."""
    build_cmd = [
        "docker",
        "build",
        "-t",
        f"{self.docker_name}:latest",
        "-f",
        str(self.services_network_docker_file_path),
        str(self.services_network_docker_file_path.parent),
    ]
    
    self.execute_with_retry(
        command=build_cmd,
        max_retries=2,
        log_prefix="shadow_build",
        timeout=600,
    )
```

#### 2. Docker Compose
- Relies on service-level Docker images built by PluginManager
- Doesn't build its own images, only orchestrates pre-built service images

#### 3. Localhost Single Container  
- Similar to Docker Compose - uses pre-built service images
- No custom Docker building logic

### Issues with Current Approach
1. **Inconsistency**: Network environments use subprocess while services use DockerBuilder
2. **No caching strategy**: Each build starts fresh
3. **No multistage support**: Can't optimize network environment images
4. **No centralized logging**: Build logs scattered across different mechanisms
5. **No progress tracking**: Network env builds are opaque

## 🏗️ Proposed Integration Architecture

### 1. Extend DockerOperationsMixin to Network Environments

```python
# panther/plugins/environments/network_environment/base_network_environment.py
from panther.core.docker_builder.docker_operations_mixin import DockerOperationsMixin

class BaseNetworkEnvironment(
    INetworkEnvironment,
    DockerOperationsMixin,  # Add this mixin
    LoggerMixin,
    CommandEventMixin
):
    """Base class for network environments with Docker support."""
    
    def build_environment_image(
        self,
        dockerfile_path: Path,
        image_name: str,
        build_config: Optional[BuildConfig] = None,
        target: Optional[str] = None
    ) -> bool:
        """
        Build Docker image for network environment using centralized builder.
        
        Args:
            dockerfile_path: Path to environment Dockerfile
            image_name: Name for the built image
            build_config: Optional build configuration
            target: Optional target stage
            
        Returns:
            bool: True if build succeeded
        """
        # Use the mixin's enhanced prepare_docker_image
        return self.prepare_docker_image(
            image_name=image_name,
            dockerfile_path=dockerfile_path,
            build_config=build_config,
            target=target,
            no_cache=False
        )
```

### 2. Shadow NS Integration Example

```python
# Updated shadow_ns.py
class ShadowNSEnvironment(BaseNetworkEnvironment):
    
    def _build_shadow_image(self) -> None:
        """Build Shadow Docker image using centralized builder."""
        self.logger.info("Building Shadow NS Docker image")
        
        # Create build configuration for Shadow
        build_config = BuildConfig(
            base_image="ubuntu:22.04",
            stages=[
                BuildStage(name="base", cache=True),
                BuildStage(name="shadow-deps", dependencies=["base"]),
                BuildStage(name="shadow-build", dependencies=["shadow-deps"]),
                BuildStage(name="runtime", dependencies=["shadow-build"], target=True)
            ],
            language="cpp",  # Shadow is C++
            build_args={
                "SHADOW_VERSION": self.shadow_version,
                "ENABLE_GUI": "false"
            }
        )
        
        # Use centralized builder
        success = self.build_environment_image(
            dockerfile_path=self.services_network_docker_file_path,
            image_name=f"{self.docker_name}:latest",
            build_config=build_config,
            target="runtime"  # Build only up to runtime stage
        )
        
        if not success:
            raise RuntimeError("Failed to build Shadow NS Docker image")
```

### 3. Unified Dockerfile Templates for Network Environments

Create template-based Dockerfiles for network environments:

```dockerfile
# panther/docker/templates/network_env/shadow.dockerfile.jinja
# Multistage Dockerfile for Shadow NS
FROM {{ base_image }} AS base
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    python3 \
    git

FROM base AS shadow-deps
RUN apt-get install -y \
    libglib2.0-dev \
    libigraph-dev \
    libyaml-dev

FROM shadow-deps AS shadow-build
WORKDIR /build
RUN git clone https://github.com/shadow/shadow.git && \
    cd shadow && \
    ./setup build --clean --test
    
FROM base AS runtime
COPY --from=shadow-build /build/shadow/build/src/main/shadow /usr/bin/
WORKDIR /shadow
ENTRYPOINT ["shadow"]
```

### 4. Configuration Schema for Network Environments

```yaml
# panther/docker/build_configs/network_environments.yaml
network_environments:
  shadow_ns:
    base_image: ubuntu:22.04
    multistage: true
    stages:
      - name: base
        cache: true
      - name: shadow-deps
        dependencies: [base]
      - name: shadow-build
        dependencies: [shadow-deps]
      - name: runtime
        dependencies: [shadow-build]
        target: true
    cache_strategy:
      type: registry
      registry: ghcr.io/elniak/panther-cache
      
  docker_compose:
    # Docker Compose doesn't need its own image
    skip_build: true
    
  localhost_single_container:
    base_image: ubuntu:22.04
    stages:
      - name: base
        cache: true
      - name: runtime
        dependencies: [base]
        target: true
```

## 🔄 Migration Strategy

### Phase 1: Add DockerOperationsMixin to BaseNetworkEnvironment
```python
# Step 1: Update base class
class BaseNetworkEnvironment(
    INetworkEnvironment,
    DockerOperationsMixin,  # NEW
    # ... other mixins
):
    pass

# Step 2: Add build_environment_image method
def build_environment_image(self, ...): ...
```

### Phase 2: Update Individual Network Environments

#### Shadow NS Migration
```python
# Before
def _build_shadow_image(self):
    build_cmd = ["docker", "build", ...]
    self.execute_with_retry(build_cmd)

# After  
def _build_shadow_image(self):
    build_config = self._get_shadow_build_config()
    self.build_environment_image(
        dockerfile_path=self.services_network_docker_file_path,
        image_name=f"{self.docker_name}:latest",
        build_config=build_config
    )
```

#### Localhost Single Container Migration
- Add Docker building capability if needed
- Use centralized builder for any custom images

### Phase 3: Centralize Dockerfile Management

1. Move network environment Dockerfiles to `panther/docker/network_envs/`
2. Convert to Jinja templates with multistage support
3. Update paths in environment classes

## 🎯 Benefits of Centralization

### 1. Consistency
- All Docker builds use the same underlying mechanism
- Unified logging and error handling
- Consistent caching strategy

### 2. Performance
- Network environment images benefit from layer caching
- Registry-based caching for CI/CD
- Parallel stage building where applicable

### 3. Maintainability
- Single source of truth for Docker building logic
- Easier to update and optimize
- Consistent configuration format

### 4. Features
- Multistage builds for smaller images
- Target specification for development vs production
- Build progress monitoring
- Centralized build metrics

## 📊 Implementation Timeline

### Week 1: Foundation
- [ ] Add DockerOperationsMixin to BaseNetworkEnvironment
- [ ] Implement build_environment_image method
- [ ] Create build configuration schema for network envs

### Week 2: Shadow NS Migration
- [ ] Convert Shadow Dockerfile to multistage
- [ ] Update _build_shadow_image to use centralized builder
- [ ] Test Shadow NS with new build system

### Week 3: Other Environments
- [ ] Update localhost_single_container if needed
- [ ] Document docker_compose considerations
- [ ] Create migration guide for custom network environments

### Week 4: Testing and Documentation
- [ ] Comprehensive testing of all network environments
- [ ] Performance benchmarking
- [ ] Update documentation
- [ ] Create examples for custom network environments

## 🧪 Testing Plan

### Unit Tests
```python
def test_network_env_docker_build():
    """Test network environment can build Docker images."""
    env = ShadowNSEnvironment(...)
    
    # Mock docker builder
    with patch.object(env.docker_builder, 'build_image') as mock_build:
        mock_build.return_value = "shadow:latest"
        
        env._build_shadow_image()
        
        # Verify centralized builder was used
        mock_build.assert_called_once()
        assert "shadow" in mock_build.call_args[1]['impl_name']
```

### Integration Tests
```python
def test_shadow_multistage_build():
    """Test Shadow NS builds with multistage support."""
    env = ShadowNSEnvironment(...)
    
    # Enable multistage
    env.global_config.docker.multistage_builds_enabled = True
    
    # Build should succeed and use less space
    env._build_shadow_image()
    
    # Verify image size is reduced
    image_info = env.docker_builder.get_image_info("shadow:latest")
    assert image_info['size'] < previous_size
```

## 🚀 Expected Outcomes

1. **Unified Build System**: All PANTHER components use the same Docker building infrastructure
2. **Performance Gains**: 40-60% faster network environment builds through caching
3. **Smaller Images**: 30-50% size reduction through multistage optimization
4. **Better Monitoring**: Real-time build progress for all components
5. **Easier Maintenance**: Single point of updates for Docker building logic

## 📝 Notes

### Special Considerations

1. **Shadow NS**: Requires privileged mode and special capabilities - ensure these are preserved
2. **Docker Compose**: Doesn't build its own image but orchestrates others
3. **Localhost**: May need custom image for specific testing scenarios

### Backward Compatibility

- Existing subprocess-based builds continue to work during migration
- Environment variable to toggle between old and new build systems
- Gradual rollout with feature flags

This integration completes the Docker build centralization vision, bringing network environments into the unified system alongside services.