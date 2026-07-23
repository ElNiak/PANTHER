# Unified Workspace & Offline Pre-Indexing Design

**Date**: 2026-03-20
**Status**: Draft
**Scope**: ivy-lsp indexing, MCP/LSP workspace coherence, per-test scope views

## Problem Statement

The ivy-lsp system has three separate, incoherent workspace initialization paths:

1. **SessionStart hook** (`detect-ivy-workspace.sh`) — bash-based detection, writes `IVY_WORKSPACE_ROOT` to env, outputs context to Claude
2. **LSP server** (`.lsp.json` + `server.py`) — hardcoded env vars (`IVY_LSP_INCLUDE_PATHS`, `IVY_LSP_WORKSPACE_HINT`), builds full indexer from scratch (2-4 min cold start)
3. **MCP server** (`start-ivy-tools.sh` + `mcp_server.py`) — re-detects workspace from `$PWD`, no indexer, stateless `_validate_path()` per tool call

This causes:
- **Redundant detection**: Three implementations of the same workspace-finding logic (two in bash, one in Python)
- **MCP blindness**: MCP tools have no access to the symbol table, include graph, layer-aware staging, or test scope data that LSP maintains
- **Slow cold starts**: LSP rebuilds the full index from scratch every session (~2-4 min for semantic model)
- **No per-test scoping**: Tools operate on the full workspace even when the user is working on a single test's file set
- **Incomplete model brittleness**: New protocols being built from scratch have no index, no scopes, and limited tool support

## Architecture

Three layers, each with a single responsibility:

### Layer 1 — Offline Index Builder (`ivy-lsp index`)

A CLI command that pre-computes a `.ivy-index/` directory at each protocol root. Uses the full Ivy parser (Tier 1) by default. Produces AST-quality symbols, include graphs, per-test scope closures, and requirement annotations.

**Trigger**: Manual CLI command (Stage A). Designed to evolve toward git-event (B), session-start auto-rebuild (C), and file watcher (D) without changing the index format.

### Layer 2 — Unified Workspace Context (`WorkspaceContext`)

A single Python class that loads `.ivyworkspace` + all per-protocol `.ivy-index/` directories. Replaces the three separate detection paths. Consumed identically by LSP init, MCP init, and SessionStart hook.

### Layer 3 — Session Overlay

An in-memory dirty layer that tracks file creates/edits/deletes during a session. Overlays on top of the cached index. Supports multiple concurrent `TestScopeView` filters for different agents working on different test scopes simultaneously.

### Data Flow

```
Offline:
  ivy-lsp index → protocol-testing/<prot>/.ivy-index/ (per protocol)

Session start:
  .ivyworkspace + .ivy-index/* → WorkspaceContext
    ├→ LSP server (loads index, skips fast-index, deep parse only for upgrades)
    ├→ MCP server (loads same index, tools use it for resolution + scoping)
    └→ SessionStart hook (reports workspace info + staleness to Claude)

During session:
  File edits → SessionOverlay → WorkspaceContext queries return merged results
  Multiple views:
    Agent A → TestScopeView("quic_server_test_reset") → 37 files
    Agent B → TestScopeView("apt_quic_attacker_test") → 52 files
    Both read from same WorkspaceContext with different scope filters
```

## Index Format

### Protocol Definition & Isolation Model

A "protocol" for indexing purposes is a **top-level directory** under `protocol-testing/` (e.g., `quic/`, `apt/`, `bgp/`, `coap/`). Each protocol owns its own `.ivy-index/` containing only files physically under that directory.

**Protocols are self-contained. There are no cross-protocol file references.**

APT is a complete parallel architecture that maintains its own **forked copies** of base protocol models:
- `protocol-testing/apt/apt_protocols/quic/` has 184 `.ivy` files — forked copies of base QUIC with modifications (FSM omissions, type redefinitions, attack entity additions)
- APT test files use ONLY APT-local includes — `include quic_types` resolves to APT's fork (`apt_protocols/quic/quic_stack/quic_types.ivy`), never to `protocol-testing/quic/quic_stack/quic_types.ivy`
- `apt_shim.ivy` bridges `apt_types` and the forked `quic_types` within APT — both are APT-internal files

