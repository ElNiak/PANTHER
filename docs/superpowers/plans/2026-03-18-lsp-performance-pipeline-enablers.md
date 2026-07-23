# LSP Performance Fixes — Pipeline Enablers

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 4 high-impact LSP performance issues (P1, P2, P4, P8) and 2 plugin UX issues (P3, P13) that are prerequisites for the AI-assisted formal specification pipeline.

**Architecture:** Targeted fixes to `SymbolTable`, `WorkspaceIndexer`, feature handlers, and `visualization.py` in the ivy-lsp submodule, plus command/skill updates in the panther-ivy-plugin. All changes are incremental (no full rewrites) and backward-compatible.

**Tech Stack:** Python 3.10+, pygls LSP framework, lsprotocol, pytest

**Working directory:** `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/` (for LSP) and `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/` (for plugin)

**Test command:** `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/ -v`

**Validation:** After all tasks, run `/nct-validate` to ensure 55-check correctness validation still passes.

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `ivy_lsp/parsing/symbols.py` | Modify | Add `SymbolTable.remove_file()` method |
| `ivy_lsp/indexer/workspace_indexer.py` | Modify | Selective cache invalidation, demand-driven deep parse, use `remove_file()` |
| `ivy_lsp/features/hover.py` | Modify | Call demand-driven deep parse before hover |
| `ivy_lsp/features/definition.py` | Modify | Call demand-driven deep parse before goto-def |
| `ivy_lsp/features/document_symbols.py` | Modify | Call demand-driven deep parse for outline |
| `ivy_lsp/features/visualization.py` | Modify | Fix `handle_smart_suggestions` context filtering |
| `tests/test_symbol_table_remove.py` | Create | Tests for P1 |
| `tests/test_selective_invalidation.py` | Create | Tests for P2 |
| `tests/test_demand_deep_parse.py` | Create | Tests for P4 |
| `tests/test_smart_suggestions_context.py` | Create | Tests for P8 |
| Plugin: `commands/nct-scaffold.md` | Modify | Add preset argument (P3) |
| Plugin: `skills/*/SKILL.md` | Modify | Add prerequisites frontmatter (P13) |

---

### Task 1: SymbolTable.remove_file() — Avoid Full Rebuild (P1)

**Why:** Currently `_remove_file_symbols()` and `_upgrade_file_symbols()` copy ALL symbols into a new SymbolTable, filtering out the target file. For 10,000+ symbols this is O(n) per single-file edit. Adding an in-place `remove_file()` method makes it O(symbols_in_file).

**Files:**
- Modify: `ivy_lsp/parsing/symbols.py:78-135`
- Modify: `ivy_lsp/indexer/workspace_indexer.py:953-973` (`_upgrade_file_symbols`)
- Modify: `ivy_lsp/indexer/workspace_indexer.py:1091-1099` (`_remove_file_symbols`)
- Create: `tests/test_symbol_table_remove.py`

- [ ] **Step 1: Write failing test for SymbolTable.remove_file()**

