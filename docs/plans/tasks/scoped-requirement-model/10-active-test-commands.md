# Task 10: Active Test Selector + Compile Commands

**Status:** pending
**Depends on:** Task 5, Task 6

**Files:**
- Modify: `ivy_lsp/features/commands.py`
- Create: `tests/test_active_test_command.py`

**New commands** following existing patterns in `commands.py:177-259`:
- `ivy/setActiveTest` -- select which test's scope to use for diagnostics/lenses
- `ivy/listTests` -- list all discovered test scopes with roles
- `ivy/compileTest` -- compile a specific test via `ivyc target=test`

**Reuse patterns from existing code:**
- `_run_tool` (line 96-174): async subprocess with progress reporting
- `_resolve_via_staging` (line 39-58): staging directory for include resolution
- `ivy/verify`, `ivy/compile` (line 177-259): existing command registration patterns

---

## Step 1: Write the failing test

```python
# tests/test_active_test_command.py
"""Tests for ivy/setActiveTest, ivy/listTests, ivy/compileTest commands."""
import pytest
from unittest.mock import MagicMock, AsyncMock
from ivy_lsp.analysis.test_scope import ScopedRequirementModel, TestScope


class TestSetActiveTestModel:
    """Test the model-level API (already tested in Task 5, verify here too)."""

    def test_set_and_get_active_test(self):
        model = ScopedRequirementModel()
        scope = TestScope(
            test_file="/test/a.ivy",
            include_closure=frozenset({"/test/a.ivy"}),
            exported_actions=frozenset({"quic.send"}),
            imported_actions=frozenset(),
            tester_role="client",
        )
        model.register_test_scope(scope)
        model.set_active_test("/test/a.ivy")
        assert model.get_active_scope().test_file == "/test/a.ivy"


class TestListTestsModel:
    def test_list_all_scopes(self):
        model = ScopedRequirementModel()
        scope_a = TestScope(
            test_file="/test/a.ivy",
            include_closure=frozenset({"/test/a.ivy"}),
            exported_actions=frozenset({"quic.send"}),
            imported_actions=frozenset(),
            tester_role="client",
        )
        scope_b = TestScope(
            test_file="/test/b.ivy",
            include_closure=frozenset({"/test/b.ivy"}),
            exported_actions=frozenset({"quic.recv"}),
            imported_actions=frozenset(),
            tester_role="server",
        )
        model.register_test_scope(scope_a)
        model.register_test_scope(scope_b)
        scopes = model._test_scopes
        assert len(scopes) == 2
        assert "/test/a.ivy" in scopes
        assert scopes["/test/a.ivy"].tester_role == "client"
```

## Step 2: Run test to verify it fails/passes

```bash
python -m pytest tests/test_active_test_command.py -v
```

Expected: These model-level tests should PASS (model already implemented in Task 5).

## Step 3: Add command handlers to `commands.py`

In `ivy_lsp/features/commands.py`, inside the `register()` function, add after existing command registrations:

```python
@server.command("ivy/setActiveTest")
async def set_active_test(params):
    """Set the active test for scoped diagnostics and code lenses."""
    test_file = params.get("testFile")
    graph = indexer._requirement_graph
    if isinstance(graph, ScopedRequirementModel):
        graph.set_active_test(test_file)
        # Trigger refresh of all open documents
        return {"success": True, "activeTest": test_file}
    return {"success": False, "error": "Scoped model not available"}


@server.command("ivy/listTests")
async def list_tests(params):
    """List all discovered test scopes."""
    graph = indexer._requirement_graph
    if not isinstance(graph, ScopedRequirementModel):
        return {"tests": []}
    tests = []
    for test_file, scope in graph._test_scopes.items():
        tests.append({
            "testFile": test_file,
            "testerRole": scope.tester_role,
            "exportCount": len(scope.exported_actions),
            "importCount": len(scope.imported_actions),
            "includeCount": len(scope.include_closure),
        })
    return {"tests": tests}


@server.command("ivy/compileTest")
async def compile_test(params):
    """Compile a specific test file with ivyc target=test."""
    test_file = params.get("testFile")
    if not test_file:
        return {"success": False, "error": "No testFile specified"}

    staging_dir = _resolve_via_staging(test_file, indexer)
    cmd = ["ivyc", "target=test", os.path.basename(test_file)]
    result = await _run_tool(
        cmd, staging_dir, server, f"Compiling {os.path.basename(test_file)}"
    )

    # Store compilation result
    graph = indexer._requirement_graph
    if isinstance(graph, ScopedRequirementModel):
        graph._compilation_results[test_file] = result

    return result
```

**Note:** The exact command handler signature depends on the LSP framework being used. Check existing `ivy/verify` and `ivy/compile` registrations for the exact pattern.

## Step 4: Run tests

```bash
python -m pytest tests/test_active_test_command.py -v
```

Expected: PASS

## Step 5: Commit

```bash
git add ivy_lsp/features/commands.py tests/test_active_test_command.py
git commit -m "feat(commands): add ivy/setActiveTest, ivy/listTests, ivy/compileTest"
```
