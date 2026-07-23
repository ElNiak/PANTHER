# ivy-lsp Internal Refactoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Clean up the ivy-lsp submodule (~40K lines) by removing dead code, consolidating duplicated symbol resolution logic, splitting oversized files, and reorganizing root-level workspace modules into a proper package.

**Architecture:** Internal refactoring only — no cross-submodule changes, public API (`server.py`, `mcp_server.py`, `tools/`) stays stable. No backward-compat shims; all imports updated directly.

**Tech Stack:** Python 3.10+, pygls (LSP), pytest, flake8

**Base path:** `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/`

**Spec:** See `/Users/elniak/.claude/plans/squishy-gathering-robin.md` for design rationale and review feedback.

---

## Batch A: Dead Code + Workspace Package

---

### Task 1: Remove dead module `indexer/shared_cache.py`

**Files:**
- Delete: `ivy_lsp/indexer/shared_cache.py`

- [ ] **Step 1: Verify baseline tests pass**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/ -x -q --tb=short 2>&1 | tail -5`
Expected: All tests pass

- [ ] **Step 2: Confirm zero imports of shared_cache**

Run: `grep -r "shared_cache" ivy_lsp/ tests/ --include="*.py" | grep -v __pycache__`
Expected: Zero results (note: `bulk_orchestrator._write_shared_cache` is a method name, not an import)

- [ ] **Step 3: Delete the file**

```bash
rm ivy_lsp/indexer/shared_cache.py
```

- [ ] **Step 4: Run tests to verify no breakage**

Run: `python -m pytest tests/ -x -q --tb=short 2>&1 | tail -5`
Expected: All tests pass

- [ ] **Step 5: Commit**

```bash
git add -A ivy_lsp/indexer/shared_cache.py
git commit -m "$(cat <<'EOF'
refactor: remove dead indexer/shared_cache.py module

Zero imports anywhere in the codebase. The model-write logic in
bulk_orchestrator.py and mcp_server.py superseded this approach.
EOF
)"
```

---

### Task 2: Remove dead Protocol interfaces and functions/methods

**Files:**
- Modify: `ivy_lsp/protocols.py` — delete `IIndexer` (lines 84-122) and `IRequirementGraph` (lines 124-131)
- Modify: `ivy_lsp/tools/__init__.py` — delete `_timeout_response` (lines 189-196) and its `_injected_names` entry (line 470) and comment reference (line 462)
- Modify: `ivy_lsp/semantic/analysis_pipeline.py` — delete `build_model_from_files` static method
- Modify: `ivy_lsp/observability/handlers.py` — delete `ToolTraceContext.finish_error` method, delete `_LspLogHandler` alias
- Modify: `ivy_lsp/observability/session.py` — delete `SessionEventLogger.log_dir` and `.drop_count` properties
- Modify: `ivy_lsp/observability/core.py` — delete `IvyLogAdapter` alias
- Modify: `ivy_lsp/observability/__init__.py` — remove `_LspLogHandler` and `IvyLogAdapter` from exports/`__all__`
- Modify: `ivy_lsp/parsing/symbols.py` — delete `IncludeGraph.get_transitive_included_by` method
- Modify: `ivy_lsp/indexer/include_resolver.py` — delete `IncludeResolver.get_files_in_partition` method
- Modify: `ivy_lsp/features/hover.py` — delete `_sort_by_proximity` function (lines 182-207)
- Modify: `ivy_lsp/mcp_server.py` — remove `shared_ivy_compile` and `shared_ivy_show` re-exports

- [ ] **Step 1: Remove `IIndexer` and `IRequirementGraph` from `protocols.py`**

Delete lines 84-131 (everything after `IvyServerProtocol`). Also remove unused TYPE_CHECKING imports (`EdgeType`, `RequirementGraph`, `IncludeResolver`, `IncludeGraph`, `IvySymbol`) that are only used by the deleted protocols. Keep imports used by `IvyServerProtocol`.

- [ ] **Step 2: Remove `_timeout_response` from `tools/__init__.py`**

Delete the function (lines 189-196). Delete its entry `"_timeout_response": _timeout_response,` from the `_injected_names` dict (line 470). Update the comment at lines 458-466 to remove the `_timeout_response` reference.

- [ ] **Step 3: Remove dead methods from `semantic/analysis_pipeline.py`**

Delete the `build_model_from_files` `@staticmethod` method. Grep first to confirm zero callers: `grep -r "build_model_from_files" ivy_lsp/ tests/`

- [ ] **Step 4: Remove dead observability code**

In `observability/handlers.py`:
- Delete `ToolTraceContext.finish_error` method
- Delete `_LspLogHandler = LspLogHandler` alias

In `observability/session.py`:
- Delete `SessionEventLogger.log_dir` property
- Delete `SessionEventLogger.drop_count` property

In `observability/core.py`:
- Delete `IvyLogAdapter = StructuredLogAdapter` alias

In `observability/__init__.py`:
- Remove `_LspLogHandler` and `IvyLogAdapter` from `__all__` and any re-export lines

- [ ] **Step 5: Remove dead parsing/indexer methods**

In `parsing/symbols.py`: Delete `IncludeGraph.get_transitive_included_by` method.
In `indexer/include_resolver.py`: Delete `IncludeResolver.get_files_in_partition` method.

- [ ] **Step 6: Remove `_sort_by_proximity` from `features/hover.py`**

Delete lines 182-207. Verify it has no callers in production code (only test imports). Update any test files that import it.

- [ ] **Step 7: Remove dead re-exports from `mcp_server.py`**

Remove `shared_ivy_compile` and `shared_ivy_show` import lines (lines 29-30). Keep `shared_ivy_check` (has `noqa: F401` — intentional re-export used by tests).

- [ ] **Step 8: Run tests**

Run: `python -m pytest tests/ -x -q --tb=short 2>&1 | tail -5`
Expected: All tests pass

- [ ] **Step 9: Commit**

```bash
git add -u
git commit -m "$(cat <<'EOF'
refactor: remove dead code across ivy-lsp