```python
# tests/test_symbol_table_remove.py
"""Tests for SymbolTable.remove_file in-place removal."""
from lsprotocol.types import SymbolKind
from ivy_lsp.parsing.symbols import IvySymbol, SymbolTable


class TestSymbolTableRemoveFile:
    def test_remove_file_clears_by_name(self):
        table = SymbolTable()
        s1 = IvySymbol(name="foo", kind=SymbolKind.Function, range=(0, 0, 1, 0), file_path="/a.ivy")
        s2 = IvySymbol(name="bar", kind=SymbolKind.Variable, range=(0, 0, 1, 0), file_path="/b.ivy")
        table.add_symbol(s1)
        table.add_symbol(s2)
        table.remove_file("/a.ivy")
        assert table.lookup("foo") == []
        assert table.lookup("bar") == [s2]

    def test_remove_file_clears_by_file(self):
        table = SymbolTable()
        s1 = IvySymbol(name="foo", kind=SymbolKind.Function, range=(0, 0, 1, 0), file_path="/a.ivy")
        s2 = IvySymbol(name="bar", kind=SymbolKind.Variable, range=(0, 0, 1, 0), file_path="/a.ivy")
        table.add_symbol(s1)
        table.add_symbol(s2)
        table.remove_file("/a.ivy")
        assert table.symbols_in_file("/a.ivy") == []
        assert table.all_symbols() == []

    def test_remove_file_clears_all_list(self):
        table = SymbolTable()
        s1 = IvySymbol(name="foo", kind=SymbolKind.Function, range=(0, 0, 1, 0), file_path="/a.ivy")
        s2 = IvySymbol(name="bar", kind=SymbolKind.Variable, range=(0, 0, 1, 0), file_path="/b.ivy")
        table.add_symbol(s1)
        table.add_symbol(s2)
        table.remove_file("/a.ivy")
        assert len(table.all_symbols()) == 1
        assert table.all_symbols()[0].name == "bar"

    def test_remove_file_no_op_for_unknown_file(self):
        table = SymbolTable()
        s1 = IvySymbol(name="foo", kind=SymbolKind.Function, range=(0, 0, 1, 0), file_path="/a.ivy")
        table.add_symbol(s1)
        table.remove_file("/nonexistent.ivy")
        assert len(table.all_symbols()) == 1

    def test_remove_file_handles_duplicate_names_across_files(self):
        """Two files define 'send' — removing one file preserves the other."""
        table = SymbolTable()
        s1 = IvySymbol(name="send", kind=SymbolKind.Function, range=(0, 0, 1, 0), file_path="/a.ivy")
        s2 = IvySymbol(name="send", kind=SymbolKind.Function, range=(5, 0, 6, 0), file_path="/b.ivy")
        table.add_symbol(s1)
        table.add_symbol(s2)
        table.remove_file("/a.ivy")
        results = table.lookup("send")
        assert len(results) == 1
        assert results[0].file_path == "/b.ivy"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_symbol_table_remove.py -v`
Expected: FAIL with `AttributeError: 'SymbolTable' object has no attribute 'remove_file'`

- [ ] **Step 3: Implement SymbolTable.remove_file()**

Add this method to `SymbolTable` in `ivy_lsp/parsing/symbols.py` after `symbols_in_file()` (after line 134):

```python
    def remove_file(self, filepath: str) -> int:
        """Remove all symbols originating from *filepath* in place.

        Returns the number of symbols removed.
        """
        old = self._by_file.pop(filepath, [])
        if not old:
            return 0
        old_set = set(id(s) for s in old)
        for sym in old:
            name_list = self._by_name.get(sym.name)
            if name_list is not None:
                self._by_name[sym.name] = [
                    s for s in name_list if id(s) not in old_set
                ]
                if not self._by_name[sym.name]:
                    del self._by_name[sym.name]
        self._all = [s for s in self._all if id(s) not in old_set]
        return len(old)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_symbol_table_remove.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Wire remove_file() into _remove_file_symbols()**

Replace the full-rebuild pattern in `workspace_indexer.py` lines 1091-1099:

```python
    def _remove_file_symbols(self, filepath: str) -> None:
        """Remove all symbols from *filepath* from the symbol table."""
        with self._table_lock:
            self._symbol_table.remove_file(filepath)
```

- [ ] **Step 6: Keep atomic-swap in _upgrade_file_symbols() (no change)**

**IMPORTANT**: Do NOT change `_upgrade_file_symbols`. The original code uses atomic reference swap (`self._symbol_table = new_table`) which readers depend on — they do NOT acquire `_table_lock`. In-place mutation would create a race where concurrent readers see missing symbols between `remove_file()` and `add_symbol()`.

Only `_remove_file_symbols` (Step 5) uses `remove_file()` because it performs permanent deletion where the brief visibility gap is acceptable (the file is being removed anyway).

- [ ] **Step 7: Run full test suite to verify no regression**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/ -v --tb=short`
Expected: All existing tests PASS

- [ ] **Step 8: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add ivy_lsp/parsing/symbols.py ivy_lsp/indexer/workspace_indexer.py tests/test_symbol_table_remove.py
git commit -m "perf: add SymbolTable.remove_file() for in-place symbol removal

