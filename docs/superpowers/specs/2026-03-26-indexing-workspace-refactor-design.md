# Design: ivy-lsp & panther-ivy-plugin Indexing and Workspace Management Refactor

**Date**: 2026-03-26
**Status**: Draft
**Author**: Claude (with ElNiak review)
**Branch**: `refactor/indexing-workspace-management` (TBD)

## 1. Problem Statement

The ivy-lsp LSP server and panther-ivy-plugin MCP integration have grown organically, accumulating performance bottlenecks, state management fragmentation, and dead code.

### 1.1 Indexing Performance

`SemanticModel` (343 lines, `core/semantic/model.py`) stores all semantic nodes but lacks a by-name index. Every `textDocument/definition`, `textDocument/hover`, and `textDocument/completion` request performs O(N) scans across ALL nodes. The TODO at `definition.py:152` acknowledges this:

```python
# TODO: add a by-name index to SemanticModel to avoid O(N) scans here
# and in hover.py (_enrich_with_semantic_model).
```

Additionally, Tier 2 (PLY-lexer, `tiered_extractor.py:396-448`) and Tier 3 (regex, `tiered_extractor.py:578-642`) parsers contain structurally identical reference extraction loops (~100 lines each) using the same `_CALL_STMT_RE`, `_INSTANCE_RE`, `_MONITOR_RE` patterns.

### 1.2 Session/State Fragmentation

Session ID is resolved in **5 divergent code paths** with inconsistent priority ordering:

| Code Path | Priority Order | Date-Prefix |
|-----------|---------------|-------------|
| `detect-ivy-workspace.sh:23-37` | hook_payload > CLAUDE_SESSION_ID > CLAUDE_CODE_SESSION_ID > IVY_SESSION_ID | Applied, then written to /tmp |
| `start-ivy-server.sh:70-82` | IVY_SESSION_ID > CLAUDE_SESSION_ID > CLAUDE_CODE_SESSION_ID > /tmp file | Not applied (reads already-prefixed) |
| `log_event.py:45-68` | IVY_SESSION_ID > /tmp file > raw_session_id > "unknown" | Not applied |
| `check-workspace-scope.py:137-142` | hook_payload > IVY_SESSION_ID > "unknown" | Not applied |
| `session.py:65-82` | IVY_SESSION_ID > /tmp file > "unknown" | Not applied |

`_workspace_hash()` (SHA-256 first 12 hex chars) is duplicated in 5+ locations across both Python modules and bash scripts.

State files are scattered across `/tmp/` with inconsistent cleanup:
- `/tmp/ivy-session-{ws_hash}.id` — session ID persistence (no TTL)
- `/tmp/ivy-inferred-protocol-{session_id}.json` — progressive narrowing (never cleaned)
- `/tmp/ivy-mcp-health-state.json` — circuit breaker (no file locking, race condition)
- `/tmp/ivy-lsp-pids/` — PID tracking (cleaned on startup and session end)
- `/tmp/ivy-mcp-{ws_hash}.port` — MCP port discovery (cleaned on shutdown)

### 1.3 Dead Code and Bugs

- `ivy_quality` MCP tool: `file_path` parameter silently ignored (missing `"file"` key on `state_var` and `missing_guard` suggestion dicts in `viz_suggestions.py`)
- Legacy in-process compilation paths in `compiler_adapter.py` (triggered only when `CompilerManager` is None)
- `start-ivy-tools.sh`: 3-line backward-compat wrapper
- Legacy flat keys in `ivy_capabilities` response
- `check_lsp_log.py`: Uses `systemMessage` output format instead of `hookSpecificOutput.additionalContext`

### 1.4 What Works Well (Preserved)

- Zero data duplication between LSP and MCP (shared via `ToolContext.from_lsp_server()`)
- Single `WorkspaceContext` as source of truth for all protocol indexes
- `FlatStagingStrategy` symlink system for Ivy's flat-directory parser requirement
- All hook scripts exist and are functional
- `IVY_LSP_DEV_ROOT` is implemented in `workspace-common.sh:85-87`

## 2. NCT Methodology Constraints

