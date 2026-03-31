# Tier Analysis Path & Scope Unification Design

**Date**: 2026-03-30
**Status**: Draft
**Scope**: ivy-lsp submodule (`panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/`)
**Builds on**: `2026-03-30-ivy-lsp-mcp-reliability-fixes` Task 5 (remap_paths)

## Context

The ivy-lsp 3-tier analysis pipeline (T1: syntactic, T2: AST-enriched, T3: compiler) was built incrementally, introducing inconsistencies in path handling and scope usage.

**Prior fix (Task 5 of reliability plan)**: `remap_paths()` was added to `ScopedRequirementModel` to convert relative `_test_scopes` paths to absolute on pickle load. This fixed the primary symptom (`open(test_file)` failing on relative paths in bulk T3).

**Remaining gaps this design addresses**:

1. **RequirementNode paths still broken**: The pickle's `requirements` dict has build-machine absolute paths in `RequirementNode.file` and `.id` (`"filepath:line"` format). These are NOT remapped by `remap_paths()`, so `r.file in scope.include_closure` checks in `compute_requirement_diagnostics()` silently fail when build-machine paths differ from runtime paths.

2. **No centralized path utility**: Ad-hoc `os.path.join()` and `os.path.abspath()` scattered across components. `remap_paths` uses `os.path.join(base_dir, path)` directly — works but fragile.

3. **Scope filtering only wired to T1**: `_compute_test_scopes()` builds per-test `TestScope` objects, but only T1 requirement diagnostics partially use them. T2/T3 bulk analysis processes all files including orphans. Workspace diagnostics include all indexed files.

## Goals

1. Extend requirement graph path patching to cover `RequirementNode.file/.id`
2. Create a centralized `PathResolver` utility
3. Wire `_test_scopes` into bulk T1/T2 analysis (skip out-of-scope files)
4. Wire scope filtering into diagnostic computation (workspace + requirement level)
5. Normalize `RequirementNode.file` in index_builder before pickling
6. Keep offline index portable (relative paths in storage)

## Non-Goals

- Replacing the existing `remap_paths` — we extend it
- Full `IvyPath` newtype refactor
- Changing tier dispatch logic

---

## Design

### 1. PathResolver Utility

**File**: `ivy_lsp/infra/utils/path_normalize.py` (extend existing)

```python
class PathResolver:
    """Single source of truth for path canonicalization within a protocol workspace."""

    def __init__(self, protocol_dir: str) -> None:
        self._protocol_dir = os.path.realpath(os.path.abspath(protocol_dir))

    @property
    def protocol_dir(self) -> str:
        return self._protocol_dir

    def to_absolute(self, rel_path: str) -> str:
        """Convert offline-index relative path to canonical absolute."""
        if os.path.isabs(rel_path):
            return os.path.realpath(rel_path)
        return os.path.realpath(os.path.join(self._protocol_dir, rel_path))

    def to_relative(self, abs_path: str) -> str:
        """Convert absolute path to protocol-relative."""
        return os.path.relpath(abs_path, self._protocol_dir)

    def canonicalize(self, path: str) -> str:
        """Canonicalize any path (abs or rel) to resolved absolute form."""
        return os.path.realpath(path) if os.path.isabs(path) else self.to_absolute(path)
```

### 2. Extend remap_paths to Also Patch Requirements

**File**: `ivy_lsp/core/analysis/test_scope.py`

Extend the existing `remap_paths()` method (line 238) to also remap `requirements` dict entries. The method currently only handles `_test_scopes`. Add requirement patching:

```python
def remap_paths(self, base_dir: str) -> None:
    """Convert relative/stale paths in _test_scopes and requirements to absolute."""
    from ivy_lsp.infra.utils.path_normalize import PathResolver
    resolver = PathResolver(base_dir)

    with self._lock:
        # --- Existing: remap _test_scopes (unchanged) ---
        remapped: Dict[str, TestScope] = {}
        for path, scope in self._test_scopes.items():
            abs_path = resolver.canonicalize(path)
            if abs_path != path:
                scope = TestScope(
                    test_file=abs_path,
                    include_closure=frozenset(
                        resolver.canonicalize(f) for f in scope.include_closure
                    ),
                    exported_actions=scope.exported_actions,
                    imported_actions=scope.imported_actions,
                    tester_role=scope.tester_role,
                )
            remapped[abs_path] = scope
        self._test_scopes = remapped

        # Rebuild file_to_tests
        self._file_to_tests.clear()
        for test_file, scope in self._test_scopes.items():
            for f in scope.include_closure:
                self._file_to_tests[f].add(test_file)
        self._scope_cache.clear()

        # --- NEW: remap RequirementNode paths ---
        patched_reqs = {}
        for old_id, node in self.requirements.items():
            node.file = resolver.canonicalize(node.file)
            # Patch ID format "filepath:line"
            parts = old_id.split(":")
            if len(parts) >= 2:
                parts[0] = resolver.canonicalize(parts[0])
                node.id = ":".join(parts)
            patched_reqs[node.id] = node
        self.requirements = patched_reqs

        # --- NEW: remap PropertyNode paths (same ID format) ---
        patched_props = {}
        for old_id, node in self.properties.items():
            node.file = resolver.canonicalize(node.file)
            parts = old_id.split(":")
            if len(parts) >= 2:
                parts[0] = resolver.canonicalize(parts[0])
                node.id = ":".join(parts)
            patched_props[node.id] = node
        self.properties = patched_props

        # --- NEW: remap ActionNode/StateVarNode .file ---
        for collection in (self.actions, self.state_vars):
            for node in collection.values():
                if hasattr(node, 'file') and node.file:
                    node.file = resolver.canonicalize(node.file)

        # --- NEW: remap edge IDs ---
        def _patch_id(node_id: str) -> str:
            parts = node_id.split(":")
            if len(parts) >= 2:
                parts[0] = resolver.canonicalize(parts[0])
                return ":".join(parts)
            return node_id

        self.edges = [(_patch_id(src), etype, _patch_id(tgt)) for src, etype, tgt in self.edges]
        self._edge_set = set(self.edges)
        self._rebuild_adjacency()

        self._version += 1
```

Note: `actions`, `state_vars`, `properties`, `edges` are actually empty in offline-built pickles (index_builder only adds requirements + test scopes). But patching them is defensive — costs nothing and handles future changes.

### 3. Normalize RequirementNode.file in Index Builder

**File**: `ivy_lsp/lsp/index_builder.py` (~line 207)

Override `RequirementNode.file` with the relative path before serialization:

```python
reqs, _writes = extract_requirements_light(source, filepath)
for r in reqs:
    r.file = rel_path  # Override build-machine absolute with protocol-relative
requirements_map[rel_path] = [
    {"id": r.id, "kind": r.kind, ...}
    for r in reqs
]
```

Also normalize `r.id` (which has format `"filepath:line"`):

```python
for r in reqs:
    r.file = rel_path
    # Normalize id from "abs_filepath:line" to "rel_path:line"
    parts = r.id.split(":")
    if len(parts) >= 2:
        parts[0] = rel_path
        r.id = ":".join(parts)
```

This makes the pickle predictable: all paths are relative. The loader's `remap_paths` converts them to current-machine absolute.

### 4. Scope-Aware Analysis Pipeline

**File**: `ivy_lsp/core/semantic/analysis_pipeline.py`

```python
class AnalysisPipeline:
    def __init__(self, ...) -> None:
        ...
        self._scope_provider = None

    def set_scope_provider(self, provider: Any) -> None:
        """Set the ScopedRequirementModel for scope-aware bulk filtering."""
        self._scope_provider = provider

    def _files_in_any_scope(self, filepaths: List[str]) -> List[str]:
        """Filter to files in at least one test scope's include_closure."""
        if self._scope_provider is None:
            return filepaths
        return [f for f in filepaths if self._scope_provider.get_tests_for_file(f)]
```