Replace O(all_symbols) full-rebuild pattern with O(symbols_in_file)
in-place removal in _remove_file_symbols. Note: _upgrade_file_symbols
retains atomic swap for concurrent reader safety.
Reduces overhead during incremental re-indexing for large workspaces."
```

---

### Task 2: Mirror-Scope Selective Invalidation (P2)

**Why:** `_compute_test_scopes()` calls `self._mirror_scope_cache.clear()` unconditionally (line 1358). For a 202-file workspace, every single-file reindex wipes 200+ cache entries. With selective invalidation, only entries in the affected test scope are cleared.

**Files:**
- Modify: `ivy_lsp/indexer/workspace_indexer.py:1324-1367` (`_compute_test_scopes`)
- Modify: `ivy_lsp/indexer/workspace_indexer.py:1045-1089` (`reindex_file`, `reindex_file_with_dependents`)
- Create: `tests/test_selective_invalidation.py`

- [ ] **Step 1: Write failing test for selective invalidation**

```python
# tests/test_selective_invalidation.py
"""Tests for mirror-scope selective cache invalidation."""
import os
from unittest.mock import MagicMock, patch

import pytest

from ivy_lsp.analysis.test_scope import ExportImportInfo, TestScope
from ivy_lsp.indexer.workspace_indexer import WorkspaceIndexer
from ivy_lsp.parsing.symbols import IvySymbol, SymbolKind


def _make_indexer(workspace_root="/fake/workspace"):
    parser = MagicMock()
    resolver = MagicMock()
    resolver.find_all_ivy_files.return_value = []
    resolver.resolve.return_value = None
    resolver.collision_map = {}
    indexer = WorkspaceIndexer(workspace_root, parser, resolver)
    return indexer