In NCT methodology, a **workspace** is defined by endpoint mirror test entry points. Master test files (e.g., `quic_client_test.ivy`) include all specification requirements for a given mirror via transitive `include` closure.

**Role inversion**: `quic_client_test.ivy` includes `ivy_quic_shim_server` because Ivy acts as the server while testing a client IUT.

**Staging requirement**: Ivy's parser/lexer requires all included files in a flat directory. The `FlatStagingStrategy` creates symlinks to satisfy this constraint. **Staging is required during indexing** (not just compilation) because `IncludeResolver.resolve()` uses `_active_layers` to resolve include paths.

## 3. Architecture Decisions

### 3.1 Influenced by Industry Research

| Pattern | Source | Application |
|---------|--------|-------------|
| Multi-index symbol table | rust-analyzer, OLS | `_nodes_by_name` + `_nodes_by_file` + `_nodes_by_type` (1A) |
| Scope projection | Pyright execution environments | Query-time visibility filter by workspace layers (1E) |
| Cut-off optimization | rust-analyzer salsa framework | Skip downstream re-wiring when exports unchanged (1F) |
| Version counter | clangd MergedIndex freshness | Monotonic version for MCP cache invalidation (1G) |
| SCIP-style offline index | Sourcegraph SCIP | Existing `.ivy-index/` already follows this pattern |

### 3.2 Key Design Decisions

1. **Extend `session.py`, not create `state_resolver.py`** — The existing `infra/observability/session.py` already contains `get_session_id()`, `resolve_session_log_dir()`, and `_workspace_hash()`. Extending it avoids creating a parallel module.

2. **Scope projection is query-time only** — Staging directories must still be rebuilt for indexing because `IncludeResolver.resolve()` depends on `_active_layers`. The projection adds an O(1) visibility filter on query results, not a staging replacement.

3. **Cut-off targets `_wire_requirement_graph()` and `_compute_test_scopes()`** — There is no `_propagate_to_dependents` method. The actual expensive operations after `reindex_file()` in `scope_manager.py` are requirement graph re-wiring and test scope recomputation.

4. **Session ID priority chain matches boot hook** — `detect-ivy-workspace.sh` puts hook_payload first (step 1), IVY_SESSION_ID last (step 4). The canonical resolver preserves this ordering.

5. **Plugin delegates to ivy-lsp** — `workspace-common.sh` calls ivy-lsp's Python functions via `PYTHONPATH="$IVY_LSP_SRC" python3 -c "..."` with bash fallback for environments without ivy-lsp.

## 4. Detailed Design

### 4.1 Workstream 1: Indexing Performance & Consolidation

#### 4.1.1 SemanticModel `_nodes_by_name` Index (1A)

Add `_nodes_by_name: Dict[str, List[Any]] = defaultdict(list)` to `SemanticModel.__init__()`.

**Mutation methods** (all under existing `self._lock`):
- `add_node()`: Check for existing node with same `id` but different `name` — remove old name entry first (replace semantics). Then `_nodes_by_name[name].append(node)` if `hasattr(node, 'name')`.
- `remove_file()`: For each removed node, remove from `_nodes_by_name[node.name]`.
- `update_file()`: Phase 1 (remove old) cleans name index. Phase 2 (add new) must place name-indexing AFTER the tier-check at line 186-187 (`continue` when existing tier is higher) — do NOT index before the check or stale entries accumulate.
- `merge_from()`: Inline name indexing alongside existing inline mutations.
- `__setstate__()`: Rebuild `_nodes_by_name` from `_nodes.values()` if field is missing (pickle backward compat).

**New query**: `get_nodes_by_name(name: str) -> List[Any]` — O(1) lookup under `self._lock`.

**Consumer updates** (7+ callsites):
```
definition.py:152-163  → semantic_model.get_nodes_by_name(word)
hover.py               → semantic_model.get_nodes_by_name(word)
call_hierarchy.py      → semantic_model.get_nodes_by_name(name)
completion.py:552      → semantic_model.get_nodes_by_name(name)
model_builder.py       → Replace local type_by_name/symbol_by_name dicts
```

#### 4.1.2 SymbolTable `_by_kind` Index (1B)