Remove unused Protocol interfaces (IIndexer, IRequirementGraph),
dead functions (_timeout_response, build_model_from_files,
_sort_by_proximity, finish_error), dead properties, dead aliases,
and dead re-exports. ~170 lines of verified dead code.
EOF
)"
```

---

### Task 3: Remove unused imports and aliases

**Files:**
- Modify: `ivy_lsp/features/visualization.py` — remove `PatternKind` import
- Modify: `ivy_lsp/utils/counterexample_formatter.py` — remove `Optional` import

- [ ] **Step 1: Remove unused imports**

In `features/visualization.py`: Remove `PatternKind` from the import inside `handle_coverage_gaps()`.
In `utils/counterexample_formatter.py`: Remove `Optional` from the typing import.

- [ ] **Step 2: Run tests and commit**

Run: `python -m pytest tests/ -x -q --tb=short 2>&1 | tail -5`

```bash
git add -u
git commit -m "refactor: remove unused imports (PatternKind, Optional)"
```

---

### Task 4: Remove unused test fixtures and helpers

**Files:**
- Modify: `tests/conftest.py` — remove ~15 unused fixtures
- Modify: `tests/helpers/lsp_helpers.py` — remove unused helpers
- Modify: `tests/helpers/mcp_helpers.py` — remove unused helpers

- [ ] **Step 1: Identify unused conftest fixtures**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp`

For each fixture in `tests/conftest.py`, check if any test file uses it:
```bash
for fixture in ivy_source_minimal ivy_source_object ivy_source_complex ivy_source_syntax_error ivy_source_module ivy_source_include ivy_source_isolate ivy_source_property ivy_source_instance ivy_source_enum ivy_source_variant quic_frame_path quic_frame_source multi_file_workspace syntax_error_workspace large_workspace_source ivy_source_test_file ivy_source_untagged_assertion; do
  count=$(grep -r "$fixture" tests/ --include="*.py" | grep -v "def $fixture" | grep -v conftest.py | wc -l)
  echo "$fixture: $count references"
done
```

Only remove fixtures with 0 references.

- [ ] **Step 2: Remove unused fixtures from conftest.py**

Delete fixture functions with zero external references. Keep fixtures that ARE used by tests.

- [ ] **Step 3: Identify and remove unused test helpers**

Check `tests/helpers/lsp_helpers.py` functions: `create_indexed_workspace`, `parse_to_symbols`, `get_fixture_path`.
Check `tests/helpers/mcp_helpers.py` functions: `get_mcp_app`, `extract_json`.

For each, grep for usage: `grep -r "function_name" tests/ --include="*.py" | grep -v "def function_name"`

Remove functions with zero callers.

- [ ] **Step 4: Run tests and commit**

Run: `python -m pytest tests/ -x -q --tb=short 2>&1 | tail -5`

```bash
git add -u
git commit -m "$(cat <<'EOF'
refactor: remove unused test fixtures and helpers

Remove conftest fixtures and test helper functions that have zero
references in any test file.
EOF
)"
```

---

### Task 5: Extract workspace modules into `workspace/` package (ATOMIC)

**CRITICAL**: This entire task must be a single atomic commit. Do NOT commit intermediate states where old files and new package coexist — `observability/core.py` `enable_package_instrumentation` would double-load modules.

