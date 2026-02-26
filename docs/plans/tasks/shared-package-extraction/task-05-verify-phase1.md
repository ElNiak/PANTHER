# Task 05: Verify Phase 1 - panther-ivy-types

## Goal
Install panther-ivy-types and verify all imports, re-exports, and tests work correctly.

## Prerequisites
- Tasks 01-04 completed

## Steps

### Step 1: Install panther-ivy-types in editable mode
```bash
source .venv/bin/activate
pip install -e packages/panther-ivy-types/
```

### Step 2: Run panther-ivy-types tests
```bash
cd packages/panther-ivy-types
pytest tests/ -v
```

All tests from tasks 02-03 should pass.

### Step 3: Verify re-export shims

```bash
# Test panther_ivy re-exports
python -c "
from panther_ivy.api.types import CommandResult, CompileResult, TestRunResult
from panther_ivy.api.types import DiagnosticItem, TestInfo, ExecutionResult
print('DiagnosticItem module:', DiagnosticItem.__module__)
assert DiagnosticItem.__module__ == 'panther_ivy_types.api', f'Expected panther_ivy_types.api, got {DiagnosticItem.__module__}'
print('panther_ivy re-exports: OK')
"

# Test direct panther_ivy_types imports
python -c "
from panther_ivy_types import RequirementNode, StateVarNode, ExportImportInfo, TestScope
print('Direct imports: OK')
"

# Test that RequirementGraph still works (imports RequirementNode from new location)
python -c "
from ivy_lsp.analysis.requirement_graph import RequirementGraph, RequirementNode
print('RequirementNode module:', RequirementNode.__module__)
print('RequirementGraph import: OK')
"
```

### Step 4: Run existing test suites

```bash
# Run panther_ivy API tests if they exist
pytest panther/plugins/services/testers/panther_ivy/tests/ -v 2>/dev/null || echo "No panther_ivy tests found"

# Run ivy-lsp tests
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
pytest tests/ -v 2>/dev/null || echo "No ivy-lsp tests found or not runnable from this context"
cd -

# Run panther unit tests (should have no regressions)
pytest tests/ -n auto -m unit --timeout=60 2>/dev/null || echo "Panther unit tests - check for regressions"
```

### Step 5: Verify type identity

```bash
# Ensure the types are the SAME objects regardless of import path
python -c "
from panther_ivy.api.types import DiagnosticItem as D1
from panther_ivy_types.api import DiagnosticItem as D2
assert D1 is D2, 'Type identity mismatch!'
print('Type identity: OK')
"
```

### Step 6: Update dependency declarations

After verifying everything works, add `panther-ivy-types` as a dependency in the consuming packages:

- **panther pyproject.toml**: Add `panther-ivy-types>=0.1.0` to dependencies
- **panther_ivy setup.py/pyproject.toml**: Add `panther-ivy-types>=0.1.0` to dependencies
- **ivy-lsp**: Add `panther-ivy-types>=0.1.0` to its dependencies (if it has a pyproject.toml or setup.py)

For development, editable installs (`pip install -e`) handle this automatically, but production installs need explicit dependency declarations.

## Success Criteria
1. `pip install -e packages/panther-ivy-types/` succeeds
2. All panther-ivy-types tests pass
3. Re-export shims work (old import paths still resolve)
4. Type identity is preserved (same object via both import paths)
5. No regressions in existing test suites
6. Dependency declarations updated in consuming packages

## Troubleshooting

### "ModuleNotFoundError: No module named 'panther_ivy_types'"
- Ensure `pip install -e packages/panther-ivy-types/` was run
- Ensure the virtual environment is activated

### Test failures in ivy-lsp
- Check that the dataclass field names exactly match the originals
- Check that `frozen=True` is preserved on TestScope
- Check that default_factory values match (e.g., `field(default_factory=set)` vs `field(default_factory=frozenset)`)

### Import errors in requirement_graph.py
- The import of RequirementGraph must still come from `ivy_lsp.analysis.requirement_graph`
- Only RequirementNode and StateVarNode come from `panther_ivy_types`

## Commit Message
```
test: verify Phase 1 panther-ivy-types extraction
```

## Files Modified
- None (verification only)