Add `_by_kind: Dict[SymbolKind, List[IvySymbol]] = defaultdict(list)` to `SymbolTable.__init__()`. Follow existing `_by_name`/`_by_file` pattern. ~20 lines.

#### 4.1.3 Shared Reference Extraction (1C)

Create `core/parsing/reference_extraction.py` (~100 lines):
```python
def extract_references_regex(
    source: str, filepath: str, symbols: List[IvySymbol]
) -> List[SymbolReference]:
    """Extract call, instance, and monitor references using regex patterns.

    Args:
        symbols: Either Tier 2 declaration_symbols (PLY-lexer, more accurate)
                 or Tier 3 regex-extracted symbols (flat, less accurate).
                 Both work because the extraction only needs symbol names,
                 kinds, and line ranges.
    """
```

Move `_CALL_STMT_RE`, `_INSTANCE_RE`, `_MONITOR_RE` patterns from `tiered_extractor.py`. Both `_try_lexer()` and `_try_regex()` import and call `extract_references_regex()`.

#### 4.1.4 Include Resolver Chain (1D)

Refactor `include_resolver.py:resolve()` from 120+ line monolith into 4 chained sub-methods:
1. `_resolve_same_dir(fname, from_file)`
2. `_resolve_via_layers(fname, from_file)`
3. `_resolve_via_flat_staging(fname)`
4. `_resolve_via_stdlib(fname)`

Internal refactor, no behavior change. ~20-line main method.

#### 4.1.5 Scope Projection (1E)

```python
@dataclass
class ScopeProjection:
    """Query-time visibility filter by workspace layers.

    Does NOT replace staging (staging still needed for include resolution
    during indexing). Only filters symbol/node query results.
    """
    active_layers: Set[str]
    file_to_layer: Dict[str, str]

    def is_visible(self, filepath: str) -> bool:
        layer = self.file_to_layer.get(filepath)
        return layer is None or layer in self.active_layers
```

`set_active_workspace()` updates projection immediately (O(1)), triggers staging rebuild asynchronously for indexing.

**Thread safety**: `ScopeProjection` is an immutable frozen dataclass. On workspace switch, a new instance is created and assigned atomically via `self._projection = new_projection`. No lock needed — reads always see a consistent snapshot.

#### 4.1.6 Cut-off Optimization (1F)

In `scope_manager.py:reindex_file()`, after symbol extraction:
1. Compute: `sig = hash(tuple(sorted((s.name, s.kind, s.detail) for s in symbols)))`
2. Compare with `self._file_signature_hashes.get(filepath)`
3. If equal: skip `_wire_requirement_graph()` and `_compute_test_scopes()`
4. If different: proceed as before, store new hash

#### 4.1.7 Version Counter (1G)

Add `self._version: int = 0` to `SemanticModel.__init__()`. Increment in `add_node()`, `remove_file()`, `update_file()`, `merge_from()`. Expose via `@property version`. MCP `ToolContext` adds `get_index_version()` callable.

### 4.2 Workstream 2: Session/State Separation

#### 4.2.1 Extend `session.py` (2A)

Add to `infra/observability/session.py`:

```python
def resolve_session_id(hook_payload: dict | None = None) -> str:
    """Canonical session ID resolution. Matches detect-ivy-workspace.sh boot order.

    Priority:
    1. hook_payload["session_id"] (from Claude hook stdin)
    2. CLAUDE_SESSION_ID env
    3. CLAUDE_CODE_SESSION_ID env
    4. IVY_SESSION_ID env (already date-prefixed by boot hook)
    5. /tmp/ivy-session-{ws_hash}.id file
    6. "unknown"

    Date-prefix note: Steps 1-3 return RAW session IDs. The boot hook
    applies YYYY-MM-DDTHHMM-{id} prefix before writing to /tmp and env.
    """
```

Make `_workspace_hash()` public as `workspace_hash()`. Update all 4 Python duplicates to import.

**Deprecation**: The existing `get_session_id()` function is **deprecated** in favor of `resolve_session_id()`. Callers that only need env-var resolution (no hook_payload context) should call `resolve_session_id(hook_payload=None)` — the hook_payload step is skipped and the function falls through to CLAUDE_SESSION_ID / IVY_SESSION_ID / /tmp file. Keeping both functions creates confusion about which to use. Migration: update all callers of `get_session_id()` to `resolve_session_id()`, then remove `get_session_id()`.