**Files:**
- Create: `ivy_lsp/workspace/__init__.py`
- Move: `ivy_lsp/active_workspace.py` → `ivy_lsp/workspace/active_workspace.py`
- Move: `ivy_lsp/workspace_context.py` → `ivy_lsp/workspace/context.py`
- Move: `ivy_lsp/workspace_detection.py` → `ivy_lsp/workspace/detection.py`
- Move: `ivy_lsp/session_overlay.py` → `ivy_lsp/workspace/session_overlay.py`
- Delete: old root-level files (after move)
- Modify (source imports, 7 files):
  - `ivy_lsp/mcp_server.py`
  - `ivy_lsp/indexer/include_resolver.py`
  - `ivy_lsp/__main__.py`
  - `ivy_lsp/server_setup.py`
  - `ivy_lsp/tools/workspace.py`
  - `ivy_lsp/tools/analysis.py`
  - `ivy_lsp/index_builder.py`
- Modify (test imports, 13 files):
  - `tests/test_workspace_detection.py`
  - `tests/test_active_workspace.py`
  - `tests/test_workspace_context.py`
  - `tests/test_workspace_context_active.py`
  - `tests/test_scope_views.py`
  - `tests/test_session_overlay.py`
  - `tests/test_index_builder.py`
  - `tests/test_index_integration.py`
  - `tests/test_cross_layer_deps.py`
  - `tests/test_task_2_1_include_resolver.py`
  - `tests/test_task_2_5_references.py`
  - `tests/test_active_workspace_resolver.py`
  - `tests/test_workspace_symbols_filtering.py`

- [ ] **Step 1: Create `workspace/` package directory and `__init__.py`**

```bash
mkdir -p ivy_lsp/workspace
```

Create `ivy_lsp/workspace/__init__.py`:
```python
"""Workspace management: detection, context, overlays, and active workspace scoping."""

from ivy_lsp.workspace.active_workspace import ActiveWorkspace
from ivy_lsp.workspace.context import ProtocolIndex, StalenessInfo, WorkspaceContext
from ivy_lsp.workspace.detection import (
    WorkspaceConfig,
    WorkspaceLayer,
    detect_ivy_workspace,
)
from ivy_lsp.workspace.session_overlay import OverlayEntry, SessionOverlay, TestScopeView

__all__ = [
    "ActiveWorkspace",
    "WorkspaceContext",
    "ProtocolIndex",
    "StalenessInfo",
    "WorkspaceConfig",
    "WorkspaceLayer",
    "detect_ivy_workspace",
    "SessionOverlay",
    "TestScopeView",
    "OverlayEntry",
]
```

- [ ] **Step 2: Move files to new locations**

```bash
cp ivy_lsp/active_workspace.py ivy_lsp/workspace/active_workspace.py
cp ivy_lsp/workspace_context.py ivy_lsp/workspace/context.py
cp ivy_lsp/workspace_detection.py ivy_lsp/workspace/detection.py
cp ivy_lsp/session_overlay.py ivy_lsp/workspace/session_overlay.py
```

- [ ] **Step 3: Update internal cross-references within moved files**

In `ivy_lsp/workspace/context.py` (was `workspace_context.py`):
- `from ivy_lsp.active_workspace import ActiveWorkspace` → `from ivy_lsp.workspace.active_workspace import ActiveWorkspace`
- `from ivy_lsp.session_overlay import SessionOverlay, TestScopeView` → `from ivy_lsp.workspace.session_overlay import SessionOverlay, TestScopeView`
- `from ivy_lsp.workspace_detection import WorkspaceConfig, detect_ivy_workspace` → `from ivy_lsp.workspace.detection import WorkspaceConfig, detect_ivy_workspace`

In `ivy_lsp/workspace/active_workspace.py`:
- If there's a self-referencing TYPE_CHECKING import, update `from ivy_lsp.active_workspace import ActiveWorkspace` → `from ivy_lsp.workspace.active_workspace import ActiveWorkspace`

- [ ] **Step 4: Update all source file imports (7 files)**

Apply the following find-replace patterns across source files:

| Pattern | Replacement |
|---|---|
| `from ivy_lsp.workspace_detection import` | `from ivy_lsp.workspace.detection import` |
| `from ivy_lsp.workspace_context import` | `from ivy_lsp.workspace.context import` |
| `from ivy_lsp.active_workspace import` | `from ivy_lsp.workspace.active_workspace import` |
| `from ivy_lsp.session_overlay import` | `from ivy_lsp.workspace.session_overlay import` |

Files to update:
- `ivy_lsp/mcp_server.py` (lines 479, 1146)
- `ivy_lsp/indexer/include_resolver.py` (line 197)
- `ivy_lsp/__main__.py` (lines 129, 251)
- `ivy_lsp/server_setup.py` (lines 74, 102, 103, 225)
- `ivy_lsp/tools/workspace.py` (lines 56, 142, 170)
- `ivy_lsp/tools/analysis.py` (lines 458, 501)
- `ivy_lsp/index_builder.py` (line 38)

- [ ] **Step 5: Update all test file imports (13 files)**

