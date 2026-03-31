# Ivy LSP Indexing & Plugin Architecture Improvements

**Date**: 2026-03-18
**Scope**: ivy-lsp submodule, panther-ivy-plugin, `.ivyworkspace` schema
**Status**: Design

## 1. Problem Statement

The Ivy LSP server and panther-ivy-plugin provide formal verification tooling for PANTHER's NCT (Network-Centric Compositional Testing) methodology. A comprehensive audit of `/tmp/ivy-lsp.log`, observability session logs, and source code revealed four categories of issues:

1. **Symlink staging lifecycle bugs**: `build_partitioned_staging()` in `include_resolver.py:446` calls `os.symlink()` without checking for pre-existing symlinks, producing `[Errno 17] File exists` errors. 50+ basename collisions exist between APT and standard models (e.g., `ivy_quic_client.ivy` in both `quic/` and `apt/quic/`).

2. **MCP tool prompt bloating**: 33 `@mcp.tool()` registrations across 6 modules — 18 primary tools + 15 legacy aliases. Research (arXiv:2510.14537) shows ~40 tools cause significant prompt bloating; taxonomy-based filtering is recommended.

3. **Stale symbol window**: Between Phase 1 (fast lexer, seconds) and Phase 2 (deep AST, minutes) completion, symbols are degraded. No viewport-aware prioritization exists — unlike Lean 4 (per-file workers, snapshot chains) or Coq-lsp (viewport-following incremental checking).

4. **No VFS abstraction**: Raw symlink management with no atomic refresh, reference counting, or lifecycle encapsulation. Partition dirs accumulate stale symlinks across re-indexing passes.

## 2. NCT Workspace Model (Background)

In NCT methodology, a **workspace** is defined by endpoint mirror test entry points. Master test files (e.g., `quic_client_test.ivy`, `quic_server_test.ivy`) include all specification requirements for a given mirror via transitive `include` closure. The Ivy parser/lexer requires all included files to be accessible in a flat directory — the staging system creates symlinks to satisfy this constraint.

**Role inversion**: `quic_client_test.ivy` includes `ivy_quic_shim_server` because Ivy acts as the server while testing a client IUT. The `test_file` parameter to coverage tools provides NCT-aligned per-endpoint scoping.

## 3. Current Architecture Assessment

### 3.1 Indexing (ivy-lsp)

**Architecture**: Two-phase progressive indexing.

| Phase | Strategy | Concurrency | Output Quality | Duration |
|-------|----------|-------------|----------------|----------|
| Phase 1 | PLY lexer tokenization | ThreadPoolExecutor (4 workers) | Degraded symbols, include graph, exports | Seconds |
| Phase 2 | Full AST parse from test entry points | ProcessPoolExecutor (parallel) or serial | Full symbols, requirements, test scopes | Minutes |

**Key data structures** (`ivy_lsp/parsing/symbols.py`):
- `SymbolTable`: O(1) lookup by name, file, qualified path
- `IncludeGraph`: Bidirectional adjacency lists with BFS transitive closure
- `ScopedRequirementModel` (`ivy_lsp/analysis/test_scope.py`): Per-test-scope RFC requirement filtering

**Incremental re-indexing**: `reindex_file()` cascades invalidation through transitive include dependents. No viewport-aware ordering.

**Caching**: LRU in-memory (500 files) + optional SQLite persistent cache (`~/.cache/ivy-lsp/<hash>/index.db`), mtime-validated.

### 3.2 Include Resolution & Staging

**Resolution order** (`include_resolver.py:107-143`):
1. Same directory as including file
2. Staging directory (flat symlinks)
3. Workspace root
4. Standard library (`ivy/include/1.7/`)

**Partitioned staging** (`include_resolver.py:332-461`): Graph coloring assigns test scopes to conflict-free partitions. When basename collisions occur, a conflict graph is built and greedy colored to produce `partition_0/`, `partition_1/`, etc.