#### 4.2.2 Consumer Updates (2B)

**panther-ivy-plugin files**:

1. `scripts/workspace-common.sh`: Add `resolve_session_id()` bash function that calls `PYTHONPATH="$IVY_LSP_SRC" python3 -c "from ivy_lsp.infra.observability.session import resolve_session_id; print(resolve_session_id())"` with bash fallback for environments without ivy-lsp.
2. `scripts/start-ivy-server.sh` (lines 70-82): Replace inline session ID chain with `resolve_session_id` call from workspace-common.sh.
3. `hooks/scripts/check-workspace-scope.py` (lines 137-142): Import `resolve_session_id` from `ivy_lsp.infra.observability.session` (with try/except fallback to inline logic).
4. `hooks/scripts/observability/log_event.py` (lines 45-68): Import `resolve_session_id` from `ivy_lsp.infra.observability.session` (with try/except fallback). Remove local `_resolve_session_id()` and `_workspace_hash()`.
5. `hooks/scripts/observability/obs_session_end.py` (line 12): Currently imports `_resolve_session_id` and `_resolve_log_dir` from `log_event.py`. After step 4 removes these from `log_event.py`, update to import directly from `ivy_lsp.infra.observability.session` (or keep importing from `log_event.py` which now re-exports the canonical version).

**ivy-lsp files**:

6. `mcp/sidecar.py`: Replace local `_workspace_hash()` (line 46) with `from ivy_lsp.infra.observability.session import workspace_hash`.
7. `mcp/client.py`: Replace local `workspace_hash()` (line 53) with re-export from `session`.

#### 4.2.3 State Migration (2C-2F)

- Progressive narrowing: `/tmp/ivy-inferred-protocol-*.json` → `.observability/sessions/{id}/inferred-protocol.json`
- Health state: Add `fcntl.flock()`, move alongside progressive narrowing
- Session GC: `find ... -mtime +7 -exec rm -rf {} +` in SessionStart hook
- Update `stop-session-summary.sh` fallback path

### 4.3 Workstream 3: Bug Fixes & Dead Code

#### 4.3.1 `ivy_quality` Fix (3A)

Add `"file": sv.file` to `state_var` and `missing_guard` suggestion dicts in `viz_suggestions.py`. The `sv` object is a state var node (from `snap.get_state_vars_written_by_action()`), NOT an action node.

#### 4.3.2 Dead Code Removal (3B)

1. Legacy in-process compilation in `compiler_adapter.py` (lines 112-163, 208-254 including `_on_done` callback)
2. `start-ivy-tools.sh` backward-compat wrapper
3. Legacy flat keys in `ivy_capabilities` + formatter fallback
4. `interaction-checkpoint-test.py` orphaned in hooks/scripts/
5. `check_lsp_log.py` output format bug (systemMessage → hookSpecificOutput)

#### 4.3.3 Documentation Updates (3C)

Update `/tmp/` path references in: CLAUDE.md, nct-health.md, nct-validate.md, nct-observability.md, README.md.

## 5. Implementation Order

| Phase | Items | Dependencies | Parallelizable With |
|-------|-------|-------------|-------------------|
| 1 | 1A (name index) + 1G (version counter) | None | Phase 3, 6 |
| 2 | 1B (kind index) + 1C (reference extraction) | None | Phase 1, 3, 6 |
| 3 | 2A (extend session.py) + 2B (consumers) | None | Phase 1, 2, 6 |
| 4 | 1E (scope projection) + 1F (cut-off) | Phase 1 stable | Phase 5, 6 |
| 5 | 2C + 2D + 2E + 2F (state migration) | Phase 3 | Phase 4, 6 |
| 6 | 3A (bug fix) + 3B (dead code) + 3C (docs) | None | All |
| 7 | 1D (resolver refactor) | None | All |

## 6. Verification

### 6.1 Automated Tests