Apply the same find-replace patterns across test files:
- `tests/test_workspace_detection.py` — also update `from ivy_lsp.workspace_detection import _apply_marker` (4 occurrences) to `from ivy_lsp.workspace.detection import _apply_marker`
- `tests/test_active_workspace.py`
- `tests/test_workspace_context.py`
- `tests/test_workspace_context_active.py`
- `tests/test_scope_views.py`
- `tests/test_session_overlay.py`
- `tests/test_index_builder.py`
- `tests/test_index_integration.py`
- `tests/test_cross_layer_deps.py`
- `tests/test_task_2_1_include_resolver.py` (6 occurrences of `from ivy_lsp.workspace_detection import WorkspaceLayer`)
- `tests/test_task_2_5_references.py`
- `tests/test_active_workspace_resolver.py`
- `tests/test_workspace_symbols_filtering.py`

- [ ] **Step 6: Delete old root-level files**

```bash
rm ivy_lsp/active_workspace.py
rm ivy_lsp/workspace_context.py
rm ivy_lsp/workspace_detection.py
rm ivy_lsp/session_overlay.py
```

- [ ] **Step 7: Verify no stale references remain**

```bash
grep -r "from ivy_lsp\.workspace_detection\b\|from ivy_lsp\.workspace_context\b\|from ivy_lsp\.active_workspace\b\|from ivy_lsp\.session_overlay\b" ivy_lsp/ tests/ --include="*.py" | grep -v __pycache__
```
Expected: Zero results

- [ ] **Step 8: Run tests**

Run: `python -m pytest tests/ -x -q --tb=short 2>&1 | tail -5`
Expected: All tests pass

- [ ] **Step 9: Verify old import paths fail**

```bash
python -c "from ivy_lsp.workspace_context import WorkspaceContext" 2>&1 | grep ModuleNotFoundError
python -c "from ivy_lsp.workspace import WorkspaceContext" && echo "OK"
```
Expected: First command shows ModuleNotFoundError, second prints OK

- [ ] **Step 10: Commit (ATOMIC — all changes in one commit)**

```bash
git add -A
git commit -m "$(cat <<'EOF'
refactor: extract workspace modules into ivy_lsp/workspace/ package

Move active_workspace.py, workspace_context.py, workspace_detection.py,
and session_overlay.py into ivy_lsp/workspace/ sub-package.
Update all imports across 7 source files and 13 test files.
No backward-compat shims — old paths are removed.
EOF
)"
```

---

## Batch B: Deduplication + Workspace Indexer Split

---

### Task 6: Create `utils/symbol_resolver.py` shared module

**Files:**
- Create: `ivy_lsp/utils/symbol_resolver.py`
- Test: `tests/test_symbol_resolver.py`

- [ ] **Step 1: Write tests for the shared helpers**

Create `tests/test_symbol_resolver.py`:
```python
"""Tests for ivy_lsp.utils.symbol_resolver shared helpers."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from ivy_lsp.utils.symbol_resolver import (
    ensure_deep_parsed,
    lookup_with_dotted_fallback,
)


class TestLookupWithDottedFallback:
    """Test progressive dotted suffix lookup."""

    def test_direct_match(self):
        indexer = MagicMock()
        indexer.lookup_symbol.return_value = ["result"]
        assert lookup_with_dotted_fallback(indexer, "foo") == ["result"]
        indexer.lookup_symbol.assert_called_once_with("foo")

    def test_no_dot_no_match(self):
        indexer = MagicMock()
        indexer.lookup_symbol.return_value = []
        assert lookup_with_dotted_fallback(indexer, "foo") == []

    def test_dotted_fallback_progressive(self):
        indexer = MagicMock()
        indexer.lookup_symbol.side_effect = [
            [],          # "a.b.c" -> no match
            [],          # "b.c" -> no match
            ["found"],   # "c" -> match
        ]
        assert lookup_with_dotted_fallback(indexer, "a.b.c") == ["found"]

    def test_dotted_fallback_stops_at_first_match(self):
        indexer = MagicMock()
        indexer.lookup_symbol.side_effect = [
            [],          # "a.b.c" -> no match
            ["found"],   # "b.c" -> match
        ]
        result = lookup_with_dotted_fallback(indexer, "a.b.c")
        assert result == ["found"]
        assert indexer.lookup_symbol.call_count == 2


class TestEnsureDeepParsed:
    """Test demand-driven deep parse guard."""

    def test_calls_deep_parse_when_available(self):
        indexer = MagicMock(spec=["deep_parse_on_demand"])
        ensure_deep_parsed(indexer, "/path/to/file.ivy")
        indexer.deep_parse_on_demand.assert_called_once_with("/path/to/file.ivy")

    def test_no_op_when_method_missing(self):
        indexer = MagicMock(spec=[])
        ensure_deep_parsed(indexer, "/path/to/file.ivy")  # should not raise

    def test_no_op_when_indexer_is_none(self):
        ensure_deep_parsed(None, "/path/to/file.ivy")  # should not raise
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_symbol_resolver.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ivy_lsp.utils.symbol_resolver'`