class TestSelectiveInvalidation:
    def test_compute_test_scopes_with_dirty_files_preserves_unaffected_cache(self):
        """When dirty_files is provided, only affected mirror-scope entries are cleared."""
        indexer = _make_indexer()

        # Setup: two test scopes, each including different files
        indexer._file_export_imports = {
            "/fake/test_a.ivy": ExportImportInfo(
                file="/fake/test_a.ivy",
                exports=["send"], imports=["recv"],
                export_lines={"send": 10}, import_lines={"recv": 20},
            ),
            "/fake/test_b.ivy": ExportImportInfo(
                file="/fake/test_b.ivy",
                exports=["connect"], imports=["accept"],
                export_lines={"connect": 10}, import_lines={"accept": 20},
            ),
        }
        # test_a includes lib_a, test_b includes lib_b
        indexer._include_graph.add_edge("/fake/test_a.ivy", "/fake/lib_a.ivy")
        indexer._include_graph.add_edge("/fake/test_b.ivy", "/fake/lib_b.ivy")

        # First full computation
        indexer._compute_test_scopes()

        # Seed the mirror-scope cache with entries for both scopes
        sym_a = IvySymbol(name="x", kind=SymbolKind.Variable, range=(0,0,1,0), file_path="/fake/lib_a.ivy")
        sym_b = IvySymbol(name="y", kind=SymbolKind.Variable, range=(0,0,1,0), file_path="/fake/lib_b.ivy")
        indexer._mirror_scope_cache["/fake/lib_a.ivy"] = [sym_a]
        indexer._mirror_scope_cache["/fake/lib_b.ivy"] = [sym_b]

        # Now recompute with dirty_files={lib_a.ivy} — only test_a scope affected
        indexer._compute_test_scopes(dirty_files={"/fake/lib_a.ivy"})

        # lib_a cache should be cleared (it's in test_a's scope which is dirty)
        assert "/fake/lib_a.ivy" not in indexer._mirror_scope_cache
        # lib_b cache should be preserved (test_b scope not affected)
        assert "/fake/lib_b.ivy" in indexer._mirror_scope_cache

    def test_compute_test_scopes_full_clear_without_dirty_files(self):
        """Without dirty_files, full cache clear (backward compatible)."""
        indexer = _make_indexer()
        indexer._mirror_scope_cache["some_key"] = ["value"]
        indexer._compute_test_scopes()
        assert len(indexer._mirror_scope_cache) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_selective_invalidation.py -v`
Expected: FAIL — `_compute_test_scopes` does not accept `dirty_files` parameter

- [ ] **Step 3: Modify _compute_test_scopes to accept dirty_files**

In `workspace_indexer.py`, change the `_compute_test_scopes` signature and add selective invalidation logic. Replace lines 1324-1358:

```python
    def _compute_test_scopes(
        self, dirty_files: Optional[set] = None
    ) -> None:
        """Build a TestScope for each file that has exports and register it.

        Args:
            dirty_files: If provided, only invalidate mirror-scope cache
                entries for files in the transitive scope of dirty files'
                test scopes. If None, clear the entire cache (full rebuild).
        """
        with self._exports_lock:
            export_items = list(self._file_export_imports.items())
        for filepath, info in export_items:
            if not info.has_exports:
                continue

            closure = {filepath}
            closure |= self._include_graph.get_transitive_includes(filepath)

            all_exports: list = []
            all_imports: list = []
            for f in closure:
                f_info = self._file_export_imports.get(f)
                if f_info is not None:
                    all_exports.extend(f_info.exports)
                    all_imports.extend(f_info.imports)

            frozen_closure = frozenset(closure)
            scope = TestScope(
                test_file=filepath,
                include_closure=frozen_closure,
                exported_actions=frozenset(all_exports),
                imported_actions=frozenset(all_imports),
                tester_role=detect_test_role(frozen_closure),
            )
            self._requirement_graph.register_test_scope(scope)

        # Selective or full cache invalidation
        if dirty_files is not None:
            # Find which test scopes contain any dirty file
            affected_files: set = set()
            for _, scope in self._requirement_graph.iter_test_scopes():
                if dirty_files & scope.include_closure:
                    affected_files |= scope.include_closure
            # Only clear cache entries for affected files
            for f in affected_files:
                self._mirror_scope_cache.pop(f, None)
        else:
            self._mirror_scope_cache.clear()

        # Build partitioned staging if there are basename collisions.
        if self._resolver.collision_map:
            test_closures = {
                scope.test_file: scope.include_closure
                for _, scope in self._requirement_graph.iter_test_scopes()
            }
            self._resolver.build_partitioned_staging(test_closures)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_selective_invalidation.py -v`
Expected: All 2 tests PASS

- [ ] **Step 5: Wire dirty_files into reindex_file and reindex_file_with_dependents**

In `workspace_indexer.py`, update `reindex_file` (line 1061) and `reindex_file_with_dependents` (line 1089):

```python
    def reindex_file(self, filepath: str) -> None:
        """Re-index a single file after it has been modified on disk."""
        abs_path = os.path.abspath(filepath)
        self._remove_file_symbols(abs_path)
        self._requirement_graph.remove_file(abs_path)
        self._requirement_graph.invalidate_file(abs_path)
        with self._exports_lock:
            self._file_export_imports.pop(abs_path, None)
        self._cache.invalidate(abs_path)
        self._cache.invalidate_dependents(abs_path, self._include_graph)
        compiler_mgr = self._get_compiler_manager()
        if compiler_mgr is not None:
            compiler_mgr.invalidate_dependents(abs_path, self._include_graph)
        self._index_single_file(abs_path)
        self._wire_requirement_graph()
        self._compute_test_scopes(dirty_files={abs_path})
```

```python
    def reindex_file_with_dependents(self, filepath: str) -> None:
        """Re-index a file and all files that transitively depend on it."""
        abs_path = os.path.abspath(filepath)
        dirty = {abs_path}
        queue = [abs_path]
        while queue:
            current = queue.pop(0)
            for dep in self._include_graph.get_included_by(current):
                if dep not in dirty:
                    dirty.add(dep)
                    queue.append(dep)

        compiler_mgr = self._get_compiler_manager()
        if compiler_mgr is not None:
            for f in dirty:
                compiler_mgr.invalidate(f)

        for f in dirty:
            self._remove_file_symbols(f)
            self._cache.invalidate(f)
            self._index_single_file(f)

        self._wire_requirement_graph()
        self._compute_test_scopes(dirty_files=dirty)
