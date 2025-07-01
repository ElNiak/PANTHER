# Docker Builder Enhancement Task: BUILD_MODE & RUNTIME_MODE Integration

## Task Overview

**Objective**: Resolve TODO on line 986 of `docker_builder.py` by implementing centralized BUILD_MODE and RUNTIME_MODE handling in image tag generation, improving cache differentiation and architectural clarity.

**Priority**: High
**Effort**: Large (3-5 days)
**Complexity**: Medium-High

## Current State Analysis

### Problems Identified

1. **TODO on Line 986**: `generate_image_tag()` doesn't use BUILD_MODE/RUNTIME_MODE
2. **Split Responsibility**: Image naming logic exists in both:
   - `service_manager_docker_mixin.py:262-263` (partial handling)
   - `docker_builder.py:986-991` (incomplete implementation)
3. **Cache Inefficiency**: Same image name for different RUNTIME_MODEs
4. **Missing Runtime Differentiation**: `minimal` vs `debug` vs `profile` images not distinguished

### Current Flow Analysis
```
BUILD_MODE: Config → service_manager → version string → docker_builder (incomplete)
RUNTIME_MODE: Config → service_manager → build_args only (not in image names)
```

## Implementation Plan

### Phase 1: Core Enhancement (Days 1-2)

#### 1.1 Enhance `generate_image_tag()` Method
**File**: `docker_builder.py:986-991`

```python
def generate_image_tag(self, impl_name, version, tag_version, build_mode="", runtime_mode="minimal"):
    """
    Generate Docker image tag with build and runtime mode differentiation.

    Args:
        impl_name: Implementation name (e.g., 'picoquic')
        version: Version string (e.g., 'v1.0' or 'latest')
        tag_version: Tag version (e.g., 'latest', 'stable')
        build_mode: Build mode ('', 'debug-asan', 'rel-lto', 'release-static-pgo')
        runtime_mode: Runtime mode ('minimal', 'debug', 'profile')

    Returns:
        str: Complete image tag

    Examples:
        - picoquic_v1.0_debug-asan_debug:latest
        - picoquic_v1.0__minimal:latest (empty build_mode)
        - picoquic_v1.0_rel-lto_profile:latest
        - picoquic:latest (no version, minimal runtime)
    """
    # Build mode suffix (empty string results in no suffix)
    build_suffix = f"_{build_mode}" if build_mode else ""

    # Runtime mode suffix (minimal is default, so no suffix needed)
    runtime_suffix = f"_{runtime_mode}" if runtime_mode and runtime_mode != "minimal" else ""

    # Construct base name with version
    if version:
        base_name = f"{impl_name}_{version}"
    else:
        base_name = impl_name

    # Combine all parts
    full_tag = f"{base_name}{build_suffix}{runtime_suffix}:{tag_version}"

    # Sanitize tag (Docker tags have character restrictions)
    return self._sanitize_docker_tag(full_tag)

def _sanitize_docker_tag(self, tag: str) -> str:
    """
    Sanitize Docker tag to meet Docker naming requirements.

    Docker tag rules:
    - Lowercase letters, digits, underscores, periods, dashes
    - Cannot start with period or dash
    - Max 128 characters
    """
    import re

    # Convert to lowercase and replace invalid characters
    sanitized = re.sub(r'[^a-z0-9._-]', '_', tag.lower())

    # Ensure doesn't start with period or dash
    sanitized = re.sub(r'^[.-]+', '', sanitized)

    # Truncate if too long (leave room for registry prefix)
    if len(sanitized) > 100:
        # Keep the tag version part intact
        parts = sanitized.split(':')
        if len(parts) == 2:
            name_part, tag_part = parts
            max_name_length = 100 - len(tag_part) - 1  # -1 for ':'
            if len(name_part) > max_name_length:
                name_part = name_part[:max_name_length]
            sanitized = f"{name_part}:{tag_part}"
        else:
            sanitized = sanitized[:100]

    return sanitized
```

#### 1.2 Update `build_image()` Method Signature
**File**: `docker_builder.py:775-784`

```python
def build_image(
    self,
    impl_name: str,
    version: str,
    dockerfile_path: Path,
    context_path: Path,
    config: Dict[str, Any],
    tag_version: str = "latest",
    remove_dangling: bool = False,
    experiment_id: Optional[str] = None,
) -> Optional[str]:
```

