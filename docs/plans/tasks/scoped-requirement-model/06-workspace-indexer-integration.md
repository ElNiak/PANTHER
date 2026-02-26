# Task 6: WorkspaceIndexer Integration

**Status:** pending
**Depends on:** Task 1, Task 2, Task 3, Task 4, Task 5

**Files:**
- Modify: `ivy_lsp/indexer/workspace_indexer.py`
- Create: `tests/test_workspace_indexer_scoping.py`

**This is the wiring task** -- connects all the new data structures into the existing indexing pipeline.

---

## Step 1: Write the failing test

```python
# tests/test_workspace_indexer_scoping.py
"""Tests for WorkspaceIndexer export/import and test scope integration."""
import pytest
from unittest.mock import MagicMock
from ivy_lsp.analysis.test_scope import ScopedRequirementModel


class TestIndexerUseScopedModel:
    def test_requirement_graph_is_scoped_model(self):
        from ivy_lsp.indexer.workspace_indexer import WorkspaceIndexer
        parser = MagicMock()
        resolver = MagicMock()
        indexer = WorkspaceIndexer("/tmp/workspace", parser, resolver)
        assert isinstance(indexer._requirement_graph, ScopedRequirementModel)

    def test_file_export_imports_dict_exists(self):
        from ivy_lsp.indexer.workspace_indexer import WorkspaceIndexer
        parser = MagicMock()
        resolver = MagicMock()
        indexer = WorkspaceIndexer("/tmp/workspace", parser, resolver)
        assert hasattr(indexer, "_file_export_imports")
        assert isinstance(indexer._file_export_imports, dict)
```

## Step 2: Run test to verify it fails

```bash
python -m pytest tests/test_workspace_indexer_scoping.py -v
```

Expected: FAIL (RequirementGraph is not ScopedRequirementModel)

## Step 3: Write minimal implementation

Changes to `ivy_lsp/indexer/workspace_indexer.py`:

**1. Add imports** (at top, after existing imports):

```python
from ivy_lsp.analysis.test_scope import ExportImportInfo, ScopedRequirementModel
```

**2. In `__init__`**, change:

```python
# OLD:
self._requirement_graph = RequirementGraph()

# NEW:
self._requirement_graph = ScopedRequirementModel()
self._file_export_imports: Dict[str, ExportImportInfo] = {}
```

**3. In `index_workspace`**, change:

```python
# OLD:
self._requirement_graph = RequirementGraph()

# NEW:
self._requirement_graph = ScopedRequirementModel()
self._file_export_imports = {}
```

And after `self._wire_coverage_edges()` add:

```python
self._compute_test_scopes()
```

**4. In `_index_single_file`**, after `self._extract_file_requirements(...)` add:

```python
self._extract_file_exports_imports(filepath, result, source)
```

**5. Add new methods:**

```python
def _extract_file_exports_imports(
    self, filepath: str, result: Any, source: str
) -> None:
    """Extract export/import declarations from a single file."""
    try:
        if result.success:
            from ivy_lsp.analysis.requirement_extractor import extract_exports_imports_full
            info = extract_exports_imports_full(result.ast, filepath, source)
        else:
            from ivy_lsp.analysis.light_mode_extractor import extract_exports_imports_light
            info = extract_exports_imports_light(source, filepath)
        self._file_export_imports[filepath] = info
    except Exception:
        logger.warning(
            "Export/import extraction failed for %s", filepath, exc_info=True
        )

def _compute_test_scopes(self) -> None:
    """Compute TestScope for each file that has exports."""
    from ivy_lsp.analysis.test_scope import TestScope, detect_test_role

    for filepath, info in self._file_export_imports.items():
        if not info.has_exports:
            continue
        closure = {filepath}
        closure |= self._include_graph.get_transitive_includes(filepath)
        all_exports: set = set()
        all_imports: set = set()
        for f in closure:
            f_info = self._file_export_imports.get(f)
            if f_info:
                all_exports.update(f_info.exports)
                all_imports.update(f_info.imports)
        role = detect_test_role(frozenset(closure))
        scope = TestScope(
            test_file=filepath,
            include_closure=frozenset(closure),
            exported_actions=frozenset(all_exports),
            imported_actions=frozenset(all_imports),
            tester_role=role,
        )
        self._requirement_graph.register_test_scope(scope)
```

**6. In `reindex_file`**, after `self._requirement_graph.remove_file(abs_path)` add:

```python
self._requirement_graph.invalidate_file(abs_path)
self._file_export_imports.pop(abs_path, None)
```

And after `self._wire_requirement_graph()` add:

```python
self._compute_test_scopes()
```

## Step 4: Run test to verify it passes

```bash
python -m pytest tests/test_workspace_indexer_scoping.py -v
```

Expected: PASS

## Step 5: Commit

```bash
git add ivy_lsp/indexer/workspace_indexer.py tests/test_workspace_indexer_scoping.py
git commit -m "feat(indexer): integrate ScopedRequirementModel and export/import extraction"
```