- [ ] **Step 3: Write implementation**

Create `ivy_lsp/utils/symbol_resolver.py`:
```python
"""Shared symbol resolution helpers used by multiple LSP feature handlers.

Extracts common patterns for symbol lookup with dotted fallback and
demand-driven deep parsing that were duplicated across definition.py,
hover.py, call_hierarchy.py, implementation.py, and document_symbols.py.
"""
from __future__ import annotations

from typing import Any, List, Optional


def lookup_with_dotted_fallback(
    indexer: Any, word: str
) -> List[Any]:
    """Look up a symbol with progressive dotted suffix fallback.

    Tries the full word first, then progressively strips leading
    dot-separated components until a match is found.

    Example: "quic.frame.type" tries "quic.frame.type", then
    "frame.type", then "type".
    """
    results = indexer.lookup_symbol(word)
    if not results and "." in word:
        parts = word.split(".")
        for i in range(1, len(parts)):
            suffix = ".".join(parts[i:])
            results = indexer.lookup_symbol(suffix)
            if results:
                break
    return results


def ensure_deep_parsed(
    indexer: Optional[Any], filepath: str
) -> None:
    """Trigger demand-driven deep parse if the indexer supports it.

    No-op if indexer is None or lacks deep_parse_on_demand.
    """
    if indexer is not None and hasattr(indexer, "deep_parse_on_demand"):
        indexer.deep_parse_on_demand(filepath)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_symbol_resolver.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add ivy_lsp/utils/symbol_resolver.py tests/test_symbol_resolver.py
git commit -m "$(cat <<'EOF'
feat: add utils/symbol_resolver.py shared helpers

Extract lookup_with_dotted_fallback() and ensure_deep_parsed()
from duplicated patterns across 5 feature handler files.
EOF
)"
```

---

### Task 7: Migrate feature handlers to use symbol_resolver

**Files:**
- Modify: `ivy_lsp/features/definition.py`
- Modify: `ivy_lsp/features/hover.py`
- Modify: `ivy_lsp/features/call_hierarchy.py`
- Modify: `ivy_lsp/features/implementation.py`
- Modify: `ivy_lsp/features/document_symbols.py`

- [ ] **Step 1: Migrate `features/definition.py`**

Replace the deep-parse guard (lines 54-56) with:
```python
from ivy_lsp.utils.symbol_resolver import ensure_deep_parsed, lookup_with_dotted_fallback
# ...
ensure_deep_parsed(indexer, filepath)
```

Replace the lookup+dotted fallback block (lines 81-88) with:
```python
results = lookup_with_dotted_fallback(indexer, word)
```

- [ ] **Step 2: Run tests for definition**

Run: `python -m pytest tests/ -k "definition" -x -q --tb=short`
Expected: All pass

- [ ] **Step 3: Migrate `features/hover.py`**

Replace deep-parse guard and lookup+dotted fallback with calls to the shared helpers. The semantic model fallback and formatting logic stays as-is.

- [ ] **Step 4: Run tests for hover**

Run: `python -m pytest tests/ -k "hover" -x -q --tb=short`
Expected: All pass

- [ ] **Step 5: Migrate `features/call_hierarchy.py` and `implementation.py`**

These use a simpler 1-level `rsplit(".", 1)` variant. Replace with `lookup_with_dotted_fallback` which is a superset.

- [ ] **Step 6: Migrate `features/document_symbols.py`**

Replace deep-parse guard with `ensure_deep_parsed()`.

- [ ] **Step 7: Run full test suite**

Run: `python -m pytest tests/ -x -q --tb=short 2>&1 | tail -5`
Expected: All tests pass

- [ ] **Step 8: Commit**

```bash
git add -u
git commit -m "$(cat <<'EOF'
refactor: migrate feature handlers to use shared symbol_resolver

Replace duplicated lookup-with-dotted-fallback and deep-parse-on-demand
patterns in definition, hover, call_hierarchy, implementation, and
document_symbols with calls to utils/symbol_resolver.py.
EOF
)"
```

---

### Task 8: Extract `_is_monitor_symbol` to shared location

**Files:**
- Modify: `ivy_lsp/parsing/symbols.py` — add `is_monitor_symbol()` function
- Modify: `ivy_lsp/features/call_hierarchy.py` — use shared function
- Modify: `ivy_lsp/features/implementation.py` — use shared function

- [ ] **Step 1: Add `is_monitor_symbol` to `parsing/symbols.py`**

```python
def is_monitor_symbol(detail: str) -> bool:
    """Check if a symbol detail indicates a monitor (before/after/around)."""
    return detail.startswith("before ") or detail.startswith("after ") or detail.startswith("around ")
```

- [ ] **Step 2: Update callers**