**Bug 1**: Line 446 — `os.symlink(filepath, link_path)` without `os.path.lexists()` guard. `build_partitioned_staging()` produces `[Errno 17] File exists` errors on re-indexing.

**Bug 2**: Line 265 — `create_staging_directory()` uses `os.path.exists()` instead of `os.path.lexists()`. Since `exists()` returns `False` for dangling symlinks, stale dangling symlinks bypass the guard and cause `os.symlink()` to fail. Both locations must use `lexists`.

### 3.3 panther-ivy-plugin

**Surface area**: 18 primary MCP tools (+ 15 legacy aliases = 33 total), 11 skills, 4 agents, 12 hooks, 9 slash commands.

**Tool modules**:
- `verification.py`: 5 tools (`ivy_verify`, `ivy_compile`, `ivy_model_info`, `ivy_diagnostics`, `ivy_verification_dashboard`)
- `analysis.py`: 4 tools (`ivy_lint`, `ivy_include_graph`, `ivy_capabilities`, `ivy_scope`)
- `traceability.py`: 4 primary (`ivy_coverage`, `ivy_query`, `ivy_extract_requirements`, `ivy_manifest`) + 7 legacy aliases
- `visualization.py`: 2 primary + 4 legacy aliases
- `patterns.py`: 2 primary + 2 legacy aliases
- `quality.py`: 1 primary + 2 legacy aliases

**Observability**: 15 hook scripts capture per-session JSONL events across all Claude Code hook events (PreToolUse, PostToolUse, SessionStart, Stop, SubagentStart, etc.).

### 3.4 Workspace Detection

**`.ivyworkspace` v2 schema** (`panther_ivy/.ivyworkspace`):
```json
{
  "version": 2,
  "include_paths": ["protocol-testing"],
  "exclude_paths": ["doc/examples", "examples/ivy", "test", "notebooks", "patches"],
  "standard_library": "ivy/include/1.7",
  "scope_detection": "auto"
}
```

The flat `include_paths: ["protocol-testing"]` includes both standard models (`protocol-testing/quic/`) and APT models (`protocol-testing/apt/`), causing all 50+ basename collisions.

## 4. State-of-the-Art Comparison

| Feature | Lean 4 | Coq-lsp (Fleche) | Dafny | ivy-lsp (current) |
|---------|--------|-------------------|-------|--------------------|
| **Indexing** | Per-file worker subprocesses | Continuous incremental checking | Shared CLI/LSP pipeline | Two-phase progressive |
| **Incremental** | Snapshot chains per top-level command | Viewport-following, cursor-following | IdeState + Migrator per method | File-level cascade invalidation |
| **Project file** | `lakefile.lean` (declarative) | `_CoqProject` (declarative) | `.dfy` project files | `.ivyworkspace` (inferred scoping) |
| **Include model** | Hierarchical qualified imports | Qualified paths | Hierarchical modules | **Flat basename includes** (unique) |
| **VFS** | Virtual file system abstraction | Document model | Virtual document | Raw symlinks (no abstraction) |
| **Crash isolation** | Per-file worker crash containment | Single process | Single process | Single process |

**Key insight**: No other formal verification LSP needs flat staging or basename collision handling — they all use hierarchical module systems. Our flat-include constraint is unique to Ivy and makes the staging/VFS problem novel.

**MCP research** (arXiv:2602.14878): 97.1% of MCP tool descriptions have "smells"; augmented descriptions improve success by 5.85pp but increase token cost 67%. Taxonomy-based filtering (arXiv:2510.14537) recommended for >15 tools.

**No published academic work** exists on LSP servers for the Ivy language or on combining compositional testing + formal verification + language servers. This intersection is novel.

## 5. Design: Three Parallel Workstreams

### Workstream 1: ivy-lsp Core (Indexing & VFS)

#### Phase 1.1: Fix Symlink Staging Bugs (Immediate)

**File**: `ivy_lsp/indexer/include_resolver.py`

