# Remove Backward Compatibility Shims Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove all backward compatibility re-exports, legacy format fallbacks, conversion functions, and dead compat aliases from the ivy-lsp codebase.

**Architecture:** Each task removes one category of compat shims. Tasks are independent — each can be committed and tested separately. Import rewrites use `replace_all` edits. Dead code gets deleted outright.

**Tech Stack:** Python 3.10, pytest

**Working directory for all commands:**
```
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
```

---

## File Map

| File | Action | Category |
|------|--------|----------|
| `ivy_lsp/core/semantic/nodes.py:13-19` | Remove dead re-exports | Dead code |
| `ivy_lsp/core/semantic/edges.py:11-12` | Remove dead re-export | Dead code |
| `tests/test_semantic_nodes.py:5` | Update 1 import | Dead code |
| `ivy_lsp/infra/utils/ivy_output.py:60,330` | Remove alias + update usage | Dead alias |
| `ivy_lsp/mcp/tools/analysis.py:258-261` | Remove legacy flat keys | Legacy format |
| `ivy_lsp/mcp/tools/formatters/visualization.py:87-92` | Remove fallback branch | Legacy format |
| `ivy_lsp/core/analysis/mirror.py:83-110` | Remove conversion methods | Legacy compat |
| `ivy_lsp/core/indexer/scope_manager.py:336` | Replace `from_test_scope` call | Legacy compat |
| `ivy_lsp/mcp/server.py:32-39` | Remove re-exports | Re-export |
| `ivy_lsp/mcp/sidecar.py:130` | Update import | Re-export |
| `ivy_lsp/mcp/tools/__init__.py:593` | Update import | Re-export |
| `ivy_lsp/lsp/diagnostics/publisher.py:22-32` | Remove re-exports | Re-export |
| `ivy_lsp/lsp/commands.py` (3 sites) | Update imports | Re-export |
| `tests/test_task_3_2_diagnostics.py` (11 sites) | Update imports | Re-export |
| `tests/test_full_integration.py:27` | Update import | Re-export |
| `tests/test_semantic_diagnostics.py:7,103` | Update imports | Re-export |
| `tests/test_scoped_diagnostics.py:23` | Update import | Re-export |
| `tests/test_task_3_4_integration.py` (3 sites) | Update imports | Re-export |
| `tests/test_coverage_diagnostics.py:144` | Update import | Re-export |

---

### Task 1: Remove dead re-exports from `semantic/nodes.py` and `semantic/edges.py`

**Files:**
- Modify: `ivy_lsp/core/semantic/nodes.py:13-19`
- Modify: `ivy_lsp/core/semantic/edges.py:11-12`
- Modify: `tests/test_semantic_nodes.py:5`

These re-exports have **zero downstream consumers** (verified by grep). `ActionNode`, `PropertyNode`, `RequirementNode`, `StateVarNode` are never imported via `semantic.nodes`. `EdgeType` is only imported in one test.

- [ ] **Step 1: Remove the re-export block from `nodes.py`**

Delete lines 13-19 (the `from ivy_lsp.core.analysis.requirement_graph import ...` block and its comment).

- [ ] **Step 2: Remove the re-export line from `edges.py`**

Delete lines 11-12 (the `from ivy_lsp.core.analysis.requirement_graph import EdgeType` and its comment).

- [ ] **Step 3: Update `test_semantic_nodes.py` import**

Change line 5 from:
```python
from ivy_lsp.core.semantic.edges import EdgeType, SemanticEdgeType
```
To:
```python
from ivy_lsp.core.analysis.requirement_graph import EdgeType
from ivy_lsp.core.semantic.edges import SemanticEdgeType
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_semantic_nodes.py tests/test_semantic_model.py -v`
Expected: All pass

- [ ] **Step 5: Commit**

```bash
git add ivy_lsp/core/semantic/nodes.py ivy_lsp/core/semantic/edges.py tests/test_semantic_nodes.py
git commit -m "refactor: remove dead re-exports from semantic/nodes.py and edges.py"
```

---

### Task 2: Remove `_DEFAULT_EXCLUDE_DIRS` alias

**Files:**
- Modify: `ivy_lsp/infra/utils/ivy_output.py:60,330`

- [ ] **Step 1: Replace usage of alias with canonical name**

In `ivy_output.py`, line 330, change:
```python
        exclude_dirs = _DEFAULT_EXCLUDE_DIRS
```
To:
```python
        exclude_dirs = DEFAULT_EXCLUDE_DIRS
```

- [ ] **Step 2: Delete the alias definition**

Delete line 60:
```python
_DEFAULT_EXCLUDE_DIRS = DEFAULT_EXCLUDE_DIRS  # back-compat alias
```

- [ ] **Step 3: Run tests**