This mirrors PANTHER's Docker execution model: each container mounts only ONE protocol tree, so there is no cross-protocol mixing at compilation time. The offline index must respect this isolation.

**Consequences for indexing:**
- Each `.ivy-index/` is truly independent — no `cross_protocol_deps` field needed
- Files with the same basename across protocols (e.g., `quic_types.ivy` in both `quic/` and `apt/`) are indexed separately in their respective protocol indexes
- Test scope closures never span protocol boundaries
- The layer system within a protocol (e.g., `.ivyworkspace` layers `apt_core`, `apt_quic_fork`) handles intra-protocol collision routing

**Symbol collisions** (e.g., `version`, `pkt_num`, `type_bits` declared in both `apt_types.ivy` and the forked `quic_types.ivy`) are an intentional APT design — `apt_shim.ivy` bridges these. The indexer records them as known collisions within the `apt` index, not as cross-protocol errors.

### Directory Structure

```
protocol-testing/quic/.ivy-index/
├── manifest.json                    # File inventory, mtimes, completeness, staleness
├── symbols.json                     # IvySymbol.to_dict() per file (parser quality)
├── includes.json                    # Include graph forward edges
├── exports.json                     # ExportImportInfo.to_dict() per file
├── requirements.json                # RFC annotations + requirement nodes
├── semantic_model.pickle.gz         # Full SemanticModel graph (reuse shared_cache format)
├── requirement_graph.pickle.gz      # ScopedRequirementModel (reuse shared_cache format)
└── scopes/
    ├── _meta.json                   # Test list, scope stats, coverage summary
    └── <test_name>.json             # Per-test transitive closure
```

### Manifest Format

```json
{
  "version": 1,
  "protocol": "quic",
  "created_at": "2026-03-20T14:30:00Z",
  "builder_version": "0.5.0",
  "default_parse_tier": "ast",
  "files": {
    "quic_stack/quic_packet.ivy": {
      "mtime": 1742480000.0,
      "size": 4523,
      "sha256": "abc123...",
      "completeness": "complete",
      "parse_tier": "ast"
    },
    "quic_shims/quic_missing_shim.ivy": {
      "mtime": null,
      "completeness": "missing",
      "referenced_by": ["quic_tests/server_tests/quic_server_test_reset.ivy"]
    }
  },
  "known_collisions": {}
}
```

For APT, known collisions would include the intentional symbol overlaps:
```json
{
  "protocol": "apt",
  "known_collisions": {
    "quic_types.ivy": [
      "apt_protocols/quic/quic_stack/quic_types.ivy"
    ],
    "quic_packet.ivy": [
      "apt_protocols/quic/quic_stack/quic_packet.ivy"
    ]
  }
}
```

- `completeness`: `complete` | `partial` (parse errors) | `missing` (dangling include target)
- `parse_tier`: `ast` (Tier 1, full parser, default) | `lexer` (Tier 2, fast fallback)
- `known_collisions`: basenames that appear multiple times within this protocol — the layer system resolves which variant to use

### Per-Test Scope Format

```json
{
  "test": "quic_server_test_reset",
  "entry_file": "quic_tests/server_tests/quic_server_test_reset.ivy",
  "role": "client",
  "transitive_includes": [
    "quic_stack/quic_packet.ivy",
    "quic_stack/quic_connection.ivy",
    "quic_shims/ivy_quic_shim_client_timeout.ivy"
  ],
  "layers_used": ["quic", "quic_tests"],
  "dangling_includes": [],
  "requirement_ids": ["rfc9000:4.1", "rfc9000:7.2"],
  "completeness": "complete",
  "file_count": 37
}
```

### Serialization Strategy

Reuses existing ivy-lsp infrastructure with minimal new code:

| Data | Method | Source | New Code? |
|------|--------|--------|-----------|
| Per-file symbols | `IvySymbol.to_dict()` → JSON | `symbols.py` | No |
| Export/import info | `ExportImportInfo.to_dict()` → JSON | `test_scope.py` | No |
| Include graph edges | `{file: [module, ...]}` → JSON | `symbols.py` | `IncludeGraph.from_edges()` classmethod (new) |
| SemanticModel | `pickle.gz` via `__getstate__` | `shared_cache.py` | No |
| ScopedRequirementModel | `pickle.gz` | `shared_cache.py` | No |
| Test scopes | JSON (from frozen `TestScope`) | `test_scope.py` | `TestScope.to_dict()` (new) |

**Include graph**: `includes.json` stores raw forward edges (`{file: [included_module, ...]}`) as JSON. At load time, `IncludeGraph.from_edges(data)` reconstructs both forward and reverse maps. This is a new classmethod — the only structural serialization code needed.

**ScopedRequirementModel**: The pickle file (`requirement_graph.pickle.gz`) contains a `ScopedRequirementModel` instance (extends `RequirementGraph`, includes test scope registration). The per-test JSON scope files in `scopes/` are a lightweight derived view for MCP tools that don't need the full graph. At load time, `WorkspaceContext` serves scope queries from JSON (fast, for MCP) or the full pickle (for LSP deep analysis).

**Pickle version safety**: `WorkspaceContext` catches `pickle.UnpicklingError` and `AttributeError` on load. If the pickle was written by an incompatible `builder_version`, loading fails gracefully and falls through to live indexing with a warning to re-run `ivy-lsp index`.

### Staleness Detection

At session load, `WorkspaceContext` compares manifest mtimes against actual file mtimes:

- **Fresh**: All mtimes match → load as-is
- **Stale (minor)**: <10% files changed → log warning, load anyway (overlay handles edits)
- **Stale (major)**: >10% or manifest missing → warn user, suggest `ivy-lsp index`

### Error Recovery

If individual index files are corrupt or missing:
- **Corrupt JSON** (`symbols.json`, `includes.json`, etc.): catch `json.JSONDecodeError`, log warning, fall through to live indexing for that protocol
- **Corrupt pickle** (`semantic_model.pickle.gz`): catch `pickle.UnpicklingError`/`AttributeError`, skip semantic model loading, MCP tools still work from JSON files
- **Missing scope file**: scope reported as unavailable, can be rebuilt lazily from include graph
- **Truncated manifest**: entire protocol index treated as missing, full fallback to live indexing

The system never fails hard on index corruption — it always degrades to current behavior.

### `.ivyworkspace` Schema

The existing v3 `.ivyworkspace` schema is **sufficient** — no schema changes required. Discovery of `.ivy-index/` directories is implicit via filesystem glob (`protocol-testing/*/.ivy-index/manifest.json`). The workspace layers defined in `.ivyworkspace` are used by the index builder for layer-aware include resolution during the build process.

## Unified Workspace Context

### WorkspaceContext Class

```
WorkspaceContext
├── workspace_root: str
├── project_type: "panther" | "standalone" | "fallback"
├── workspace_config: WorkspaceConfig        # From .ivyworkspace
├── protocol_indexes: Dict[str, ProtocolIndex]
├── overlay: SessionOverlay
├── active_views: Dict[str, TestScopeView]
│
├── resolve_include(name, from_file) → str | None
├── get_test_scope(test_name) → TestScope
├── get_layer(file) → str | None
├── list_tests(protocol=None) → List[str]
├── list_protocols() → List[str]
├── get_completeness(file) → "complete" | "partial" | "missing"
├── create_view(name, test_name) → TestScopeView
├── staleness_report() → Dict[str, StalenessInfo]
```

**StalenessInfo**: `{protocol: str, status: "fresh"|"stale_minor"|"stale_major", changed_files: int, total_files: int}`

**CoverageStats**: `{total_requirements: int, covered: int, uncovered: int, percentage: float, by_level: Dict[str, int]}`

### Canonical Loading Sequence

Replaces all three detection paths with one function chain:

```
1. detect_workspace_root(start_dir)
   → walks up for .ivyworkspace or PANTHER heuristic
   → returns (root, project_type)

2. load_workspace_config(root)
   → reads .ivyworkspace (if exists)
   → returns WorkspaceConfig with layers, excludes

3. discover_protocol_indexes(root, config)
   → globs protocol-testing/*/.ivy-index/manifest.json
   → loads each ProtocolIndex (JSON files + pickle graphs)
   → catches corruption gracefully per-protocol
   → checks staleness, logs warnings

4. WorkspaceContext(root, config, indexes)
   → protocol indexes are independent (no cross-protocol merging)
   → builds per-protocol include resolution chains
```

### Entry Point Simplification

| Entry Point | Before | After |
|-------------|--------|-------|
| SessionStart hook | Bash detection (`detect-ivy-workspace.sh`) duplicates logic, sets env vars | Thin wrapper: calls `python -m ivy_lsp.workspace_context detect "$PWD"`, outputs JSON |
| LSP server | `_setup_indexer()` → `_create_resolver()` → `detect_ivy_workspace()` → full scan | `WorkspaceContext.load(root)` → skip scan if index fresh |
| MCP server | `start-ivy-tools.sh` re-detects from `$PWD`, no indexer | Reads `IVY_WORKSPACE_ROOT` from SessionStart env, receives `WorkspaceContext` |
| start-ivy-tools.sh | Re-runs detection from scratch | Reads `IVY_WORKSPACE_ROOT`, passes to `--workspace` |

**Bash hook migration**: `detect-ivy-workspace.sh` becomes a thin wrapper that calls the Python detection module. The bash `find_panther_ivy()` function and `workspace-common.sh` (if any) are deprecated. The Python module returns the same JSON structure the hook currently outputs.

### Environment Variable Cleanup

| Env Var | Status |
|---------|--------|
| `IVY_LSP_INCLUDE_PATHS` | **Deprecated** — sourced from `.ivyworkspace` |
| `IVY_LSP_EXCLUDE_PATHS` | **Deprecated** — sourced from `.ivyworkspace` |
| `IVY_LSP_WORKSPACE_HINT` | **Deprecated** — replaced by canonical detection |
| `IVY_LSP_WORKSPACE` | **Kept** — explicit override (highest priority) |
| `IVY_WORKSPACE_ROOT` | **Kept** — written by SessionStart hook, consumed by MCP |

## Session Overlay

### SessionOverlay

Tracks file mutations during a session without modifying the cached index.

```
SessionOverlay
├── created_files: Dict[str, OverlayEntry]
├── modified_files: Dict[str, OverlayEntry]
├── deleted_files: Set[str]
├── _lock: threading.Lock                    # All mutations acquire lock
│
├── notify_file_change(path, content) → None
├── notify_file_create(path) → None
├── notify_file_delete(path) → None
├── get_effective_symbols(path) → List[IvySymbol]
├── get_effective_includes(path) → List[str]
```

**Thread safety**: All mutation methods (`notify_*`) acquire `_lock`. Read methods (`get_effective_*`) return snapshots — eventually consistent with writes. This is sufficient because LSP and MCP may run in the same process (via the `from_lsp_server` bridge in `ToolContext`).

**OverlayEntry**: When a file is created or modified, it gets fast-indexed immediately (Tier 2 lexer — milliseconds):

```
OverlayEntry
├── symbols: List[IvySymbol]
├── includes: List[str]
├── exports: ExportImportInfo
├── completeness: str
├── dirty_since: float
```

**Merge semantics**: Queries check overlay first → fall through to cached index. Include graph and test scopes recomputed lazily on view refresh.

### Multiple Test Scope Views

```
TestScopeView
├── name: str                    # User-assigned
├── test_name: str               # Entry point
├── protocol: str
├── scope: TestScope             # From .ivy-index/scopes/ + overlay
├── is_stale: bool               # True if overlay touched a file in scope
│
├── files_in_scope() → List[str]
├── symbols_in_scope() → List[IvySymbol]
├── requirements_in_scope() → List[RequirementNode]
├── coverage_in_scope() → CoverageStats
├── refresh() → None
├── completeness() → "complete" | "partial" | "building"
```

