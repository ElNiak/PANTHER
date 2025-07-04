# TASK-DB-002: BuildX Command Enhancement

## Objective
Enhance the BuildX command construction in DockerBuilder to include native BuildKit platform arguments, improved build argument handling, and modern BuildKit features for better cross-platform build support.

## Technical Details

### Current Issues
- Manual BuildX command construction without platform arguments
- Missing BuildKit automatic variables (BUILDPLATFORM, TARGETARCH, etc.)
- Hardcoded build arguments without proper platform context
- No validation of BuildX command structure

### Proposed Solution
Refactor BuildX command construction to:
1. Include BuildKit automatic platform arguments
2. Add proper build argument handling with platform context
3. Improve command validation and error handling
4. Support modern BuildKit features (progress reporting, etc.)

## Files to Modify

### Primary File
- `REPOS/PANTHER/panther/core/docker_builder/docker_builder.py`

### Specific Changes

#### 1. Replace BuildX command construction in `_build_with_buildx()` method (lines 667-682)

**Current Code:**
```python
# Construct buildx command
buildx_cmd = [
    "docker", "buildx", "build",
    "--builder", builder_name,
    "--platform", self._get_target_platform(),
    "--file", str(relative_dockerfile_path),
    "--tag", image_tag,
    "--debug", "--load",  # Load the image into local Docker daemon
    str(context_path),
]

# Add build arguments with proper shell escaping for JSON values
for key, value in build_args.items():
    # For complex values like JSON, pass them as separate arguments to avoid shell parsing issues
    buildx_cmd.extend(["--build-arg", f"{key}={value}"])
```

**New Code:**
```python
# Construct buildx command with modern BuildKit features
buildx_cmd = self._construct_buildx_command(
    builder_name=builder_name,
    dockerfile_path=selected_dockerfile,
    context_path=context_path,
    image_tag=image_tag,
    build_args=build_args,
    target_platform=self._get_target_platform()
)
```

#### 2. Add new `_construct_buildx_command()` method

```python
def _construct_buildx_command(
    self,
    builder_name: str,
    dockerfile_path: Path,
    context_path: Path,
    image_tag: str,
    build_args: Dict[str, str],
    target_platform: str
) -> List[str]:
    """
    Construct optimized buildx command with modern BuildKit features.

    Args:
        builder_name: Name of the buildx builder instance
        dockerfile_path: Path to the Dockerfile
        context_path: Build context path
        image_tag: Target image tag
        build_args: Build arguments dictionary
        target_platform: Target platform string

    Returns:
        List[str]: Complete buildx command ready for execution
    """
    relative_dockerfile_path = dockerfile_path.relative_to(context_path)
    host_platform = self._get_host_platform()

    # Base buildx command with modern options
    buildx_cmd = [
        "docker", "buildx", "build",
        "--builder", builder_name,
        "--platform", target_platform,
        "--file", str(relative_dockerfile_path),
        "--tag", image_tag,
        "--progress", "plain",  # Better progress reporting than --debug
        "--load"  # Load the image into local Docker daemon
    ]

    # Add BuildKit automatic platform arguments
    automatic_args = self._get_buildkit_automatic_args(host_platform, target_platform)
    for key, value in automatic_args.items():
        buildx_cmd.extend(["--build-arg", f"{key}={value}"])

    # Add user-provided build arguments
    for key, value in build_args.items():
        buildx_cmd.extend(["--build-arg", f"{key}={value}"])

    # Add network mode for dependency resolution
    buildx_cmd.extend(["--network", "host"])

    # Add cache configuration if caching is enabled
    if hasattr(self, '_cache_enabled') and self._cache_enabled:
        cache_args = self._get_buildx_cache_args(target_platform)
        buildx_cmd.extend(cache_args)

    # Add context path
    buildx_cmd.append(str(context_path))

    self.logger.debug("Constructed buildx command: %s", " ".join(buildx_cmd))
    return buildx_cmd
```

#### 3. Add BuildKit automatic arguments method