In `features/call_hierarchy.py`: Replace inline `_is_monitor_symbol` with import from `ivy_lsp.parsing.symbols`.
In `features/implementation.py`: Replace inline monitor checks with import.

- [ ] **Step 3: Run tests and commit**

Run: `python -m pytest tests/ -x -q --tb=short 2>&1 | tail -5`

```bash
git add -u
git commit -m "refactor: extract is_monitor_symbol to parsing/symbols.py"
```

---

### Task 9: Split `indexer/workspace_indexer.py` into mixins

**Files:**
- Create: `ivy_lsp/indexer/deep_indexer.py`
- Create: `ivy_lsp/indexer/scope_manager.py`
- Modify: `ivy_lsp/indexer/workspace_indexer.py`

- [ ] **Step 1: Identify the method groups**

Read `ivy_lsp/indexer/workspace_indexer.py` and identify:
- **DeepIndexMixin methods**: `_deep_index_from_tests`, `_deep_index_from_tests_impl`, `_deep_index_serial`, `_deep_index_parallel`, `_upgrade_file_symbols`, `deep_parse_on_demand`
- **ScopeManagerMixin methods**: `_extract_file_requirements`, `_extract_file_exports_imports`, `_wire_requirement_graph`, `_load_requirement_manifests`, `_wire_coverage_edges`, `_compute_test_scopes`, `get_endpoint_mirrors_for_file`, `get_scope_files_for_file`, `get_symbols_in_scope`, `reindex_file`, `reindex_file_with_dependents`, `_remove_file_symbols`, `_extract_includes`

- [ ] **Step 2: Create `indexer/deep_indexer.py`**

Create the `DeepIndexMixin` class with the deep indexing methods extracted from `workspace_indexer.py`. Add `TYPE_CHECKING` import for type annotation:

```python
"""Deep indexing mixin for WorkspaceIndexer."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ivy_lsp.indexer.workspace_indexer import WorkspaceIndexer

class DeepIndexMixin:
    """Deep indexing methods: background parse upgrade and on-demand deep parsing."""
    # ... extracted methods ...
```

- [ ] **Step 3: Create `indexer/scope_manager.py`**

Create the `ScopeManagerMixin` class with scope and requirement graph methods. Same `TYPE_CHECKING` pattern.

- [ ] **Step 4: Update `workspace_indexer.py` to inherit from mixins**

```python
from ivy_lsp.indexer.deep_indexer import DeepIndexMixin
from ivy_lsp.indexer.scope_manager import ScopeManagerMixin

class WorkspaceIndexer(DeepIndexMixin, ScopeManagerMixin):
    # ... remaining core methods ...
```

Remove the extracted methods from `workspace_indexer.py`.

- [ ] **Step 5: Run tests**

Run: `python -m pytest tests/ -x -q --tb=short 2>&1 | tail -5`
Expected: All tests pass (zero import changes needed — class stays in same module)

- [ ] **Step 6: Commit**

```bash
git add ivy_lsp/indexer/deep_indexer.py ivy_lsp/indexer/scope_manager.py ivy_lsp/indexer/workspace_indexer.py
git commit -m "$(cat <<'EOF'
refactor: split workspace_indexer.py into mixins

Extract DeepIndexMixin (deep parsing methods) and ScopeManagerMixin
(requirement graph and test scope methods) from the 1425-line
WorkspaceIndexer into separate files. The class stays in the same
module path, so zero external import changes needed.
EOF
)"
```

---

## Batch C: Large File Splits + Diagnostic Factory

---

### Task 10: Split `tools/formatters.py` into package

**Files:**
- Convert: `ivy_lsp/tools/formatters.py` → `ivy_lsp/tools/formatters/__init__.py`
- Create: `ivy_lsp/tools/formatters/_primitives.py`
- Create: `ivy_lsp/tools/formatters/verification.py`
- Create: `ivy_lsp/tools/formatters/traceability.py`
- Create: `ivy_lsp/tools/formatters/visualization.py`

- [ ] **Step 1: Read formatters.py and identify split boundaries**

Read the file and identify:
- Building block helpers: `_section`, `_kv`, `_badge`, `_pct_bar`, `_table`, `_code_block`, `_bullet_list`, `_diag_line`, `format_error`
- Verification formatters (by tool name in `format_tool_result` dispatch)
- Traceability formatters (coverage, requirements, manifest)
- Visualization/quality formatters (visualize, model_summary, patterns, quality)

- [ ] **Step 2: Create package structure**

```bash
mkdir -p ivy_lsp/tools/formatters_pkg
```

Create the 4 sub-modules by extracting functions from `formatters.py`:
- `_primitives.py` — the markdown building blocks
- `verification.py` — `_format_ivy_verify`, `_format_ivy_compile`, etc.
- `traceability.py` — `_format_ivy_coverage`, `_format_ivy_extract_requirements`, etc.
- `visualization.py` — `_format_ivy_visualize`, `_format_ivy_model_summary`, etc.

