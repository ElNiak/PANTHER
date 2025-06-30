# Implementation Checklist

## Pre-Implementation Setup
- [x] Task analysis and planning completed
- [x] Git worktree created: `feature/docker-builder-build-runtime-mode-enhancement`
- [x] Task documentation committed
- [x] Implementation phases defined
- [x] Acceptance criteria established

## Phase 1: Core Enhancement (Days 1-2)

### 1.1 Enhanced `generate_image_tag()` Method
- [ ] Read current implementation at `docker_builder.py:986-991`
- [ ] Design new method signature with build_mode and runtime_mode parameters
- [ ] Implement tag construction logic
  - [ ] Handle empty build_mode gracefully
  - [ ] Handle minimal runtime_mode (default, no suffix)
  - [ ] Combine all parts correctly
- [ ] Add comprehensive docstring with examples
- [ ] Test basic functionality manually

### 1.2 `_sanitize_docker_tag()` Helper Method
- [ ] Implement Docker naming compliance
  - [ ] Lowercase conversion
  - [ ] Invalid character replacement
  - [ ] Prevent leading periods/dashes
  - [ ] Length limit enforcement (100 chars)
- [ ] Preserve tag version part during truncation
- [ ] Add unit tests for edge cases
- [ ] Document Docker naming rules

### 1.3 Update `build_image()` Method
- [ ] Locate current tag generation at `docker_builder.py:~817`
- [ ] Extract build_mode from config with fallback
- [ ] Extract runtime_mode from config with fallback
- [ ] Replace current tag generation with new method call
- [ ] Add debug logging for mode values
- [ ] Verify image_tag variable is used correctly throughout method

### 1.4 Update `_build_with_buildx()` Method
- [ ] Locate current tag generation at `docker_builder.py:593`
- [ ] Replace with new generate_image_tag() call
- [ ] Ensure config dict contains both modes
- [ ] Test buildx path separately if possible
- [ ] Verify logging consistency

### Phase 1 Validation
- [ ] All Phase 1 changes compile without errors
- [ ] Basic tag generation works for simple cases
- [ ] No obvious regressions in build process
- [ ] Debug logging shows correct mode extraction

## Phase 2: Integration Updates (Day 3)

### 2.1 Simplify `service_manager_docker_mixin.py`
- [ ] Read current implementation at `service_manager_docker_mixin.py:260-273`
- [ ] Remove build_mode_suffix logic
- [ ] Remove local image_name generation
- [ ] Keep clean base_version for docker_builder
- [ ] Update related comments

### 2.2 Update Docker Build Call
- [ ] Locate build call at `service_manager_docker_mixin.py:354-361`
- [ ] Ensure version_dict contains clean version (no mode suffix)
- [ ] Verify build_mode and runtime_mode in config
- [ ] Update to use returned image_tag from build_image()
- [ ] Fix any hardcoded image name references

### 2.3 Update Logging and Error Handling
- [ ] Replace local image_name with returned tag in logging
- [ ] Update error messages to use correct image names
- [ ] Ensure consistent naming throughout the flow
- [ ] Verify emit_docker_build_* calls use correct names

### Phase 2 Validation
- [ ] End-to-end build process works
- [ ] Image names are correctly generated and logged
- [ ] No duplicate tag generation logic remains
- [ ] Service manager integration is clean

## Phase 3: Testing & Validation (Days 4-5)

### 3.1 Unit Tests Creation
- [ ] Create `tests/test_docker_builder_tag_generation.py`
- [ ] Test basic tag generation scenarios
  - [ ] Basic: impl_name + version + tag_version
  - [ ] With build_mode only
  - [ ] With runtime_mode only
  - [ ] With both modes
  - [ ] Minimal runtime_mode omitted
  - [ ] No version case
- [ ] Test tag sanitization
  - [ ] Invalid characters
  - [ ] Case conversion
  - [ ] Length limits
  - [ ] Leading character restrictions
- [ ] Test edge cases and error conditions

### 3.2 Integration Tests Update
- [ ] Update existing `tests/test_service_manager_integration.py`
- [ ] Add test for mode passing from service to docker_builder
- [ ] Verify config dict contents
- [ ] Test image tag return and usage
- [ ] Mock docker_builder.build_image calls appropriately

### 3.3 Backward Compatibility Tests
- [ ] Test existing image resolution still works
- [ ] Create migration test scenarios
- [ ] Verify cache behavior with new tags
- [ ] Test rollback scenarios
- [ ] Document any breaking changes

### 3.4 Performance and Cache Validation
- [ ] Measure build time impact
- [ ] Verify cache differentiation works
  - [ ] Same build_mode, different runtime_mode = different tags
  - [ ] Different build_mode, same runtime_mode = different tags
  - [ ] Identical modes = same tag (cache hit)
- [ ] Test with real Docker builds if possible
- [ ] Validate memory usage impact

### Phase 3 Validation
- [ ] All tests pass (existing + new)
- [ ] Code coverage > 90% for new logic
- [ ] Performance regressions identified and addressed
- [ ] Cache behavior validated

## Phase 4: Documentation (Day 5)

### 4.1 Code Documentation
- [ ] Update `docker_builder.py` method docstrings
- [ ] Add inline comments for complex logic
- [ ] Remove TODO comment from line 986
- [ ] Update class-level documentation

### 4.2 Architecture Documentation
- [ ] Update `panther/core/docker_builder/README.md`
  - [ ] Document new tagging scheme
  - [ ] Explain mode handling
  - [ ] Provide examples
- [ ] Update `docs/docker_architecture.md`
  - [ ] Architecture flow diagrams
  - [ ] Decision rationale

### 4.3 Migration Guide
- [ ] Create `docs/DOCKER_TAG_MIGRATION.md`
- [ ] Document breaking changes
- [ ] Provide migration commands/scripts
- [ ] Include troubleshooting section
- [ ] Add rollback instructions

### Phase 4 Validation
- [ ] Documentation reviewed and accurate
- [ ] Examples work as documented
- [ ] Migration guide tested
- [ ] All changes properly documented

## Final Validation & Cleanup

### Code Quality
- [ ] All linting passes
- [ ] No code duplication
- [ ] Consistent error handling
- [ ] Proper logging throughout

### Testing
- [ ] Full test suite passes
- [ ] Integration tests work end-to-end
- [ ] Performance benchmarks acceptable
- [ ] Cache behavior confirmed

### Documentation
- [ ] All documentation updated
- [ ] Breaking changes documented
- [ ] Migration path clear
- [ ] Examples working

### Git & Release
- [ ] All changes committed with clear messages
- [ ] Branch ready for PR/merge
- [ ] Rollback plan tested
- [ ] Ready for production deployment

## Success Criteria Final Check

### Functional Requirements
- [ ] ✅ All Docker builds generate tags with both BUILD_MODE and RUNTIME_MODE
- [ ] ✅ Cache differentiation works correctly
- [ ] ✅ No performance regression in build times
- [ ] ✅ All existing tests pass

### Quality Requirements
- [ ] ✅ Code coverage > 90% for new tag generation logic
- [ ] ✅ No duplicate image tag generation logic
- [ ] ✅ Proper error handling for invalid mode combinations
- [ ] ✅ Documentation updated and reviewed

---

**Implementation Start**: Ready to begin Phase 1
**Current Focus**: Enhanced `generate_image_tag()` method implementation