**Changes**:

1. **Fix Errno 17** (line 446): Add `os.path.lexists(link_path)` guard + `os.unlink()` before `os.symlink()`. Use `lexists` (not `exists`) to catch dangling symlinks.

2. **Clean partition dirs before populating** (before line 430): Clear each partition dir with `os.scandir()` + `os.unlink()` before creating new symlinks.

3. **Startup cleanup**: In `create_staging_directory()`, scan `tempfile.gettempdir()` for stale `ivy-lsp-stage-*` dirs older than 1 hour and remove them.

**Reuse**: Extend existing `cleanup_staging()` pattern (line 289) with its `shutil.rmtree` + `_on_error` handler.

#### Phase 1.2: VFS Abstraction Layer (Medium-term)

**New file**: `ivy_lsp/indexer/vfs.py`

**Protocol**:
```python
class IvyVFS(Protocol):
    def resolve_include(self, name: str, from_file: str, scope_id: str | None = None) -> str | None: ...
    def materialize_scope(self, scope_id: str, file_set: frozenset[str]) -> str: ...
    def invalidate_scope(self, scope_id: str) -> None: ...
    def cleanup(self) -> None: ...
```

**Implementation**: `SymlinkOverlayVFS` — same symlink approach but encapsulated with atomic refresh, reference counting, and locking. Absorbs `IncludeResolver.resolve()` (line 107) and `resolve_partitioned()` (line 463).

**Cross-process serialization**: The current `IncludeResolver` serializes via `to_config_dict()` / `from_config()` for parallel indexer worker processes. However, `to_config_dict()` only serializes 5 fields (workspace_root, staging_dir, std_dir, include_paths, exclude_paths) — it does NOT serialize partition state (`_partition_staging`, `_file_to_partition`, `_collision_map`). Workers via `from_config()` lose all partition awareness.

**Recommended approach**: Workers continue receiving resolver config (as today). The main process retains full VFS state. This avoids the complexity of full VFS serialization across process boundaries. The VFS protocol adds:

```python
class IvyVFS(Protocol):
    # ... existing methods ...
    def to_resolver_config(self) -> dict:
        """Serialize minimal state for worker processes (no partition state)."""
        ...
```

**Modified files**: `include_resolver.py` (delegate to VFS), `workspace_indexer.py` (use VFS for scope materialization), `server_setup.py` (initialize VFS), `parallel_indexer.py` (VFS serialization for workers).

#### Phase 1.3: Viewport-Aware Indexing (Long-term)

**Files**: `workspace_indexer.py` (lines 628-678), `server.py`

**Design**:
1. Track active file set from `didOpen`/`didClose` LSP events
2. Replace flat `test_files` list (line 631-633) with priority queue:
   - **Priority 0**: Test scopes containing currently-open files
   - **Priority 1**: Test scopes containing recently-edited files
   - **Priority 2**: All other test scopes
3. Preemptive re-ordering when `didOpen` fires during background Phase 2
4. Immediate symbol promotion for open files with only Phase 1 (degraded) symbols

**Reuse**: `get_endpoint_mirrors_for_file()` (`workspace_indexer.py`) already maps files to test scopes.

**Integration note**: `didOpen`/`didClose` handlers currently live in `features/diagnostics.py` (not `server.py`). Either tap into existing handlers via a callback, or add parallel tracking in `server.py` — avoid duplicating handler registration.

### Workstream 2: panther-ivy-plugin (Tool Consolidation)

#### Phase 2.1: Remove Legacy Tool Aliases (Immediate)

**Delete all 15 legacy aliases** (no backward compatibility):

