# TASK-DB-001: Platform Detection Modernization

## Objective
Modernize the platform detection logic in DockerBuilder to use native BuildKit platform arguments while maintaining backward compatibility with existing configuration overrides.

## Technical Details

### Current Issues
- Manual platform detection using `platform.machine()`
- Hardcoded platform mapping without BuildKit integration
- Missing support for BuildKit automatic platform variables
- TODO comment indicates incomplete ARM64 support

### Proposed Solution
Replace manual platform detection with BuildKit-aware logic that:
1. Prioritizes BuildKit environment variables (`TARGETPLATFORM`)
2. Maintains configuration override capability
3. Falls back to host detection when needed
4. Adds proper ARM64 support validation

## Files to Modify

### Primary File
- `REPOS/PANTHER/panther/core/docker_builder/docker_builder.py`

### Specific Changes

#### 1. Update `_get_target_platform()` method (lines 313-354)

**Current Code:**
```python
def _get_target_platform(self) -> str:
    # Check for configuration override first
    if (hasattr(self, "global_config") and self.global_config
        and hasattr(self.global_config, "docker")
        and self.global_config.docker.target_platform):
        target_platform = self.global_config.docker.target_platform
        self.logger.debug("Using configured target platform override: %s", target_platform)
        return target_platform

    # Detect host architecture and map to appropriate Docker platform
    machine = platform.machine().lower()
    if machine in ["arm64", "aarch64"]:
        docker_platform = "linux/arm64"  # TODO: Change to arm64 when we have arm64 images for ivy and shadow
    elif machine in ["x86_64", "amd64"]:
        docker_platform = "linux/amd64"
    else:
        # Default to amd64 for unknown architectures
        docker_platform = "linux/amd64"
        self.logger.warning("Unknown architecture '%s', defaulting to %s", machine, docker_platform)

    self.logger.debug("Detected host architecture: %s -> Docker platform: %s", machine, docker_platform)
    return docker_platform
```

**New Code:**
```python
def _get_target_platform(self) -> str:
    """
    Detect the appropriate Docker platform using BuildKit-aware logic.

    Priority order:
    1. Configuration override (global_config.docker.target_platform)
    2. BuildKit environment variable (TARGETPLATFORM)
    3. Host architecture detection (fallback)

    Returns:
        str: Docker platform string (e.g., 'linux/amd64', 'linux/arm64')
    """
    # Check for configuration override first (highest priority)
    if (hasattr(self, "global_config") and self.global_config
        and hasattr(self.global_config, "docker")
        and self.global_config.docker.target_platform):
        target_platform = self.global_config.docker.target_platform
        self.logger.debug("Using configured target platform override: %s", target_platform)
        return target_platform

    # Use BuildKit automatic platform detection when available
    buildkit_platform = os.environ.get('TARGETPLATFORM')
    if buildkit_platform:
        self.logger.debug("Using BuildKit TARGETPLATFORM: %s", buildkit_platform)
        return buildkit_platform

    # Fallback to host detection with improved ARM64 support
    machine = platform.machine().lower()
    if machine in ["arm64", "aarch64"]:
        docker_platform = "linux/arm64"
        # Validate ARM64 support for current context
        if hasattr(self, '_validate_arm64_support'):
            self._validate_arm64_support()
    elif machine in ["x86_64", "amd64"]:
        docker_platform = "linux/amd64"
    else:
        # Default to amd64 for unknown architectures
        docker_platform = "linux/amd64"
        self.logger.warning("Unknown architecture '%s', defaulting to %s", machine, docker_platform)

    self.logger.debug("Detected host architecture: %s -> Docker platform: %s", machine, docker_platform)
    return docker_platform
```

#### 2. Add ARM64 validation method
```python
def _validate_arm64_support(self) -> None:
    """
    Validate ARM64 support for current implementation context.

    Some implementations (ivy, shadow) have limited ARM64 support.
    Log warnings for unsupported combinations.
    """
    # Implementation-specific ARM64 support matrix
    arm64_unsupported = ["ivy", "shadow"]

    # Try to determine current implementation from context
    current_impl = getattr(self, '_current_implementation', None)
    if current_impl and current_impl in arm64_unsupported:
        self.logger.warning(
            "ARM64 support for '%s' is experimental. "
            "Consider using linux/amd64 for production builds.",
            current_impl
        )
```

#### 3. Update imports
Add to imports section (around line 22):
```python
import os  # Add if not already present
```

