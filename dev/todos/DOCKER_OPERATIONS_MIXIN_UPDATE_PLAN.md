# Docker Operations Mixin Update Plan

## 🎯 Objective

Update `docker_operations_mixin.py` to support multistage builds and target specification while maintaining backward compatibility.

## 📝 Current Implementation Analysis

The current `DockerOperationsMixin` has these limitations:
1. No multistage build support
2. No target specification capability
3. Basic caching strategy
4. Limited build configuration options
5. No parallel build support

## 🔧 Proposed Updates

### 1. Enhanced prepare_docker_image Method

```python
def prepare_docker_image(
    self,
    image_name: str | None = None,
    dockerfile_path: str | Path | None = None,
    build_context: str | Path | None = None,
    build_args: dict[str, str] | None = None,
    no_cache: bool = False,
    target: str | None = None,  # NEW: Target stage
    cache_from: list[str] | None = None,  # NEW: Cache sources
    build_config: BuildConfig | None = None,  # NEW: Full config object
    parallel: bool = False,  # NEW: Parallel build
) -> bool:
    """
    Prepare a Docker image with multistage build support.
    
    Args:
        target: Target stage to build up to
        cache_from: List of images/stages to use as cache
        build_config: Complete build configuration object
        parallel: Enable parallel stage building
    """
```

### 2. New Build Configuration Methods

```python
def get_build_configuration(self) -> BuildConfig:
    """
    Get or create build configuration for this service.
    
    Returns:
        BuildConfig: Configuration with stage definitions
    """
    if hasattr(self, '_build_config'):
        return self._build_config
    
    # Auto-detect language and create config
    language = self._detect_language()
    return BuildConfigFactory.create_for_language(
        language=language,
        service_name=self.implementation_name,
        base_image=getattr(self, 'base_image', 'ubuntu:22.04')
    )

def set_build_target(self, target: str) -> None:
    """Set the target stage for building."""
    self._build_target = target

def enable_build_caching(self, cache_sources: list[str]) -> None:
    """Enable caching from specific sources."""
    self._cache_sources = cache_sources
```

### 3. Enhanced Docker Builder Integration

```python
def _build_with_enhanced_docker_builder(
    self,
    config: BuildConfig,
    target: str | None = None
) -> bool:
    """
    Build using enhanced DockerBuilder with multistage support.
    """
    # Create enhanced build request
    build_request = BuildRequest(
        implementation_name=self.implementation_name,
        dockerfile_path=self.docker_file_path,
        context_path=Path(self.docker_file_path).parent,
        config=config,
        target=target or self._build_target,
        cache_from=self._cache_sources,
        parallel=True,
        progress_callback=self._on_build_progress
    )
    
    # Use enhanced builder
    result = self.docker_builder.build_with_stages(build_request)
    
    if result.success:
        self.logger.info(
            f"Built {result.stages_completed} stages in {result.duration}s"
        )
        # Update image name with specific tag
        self.docker_image_name = result.final_tag
        return True
    
    return False
```

### 4. Stage Management Methods

```python
def get_available_stages(self) -> list[str]:
    """Get list of available build stages."""
    config = self.get_build_configuration()
    return [stage.name for stage in config.stages]

def build_up_to_stage(self, stage: str) -> bool:
    """Build image up to a specific stage."""
    return self.prepare_docker_image(target=stage)

def get_stage_dependencies(self, stage: str) -> list[str]:
    """Get dependencies for a specific stage."""
    config = self.get_build_configuration()
    stage_obj = next((s for s in config.stages if s.name == stage), None)
    return stage_obj.dependencies if stage_obj else []
```

### 5. Caching Strategy Methods

```python
def optimize_build_cache(self) -> CacheStrategy:
    """
    Optimize cache usage based on service type.
    
    Returns:
        CacheStrategy: Optimized caching configuration
    """
    strategy = CacheStrategy()
    
    # Language-specific optimizations
    if self._is_compiled_language():
        strategy.cache_stages = ['base', 'dev-deps', 'builder']
        strategy.cache_mount_points = ['/root/.cache', '/tmp/build-cache']
    else:
        strategy.cache_stages = ['base', 'deps']
        strategy.cache_mount_points = ['/root/.cache']
    
    # Add Docker BuildKit cache mounts
    strategy.buildkit_enabled = True
    strategy.inline_cache = True
    
    return strategy

def export_build_cache(self, registry: str) -> bool:
    """Export build cache to registry for reuse."""
    return self.docker_builder.export_cache(
        self.docker_image_name,
        registry,
        stages=self.get_available_stages()
    )
```

### 6. Progress Monitoring

```python
def _on_build_progress(self, progress: BuildProgress) -> None:
    """
    Handle build progress updates.
    
    Args:
        progress: Build progress information
    """
    self.emit_docker_build_progress(
        stage=progress.current_stage,
        percent=progress.percent_complete,
        message=progress.message
    )
    
    # Log significant milestones
    if progress.stage_completed:
        self.logger.info(
            f"Stage '{progress.current_stage}' completed "
            f"({progress.percent_complete}%)"
        )
```

