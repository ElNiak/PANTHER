# Docker Builder Enhancement Task

This directory contains task management files for the Docker Builder BUILD_MODE and RUNTIME_MODE enhancement.

## Task Files

### 📋 Core Task Documentation
- **`task.json`** - Structured task metadata, phases, and acceptance criteria
- **`DOCKER_BUILDER_ENHANCEMENT_TASK.md`** - Comprehensive implementation plan and technical details

### 📊 Progress Tracking
- **`progress.md`** - Real-time progress tracker with phase status and next actions
- **`checklist.md`** - Detailed implementation checklist with granular tasks

## Quick Status

**Current Phase**: 🔄 Phase 1 - Core Enhancement (Ready to Start)
**Branch**: `feature/docker-builder-build-runtime-mode-enhancement`
**Next Action**: Implement enhanced `generate_image_tag()` method

## Task Overview

**Objective**: Resolve TODO on line 986 of `docker_builder.py` by implementing centralized BUILD_MODE and RUNTIME_MODE handling in image tag generation.

**Problem**:
- Split responsibility between `service_manager_docker_mixin.py` and `docker_builder.py`
- RUNTIME_MODE missing from image names causing cache inefficiency
- TODO represents architectural debt

**Solution**:
- Centralize all image tagging logic in `docker_builder.py:generate_image_tag()`
- Include both BUILD_MODE and RUNTIME_MODE in image names
- Remove duplicate logic and improve cache differentiation

## Example Enhancement

```python
# Current (incomplete)
def generate_image_tag(self, impl_name, version, tag_version):
    return f"{impl_name}_{version}:{tag_version}" if version else f"{impl_name}:{tag_version}"

# Enhanced (with modes)
def generate_image_tag(self, impl_name, version, tag_version, build_mode="", runtime_mode="minimal"):
    # Build mode suffix (empty string results in no suffix)
    build_suffix = f"_{build_mode}" if build_mode else ""
    # Runtime mode suffix (minimal is default, so no suffix needed)
    runtime_suffix = f"_{runtime_mode}" if runtime_mode and runtime_mode != "minimal" else ""
    # Construct and sanitize tag
    if version:
        base_name = f"{impl_name}_{version}"
    else:
        base_name = impl_name
    full_tag = f"{base_name}{build_suffix}{runtime_suffix}:{tag_version}"
    return self._sanitize_docker_tag(full_tag)
```

## Tag Examples

| Scenario | Current | Enhanced | Benefit |
|----------|---------|----------|---------|
| Default | `picoquic_v1.0:latest` | `picoquic_v1.0:latest` | Same |
| Debug build | `picoquic_v1.0_debug-asan:latest` | `picoquic_v1.0_debug-asan:latest` | Same |
| Debug runtime | `picoquic_v1.0_debug-asan:latest` | `picoquic_v1.0_debug-asan_debug:latest` | ✅ Cache differentiation |
| Profile mode | `picoquic_v1.0:latest` | `picoquic_v1.0_profile:latest` | ✅ Runtime clarity |

## Implementation Phases

1. **Phase 1** (Days 1-2): Core enhancement of `generate_image_tag()`
2. **Phase 2** (Day 3): Integration updates and cleanup
3. **Phase 3** (Days 4-5): Testing and validation
4. **Phase 4** (Day 5): Documentation and migration guide

## Key Files

### Implementation Targets
- `panther/core/docker_builder/docker_builder.py:986` - Main TODO location
- `panther/core/docker_builder/plugin_mixin/service_manager_docker_mixin.py:260-273` - Remove split logic

### Test Files
- `tests/test_docker_builder_tag_generation.py` - New unit tests
- `tests/test_service_manager_integration.py` - Updated integration tests

## Success Criteria

✅ **Functional**:
- All Docker builds generate tags with both BUILD_MODE and RUNTIME_MODE
- Cache differentiation works correctly
- No performance regression
- All existing tests pass

✅ **Quality**:
- Code coverage > 90% for new logic
- No duplicate tag generation logic
- Proper error handling
- Documentation updated

## Getting Started

1. **Review Current State**: `progress.md` for latest status
2. **Follow Checklist**: `checklist.md` for detailed tasks
3. **Read Implementation Plan**: `DOCKER_BUILDER_ENHANCEMENT_TASK.md` for full details
4. **Start Phase 1**: Begin with `docker_builder.py:986` enhancement

## Risk Mitigation

- **Isolated Development**: All work in dedicated worktree branch
- **Incremental Testing**: Validate each phase before proceeding
- **Rollback Plan**: Documented reversion steps
- **Backward Compatibility**: Migration strategy for existing images

---

**Created**: 2025-07-01
**Ready for Implementation**: ✅ Phase 1 can begin