#### 4. Add implementation context tracking
Add to `build_image()` method (around line 827):
```python
def build_image(self, impl_name: str, version: str, dockerfile_path: Path,
                context_path: Path, config: Dict[str, Any],
                tag_version: str = "latest", remove_dangling: bool = False,
                experiment_id: Optional[str] = None) -> Optional[str]:
    """Build a Docker image for the specified implementation."""
    try:
        # Track current implementation for platform validation
        self._current_implementation = impl_name

        # Fast-fail validation before expensive build operation
        self._validate_build_prerequisites(impl_name, dockerfile_path, context_path, config)

        # ... rest of existing method
```

## Dependencies
- None (this is a foundational change)

## Testing Requirements

### Unit Tests
1. **Test configuration override priority**
   ```python
   def test_platform_override_priority(self):
       """Test that config override takes precedence over environment."""
       os.environ['TARGETPLATFORM'] = 'linux/arm64'
       builder = DockerBuilder(global_config=MockConfig(target_platform='linux/amd64'))
       assert builder._get_target_platform() == 'linux/amd64'
   ```

2. **Test BuildKit environment detection**
   ```python
   def test_buildkit_platform_detection(self):
       """Test BuildKit TARGETPLATFORM environment variable usage."""
       os.environ['TARGETPLATFORM'] = 'linux/arm64'
       builder = DockerBuilder()
       assert builder._get_target_platform() == 'linux/arm64'
   ```

3. **Test ARM64 validation warnings**
   ```python
   def test_arm64_validation_warning(self):
       """Test ARM64 validation warns for unsupported implementations."""
       builder = DockerBuilder()
       builder._current_implementation = 'ivy'
       with self.assertLogs(level='WARNING') as log:
           builder._validate_arm64_support()
       self.assertIn('ARM64 support for \'ivy\' is experimental', log.output[0])
   ```

### Integration Tests
1. **Test with real BuildKit environment**
   - Set `TARGETPLATFORM=linux/arm64` in environment
   - Verify platform detection returns correct value
   - Test with different platform combinations

2. **Test backward compatibility**
   - Ensure existing configurations continue to work
   - Verify fallback behavior when BuildKit variables not set
   - Test unknown architecture handling

## Risk Assessment

### Risk Level: Medium

### Potential Issues
1. **Environment Variable Conflicts**: BuildKit variables might conflict with existing setup
2. **Backward Compatibility**: Changes to platform detection could break existing workflows
3. **ARM64 Support**: Enabling ARM64 detection might expose unsupported implementations

### Mitigation Strategies
1. **Feature Flag**: Add configuration to enable/disable BuildKit detection
   ```python
   use_buildkit_detection = getattr(self.global_config.docker, 'use_buildkit_detection', True)
   ```

2. **Comprehensive Logging**: Add detailed logging for platform detection decisions
3. **Gradual Rollout**: Test with single implementation before system-wide deployment

## Acceptance Criteria

### Must Have
- [ ] Platform detection prioritizes config override > BuildKit env > host detection
- [ ] BuildKit `TARGETPLATFORM` environment variable is respected
- [ ] Backward compatibility maintained for existing configurations
- [ ] ARM64 validation warnings added for unsupported implementations
- [ ] All existing unit tests pass
- [ ] New unit tests cover all platform detection paths

### Should Have
- [ ] Integration tests validate BuildKit environment behavior
- [ ] Performance impact is negligible (< 5ms overhead)
- [ ] Logging provides clear visibility into platform detection decisions
- [ ] Documentation updated to reflect new behavior

### Nice to Have
- [ ] Feature flag for gradual enablement
- [ ] Metrics collection for platform usage patterns
- [ ] Automated testing on multiple architectures

## Implementation Notes

### Development Steps
1. Create feature branch: `feature/modernize-platform-detection`
2. Add new imports and helper methods
3. Update `_get_target_platform()` method
4. Add ARM64 validation logic
5. Update build_image() to track implementation context
6. Write comprehensive unit tests
7. Test on development environment
8. Create pull request with detailed testing results

### Testing Environment
- Test on both x86_64 and ARM64 hosts
- Verify with and without BuildKit environment variables
- Test with various configuration combinations
- Validate log output clarity and usefulness

### Rollback Plan
If issues are discovered:
1. Revert to original `_get_target_platform()` implementation
2. Remove new helper methods and imports
3. Restore original behavior through configuration flag
4. Investigate issues before re-implementing

## Related Tasks
- **TASK-DB-002**: BuildX Command Enhancement (depends on this platform detection)
- **TASK-CS-002**: Platform-Aware Caching (uses platform detection output)
- **TASK-DT-002**: Cross-Compilation Support (relies on accurate platform detection)

## Success Metrics
- Platform detection works correctly in 100% of test scenarios
- Zero regression in existing platform detection behavior
- BuildKit integration provides expected platform values
- ARM64 warnings appear for appropriate implementations
- Performance overhead < 5ms per platform detection call