```python
def _get_buildkit_automatic_args(self, host_platform: str, target_platform: str) -> Dict[str, str]:
    """
    Generate BuildKit automatic platform arguments.

    These arguments are automatically available in modern Dockerfiles but
    need to be explicitly passed when using buildx programmatically.

    Args:
        host_platform: Platform where build is executed
        target_platform: Platform where image will run

    Returns:
        Dict[str, str]: BuildKit automatic arguments
    """
    # Extract OS and architecture from platform strings
    target_os, target_arch = self._parse_platform(target_platform)
    build_os, build_arch = self._parse_platform(host_platform)

    automatic_args = {
        "BUILDPLATFORM": host_platform,
        "TARGETPLATFORM": target_platform,
        "TARGETOS": target_os,
        "TARGETARCH": target_arch,
        "BUILDOS": build_os,
        "BUILDARCH": build_arch
    }

    self.logger.debug("BuildKit automatic arguments: %s", automatic_args)
    return automatic_args

def _parse_platform(self, platform: str) -> Tuple[str, str]:
    """
    Parse platform string into OS and architecture components.

    Args:
        platform: Platform string (e.g., 'linux/amd64', 'linux/arm64')

    Returns:
        Tuple[str, str]: (os, architecture)
    """
    parts = platform.split('/')
    if len(parts) >= 2:
        return parts[0], parts[1]
    else:
        # Default to linux if OS not specified
        return "linux", parts[0] if parts else "amd64"
```

#### 4. Add BuildX cache arguments method

```python
def _get_buildx_cache_args(self, target_platform: str) -> List[str]:
    """
    Get cache arguments for BuildX command.

    Args:
        target_platform: Target platform for cache isolation

    Returns:
        List[str]: Cache arguments for buildx
    """
    if not hasattr(self, 'get_cache_mount_args'):
        return []

    try:
        # Use existing cache mixin if available
        cache_strategy = getattr(self, '_cache_mount_strategy', 'conservative')
        runtime_mode = 'minimal'  # Default, could be made configurable

        # Get cache arguments from mixin
        cache_args = []
        if hasattr(self, '_get_cache_mount_args'):
            mount_args = self._get_cache_mount_args(cache_strategy, runtime_mode, target_platform)
            # Convert mount args to buildx cache args
            platform_safe = target_platform.replace("/", "-")
            cache_args.extend([
                "--cache-from", f"type=local,src=/tmp/buildx-cache-{platform_safe}",
                "--cache-to", f"type=local,dest=/tmp/buildx-cache-{platform_safe},mode=max"
            ])

        return cache_args

    except Exception as e:
        self.logger.warning("Failed to get cache arguments: %s", e)
        return []
```

#### 5. Add command validation method

```python
def _validate_buildx_command(self, buildx_cmd: List[str]) -> bool:
    """
    Validate BuildX command structure before execution.

    Args:
        buildx_cmd: BuildX command list

    Returns:
        bool: True if command is valid, False otherwise
    """
    required_args = ["--platform", "--file", "--tag"]

    # Check for required arguments
    for required_arg in required_args:
        if required_arg not in buildx_cmd:
            self.logger.error("Missing required BuildX argument: %s", required_arg)
            return False

    # Validate platform format
    try:
        platform_index = buildx_cmd.index("--platform") + 1
        platform_value = buildx_cmd[platform_index]
        if not self._is_valid_platform(platform_value):
            self.logger.error("Invalid platform format: %s", platform_value)
            return False
    except (IndexError, ValueError):
        self.logger.error("Invalid --platform argument structure")
        return False

    # Validate file exists
    try:
        file_index = buildx_cmd.index("--file") + 1
        dockerfile_path = buildx_cmd[file_index]
        if not Path(dockerfile_path).exists():
            self.logger.error("Dockerfile not found: %s", dockerfile_path)
            return False
    except (IndexError, ValueError):
        self.logger.error("Invalid --file argument structure")
        return False

    return True

def _is_valid_platform(self, platform: str) -> bool:
    """
    Validate platform string format.

    Args:
        platform: Platform string to validate

    Returns:
        bool: True if platform format is valid
    """
    # Valid platform format: os/arch[/variant]
    parts = platform.split('/')
    if len(parts) < 2:
        return False

    valid_os = ['linux', 'windows', 'darwin']
    valid_arch = ['amd64', 'arm64', 'arm', 'ppc64le', 's390x', '386']

    return parts[0] in valid_os and parts[1] in valid_arch
```

#### 6. Update `_build_with_buildx()` method to use validation

Add validation before command execution (around line 697):

```python
# Validate command before execution
if not self._validate_buildx_command(buildx_cmd):
    raise DockerBuildException(
        message="Invalid BuildX command structure",
        image_name=impl_name,
        dockerfile=str(dockerfile_path),
        build_error="Command validation failed"
    )

self.logger.debug("Executing buildx command: %s", " ".join(buildx_cmd))
```

## Dependencies
- **TASK-DB-001**: Platform Detection Modernization (must be completed first)

## Testing Requirements

### Unit Tests