#### 1.3 Extract Modes in `build_image()`
**File**: `docker_builder.py:~817` (after tag generation)

```python
# Extract build and runtime modes from config
build_mode = config.get("build_mode", "")
runtime_mode = config.get("runtime_mode", "minimal")

# Generate image tag with mode information
image_tag = self.generate_image_tag(
    impl_name=impl_name,
    version=version,
    tag_version=tag_version,
    build_mode=build_mode,
    runtime_mode=runtime_mode
)

self.logger.debug(
    f"Generated image tag: {image_tag} (build_mode='{build_mode}', runtime_mode='{runtime_mode}')"
)
```

### Phase 2: Integration Updates (Day 3)

#### 2.1 Update `_build_with_buildx()` Method
**File**: `docker_builder.py:593`

```python
# Replace line 593
image_tag = self.generate_image_tag(
    impl_name=impl_name,
    version=version,
    tag_version=tag_version,
    build_mode=config.get("build_mode", ""),
    runtime_mode=config.get("runtime_mode", "minimal")
)
```

#### 2.2 Simplify `service_manager_docker_mixin.py`
**File**: `service_manager_docker_mixin.py:260-273`

Remove local image tag generation:
```python
# REMOVE THESE LINES (260-273):
# base_version = protocol_version or "latest"
# build_mode_suffix = f"_{build_mode}" if build_mode else ""
# version = f"{base_version}{build_mode_suffix}"
# ...
# if version:
#     image_name = f"{self.implementation_name}_{version}:latest"
# else:
#     image_name = f"{self.implementation_name}:latest"

# REPLACE WITH:
base_version = protocol_version or "latest"
```

#### 2.3 Update Docker Build Call
**File**: `service_manager_docker_mixin.py:354-361`

```python
# Update version_dict to use clean version (without build_mode suffix)
version_dict = {
    "version": base_version,  # Remove build_mode from version
    "build_mode": build_mode,
    "runtime_mode": runtime_mode,
}
if dependencies is not None:
    version_dict["dependencies"] = dependencies
    version_dict["commit"] = commit

# The image tag will be generated by docker_builder.build_image()
image_tag = docker_builder.build_image(
    impl_name=self.implementation_name,
    version=base_version,  # Clean version without mode suffix
    dockerfile_path=dockerfile_path,
    context_path=plugin_dir,
    config=version_dict,
    tag_version="latest",
)

# Update logging to use returned image_tag
self.logger.info(f"Service Docker image {image_tag} built successfully")
```

### Phase 3: Testing & Validation (Days 4-5)

#### 3.1 Unit Tests
**File**: `tests/test_docker_builder_tag_generation.py` (new)

```python
import pytest
from panther.core.docker_builder import DockerBuilder

class TestDockerBuilderTagGeneration:

    def test_generate_image_tag_basic(self):
        builder = DockerBuilder()
        tag = builder.generate_image_tag("picoquic", "v1.0", "latest")
        assert tag == "picoquic_v1.0:latest"

    def test_generate_image_tag_with_build_mode(self):
        builder = DockerBuilder()
        tag = builder.generate_image_tag("picoquic", "v1.0", "latest", "debug-asan")
        assert tag == "picoquic_v1.0_debug-asan:latest"

    def test_generate_image_tag_with_runtime_mode(self):
        builder = DockerBuilder()
        tag = builder.generate_image_tag("picoquic", "v1.0", "latest", "", "debug")
        assert tag == "picoquic_v1.0_debug:latest"

    def test_generate_image_tag_both_modes(self):
        builder = DockerBuilder()
        tag = builder.generate_image_tag("picoquic", "v1.0", "latest", "rel-lto", "profile")
        assert tag == "picoquic_v1.0_rel-lto_profile:latest"

    def test_generate_image_tag_minimal_runtime_omitted(self):
        builder = DockerBuilder()
        tag = builder.generate_image_tag("picoquic", "v1.0", "latest", "debug-asan", "minimal")
        assert tag == "picoquic_v1.0_debug-asan:latest"

    def test_generate_image_tag_no_version(self):
        builder = DockerBuilder()
        tag = builder.generate_image_tag("picoquic", "", "latest", "debug-asan", "debug")
        assert tag == "picoquic_debug-asan_debug:latest"

    def test_tag_sanitization(self):
        builder = DockerBuilder()
        tag = builder.generate_image_tag("Test@Image", "v1.0", "latest", "Debug-ASAN", "Profile")
        assert tag == "test_image_v1.0_debug-asan_profile:latest"

    def test_tag_length_limit(self):
        builder = DockerBuilder()
        long_name = "very_long_implementation_name_that_exceeds_normal_limits"
        tag = builder.generate_image_tag(long_name, "v1.0", "latest", "release-static-pgo", "profile")
        assert len(tag) <= 100
        assert tag.endswith(":latest")
```