Apply in `run_bulk_t1_t2()`:
```python
remaining = self._files_in_any_scope(
    [f for f in filepaths if f not in self._tier2_files]
)
```

`run_bulk_tier3()` already scoped. Single-file analysis unchanged.

### 5. Wire Scope Provider

**File**: `ivy_lsp/lsp/server_setup.py`

In `_setup_analysis_pipeline()`:
```python
self._analysis_pipeline.set_scope_provider(self._indexer.requirement_graph)
```

### 6. Scope-Filtered Diagnostics

#### 6a. `compute_requirement_diagnostics()` — Complete scope awareness

**File**: `ivy_lsp/lsp/diagnostics/compute.py`

Already uses `graph.get_active_scope()` for unmonitored action hints (lines 180-192). Extend:

- **Include chain propagation** (lines 115-177): When `active_scope` is set, only count inherited requirements from files within `active_scope.include_closure`
- **High-impact state variables** (lines 226-249): When `active_scope` is set, only count readers within `active_scope.include_closure`

#### 6b. `compute_diagnostics()` — Thread scope context

Add `active_scope: Optional[TestScope] = None` parameter. Pass to sub-functions.

#### 6c. `workspace_diagnostic()` in publisher.py — Skip orphan files

```python
graph = getattr(server.indexer, "requirement_graph", None)
for fp in server.indexer.get_all_ivy_file_paths():
    if graph and not graph.get_tests_for_file(fp):
        continue
    uris.add(f"file://{fp}")
```

#### 6d. Single-file diagnostics — No change

---

## Files to Modify

| Step | File | Change |
|------|------|--------|
| 1 | `ivy_lsp/infra/utils/path_normalize.py` | Add `PathResolver` class |
| 2 | `ivy_lsp/core/analysis/test_scope.py` | Extend `remap_paths()` to also patch requirements, properties, actions, state_vars, edges |
| 3 | `ivy_lsp/lsp/index_builder.py` | Normalize `req.file` and `req.id` to relative before serialization |
| 4 | `ivy_lsp/core/semantic/analysis_pipeline.py` | Add `set_scope_provider()`, `_files_in_any_scope()`, apply in `run_bulk_t1_t2()` |
| 5 | `ivy_lsp/lsp/server_setup.py` | Wire `set_scope_provider()` in `_setup_analysis_pipeline()` |
| 6a | `ivy_lsp/lsp/diagnostics/compute.py` | Extend scope filtering in `compute_requirement_diagnostics()` |
| 6b | `ivy_lsp/lsp/diagnostics/compute.py` | Add `active_scope` param to `compute_diagnostics()` |
| 6c | `ivy_lsp/lsp/diagnostics/publisher.py` | Filter workspace diagnostic URIs by scope |

## Implementation Order

```
Step 1 (PathResolver)
    │
    ├──→ Step 2 (extend remap_paths) ──→ Step 5 (wire scope provider)
    │
    └──→ Step 3 (index_builder normalization)

Step 4 (pipeline scope filtering) ──→ Step 5 (wire scope provider)

Step 6a/6b/6c (diagnostic filtering) — independent of Steps 1-3
```

Steps 1, 4, and 6 can proceed in parallel. Step 2 depends on 1. Step 5 integrates 2 and 4.

## Verification

1. **Rebuild offline index**: `ivy-lsp index --force` on QUIC protocol directory (one-time after deploying)
2. **Start LSP**: Verify no path-related errors in logs during startup
3. **Check requirement graph**: `graph.requirements` has current-machine absolute paths
4. **Check test scopes**: `graph._test_scopes` keys are absolute paths
5. **Bulk analysis**: Confirm bulk T1+T2 logs show fewer files (orphan files skipped)
6. **Workspace diagnostics**: Orphan files not included
7. **Requirement diagnostics**: Include chain propagation respects active scope
8. **Run existing tests**: `pytest tests/ -x` in ivy-lsp directory