### 7. Backward Compatibility Layer

```python
def prepare(self, plugin_manager: Optional["PluginManager"] = None) -> None:
    """
    Enhanced prepare with backward compatibility.
    """
    # Check if we should use enhanced building
    use_enhanced = (
        hasattr(self, 'use_multistage_build') and 
        self.use_multistage_build
    ) or (
        self.global_config and 
        self.global_config.docker.multistage_builds_enabled
    )
    
    if use_enhanced:
        # Use new multistage approach
        config = self.get_build_configuration()
        self._build_with_enhanced_docker_builder(config)
    else:
        # Fall back to legacy approach
        super().prepare(plugin_manager)
```

## 🔄 Migration Path

### Phase 1: Add New Methods (Non-Breaking)
```python
# Add new methods without changing existing behavior
class DockerOperationsMixin(LoggerMixin):
    # ... existing methods remain unchanged ...
    
    # New methods added
    def prepare_docker_image_v2(self, **kwargs): ...
    def get_build_configuration(self): ...
    def set_build_target(self, target): ...
```

### Phase 2: Update Internal Implementation
```python
# Update prepare_docker_image to support new features
def prepare_docker_image(self, **kwargs):
    # Check for new parameters
    if 'target' in kwargs or 'build_config' in kwargs:
        return self._prepare_with_multistage(**kwargs)
    else:
        return self._prepare_legacy(**kwargs)
```

### Phase 3: Update Service Managers
```python
# Service managers opt-in to new features
class PicoquicServiceManager(BaseQUICServiceManager):
    use_multistage_build = True  # Enable new features
    
    def get_build_configuration(self):
        config = super().get_build_configuration()
        config.stages.append(
            BuildStage(name='picoquic-optimized', target=True)
        )
        return config
```

## 📊 Configuration Schema Updates

### Service Configuration
```yaml
services:
  picoquic:
    docker:
      multistage: true
      target: runtime  # Specific target stage
      cache_from:
        - base
        - cpp-dev
      parallel_build: true
      build_args:
        ENABLE_OPTIMIZATION: "true"
```

### Global Docker Configuration
```yaml
docker:
  multistage_builds_enabled: true
  build_cache_registry: "ghcr.io/elniak/panther-cache"
  parallel_builds: true
  buildkit_enabled: true
```

## 🧪 Testing Strategy

### Unit Tests
```python
def test_multistage_build_support():
    """Test multistage build functionality."""
    mixin = DockerOperationsMixin()
    mixin.docker_image_name = "test:latest"
    mixin.docker_file_path = "test/Dockerfile"
    
    # Test target specification
    result = mixin.prepare_docker_image(
        target="builder",
        cache_from=["base"]
    )
    assert result
    assert mixin.docker_builder.last_target == "builder"

def test_backward_compatibility():
    """Ensure old API still works."""
    mixin = DockerOperationsMixin()
    # Old-style call should work
    result = mixin.prepare_docker_image(
        image_name="test:latest",
        dockerfile_path="test/Dockerfile"
    )
    assert result
```

### Integration Tests
```python
def test_service_with_multistage():
    """Test real service with multistage builds."""
    service = PicoquicServiceManager(...)
    service.use_multistage_build = True
    
    # Should use enhanced building
    service.prepare()
    
    # Verify stages were built
    stages = service.get_completed_stages()
    assert "base" in stages
    assert "runtime" in stages
```

## 📈 Performance Impact

### Expected Improvements
- **First build**: Similar performance (all stages built)
- **Subsequent builds**: 50-70% faster (cache reuse)
- **Parallel builds**: 30-40% faster (stage parallelization)
- **CI/CD builds**: 60-80% faster (registry cache)

### Metrics to Track
```python
class BuildMetrics:
    """Track build performance metrics."""
    
    def record_build(self, service: str, duration: float, stages: int):
        self.metrics.append({
            'service': service,
            'duration': duration,
            'stages': stages,
            'cache_hit_rate': self._calculate_cache_hits(),
            'timestamp': datetime.now()
        })
```

## 🎯 Success Criteria

1. **No Breaking Changes**: All existing code continues to work
2. **Performance Improvement**: 50%+ reduction in average build time
3. **Developer Adoption**: 80%+ services using multistage builds
4. **Cache Efficiency**: 70%+ cache hit rate in CI/CD
5. **Error Reduction**: 30% fewer build failures

## 📅 Implementation Timeline

- **Week 1**: Add new methods and configuration schema
- **Week 2**: Implement enhanced DockerBuilder integration
- **Week 3**: Create migration utilities and documentation
- **Week 4**: Update service managers and test
- **Week 5**: Performance optimization and monitoring
- **Week 6**: Full rollout and deprecation planning

This plan ensures smooth transition to multistage builds while maintaining full backward compatibility and providing significant performance improvements.