Run: `python -m pytest tests/ -x -q --timeout=30 -k "ivy_output or exclude" 2>&1 | tail -5`
Expected: Pass (or no matching tests — the alias was internal)

- [ ] **Step 4: Commit**

```bash
git add ivy_lsp/infra/utils/ivy_output.py
git commit -m "refactor: remove _DEFAULT_EXCLUDE_DIRS backward compat alias"
```

---

### Task 3: Remove legacy flat keys from `analysis.py` capabilities response

**Files:**
- Modify: `ivy_lsp/mcp/tools/analysis.py:258-261`

- [ ] **Step 1: Remove the legacy flat key lines**

Delete lines 258-261 (the comment and 3 duplicate key lines):
```python
            # Also report legacy flat keys for backward compat
            "ivy_check": shutil.which("ivy_check") is not None,
            "ivyc": shutil.which("ivyc") is not None,
            "ivy_show": shutil.which("ivy_show") is not None,
```

- [ ] **Step 2: Remove the fallback branch from `visualization.py` formatter**

In `ivy_lsp/mcp/tools/formatters/visualization.py`, lines 87-92, remove the `else` branch that falls back to legacy flat keys. The `if cli_tools:` branch becomes the only path.

- [ ] **Step 3: Run tests**

Run: `python -m pytest tests/ -x -q --timeout=30 -k "capabilities or visualization" 2>&1 | tail -5`
Expected: Pass

- [ ] **Step 4: Commit**

```bash
git add ivy_lsp/mcp/tools/analysis.py ivy_lsp/mcp/tools/formatters/visualization.py
git commit -m "refactor: remove legacy flat keys from capabilities response"
```

---

### Task 4: Remove `to_test_scope()` / `from_test_scope()` conversion methods

**Files:**
- Modify: `ivy_lsp/core/analysis/mirror.py:83-110`
- Modify: `ivy_lsp/core/indexer/scope_manager.py:336`

The only caller of `from_test_scope()` is `scope_manager.py:336`. Replace with direct `Mirror` construction.

- [ ] **Step 1: Read `from_test_scope()` to understand the conversion**

Read `ivy_lsp/core/analysis/mirror.py:83-110` to understand what `from_test_scope()` does, so we can inline it at the call site.

- [ ] **Step 2: Replace `from_test_scope()` call in `scope_manager.py`**

In `scope_manager.py` line 336, replace:
```python
            mirror = Mirror.from_test_scope(scope, protocol="unknown")
```
With the direct `Mirror` construction (inline whatever `from_test_scope` does).

- [ ] **Step 3: Remove both conversion methods from `mirror.py`**

Delete `to_test_scope()` (lines 83-95) and `from_test_scope()` (lines 96-110). Also update the class docstring to remove the reference to these methods.

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/ -x -q --timeout=30 -k "mirror or scope" 2>&1 | tail -5`
Expected: Pass

- [ ] **Step 5: Commit**

```bash
git add ivy_lsp/core/analysis/mirror.py ivy_lsp/core/indexer/scope_manager.py
git commit -m "refactor: remove to_test_scope/from_test_scope backward compat conversions"
```

---

### Task 5: Remove `mcp/server.py` re-exports

**Files:**
- Modify: `ivy_lsp/mcp/server.py:32-39`
- Modify: `ivy_lsp/mcp/sidecar.py:130`
- Modify: `ivy_lsp/mcp/tools/__init__.py:593`

Only 2 downstream files import `ToolContext` from `mcp.server` instead of `mcp.context`.

- [ ] **Step 1: Update `sidecar.py` import**

In `sidecar.py` line 130, change:
```python
    from ivy_lsp.mcp.server import ToolContext, create_mcp_app
```
To:
```python
    from ivy_lsp.mcp.context import ToolContext
    from ivy_lsp.mcp.server import create_mcp_app
```

- [ ] **Step 2: Update `tools/__init__.py` import**

In `tools/__init__.py` line 593, change:
```python
    from ivy_lsp.mcp.server import ToolContext
```
To:
```python
    from ivy_lsp.mcp.context import ToolContext
```

- [ ] **Step 3: Remove the re-export block from `server.py`**

Delete lines 32-39 (the comment and `from ivy_lsp.mcp.context import ...` re-export).

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/ -x -q --timeout=30 -k "mcp" 2>&1 | tail -5`
Expected: Pass

- [ ] **Step 5: Commit**

```bash
git add ivy_lsp/mcp/server.py ivy_lsp/mcp/sidecar.py ivy_lsp/mcp/tools/__init__.py
git commit -m "refactor: remove ToolContext re-export from mcp/server.py"
```

---

### Task 6: Remove `diagnostics/publisher.py` re-exports