Multiple views coexist within a session:
- Agent A sees `quic_server_test_reset` scope (37 files)
- Agent B sees `apt_quic_attacker_test` scope (52 files)
- Both read from same `WorkspaceContext` with different scope filters
- Views from different protocols are fully isolated (no shared files)

### Incomplete Model Support

For a new `protocol-testing/rpc/` being built:

- **No index**: `WorkspaceContext` loads without `rpc` in `protocol_indexes`. Overlay tracks new files.
- **Partial index**: First `ivy-lsp index` produces scopes with `"completeness": "building"` and `dangling_includes` listed.
- **Full index**: All includes resolved, scopes become `"complete"`.

Views work at every stage — they just report reduced completeness for partial models.

### MCP Tool Scope Parameter

MCP tools gain an optional `scope` parameter:

```
ivy_verify(file="quic_packet.ivy", scope="quic_server_test_reset")
  → resolves via scope's layer-aware staging
  → coverage filtered to scope's requirements

ivy_coverage(scope="quic_server_test_reset")
  → returns coverage only for files/requirements in scope

ivy_diagnostics(scope="quic_server_test_reset")
  → checks only files in scope
```

When `scope` is omitted, tools use full workspace (backward compatible).

### Staging Directory Relationship

The existing flat staging directory (symlinks in `/tmp/ivy-lsp-stage-*/`) is still created at **session start** from the index data — not stored in the index itself. The index provides the file-to-layer mappings; the staging directory is a runtime artifact built from those mappings. With the index loaded, staging creation is faster (no filesystem walk needed) and layer-aware (uses `known_collisions` and layer priority from `.ivyworkspace`).

When a `scope` parameter is provided to MCP tools, the staging directory is filtered to only include files in that scope — preventing cross-scope collision resolution errors.

## CLI Command: `ivy-lsp index`

### Usage

```bash
# Index one protocol (full parser, default)
ivy-lsp index protocol-testing/quic/

# Index all protocols
ivy-lsp index --all

# Fast fallback (lexer only, when parser unavailable)
ivy-lsp index protocol-testing/quic/ --fast

# Check staleness without rebuilding
ivy-lsp index --status

# Force rebuild even if fresh
ivy-lsp index protocol-testing/quic/ --force
```

### Build Process

```
1. Detect workspace root (canonical detect_workspace_root())
2. Load .ivyworkspace for layer definitions
3. Walk protocol dir — discover all .ivy files (respecting exclude_paths)
4. For each file:
   a. Run TieredExtractor (Tier 1 full parser by default, Tier 2 with --fast)
   b. Collect: symbols, includes, exports, requirements, tier_used
   c. Record: mtime, sha256, completeness
5. Build IncludeGraph from all include edges
6. Identify test entry points:
   - Phase 1: use existing heuristic (`has_exports` only) to match current LSP behavior
   - Phase 4 refinement: tighten to `has_exports AND located in *_tests/ directory`
   (The stricter heuristic avoids false positives from behavior files with exports,
   but is deferred to avoid divergence between offline and live indexing until the
   live indexer is also updated to match)
7. For each test entry point:
   a. Compute transitive include closure (BFS on include graph)
   b. Detect role (client/server/mim via `detect_test_role()` — inspects behavior file basenames in include closure: `server_behavior` → role=client, `client_behavior` → role=server)
   c. Detect dangling includes (included modules with no resolved file)
   d. Write scopes/<test_name>.json
8. Build SemanticModel + ScopedRequirementModel
9. Write all output to protocol-testing/<prot>/.ivy-index/
10. Print summary
```

### MCP Tool: `ivy_index`

```
ivy_index(protocol="quic")
ivy_index(protocol="all")
ivy_index(protocol="quic", fast=true)
ivy_index(status=true)
```

### Progression Path: A → D