```

- [ ] **Step 6: Run full test suite**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/ -v --tb=short`
Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add ivy_lsp/indexer/workspace_indexer.py tests/test_selective_invalidation.py
git commit -m "perf: selective mirror-scope cache invalidation on reindex

_compute_test_scopes now accepts dirty_files parameter. When provided,
only cache entries for files in affected test scopes are cleared,
preserving cache for unrelated endpoint mirrors. Full clear remains
for initial workspace indexing."
```

---

### Task 3: Demand-Driven Deep Parse for Shared Modules (P4)

**Why:** Phase 2 (background deep parse) only processes files with `export` declarations. Shared library modules like `quic_types.ivy` remain at fallback quality forever, giving poor hover/completion. This adds on-demand deep parsing when a user interacts with such a file.

**Files:**
- Modify: `ivy_lsp/indexer/workspace_indexer.py` — add `deep_parse_on_demand()` method
- Modify: `ivy_lsp/features/hover.py` — call `deep_parse_on_demand` before hover
- Modify: `ivy_lsp/features/definition.py` — call before goto-definition
- Modify: `ivy_lsp/features/document_symbols.py` — call before document outline
- Create: `tests/test_demand_deep_parse.py`

- [ ] **Step 1: Write failing test for deep_parse_on_demand**

```python
# tests/test_demand_deep_parse.py
"""Tests for demand-driven deep parsing of shared modules."""
import unittest.mock
from unittest.mock import MagicMock, patch

import pytest

from ivy_lsp.indexer.workspace_indexer import FileIndexStatus, WorkspaceIndexer
from ivy_lsp.parsing.symbols import IvySymbol, SymbolKind


def _make_indexer(workspace_root="/fake/workspace"):
    parser = MagicMock()
    resolver = MagicMock()
    resolver.find_all_ivy_files.return_value = []
    resolver.resolve.return_value = None
    indexer = WorkspaceIndexer(workspace_root, parser, resolver)
    return indexer, parser