**Files:**
- Modify: `ivy_lsp/lsp/diagnostics/publisher.py:22-32`
- Modify: `ivy_lsp/lsp/commands.py` (3 import sites)
- Modify: 7 test files (~20 import sites total)

This is the largest rewrite — all `from ivy_lsp.lsp.diagnostics.publisher import compute_*` must become `from ivy_lsp.lsp.diagnostics.compute import compute_*`.

- [ ] **Step 1: Delete the re-export block from `publisher.py`**

Delete lines 22-32:
```python
# Re-export compute functions so that ...
from ivy_lsp.lsp.diagnostics.compute import (  # noqa: F401
    _EXPORT_RE,
    check_structural_issues,
    compute_diagnostics,
    compute_requirement_diagnostics,
    compute_semantic_diagnostics,
    parse_ivy_check_output,
    run_deep_diagnostics,
)
```

- [ ] **Step 2: Update `commands.py` (3 sites)**

Replace all occurrences of:
```python
from ivy_lsp.lsp.diagnostics.publisher import compute_diagnostics
```
With:
```python
from ivy_lsp.lsp.diagnostics.compute import compute_diagnostics
```

- [ ] **Step 3: Update test files**

Apply the same import rewrite in all test files. Use `replace_all` for each file:
- `tests/test_task_3_2_diagnostics.py` — replace `from ivy_lsp.lsp.diagnostics.publisher import compute_diagnostics` with `from ivy_lsp.lsp.diagnostics.compute import compute_diagnostics`
- `tests/test_full_integration.py` — replace `from ivy_lsp.lsp.diagnostics.publisher import compute_semantic_diagnostics` with `from ivy_lsp.lsp.diagnostics.compute import compute_semantic_diagnostics`
- `tests/test_semantic_diagnostics.py` — replace both `publisher` imports with `compute` imports
- `tests/test_scoped_diagnostics.py` — replace `from ivy_lsp.lsp.diagnostics.publisher import compute_requirement_diagnostics` with `from ivy_lsp.lsp.diagnostics.compute import compute_requirement_diagnostics`
- `tests/test_task_3_4_integration.py` — replace all `publisher` imports with `compute` imports
- `tests/test_coverage_diagnostics.py` — replace `publisher` import with `compute` import

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_task_3_2_diagnostics.py tests/test_full_integration.py tests/test_semantic_diagnostics.py tests/test_scoped_diagnostics.py tests/test_task_3_4_integration.py tests/test_coverage_diagnostics.py -v 2>&1 | tail -10`
Expected: All pass

- [ ] **Step 5: Run full test suite for regression**

Run: `python -m pytest tests/ -x -q --timeout=30 2>&1 | tail -5`
Expected: All pass

- [ ] **Step 6: Commit**

```bash
git add ivy_lsp/lsp/diagnostics/publisher.py ivy_lsp/lsp/commands.py tests/test_task_3_2_diagnostics.py tests/test_full_integration.py tests/test_semantic_diagnostics.py tests/test_scoped_diagnostics.py tests/test_task_3_4_integration.py tests/test_coverage_diagnostics.py
git commit -m "refactor: remove compute function re-exports from diagnostics/publisher.py"
```

---

### Task 7: Final verification

- [ ] **Step 1: Grep for remaining backward compat markers**

```bash
grep -rn "backward.compat\|back-compat\|Re-export.*backward" ivy_lsp/ --include="*.py" | grep -v "__pycache__"
```

Expected: Only the `--mcp` mode comment in `__main__.py` and the `workspace/detection.py` fallback remain (these are deferred — need deeper analysis).

- [ ] **Step 2: Run full test suite**

```bash
python -m pytest tests/ -x -q --timeout=30 2>&1 | tail -5
```

Expected: All pass

- [ ] **Step 3: Verify no import errors**

```bash
python -c "from ivy_lsp.core.semantic.nodes import SymbolNode; print('nodes OK')"
python -c "from ivy_lsp.core.semantic.edges import SemanticEdgeType; print('edges OK')"
python -c "from ivy_lsp.lsp.diagnostics.publisher import publish_diagnostics; print('publisher OK')"
python -c "from ivy_lsp.mcp.context import ToolContext; print('context OK')"
```

Expected: All OK

---

## Deferred (needs deeper analysis)

These are **not included** in this plan:

| Item | Reason |
|---|---|
| `--mcp` CLI flag in `__main__.py` | Need to verify no external callers (start-ivy-server.sh uses it) |
| `workspace/detection.py` hardcoded protocol fallback | Need to verify all workspaces have `.ivyworkspace` markers |
| `workspace/detection.py` flatten layer paths | Need to verify `_find_source_files` accepts layer structure |
| `hasattr` guards for private attributes | Need per-case analysis of whether attributes are guaranteed |