**Existing suites** (must pass after each phase):
```bash
cd .../ivy-lsp && python -m pytest tests/ -x -v
cd .../panther-ivy-plugin && python -m pytest tests/ -v
```

**New/extended tests**:

| Item | Test | Verifies |
|------|------|----------|
| 1A | Extend `test_semantic_model.py` | `get_nodes_by_name()`, replace semantics, pickle compat |
| 1B | Extend `test_symbol_table*.py` | `symbols_by_kind()`, remove_file cleanup |
| 1C | Extend `test_reference_extraction.py` | Extracted function matches inlined behavior |
| 1E | Extend `test_active_workspace.py` | `ScopeProjection.is_visible()` |
| 1F | New in scope_manager tests | Cut-off skips re-wiring when signature unchanged |
| 1G | Extend `test_semantic_model.py` | Version increments on mutation |
| 2A | Extend `test_session_observability.py` | Priority chain, workspace_hash parity |
| 2D | New concurrency test | `fcntl.flock` prevents corruption |
| 3A | Extend MCP tool tests | `ivy_quality(file_path=...)` filtered |

**Tests needing updates**: `test_tiered_extractor.py` (moved imports), `test_observability.py` (hardcoded /tmp path), `test_semantic_model_merge.py` (exercise name index).

### 6.2 Manual Verification

1. Open workspace, `/set-workspace quic`, verify session ID consistent across logs
2. `ivy_quality(file_path="file.ivy", mode="suggestions")` returns filtered results
3. After 2+ sessions, `.observability/sessions/` prunes old entries
4. Load old `semantic_model.pickle.gz` after upgrade — verify backward compat

## 7. Known Limitations

1. **Bash/Python parity**: 2 session ID paths remain (canonical Python + bash fallback). Recommend CI parity test.
2. **`/tmp/ivy-session-{ws_hash}.id`**: Stays in /tmp — IPC channel between SessionStart hook and server launcher, must survive process restarts.
3. **`/tmp/ivy-mcp-{ws_hash}.port`**: Stays in /tmp — cross-process port discovery. Existing `_remove_port_file` atexit handler is sufficient.
4. **Standalone `--mcp` mode**: Not deprecated in this refactoring.
5. **Legacy protocol list** `["quic", "minip", "apt"]` in `detection.py:266`: Not addressed.

## 8. File Manifest

### Creates (1 file)
- `IVY-LSP/core/parsing/reference_extraction.py` (~100 lines)

### Modifies — ivy-lsp (19 files)
- `core/semantic/model.py`, `core/semantic/model_builder.py`
- `core/parsing/symbols.py`, `core/parsing/tiered_extractor.py`
- `core/indexer/include_resolver.py`, `core/indexer/scope_manager.py`, `core/indexer/workspace_indexer.py`
- `core/workspace/active_workspace.py`
- `core/adapters/compiler_adapter.py`
- `infra/observability/session.py`
- `mcp/context.py`, `mcp/sidecar.py`, `mcp/client.py`, `mcp/tools/analysis.py`
- `lsp/navigation/definition.py`, `lsp/navigation/hover.py`, `lsp/navigation/call_hierarchy.py`
- `lsp/completion.py`, `lsp/viz_suggestions.py`

### Modifies — panther-ivy-plugin (14 files)
- `scripts/workspace-common.sh`, `scripts/start-ivy-server.sh`
- `hooks/scripts/detect-ivy-workspace.sh`, `hooks/scripts/check-workspace-scope.py`
- `hooks/scripts/check-mcp-health.py`, `hooks/scripts/stop-session-summary.sh`
- `hooks/scripts/observability/log_event.py`, `hooks/scripts/observability/obs_session_end.py`
- `hooks/scripts/observability/obs_post_tool_use_failure.py`, `hooks/scripts/observability/check_lsp_log.py`
- `CLAUDE.md`, `commands/nct-health.md`, `commands/nct-validate.md`, `commands/nct-observability.md`

### Removes/Moves (3 items)
- Remove `scripts/start-ivy-tools.sh` (backward-compat wrapper)
- Move `hooks/scripts/interaction-checkpoint-test.py` to `tests/`
- Remove legacy flat keys from `mcp/tools/analysis.py:258-261`