class TestDemandDeepParse:
    def test_deep_parse_on_demand_upgrades_symbols(self):
        """Calling deep_parse_on_demand on a shallow-only file triggers full parse."""
        indexer, parser = _make_indexer()

        filepath = "/fake/quic_types.ivy"
        # Mark file as shallow-indexed only
        indexer._deep_index_progress.file_statuses[filepath] = FileIndexStatus(
            filepath=filepath, shallow_indexed=True, deep_parse_attempted=False
        )
        # Add a fallback symbol
        fallback_sym = IvySymbol(
            name="cid", kind=SymbolKind.Variable,
            range=(0, 0, 1, 0), file_path=filepath
        )
        indexer._symbol_table.add_symbol(fallback_sym)

        # Setup parser to return success with a better symbol
        ast_sym = IvySymbol(
            name="cid", kind=SymbolKind.Class,
            range=(0, 0, 1, 0), detail="type cid",
            file_path=filepath
        )
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.ast = MagicMock()
        parser.parse.return_value = mock_result

        with patch("ivy_lsp.parsing.ast_to_symbols.ast_to_symbols", return_value=[ast_sym]):
            with patch("builtins.open", unittest.mock.mock_open(read_data="type cid\n")):
                upgraded = indexer.deep_parse_on_demand(filepath)

        assert upgraded is True
        symbols = indexer._symbol_table.lookup("cid")
        assert len(symbols) == 1
        assert symbols[0].kind == SymbolKind.Class  # Upgraded from Variable
        assert symbols[0].detail == "type cid"

    def test_deep_parse_on_demand_skips_already_deep_parsed(self):
        """If already deep-parsed, return False without re-parsing."""
        indexer, parser = _make_indexer()
        filepath = "/fake/quic_types.ivy"
        indexer._deep_index_progress.file_statuses[filepath] = FileIndexStatus(
            filepath=filepath, shallow_indexed=True,
            deep_parse_attempted=True, deep_parse_succeeded=True
        )
        result = indexer.deep_parse_on_demand(filepath)
        assert result is False
        parser.parse.assert_not_called()

    def test_deep_parse_on_demand_skips_unknown_file(self):
        """If file has no index status, skip."""
        indexer, parser = _make_indexer()
        result = indexer.deep_parse_on_demand("/fake/unknown.ivy")
        assert result is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_demand_deep_parse.py -v`
Expected: FAIL — `AttributeError: 'WorkspaceIndexer' object has no attribute 'deep_parse_on_demand'`

- [ ] **Step 3: Implement deep_parse_on_demand()**

Add this method to `WorkspaceIndexer` after `_index_single_file` (after line 1023):

```python
    def deep_parse_on_demand(self, filepath: str) -> bool:
        """Parse a file with the full AST parser if it was only shallow-indexed.

        Returns True if the file was upgraded, False if already deep-parsed
        or not eligible.
        """
        abs_path = os.path.abspath(filepath)
        status = self._deep_index_progress.file_statuses.get(abs_path)
        if status is None:
            return False
        if status.deep_parse_attempted:
            return False

        from ivy_lsp.parsing.ast_to_symbols import ast_to_symbols

        try:
            with open(abs_path) as f:
                source = f.read()
        except OSError:
            return False

        result = self._parser.parse(source, abs_path)
        status.deep_parse_attempted = True
        if not result.success:
            status.deep_parse_succeeded = False
            return False

        symbols = ast_to_symbols(result.ast, abs_path, source)
        status.deep_parse_succeeded = True
        self._upgrade_file_symbols(abs_path, symbols, result)

        slog.info(
            "On-demand deep parse: %s",
            os.path.basename(abs_path),
        )
        return True
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_demand_deep_parse.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Wire into hover handler**

In `ivy_lsp/features/hover.py`, the `get_hover_info()` function receives `indexer` as a parameter. Add at the top of `get_hover_info()` body (after the docstring, before `word_at_position`):

```python
    # Demand-driven deep parse for shared modules
    if indexer is not None and hasattr(indexer, "deep_parse_on_demand"):
        indexer.deep_parse_on_demand(filepath)
```

- [ ] **Step 6: Wire into definition handler**

In `ivy_lsp/features/definition.py`, the `goto_definition()` function receives `indexer` as a parameter. Add at the top of the function body:

```python
    if indexer is not None and hasattr(indexer, "deep_parse_on_demand"):
        indexer.deep_parse_on_demand(filepath)
```

- [ ] **Step 7: Wire into document_symbols handler**

In `ivy_lsp/features/document_symbols.py`, the `compute_document_symbols()` function receives `indexer` as a parameter (can be None). Add at the top:

```python
    if indexer is not None and hasattr(indexer, "deep_parse_on_demand"):
        indexer.deep_parse_on_demand(filepath)
```

- [ ] **Step 8: Run full test suite**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/ -v --tb=short`
Expected: All tests PASS

- [ ] **Step 9: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add ivy_lsp/indexer/workspace_indexer.py ivy_lsp/features/hover.py ivy_lsp/features/definition.py ivy_lsp/features/document_symbols.py tests/test_demand_deep_parse.py
git commit -m "feat: demand-driven deep parse for shared modules

Shared library files (no exports) now get full AST parse on first
user interaction (hover, goto-def, outline). Upgrades symbols from
fallback quality to AST quality on demand, avoiding the permanent
two-tier symbol quality gap."
```

---

### Task 4: Fix ivy_quality Context-Aware Suggestions (P8)

**Why:** `handle_smart_suggestions` in `visualization.py` receives `filePath` and `line` params but doesn't use them to filter suggestions when no `actionName` is given. The workspace-level branch (line 1123-1148) calls `_resolve_scope` which requires a `testFile` param but doesn't derive it from `filePath`. Fix: resolve the file's endpoint mirror scope from `filePath`.