1. **Test BuildX command construction**
   ```python
   def test_buildx_command_construction(self):
       """Test BuildX command includes all required arguments."""
       builder = DockerBuilder()
       cmd = builder._construct_buildx_command(
           builder_name="test-builder",
           dockerfile_path=Path("Dockerfile"),
           context_path=Path("."),
           image_tag="test:latest",
           build_args={"VERSION": "1.0"},
           target_platform="linux/amd64"
       )

       self.assertIn("--platform", cmd)
       self.assertIn("linux/amd64", cmd)
       self.assertIn("--build-arg", cmd)
       self.assertIn("TARGETPLATFORM=linux/amd64", " ".join(cmd))
   ```

2. **Test BuildKit automatic arguments**
   ```python
   def test_buildkit_automatic_args(self):
       """Test BuildKit automatic arguments generation."""
       builder = DockerBuilder()
       args = builder._get_buildkit_automatic_args("linux/amd64", "linux/arm64")

       expected_args = {
           "BUILDPLATFORM": "linux/amd64",
           "TARGETPLATFORM": "linux/arm64",
           "TARGETOS": "linux",
           "TARGETARCH": "arm64",
           "BUILDOS": "linux",
           "BUILDARCH": "amd64"
       }

       self.assertEqual(args, expected_args)
   ```

3. **Test command validation**
   ```python
   def test_buildx_command_validation(self):
       """Test BuildX command validation catches invalid commands."""
       builder = DockerBuilder()

       # Valid command
       valid_cmd = ["docker", "buildx", "build", "--platform", "linux/amd64",
                   "--file", "Dockerfile", "--tag", "test:latest", "."]
       self.assertTrue(builder._validate_buildx_command(valid_cmd))

       # Invalid command (missing platform)
       invalid_cmd = ["docker", "buildx", "build", "--file", "Dockerfile",
                     "--tag", "test:latest", "."]
       self.assertFalse(builder._validate_buildx_command(invalid_cmd))
   ```

### Integration Tests

1. **Test with real BuildX builder**
   - Create test builder instance
   - Execute command with mock Dockerfile
   - Verify platform arguments are passed correctly

2. **Test cross-platform scenarios**
   - Test AMD64 to ARM64 cross-compilation setup
   - Verify automatic arguments match target platform
   - Test cache argument generation

## Risk Assessment

### Risk Level: Medium

### Potential Issues
1. **Command Structure Changes**: New command format might break existing BuildX integrations
2. **Platform Argument Conflicts**: Automatic arguments might conflict with user-provided ones
3. **Cache Integration**: Cache arguments might interfere with existing cache strategies

### Mitigation Strategies
1. **Comprehensive Validation**: Validate all command components before execution
2. **Fallback Mechanism**: Keep original command construction as fallback
3. **Detailed Logging**: Log full command structure for debugging
4. **Incremental Rollout**: Test with single implementation before full deployment

## Acceptance Criteria

### Must Have
- [ ] BuildX commands include all BuildKit automatic platform arguments
- [ ] User-provided build arguments are preserved and properly formatted
- [ ] Command validation prevents invalid BuildX commands from execution
- [ ] Platform parsing works correctly for all supported platforms
- [ ] All existing BuildX functionality continues to work

### Should Have
- [ ] Cache arguments are properly integrated with existing cache strategy
- [ ] Performance impact is minimal (< 10ms overhead per command construction)
- [ ] Error messages provide clear guidance on command validation failures
- [ ] Integration tests pass on multiple platforms

### Nice to Have
- [ ] Command construction is configurable through feature flags
- [ ] Metrics collection for BuildX command success rates
- [ ] Automated testing with different builder configurations

## Implementation Notes

### Development Steps
1. Create feature branch: `feature/enhance-buildx-commands`
2. Add new helper methods for command construction
3. Update `_build_with_buildx()` to use new command construction
4. Add comprehensive validation logic
5. Write unit tests for all new methods
6. Test with existing QUIC implementations
7. Performance testing and optimization
8. Create pull request with testing results

### Testing Strategy
- Unit tests for all new methods
- Integration tests with real BuildX builders
- Performance benchmarking
- Cross-platform validation
- Error scenario testing

### Performance Considerations
- Command construction should add < 10ms overhead
- Validation should be lightweight (< 5ms)
- Caching of parsed platform information
- Avoid expensive operations in command construction

## Related Tasks
- **TASK-DB-001**: Platform Detection Modernization (prerequisite)
- **TASK-CS-002**: Platform-Aware Caching (uses BuildX cache integration)
- **TASK-DT-001**: Dockerfile Syntax Modernization (benefits from automatic args)

## Success Metrics
- BuildX commands successfully include automatic platform arguments
- Command validation catches 100% of tested invalid scenarios
- Zero regression in existing BuildX build functionality
- Cross-platform builds work correctly with new command structure
- Performance overhead stays within acceptable limits (< 10ms)