Each sub-module imports building blocks from `._primitives`.

Create `__init__.py` with `format_tool_result` dispatcher, `format_error`, and `_format_generic` (needed by `test_formatters.py`).

- [ ] **Step 3: Replace original file with package**

```bash
# Clean stale .pyc
find ivy_lsp/tools/__pycache__ -name "formatters*" -delete 2>/dev/null
# Move package into place
rm ivy_lsp/tools/formatters.py
mv ivy_lsp/tools/formatters_pkg ivy_lsp/tools/formatters
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/ -x -q --tb=short 2>&1 | tail -5`
Expected: All tests pass

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "$(cat <<'EOF'
refactor: split tools/formatters.py (1207 lines) into package

Extract building blocks into _primitives.py, then split per-tool
formatters by category: verification, traceability, visualization.
format_tool_result dispatcher stays in __init__.py.
EOF
)"
```

---

### Task 11: Split `features/visualization.py` into handler modules

**Files:**
- Modify: `ivy_lsp/features/visualization.py` (trimmed to ~520 lines)
- Create: `ivy_lsp/features/viz_coverage.py`
- Create: `ivy_lsp/features/viz_graphs.py`
- Create: `ivy_lsp/features/viz_suggestions.py`
- Modify: 3 test files

- [ ] **Step 1: Extract handler functions**

Move `handle_coverage_gaps` → `viz_coverage.py`
Move `handle_action_dependency_graph`, `handle_state_machine_view`, `handle_layered_overview` → `viz_graphs.py`
Move `handle_smart_suggestions` → `viz_suggestions.py`

Keep shared helpers (`_cap_response`, `_get_requirement_graph`, `_resolve_scope`, `_filter_by_scope`, `_filter_by_protocol`, `_rel`, `_classify_direction`, `_serialize_requirement`, `_serialize_state_var`) and `register()` in `visualization.py`.

Each new file imports helpers from `ivy_lsp.features.visualization`.

- [ ] **Step 2: Update `register()` in visualization.py**

Import extracted handlers and wire them in `register()`.

- [ ] **Step 3: Update test imports**

Update `test_visualization.py`, `test_visualization_integration.py`, `test_smart_suggestions_context.py` to import from new module paths.

- [ ] **Step 4: Run tests and commit**

Run: `python -m pytest tests/ -x -q --tb=short 2>&1 | tail -5`

```bash
git add -A
git commit -m "$(cat <<'EOF'
refactor: split features/visualization.py (1392 lines) into handlers

Extract viz_coverage, viz_graphs, and viz_suggestions into separate
modules. Shared helpers and register() stay in visualization.py.
EOF
)"
```

---

### Task 12: Split `features/diagnostics.py` into compute module

**Files:**
- Modify: `ivy_lsp/features/diagnostics.py` (trimmed to ~250 lines)
- Create: `ivy_lsp/features/diagnostic_compute.py`
- Modify: ~10 test files

- [ ] **Step 1: Extract compute functions**

Move `check_structural_issues`, `compute_requirement_diagnostics`, `compute_semantic_diagnostics`, `compute_diagnostics`, `parse_ivy_check_output`, `run_deep_diagnostics` → `diagnostic_compute.py`

Keep `DiagnosticCache`, `_CachedDiagnosticEntry`, `register()`, `_convert_error_to_diagnostic` in `diagnostics.py`.

- [ ] **Step 2: Update imports in diagnostics.py**

`diagnostics.py` imports compute functions from the new module.

- [ ] **Step 3: Update test imports**

Grep for all test files importing from `ivy_lsp.features.diagnostics` and update those importing compute functions. Note: `test_commands.py` imports `parse_ivy_check_output` — update it too.

- [ ] **Step 4: Run tests and commit**

Run: `python -m pytest tests/ -x -q --tb=short 2>&1 | tail -5`

```bash
git add -A
git commit -m "$(cat <<'EOF'
refactor: split features/diagnostics.py (1084 lines)

Extract compute functions (check_structural_issues,
compute_*_diagnostics, parse_ivy_check_output, run_deep_diagnostics)
into diagnostic_compute.py. Cache and registration stay in
diagnostics.py.
EOF
)"
```

---

### Task 13: Split `features/commands.py` into extended commands

**Files:**
- Modify: `ivy_lsp/features/commands.py` (trimmed to ~650 lines)
- Create: `ivy_lsp/features/commands_extended.py`
- Modify: ~5 test files

- [ ] **Step 1: Identify extended commands to extract**

Read `features/commands.py` and identify handlers in `register()` that are "extended" vs "core":
- **Core** (stay): verify, compile, showModel, capabilities, setActiveTest, listTests
- **Extended** (move): compiled_model, active_document_changed, show_action_requirements, show_property_details, navigate_to_include, show_rfc_details, noop, recompile_all

- [ ] **Step 2: Create `commands_extended.py`**

Extract extended handlers as module-level async functions:
```python
async def handle_compiled_model(server, params):
    """Handle ivy/compiledModel command."""
    # ... extracted logic ...