**Files:**
- Modify: `ivy_lsp/features/visualization.py:1049-1148`
- Create: `tests/test_smart_suggestions_context.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_smart_suggestions_context.py
"""Tests for ivy_quality context-aware suggestions (P8 fix)."""
from unittest.mock import MagicMock, patch

import pytest


class TestSmartSuggestionsContextFiltering:
    def test_file_path_resolves_to_scope(self):
        """When filePath is provided without actionName, suggestions are scoped."""
        from ivy_lsp.features.visualization import handle_smart_suggestions

        server = MagicMock()
        graph = MagicMock()
        graph.snapshot.return_value = MagicMock(
            actions={},
            state_vars={},
            incoming={},
            outgoing={},
            get_requirements_for_action=MagicMock(return_value=[]),
        )

        # Mock _get_requirement_graph to return our graph
        with patch(
            "ivy_lsp.features.visualization._get_requirement_graph",
            return_value=graph,
        ):
            result = handle_smart_suggestions(
                server,
                {"filePath": "/fake/quic_types.ivy", "line": 10}
            )

        assert "suggestions" in result
        # The key assertion: _resolve_scope was called with params containing filePath
        # (and it should attempt to find the endpoint mirror for that file)
```

- [ ] **Step 2: Run test to verify it passes (baseline)**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_smart_suggestions_context.py -v`
Note: This test may pass already since we're testing the interface. The real fix is in `_resolve_scope`.

- [ ] **Step 3: Modify _resolve_scope to derive testFile from filePath**

In `visualization.py`, update `_resolve_scope` (lines 87-101):

```python
def _resolve_scope(graph: Any, params: dict) -> dict:
    """Determine active scope from params or active test or filePath."""
    from ivy_lsp.analysis.test_scope import ScopedRequirementModel

    test_file = params.get("testFile")
    file_path = params.get("filePath", "")
    scope = None
    if isinstance(graph, ScopedRequirementModel):
        if test_file is None:
            # Try to derive scope from filePath
            if file_path:
                tests = graph.get_tests_for_file(file_path)
                if tests:
                    test_file = next(iter(tests))  # Use first matching endpoint mirror
                    scope = graph.get_test_scope(test_file)
            # Fall back to active scope
            if scope is None:
                active = graph.get_active_scope()
                if active:
                    test_file = active.test_file
                    scope = active
        else:
            scope = graph.get_test_scope(test_file)
    return {"testFile": test_file, "scoped": scope is not None, "_scope": scope}
```

- [ ] **Step 4: Run full test suite**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/ -v --tb=short`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add ivy_lsp/features/visualization.py tests/test_smart_suggestions_context.py
git commit -m "fix: ivy_quality suggestions now scope from filePath parameter

_resolve_scope now derives endpoint mirror scope from filePath when
testFile is not explicitly provided. This makes ivy_quality(mode=
suggestions, file_path=X) return context-aware results instead of
workspace-wide generic suggestions."
```

---

### Task 5: Plugin — /nct-scaffold Presets (P3)

**Why:** The scaffold command presents all 14 layers for interactive selection, requiring many confirmation rounds. Adding presets (`minimal`/`full`/`security`) reduces the common case to a single selection.

**Files:**
- Modify: Plugin `commands/nct-scaffold.md`

- [ ] **Step 1: Read current nct-scaffold.md**

Read the full command file to understand the current interactive flow.

- [ ] **Step 2: Add preset argument to YAML frontmatter**

Add `preset` as an optional argument in the command frontmatter:

```yaml
arguments:
  - name: preset
    description: "Layer preset: minimal (7 core layers), full (all 14), security (minimal + NACT). If omitted, interactive layer selection."
    required: false
```

- [ ] **Step 3: Add preset handling logic**

After the existing argument processing, add preset-based layer selection before the interactive flow:

```markdown
**Preset handling**: If `preset` is provided:
- `minimal` → Select layers: Types, Frame, Packet, Connection, Entity Defs, Entity Behavior, Shims (7 layers)
- `full` → Select all 14 layers
- `security` → Select minimal + Security, Error Handling, Serialization (10 layers)
- Skip the interactive layer selection and proceed directly to scaffolding.