| Module | Aliases to Delete |
|--------|-------------------|
| `traceability.py` | `ivy_requirement_coverage`, `ivy_coverage_gaps`, `ivy_traceability_matrix`, `ivy_query_symbol`, `ivy_impact_analysis`, `ivy_cross_references`, `ivy_generate_manifest` (7 aliases) |
| `visualization.py` | `ivy_action_dependency_graph`, `ivy_state_machine_view`, `ivy_layered_overview`, `ivy_action_requirements` (4 aliases) |
| `patterns.py` | `ivy_pattern_analysis`, `ivy_scaffold_check` (2 aliases) |
| `quality.py` | `ivy_smart_suggestions`, `ivy_quality_gate` (2 aliases) |

**Note**: `ivy_manifest` is a **primary tool** (unique `mode` parameter: `info`, `validate`, `staleness`, `refresh`) — NOT an alias. It must be preserved.

**Update all `.md` files**: Grep-and-replace all legacy name references in plugin skills, agents, commands, and CLAUDE.md in the same pass.

**Result**: 33 tools -> 18 tools. Measure actual token reduction before/after (aliases have short docstrings, so savings come primarily from reduced tool count in MCP listing, not docstring length).

#### Phase 2.2: Taxonomy-Based Categorization (Medium-term)

**6 categories** for the remaining 18 tools:

| Category | Tools | Access Pattern |
|----------|-------|---------------|
| Verification (side-effect) | `ivy_verify`, `ivy_compile` | Active modification |
| Inspection (read-only, model) | `ivy_model_info`, `ivy_diagnostics`, `ivy_capabilities`, `ivy_scope` | Model introspection |
| Analysis (read-only, file) | `ivy_lint`, `ivy_include_graph` | File-level analysis |
| Traceability (cross-file) | `ivy_coverage`, `ivy_query`, `ivy_extract_requirements` | Cross-file mapping |
| Visualization (aggregate) | `ivy_visualize`, `ivy_model_summary` | Summary views |
| Quality (advisory) | `ivy_quality`, `ivy_patterns`, `ivy_pattern_scaffold` | Improvement suggestions |

**Implementation**: Add category metadata to tool descriptions. Structure CLAUDE.md to guide LLM tool selection by workflow phase.

### Workstream 3: Workspace Model

#### Phase 3.1: APT Workspace Separation (Immediate)

**Breaking change**: `.ivyworkspace` v3 schema — no backward compatibility with v1/v2. Old markers produce a clear error with migration instructions.

```json
{
  "version": 3,
  "standard_library": "ivy/include/1.7",
  "scope_detection": "auto",
  "workspace_layers": [
    {"id": "standard", "include_paths": ["protocol-testing/quic", "protocol-testing/minip"], "priority": 1},
    {"id": "apt", "include_paths": ["protocol-testing/apt"], "priority": 2}
  ],
  "exclude_paths": ["doc/examples", "examples/ivy", "test", "notebooks", "patches"]
}
```

**Changes**:
- `workspace_detection.py`: Remove v1→v2 upgrade path. Require `workspace_layers` field. Error on absence with migration message. Update `_panther_heuristic()` (lines 168-212) to generate v3-compatible layer structure.
- `include_resolver.py`: Per-layer staging — each layer gets independent staging directory and collision scope.
- `panther_ivy/.ivyworkspace`: Replace with v3 schema.

**Impact**: Eliminates ~50 basename collisions at source. Removes v1/v2 compatibility code.

#### Phase 3.2: Qualified Includes Proposal (Long-term, Academic)

**LSP-only prototype** (does not change Ivy parser):
- Extend `IncludeResolver.resolve()` to handle `include quic.quic_types` -> `quic/quic_types.ivy`
- Academic contribution: VFS + viewport-aware indexing for flat-include formal verification languages

## 6. Relationship to Existing Documents

### 6.1 LSP Performance Pipeline Enablers (plan, FULLY EXECUTED)

The plan at `docs/superpowers/plans/2026-03-18-lsp-performance-pipeline-enablers.md` is **fully executed**. All 6 tasks are committed:

| Task | Status | Commit | Relationship to This Design |
|------|--------|--------|----------------------------|
| P1: `SymbolTable.remove_file()` | **DONE** | `8241397` | Enables efficient VFS invalidation (WS1-1.2) |
| P2: Selective mirror-scope invalidation | **DONE** | `fa45f92` | `_compute_test_scopes(dirty_files=...)` callers wired |
| P4: Demand-driven deep parse | **DONE** | `f639105` | WS1-1.3 (viewport) builds on this |
| P8: ivy_quality context scoping | **DONE** | `6f4b504` | Independent |
| P3: nct-scaffold presets | **DONE** | `e643e16` | Independent |
| P13: Skill prerequisites | **DONE** | `e643e16` | Independent |

**No blockers remain.** This design can proceed directly.

### 6.2 NCT Workspace Validation Spec (companion assessment)

The spec at `docs/superpowers/specs/2026-03-18-nct-workspace-validation-design.md` provides a validation assessment and 6-month improvement roadmap (Phases 0-3). Overlap analysis:

| Validation Spec Item | Status | This Design Phase | Overlap |
|----------------------|--------|-------------------|---------|
| F0a: Remove legacy aliases (33→18) | **Not started** | **WS2-2.1** | **Identical scope** |
| F0b: Fix Errno 17 | **Not started** | **WS1-1.1** | **Identical** |
| F0c: ivy_quality context (P8) | **DONE** (`6f4b504`) | — | Already done |
| F0d: Demand-driven deep parse (P4) | **DONE** (`f639105`) | — | Already done |
| F1: Incremental per-file re-indexing (P1+P2) | **DONE** (`8241397`, `fa45f92`) | — | Already done |
| F2: Collision diagnostics | Not started | — | **Complementary** (not in this design) |
| F3: LLM diff-checker / frozen files | Not started | — | **Complementary** (not in this design) |
| F4: Iterative verification CEGAR skill | Not started | — | **Complementary** (not in this design) |
| F5: Conformance tests vs ivyc | Not started | — | **Complementary** (not in this design) |
| D1-D5: Depth & Trust roadmap | Not started | — | D4 (multi-root) partially overlaps WS3-3.1 |
| I1-I4: Integration & Demo | Not started | — | No overlap |

**Items in this design NOT in the validation spec** (architectural improvements beyond the 6-month roadmap):
- **WS1-1.2**: VFS abstraction (validation spec says "Keep flat staging" — compatible, VFS encapsulates symlinks with better lifecycle)
- **WS1-1.3**: Viewport-aware indexing
- **WS2-2.2**: Taxonomy-based tool categorization
- **WS3-3.1**: APT workspace separation (.ivyworkspace v3 with layers)
- **WS3-3.2**: Qualified includes proposal

**Validation spec alignment**: Tool counts and stale items have been corrected in the validation spec (2026-03-18 revision). Both documents now agree on 18 primary + 15 aliases = 33 total.

## 7. Dependency Graph

All prerequisites (P1, P2, P4, P8, P3, P13) are done. This design can start immediately.

```
WS1-1.1 (symlink bugs)  ──┐
                           ├──> WS1-1.2 (VFS) ──> WS1-1.3 (viewport, builds on P4 ✓)
WS3-3.1 (APT separation) ─┘

WS2-2.1 (remove aliases) ──> WS2-2.2 (taxonomy)

WS3-3.2 (qualified includes) — independent, academic
```

**Parallel start**: WS1-1.1, WS2-2.1, WS3-3.1 all begin immediately (no blockers).

**Complementary validation spec items** (can be done in parallel or after):
- F2 (collision diagnostics), F3 (frozen file guard), F4 (CEGAR loop skill), F5 (ivyc conformance tests)

## 8. Critical Files

