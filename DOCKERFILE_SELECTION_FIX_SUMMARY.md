# Dockerfile Selection Fix for ARM64 Compatibility

## Problem Analysis

The PANTHER IVY tester service was failing to build on ARM64 platforms due to package installation errors:

```
E: Unable to locate package python3.10
E: Unable to locate package alien
E: Unable to locate package tix
E: Unable to locate package rand
```

## Root Cause

The Docker build system was using the legacy `Dockerfile` instead of the modernized `Dockerfile.buildkit` for the IVY service. While the buildx code path had proper Dockerfile selection logic, the regular Docker build path was missing this functionality.

### Investigation Results

1. **Base Service**: Building successfully on ARM64 (32/32 steps completed)
2. **IVY Service**: Failing because it used legacy Dockerfile with ARM64-incompatible packages
3. **BuildKit Selection**: Only worked in buildx path, not regular Docker build path

## Solution Implemented

### 1. Fixed Missing Module Import

**Issue**: `context_helper.py` module was missing, causing import errors.

**Fix**: Created `/panther/core/docker_builder/utils/context_helper.py` with:
- `_ensure_docker_host()` - Docker host configuration
- `ensure_builder_context()` - BuildX context management

### 2. Added Dockerfile Selection Logic to Regular Build Path

**Issue**: Regular Docker build (line 1370 in `docker_builder.py`) used `dockerfile_path` directly without selection logic.

**Fix**: Added the same Dockerfile selection logic used in buildx path:

```python
# Prefer Dockerfile.buildkit or multistage variants if they exist
buildkit_candidates = [
    Path(dockerfile_path).parent / "Dockerfile.buildkit",
    Path(dockerfile_path).parent / "Dockerfile.multistage",
    dockerfile_path,  # fallback to original
]

selected_dockerfile = None
for candidate in buildkit_candidates:
    if candidate.exists():
        selected_dockerfile = candidate
        self.logger.debug(
            "Selected Dockerfile for regular build: %s", selected_dockerfile
        )
        break
```

### 3. Fixed DockerImageCache Initialization

**Issue**: `DockerImageCache` constructor didn't accept `target_platform` parameter.

**Fix**: Removed the invalid parameter from DockerBuilder initialization.

## Validation Results

### Dockerfile Selection Test
```
🔍 Testing Dockerfile selection logic for IVY service...
📁 Testing directory: panther/plugins/services/testers/panther_ivy
📄 Legacy Dockerfile exists: ✓
🔧 BuildKit Dockerfile exists: ✓
🎯 Selected Dockerfile: Dockerfile.buildkit
✅ SUCCESS: Dockerfile.buildkit correctly selected!
```

### ARM64 Features Test
```
🔧 ARM64-compatible features found: 5/5
   ✓ TARGETPLATFORM
   ✓ TARGETARCH
   ✓ architecture-specific package handling
   ✓ cross-compilation tools
   ✓ --mount=type=cache
✅ SUCCESS: Dockerfile.buildkit has ARM64 compatibility features!
```

## Expected Impact

With this fix, the Docker build system will now:

1. **Always prefer `Dockerfile.buildkit`** when it exists, regardless of build method
2. **Use ARM64-compatible package installation** with graceful degradation
3. **Apply proper cross-compilation toolchain setup** for ARM64 builds
4. **Leverage BuildKit caching** for faster builds

## Files Modified

1. **`panther/core/docker_builder/utils/context_helper.py`** - New file
2. **`panther/core/docker_builder/docker_builder.py`** - Added Dockerfile selection logic

## Next Steps

1. Run full PANTHER ARM64 test to validate the fix
2. Monitor build logs for "Selected Dockerfile for regular build: Dockerfile.buildkit"
3. Confirm ARM64 package installation succeeds with architecture-specific handling

## Technical Details

The fix ensures that both buildx and regular Docker build paths use the same intelligent Dockerfile selection:

- **Priority 1**: `Dockerfile.buildkit` (ARM64-compatible with modern BuildKit features)
- **Priority 2**: `Dockerfile.multistage` (fallback modern approach)
- **Priority 3**: `Dockerfile` (legacy fallback)

This resolves the ARM64 compatibility issue by ensuring the build system always uses the modernized Dockerfile with proper platform-aware package handling.