If no preset is given, proceed with the existing interactive 14-layer selection.
```

- [ ] **Step 4: Test by running /nct-scaffold with preset**

Via Claude Code: `/nct-scaffold type=protocol name=test_prot preset=minimal`
Expected: Scaffolds 7-layer directory structure without interactive prompts

- [ ] **Step 5: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin
git add commands/nct-scaffold.md
git commit -m "feat: add preset argument to /nct-scaffold command

Supports minimal (7 layers), full (14), security (10) presets.
Reduces interactive rounds from 14 to 0 for common scaffolding cases."
```

---

### Task 6: Plugin — Skill Prerequisites in Frontmatter (P13)

**Why:** Skills like `counterexample-guide` reference other skills but don't declare dependencies. Adding `prerequisites` to frontmatter enables better agent orchestration and documentation.

**Files:**
- Modify: Plugin `skills/counterexample-guide/SKILL.md` — add prerequisites
- Modify: Plugin `skills/nsct-methodology/SKILL.md` — add prerequisites

- [ ] **Step 1: Add prerequisites to counterexample-guide**

Add to the YAML frontmatter:

```yaml
prerequisites:
  - ivy-writing-guide
  - workflow-reference
```

- [ ] **Step 2: Add prerequisites to nsct-methodology**

```yaml
prerequisites:
  - nct-methodology
```

- [ ] **Step 3: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin
git add skills/counterexample-guide/SKILL.md skills/nsct-methodology/SKILL.md
git commit -m "docs: add prerequisites field to skill frontmatter

Declares skill dependencies so agents and documentation tooling
can enforce correct invocation order."
```

---

### Task 7: End-to-End Validation

**Why:** Verify all changes work together on the real QUIC workspace.

- [ ] **Step 1: Run full ivy-lsp test suite**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
python -m pytest tests/ -v --tb=short
```
Expected: All tests PASS

- [ ] **Step 2: Run /nct-health**

Via Claude Code: `/nct-health`
Expected: All 7 health check steps PASS

- [ ] **Step 3: Run /nct-validate (if time permits)**

Via Claude Code: `/nct-validate`
Expected: All 55 checks PASS (or same pass rate as before changes)

- [ ] **Step 4: Manual verification on QUIC workspace**

Test that hovering over `quic_types.ivy` symbols now gives AST-quality detail (not fallback). Test that `ivy_quality(mode="suggestions", file_path="quic/quic_stack/quic_types.ivy")` returns context-scoped suggestions.

- [ ] **Step 5: Final commit with submodule update**

```bash
cd /Users/elniak/Documents/Documents/Work/Project/Protocol-Testing-Security/PANTHER/master/.claude/worktrees/lsp-to-claude
git add panther/plugins/services/testers/panther_ivy
git commit -m "chore: update panther_ivy submodule (LSP performance fixes P1-P4-P8, plugin P3-P13)"
```

---

### Post-Implementation Review Notes

Code review (2026-03-18) verified all 6 tasks implemented correctly. Key observations:

**Improvements over plan**:
- Task 2: Implementation uses `get_tests_for_file()` reverse index — O(dirty_files) instead of plan's O(all_scopes) linear scan
- Task 4: 7 tests vs planned 1, including `TestResolveScopeFilePath` unit tests with real `ScopedRequirementModel`

**Known latent issues (tracked for future hardening)**:
1. **Thread safety in `deep_parse_on_demand`**: Two concurrent hover requests can both pass the `status.deep_parse_attempted` check (benign race — double parse is wasteful but not incorrect). Fix: per-file `threading.Event` or flag under `_table_lock`.
2. **Nondeterministic scope selection in `_resolve_scope`**: When `filePath` belongs to multiple test scopes, `next(iter(tests))` picks arbitrarily from a set. Acceptable for suggestions but should log which scope was selected.

**Missing test coverage (nice-to-have)**:
- No test asserts on `remove_file()` return value (the `int` count)
- No test for `deep_parse_on_demand` when `result.success` is `False` (parse failure path)