```

Create `register_extended_commands(server)` that registers all extended handlers.

Import shared helpers from `ivy_lsp.features.commands` (`_track_start`, `_track_end`, `_refresh_open_diagnostics_sync`, `_ServerProxy`, etc.).

- [ ] **Step 3: Update `register()` in commands.py**

Call `register_extended_commands(server)` at the end of `register()`.

- [ ] **Step 4: Update test imports and run tests**

Run: `python -m pytest tests/ -x -q --tb=short 2>&1 | tail -5`

```bash
git add -A
git commit -m "$(cat <<'EOF'
refactor: split features/commands.py (1118 lines)

Extract extended command handlers (compiled_model, action_requirements,
navigate_to_include, etc.) into commands_extended.py. Core commands
and shared helpers stay in commands.py.
EOF
)"
```

---

### Task 14: Split `tools/traceability.py` into extraction module

**Files:**
- Modify: `ivy_lsp/tools/traceability.py` (trimmed to ~500 lines)
- Create: `ivy_lsp/tools/traceability_extraction.py`

- [ ] **Step 1: Extract requirement extraction and manifest handlers**

Move `ivy_extract_requirements` and `ivy_manifest` tool handler logic → `traceability_extraction.py`.

Keep coverage dispatcher and sub-functions in `traceability.py`.

- [ ] **Step 2: Update `register_traceability_tools` to import from new module**

- [ ] **Step 3: Check structural tests**

Read `tests/test_tools_traceability.py` lines 198-254. If any structural tests read `traceability.__file__` source and search for strings that moved, update them to check both files or convert to functional tests.

- [ ] **Step 4: Run tests and commit**

Run: `python -m pytest tests/ -x -q --tb=short 2>&1 | tail -5`

```bash
git add -A
git commit -m "$(cat <<'EOF'
refactor: split tools/traceability.py (1064 lines)

Extract ivy_extract_requirements and ivy_manifest handlers into
traceability_extraction.py. Coverage tools stay in traceability.py.
EOF
)"
```

---

### Task 15: Add diagnostic factory (optional, low priority)

**Files:**
- Modify: `ivy_lsp/diagnostics/rich_diagnostic.py`
- Modify: `ivy_lsp/features/diagnostic_compute.py`

- [ ] **Step 1: Add `make_line_diagnostic()` factory**

In `diagnostics/rich_diagnostic.py`:
```python
def make_line_diagnostic(
    code: str,
    message: str,
    line: int,
    line_text: str,
    *,
    severity: Optional[lsp.DiagnosticSeverity] = None,
    source: Optional[str] = None,
) -> IvyDiagnostic:
    """Create an IvyDiagnostic with defaults from DIAGNOSTIC_REGISTRY."""
    # ... implementation ...
```

- [ ] **Step 2: Migrate 6 diagnostic sites in `diagnostic_compute.py`**

Replace repetitive `lsp.Diagnostic(range=..., message=..., severity=...)` constructions with `make_line_diagnostic(...).to_lsp()` for sites using `DIAGNOSTIC_REGISTRY` codes.

- [ ] **Step 3: Run tests and commit**

Run: `python -m pytest tests/ -x -q --tb=short 2>&1 | tail -5`

```bash
git add -u
git commit -m "$(cat <<'EOF'
refactor: add make_line_diagnostic factory, migrate 6 diagnostic sites

Revive the IvyDiagnostic class with a convenience factory. Migrate
diagnostic construction sites that already use DIAGNOSTIC_REGISTRY
codes to the new factory pattern.
EOF
)"
```

---

## Final Verification

After all tasks are complete:

- [ ] **Full test suite**: `python -m pytest tests/ -x -q --tb=short`
- [ ] **Server starts**: `python -m ivy_lsp --help`
- [ ] **Public API imports**:
  ```bash
  python -c "from ivy_lsp.mcp_server import start_mcp; print('OK')"
  python -c "from ivy_lsp.server import IvyLanguageServer; print('OK')"
  python -c "from ivy_lsp.tools import register_all_tools; print('OK')"
  python -c "from ivy_lsp.workspace import ActiveWorkspace, WorkspaceConfig; print('OK')"
  ```
- [ ] **Old paths fail**: `python -c "from ivy_lsp.workspace_context import WorkspaceContext" 2>&1 | grep ModuleNotFoundError`
- [ ] **Lint**: `flake8 ivy_lsp/ --max-line-length 120 && flake8 tests/ --max-line-length 120`
- [ ] **File sizes**: Verify no file exceeds 800 lines: `find ivy_lsp/ -name "*.py" -exec wc -l {} + | sort -rn | head -10`