| Stage | Trigger | Implementation |
|-------|---------|---------------|
| **A** (this design) | Manual CLI + MCP tool | `ivy-lsp index`, `ivy_index` MCP tool |
| **B** | Git post-commit hook | `ivy-lsp index --all --if-stale` in `.git/hooks/post-commit` |
| **C** | Session-start auto | SessionStart hook runs `ivy-lsp index --all` if staleness > threshold |
| **D** | Background watcher | `ivy-lsp watch` — `watchdog`/`fsevents`, incremental `.ivy-index/` updates |

Index format is identical across all stages. Only the trigger mechanism changes.

## Migration Path

### Phase 1 — Index Builder + Loading

Ship together (both are needed for testing):
- `ivy-lsp index` CLI command
- `WorkspaceContext.load()` with `.ivy-index/` discovery
- If `.ivy-index/` not found: fall through to current behavior (scan from scratch)
- No regressions for users without pre-computed indexes

### Phase 2 — Unify Detection Paths

- `detect-ivy-workspace.sh` simplified to thin wrapper calling `python -m ivy_lsp.workspace_context detect`
- `start-ivy-tools.sh` reads `IVY_WORKSPACE_ROOT` from env instead of re-detecting
- `.lsp.json` removes hardcoded env vars
- Deprecate `IVY_LSP_INCLUDE_PATHS`, `IVY_LSP_EXCLUDE_PATHS`, `IVY_LSP_WORKSPACE_HINT`

### Phase 3 — Wire MCP to Shared Index

- `start_mcp()` receives `WorkspaceContext` instead of bare `workspace_root`
- MCP tools use `ctx.resolve_include()`, `ctx.get_test_scope()`, layer-aware staging
- Add `scope` parameter to MCP tools

### Phase 4 — Session Overlay & Views

- Add `SessionOverlay` for in-memory file tracking
- Add `TestScopeView` for concurrent views
- Expose `ivy_index` MCP tool

## Testing Strategy

### Unit Tests

- `test_workspace_context.py` — load, staleness, error recovery, protocol isolation
- `test_index_builder.py` — CLI produces valid `.ivy-index/`, handles partial models, correct test entry point detection
- `test_session_overlay.py` — create/modify/delete tracking, merge with index, thread safety
- `test_scope_views.py` — view creation, staleness, refresh, concurrent views
- `test_migration.py` — graceful fallback when no `.ivy-index/` exists, corrupt index recovery

### Integration Tests

- Index `protocol-testing/quic/`, load in `WorkspaceContext`, verify symbol count matches live indexer
- Index `protocol-testing/apt/`, verify APT's forked QUIC files are indexed independently from base QUIC
- Index incomplete protocol (temp dir with partial files), verify dangling includes and `"building"` completeness
- Verify protocol isolation: APT scope never references files from base QUIC index
- MCP tool with scope: `ivy_verify(file, scope=test_name)` resolves to correct layer variant

### Ground Truth Validation

For each test in `protocol-testing/quic/quic_tests/`, compare `scopes/<test>.json` transitive closure against what PANTHER's `ivyc` actually includes. The offline index must produce the same file set that ivyc would use. Repeat for APT tests to verify the forked QUIC files resolve correctly within the APT index.

## Success Criteria

1. `ivy-lsp index --all` completes in <60s for the full 678-file workspace (profiling needed to validate; the 2-4 min current cold start includes LSP overhead not present in offline indexing)
2. Session cold start with pre-computed index: <2s (vs current ~4 min)
3. MCP tools with `scope` return results consistent with LSP scoped queries
4. No regression: sessions without `.ivy-index/` work identically to today
5. Incomplete models: overlay tracks new files, views show `"building"` status
6. Protocol isolation: APT and base QUIC indexes are fully independent, test scopes never cross protocol boundaries

## Platform Notes

- File locking for concurrent index writes uses `fcntl.flock()` (Unix-only). Windows is not currently supported by PANTHER.
- Pickle files are version-coupled to the `SemanticModel` and `ScopedRequirementModel` class structure. Any field changes invalidate cached indexes; `builder_version` mismatch triggers graceful fallback + rebuild warning.
