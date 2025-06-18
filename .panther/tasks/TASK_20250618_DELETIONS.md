# Deletions for Task 20250618: Legacy Code Removal

## Phase 1: ConfigLoader Removal

### Entire Files to Delete
```
panther/config/config_loader.py - ENTIRE FILE (1154 lines)
```

### Code Blocks to Remove

**panther/config/config_manager.py**
- [ ] Lines 51-1205: Remove entire ConfigLoader class
- [ ] Lines 132-192: Remove duplicate `add_plugin_tester_service()` method
- [ ] Lines 193-253: Remove duplicate `remove_plugin_tester_service()` method
- [ ] Lines 254-314: Remove duplicate `add_plugin_iut_service()` method
- [ ] Lines 315-343: Remove remaining duplicate plugin methods
- [ ] Lines 732-926: Remove all `get_all_*_classes()` duplicate methods

## Phase 2: Legacy Schema Code

### Files in Legacy Backup (6 files)
```
dev/legacy_backup_20250617/config_schema.py - ENTIRE FILE
dev/legacy_backup_20250617/config_experiment_schema.py - ENTIRE FILE
dev/legacy_backup_20250617/config_global_schema.py - ENTIRE FILE
dev/legacy_backup_20250617/config_observer_schema.py - ENTIRE FILE
dev/legacy_backup_20250617/plugin_config_schema.py - ENTIRE FILE
dev/legacy_backup_20250617/old_config_manager.py - ENTIRE FILE
```

## Phase 3: TODO/FIXME Comment Removal

**panther/config/config_manager.py**
- [ ] Line 280: Remove `# TODO improve this`
- [ ] Line 320: Remove `# TODO improve this`
- [ ] Line 463: Remove `# TODO: Not implemented yet, but could be useful in the future`
- [ ] Line 625: Remove `# TODO: Default to client-server for now`
- [ ] Line 685: Remove `# TODO cleanup`

**panther/plugins/environments/network_environment/shadow_ns/config_schema.py**
- [ ] Line 83: Remove `# TODO: Add support for multiple network nodes`

**panther/plugins/services/testers/panther_ivy/config_schema.py**
- [ ] Line 22: Remove `# TODO`
- [ ] Line 28: Remove `# TODO`
- [ ] Line 96: Remove `# TODO redirect directly to the network environment shared volume`

## Phase 4: Commented-Out Code

### Search and Remove Pattern
```bash
# Find all commented-out code blocks
grep -n "^#.*def\|^#.*class\|^#.*import" panther/**/*.py
```

**Common patterns to remove**:
- [ ] Commented function definitions: `# def old_method():`
- [ ] Commented class definitions: `# class OldClass:`
- [ ] Commented imports: `# from old_module import deprecated`
- [ ] Block comments with old code:
  ```python
  # OLD CODE - REMOVE
  # def deprecated_function():
  #     pass
  ```

## Phase 5: Unused Imports

### Automated Detection
```bash
# Use flake8 to find unused imports
flake8 panther/ --select=F401 | grep "imported but unused"
```

**Known unused imports to remove**:
- [ ] `from typing import Any` (where replaced with specific types)
- [ ] `from old_config import ConfigLoader` (after migration)
- [ ] Legacy utility imports no longer needed

## Phase 6: Dead Code Patterns

### Static Version Loading
**panther/plugins/services/iut/quic/picoquic/config_schema.py**
- [ ] Lines 66-84: Remove static `load_available_versions()` method

### Empty Methods
```python
# Remove methods like:
def placeholder_method(self):
    """TODO: Implement this."""
    pass
```

### Deprecated Decorators
```python
# Remove uses of:
@deprecated("Use new_method instead")
def old_method(self):
    pass
```

## Phase 7: Old Development Files

### Development Directory Cleanup
```
dev/old/ - ENTIRE DIRECTORY
dev/legacy_backup_*/ - ALL BACKUP DIRECTORIES
dev/deprecated/ - ENTIRE DIRECTORY
```

### Temporary Files
```
*.generated.py - ALL GENERATED FILES
*.backup - ALL BACKUP FILES
*.old - ALL OLD FILES
```

## Phase 8: Test File Cleanup

### Obsolete Test Files
```
tests/unit/test_old_config.py - ENTIRE FILE
tests/unit/test_config_loader.py - ENTIRE FILE
tests/integration/test_deprecated_features.py - ENTIRE FILE
```

### Test Code Blocks
- [ ] Remove tests for deleted methods
- [ ] Remove commented-out test cases
- [ ] Remove skip decorators for fixed issues

## Summary of Deletions

| Category | Files | Lines | Impact |
|----------|-------|--------|---------|
| ConfigLoader | 1 | 1154 | Major |
| Duplicate Methods | 1 | 350+ | Major |
| Legacy Backups | 6 | ~2000 | Cleanup |
| TODO Comments | 5 | 9 | Minor |
| Commented Code | Many | ~500 | Cleanup |
| Dead Code | Various | ~300 | Cleanup |
| Test Files | 3 | ~600 | Cleanup |

**Total Lines to Delete**: ~4,900+
**Total Files to Delete**: 10+ complete files
**Net Code Reduction**: ~60%

## Deletion Verification Checklist

After each deletion:
1. [ ] Run unit tests to ensure nothing breaks
2. [ ] Check for import errors
3. [ ] Verify no references remain to deleted code
4. [ ] Update documentation if needed
5. [ ] Commit with clear message about what was removed