| File | Workstream | Changes |
|------|------------|---------|
| `ivy_lsp/indexer/include_resolver.py` | WS1, WS3 | Fix Errno 17, clean partitions, VFS delegation, per-layer staging |
| `ivy_lsp/indexer/workspace_indexer.py` | WS1 | Viewport priority queue, VFS integration |
| `ivy_lsp/indexer/vfs.py` (new) | WS1 | IvyVFS protocol + SymlinkOverlayVFS implementation |
| `ivy_lsp/workspace_detection.py` | WS3 | v3 schema parsing, remove v1/v2 compat, layer support |
| `ivy_lsp/server.py` | WS1 | didOpen/didClose active file tracking |
| `ivy_lsp/server_setup.py` | WS1 | VFS initialization |
| `ivy_lsp/tools/traceability.py` | WS2 | Remove 7 legacy aliases (preserve `ivy_manifest` — primary tool) |
| `ivy_lsp/tools/visualization.py` | WS2 | Remove 4 legacy aliases |
| `ivy_lsp/tools/patterns.py` | WS2 | Remove 2 legacy aliases |
| `ivy_lsp/tools/quality.py` | WS2 | Remove 2 legacy aliases |
| `panther_ivy/.ivyworkspace` | WS3 | Replace with v3 schema (breaking) |
| Plugin `CLAUDE.md` | WS2 | Update tool reference, add taxonomy |
| `ivy_lsp/indexer/parallel_indexer.py` | WS1 | VFS serialization for worker processes |
| `ivy_lsp/features/hover.py` | Prereq (P4) | Demand-driven deep parse wiring |
| `ivy_lsp/features/definition.py` | Prereq (P4) | Demand-driven deep parse wiring |
| `ivy_lsp/features/document_symbols.py` | Prereq (P4) | Demand-driven deep parse wiring |
| `ivy_lsp/features/visualization.py` | Prereq (P8) | `_resolve_scope` filePath derivation |
| Plugin skills/agents/commands `.md` | WS2 | Replace legacy tool name references |

## 9. Verification Strategy

### Per-Phase
1. **WS1-1.1**: `test_partitioned_staging_idempotent`, `test_partition_stale_cleanup`; existing 1965 tests pass
2. **WS2-2.1**: `/nct-validate` passes with consolidated names; grep confirms zero legacy references in .md files; measure token count reduction
3. **WS3-3.1**: Index with layers -> zero standard-layer collisions; v1/v2 markers produce clear error with migration message

### End-to-End
- `/nct-health` — LSP + MCP alive
- `/nct-validate` — all checks pass (update ground truth for removed tools)
- Index full QUIC workspace — measure indexing time, collision count, symbol accuracy
- Verify hover, definition, workspace symbols work in Claude Code
- `ivy_coverage(mode="stats", test_file="quic_client_test.ivy")` — NCT-scoped results correct

### Regression Baseline
- Test suite: 1965 tests passing
- MCP tool count: 33 -> 18 (15 legacy aliases removed)
- Collision count: 50+ -> ~0 (with layers)
- Indexing time: benchmark before/after VFS

## 10. Research References

- **Lean 4 LSP**: Watchdog-worker architecture, snapshot chains (https://github.com/leanprover/lean4)
- **Coq-lsp (Fleche)**: Continuous incremental checking, viewport-following (https://github.com/ejgallego/coq-lsp)
- **Dafny LSP**: Shared verification pipeline, IdeState+Migrator (https://github.com/dafny-lang/dafny)
- **MCP tool smells**: arXiv:2602.14878 — 97.1% of descriptions have smells
- **Tool taxonomy filtering**: arXiv:2510.14537 (JSPLIT) — taxonomy-based filtering for LLM tool selection
- **Context re-grounding**: arXiv:2602.13320 — periodic re-grounding every ~9 steps reduces distortion 80%
- **MCP production gaps**: arXiv:2603.13417 — identity-aware routing, adaptive timeout, structured error recovery
- **LSPFuzz**: arXiv:2510.00532 — 51 bugs found in LSP servers from source change + editor operation combinations
- **PANTHER/NSCT**: arXiv:2503.04810 — Network Simulator-centric Compositional Testing with Ivy + Shadow