#### 3.2 Integration Tests
**File**: `tests/test_service_manager_integration.py` (update existing)

```python
def test_service_docker_build_with_modes(self):
    """Test that service manager properly passes modes to docker builder."""
    # Mock service with build and runtime modes
    service = MockService()
    service.implementation_name = "test_service"
    service.get_build_mode = lambda: "debug-asan"
    # ... set up runtime mode configuration

    # Verify docker_builder.build_image is called with correct parameters
    with patch.object(DockerBuilder, 'build_image') as mock_build:
        service.prepare(mock_plugin_manager)

        mock_build.assert_called_once()
        call_args = mock_build.call_args
        config = call_args.kwargs['config']

        assert config['build_mode'] == 'debug-asan'
        assert config['runtime_mode'] in ['minimal', 'debug', 'profile']
```

#### 3.3 Backward Compatibility Tests
```python
def test_backward_compatibility_existing_images(self):
    """Ensure existing images still work with new naming scheme."""
    # Test that old image references still resolve
    # Test migration path for existing cached images
```

### Phase 4: Documentation & Migration (Day 5)

#### 4.1 Update Documentation
**Files**:
- `panther/core/docker_builder/README.md`
- `docs/docker_architecture.md`

#### 4.2 Migration Guide
**File**: `docs/DOCKER_TAG_MIGRATION.md`

```markdown
# Docker Tag Migration Guide

## New Tagging Scheme

Old: `picoquic_v1.0_debug-asan:latest`
New: `picoquic_v1.0_debug-asan_debug:latest`

## Breaking Changes
- RUNTIME_MODE now included in image tags
- Image cache will need to rebuild for new tags
```

## Risk Assessment

### High Risk Areas
1. **Cache Invalidation**: All existing images will need rebuilding
2. **CI/CD Impact**: Build pipelines may reference old tag patterns
3. **Registry Storage**: Temporary storage increase during transition

### Mitigation Strategies
1. **Gradual Rollout**: Feature flag for new tagging scheme
2. **Parallel Tags**: Generate both old and new tags during transition
3. **Cleanup Scripts**: Remove old images after validation

## Success Metrics

### Functional Requirements
- [ ] All Docker builds generate tags with both BUILD_MODE and RUNTIME_MODE
- [ ] Cache differentiation works correctly
- [ ] No performance regression in build times
- [ ] All existing tests pass

### Quality Requirements
- [ ] Code coverage > 90% for new tag generation logic
- [ ] No duplicate image tag generation logic
- [ ] Proper error handling for invalid mode combinations
- [ ] Documentation updated and reviewed

## Rollback Plan

If issues are discovered:
1. Revert `generate_image_tag()` changes
2. Restore original tagging logic in `service_manager_docker_mixin.py`
3. Clear problematic cached images
4. Rebuild with original naming scheme

## Implementation Checklist

### Phase 1: Core Enhancement
- [ ] Implement enhanced `generate_image_tag()` method
- [ ] Add `_sanitize_docker_tag()` helper method
- [ ] Update `build_image()` to extract modes from config
- [ ] Update `_build_with_buildx()` method

### Phase 2: Integration
- [ ] Remove image tag generation from `service_manager_docker_mixin.py`
- [ ] Update Docker build call to use clean version
- [ ] Update logging to use returned image tags

### Phase 3: Testing
- [ ] Write comprehensive unit tests
- [ ] Update integration tests
- [ ] Add backward compatibility tests
- [ ] Validate cache behavior

### Phase 4: Documentation
- [ ] Update README and architecture docs
- [ ] Create migration guide
- [ ] Update inline code comments

This implementation resolves the architectural debt while maintaining backward compatibility and improving cache efficiency through proper mode differentiation.
