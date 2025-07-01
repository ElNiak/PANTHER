# Docker Builder Enhancement - Progress Tracker

## Task Overview
**Objective**: Resolve TODO on line 986 of `docker_builder.py` by implementing centralized BUILD_MODE and RUNTIME_MODE handling in image tag generation.

**Branch**: `feature/docker-builder-build-runtime-mode-enhancement`
**Created**: 2025-07-01
**Status**: 🟡 Planning Complete, Ready for Implementation

## Phase Progress

### ✅ Phase 0: Analysis & Planning (Completed)
- [x] Analyzed current architecture and flow
- [x] Identified problems and split responsibility issues
- [x] Created comprehensive implementation plan
- [x] Set up git worktree and task structure
- [x] Documented acceptance criteria and success metrics

### 🔄 Phase 1: Core Enhancement (Days 1-2) - **NEXT**
**Target**: Enhance `generate_image_tag()` method and update core build logic

#### Tasks:
- [ ] **P1.1**: Implement enhanced `generate_image_tag()` method
  - Location: `docker_builder.py:986-991`
  - Add BUILD_MODE and RUNTIME_MODE parameters
  - Include tag sanitization logic

- [ ] **P1.2**: Add `_sanitize_docker_tag()` helper method
  - Docker naming compliance
  - Character restrictions and length limits

- [ ] **P1.3**: Update `build_image()` to extract modes from config
  - Location: `docker_builder.py:~817`
  - Extract build_mode and runtime_mode from config dict
  - Call enhanced generate_image_tag()

- [ ] **P1.4**: Update `_build_with_buildx()` method
  - Location: `docker_builder.py:593`
  - Use new tag generation approach

### 🟡 Phase 2: Integration Updates (Day 3) - **PENDING**
**Target**: Remove split responsibility and update integration points

#### Tasks:
- [ ] **P2.1**: Remove image tag generation from `service_manager_docker_mixin.py`
  - Location: `service_manager_docker_mixin.py:260-273`
  - Clean up local tag generation logic

- [ ] **P2.2**: Update Docker build call to use clean version
  - Location: `service_manager_docker_mixin.py:354-361`
  - Pass clean version without mode suffix

- [ ] **P2.3**: Update logging to use returned image tags
  - Ensure consistent logging across the system

### 🟡 Phase 3: Testing & Validation (Days 4-5) - **PENDING**
**Target**: Comprehensive testing and validation

#### Tasks:
- [ ] **P3.1**: Write comprehensive unit tests
  - Create `tests/test_docker_builder_tag_generation.py`
  - Test all tag generation scenarios

- [ ] **P3.2**: Update integration tests
  - Update `tests/test_service_manager_integration.py`
  - Verify end-to-end flow

- [ ] **P3.3**: Add backward compatibility tests
  - Ensure existing images still work
  - Test migration scenarios

- [ ] **P3.4**: Validate cache behavior
  - Verify cache differentiation works
  - Performance regression testing

### 🟡 Phase 4: Documentation (Day 5) - **PENDING**
**Target**: Update documentation and create migration guide

#### Tasks:
- [ ] **P4.1**: Update README and architecture docs
  - `panther/core/docker_builder/README.md`
  - `docs/docker_architecture.md`

- [ ] **P4.2**: Create migration guide
  - `docs/DOCKER_TAG_MIGRATION.md`
  - Document breaking changes and migration path

- [ ] **P4.3**: Update inline code comments
  - Improve code documentation
  - Remove TODO comment on line 986

## Current State Analysis

### Key Files Status
| File | Status | Phase | Description |
|------|--------|-------|-------------|
| `docker_builder.py:986` | 🔴 TODO | P1.1 | Main implementation target |
| `docker_builder.py:593` | 🔴 Needs Update | P1.4 | buildx method update |
| `service_manager_docker_mixin.py:260-273` | 🔴 Split Logic | P2.1 | Remove local tagging |
| `service_manager_docker_mixin.py:354-361` | 🔴 Needs Update | P2.2 | Update build call |

### Architecture Insights
- **Current Problem**: Image naming split between two files
- **BUILD_MODE Flow**: `ivy_build_mode_mixin.py` → `service_manager_docker_mixin.py` → `docker_builder.py` (incomplete)
- **RUNTIME_MODE Issue**: Auto-detected but not included in image names
- **Cache Impact**: Same image name for different runtime modes = cache misses

### Example Tag Evolution
```
Current:  picoquic_v1.0_debug-asan:latest
Enhanced: picoquic_v1.0_debug-asan_debug:latest
          ^impl    ^ver ^build      ^runtime
```

## Next Actions

### Immediate (Phase 1 Start)
1. **Read current implementation**: `docker_builder.py:986-991`
2. **Implement enhanced method**: Add BUILD_MODE/RUNTIME_MODE parameters
3. **Add sanitization helper**: Handle Docker naming requirements
4. **Update build_image()**: Extract modes and call new method
5. **Test incrementally**: Verify each change works

### Risk Mitigation
- **Backup Strategy**: All changes in isolated worktree
- **Incremental Testing**: Test each phase before proceeding
- **Rollback Plan**: Documented reversion steps
- **Cache Strategy**: Plan for existing image invalidation

## Success Criteria Tracking

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

---

**Last Updated**: 2025-07-01
**Next Review**: After Phase 1 completion
