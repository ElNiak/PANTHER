# NCT Workspace Model Validation & Improvement Roadmap

**Date**: 2026-03-18
**Status**: Draft
**Scope**: Full-stack validation of ivy-lsp indexing + panther-ivy-plugin integration
**Audience**: Dual-purpose — engineering assessment (6-month POC guide) + academic framing (P6 Ivy LSP Tool Paper, AMC3 WP2 deliverables)

---

## 1. Context

The PANTHER/ivy-lsp/panther-ivy-plugin stack implements an "endpoint-mirror-as-workspace" model for NCT (Network-Centric Compositional Testing). In this model, each master test file (e.g., `quic_client_test.ivy`) defines a complete workspace partition via its transitive include closure. The ivy-lsp server indexes this workspace, and the panther-ivy-plugin exposes it to Claude Code via MCP tools, hooks, skills, and agents.

Before AMC3 WP2's 6-month POC sprint (Feb-Aug 2026), this document validates whether:
1. The workspace model is conceptually sound and faithfully implemented
2. The current implementation is competitive with state-of-the-art formal language tooling
3. The gaps can be addressed within the POC timeline

This feeds into P6 (Ivy LSP Tool Paper, TACAS/FSE 2027) and P3 (Agent-Driven Evidence, ICSE 2027 SEIP).

---

## 2. Validation Assessment

### 2.1 Conceptual Validation

**Verdict: Sound, with two documented caveats.**

The model treats each test entry point as defining a complete workspace partition. This mirrors what `ivyc` sees when compiling that test — the compiler resolves includes from a flat directory and builds only the reachable graph.

**Evidence of correctness**:
- `_compute_test_scopes()` (`workspace_indexer.py:1324`) walks files with exports, computes transitive closure via `IncludeGraph.get_transitive_includes()`, and registers a `TestScope` with `include_closure` (FrozenSet), `exported_actions`, `imported_actions`, and `tester_role`
- Role detection in `detect_test_role()` (`test_scope.py:75`) implements Ivy's role inversion by checking for `server_behavior`/`client_behavior` basename patterns in the include closure
- The `test_file` parameter in coverage tools filters requirements to `scope.include_closure`, matching exactly the files PANTHER copies into the Docker staging directory

**Caveat 1 — Basename collision semantics**: The flat symlink staging (`create_staging_directory()`, `include_resolver.py:223`) mirrors `ivyc`'s CWD-relative resolution. When two test scopes need different files sharing a basename, partitioned staging via graph coloring (`build_partitioned_staging()`) handles this. The greedy graph coloring is correct (produces optimal partitions when the conflict graph is a tree). Complexity is O(T x B x V) where T=test scopes, B=colliding basenames, V=variants per basename. For the QUIC workspace (~200 files, ~30 collisions, ~20 test scopes), this is negligible.

**Caveat 2 — No cross-scope invariant checking**: Each test scope is treated independently. No mechanism verifies that shared files (e.g., `quic_connection.ivy` included by both client and server tests) maintain consistent assume-guarantee contracts across scopes. Theoretically safe by Ivy's compositionality guarantee, but not surfaced as a verifiable property.

### 2.2 Layer-by-Layer Assessment

#### Layer 1: Workspace Detection (`workspace_detection.py`, 321 lines) — Adequate

**Implementation**: 6-strategy priority chain: explicit > hint > walk-up `.ivyworkspace` marker > walk-down marker > PANTHER heuristic > git worktree > fallback. The v2 `.ivyworkspace` schema supports `include_paths`, `exclude_paths`, `scope_detection`, `standard_library`, `project_type`.

**Edge cases**:
- Multiple `.ivyworkspace` in walk-down: returns FIRST found at any depth, not closest
- `max_depth=10` in walk-up prevents infinite loops but could miss very deep markers
- PANTHER heuristic false-positive: any dir with `protocol-testing/` + `panther_ivy.py`

**Gap**: No multi-root workspace support (LSP 3.6 `workspace/didChangeWorkspaceFolders`).

#### Layer 2: Include Resolution (`include_resolver.py`, 552 lines) — Novel, Strong

**Implementation**: 4-step resolution chain (same dir > staging > workspace root > stdlib). Staging creates flat symlinks to all `.ivy` files, with first-sorted-path-wins collision handling. Partitioned staging via graph coloring for multi-test isolation.

**Critical finding — ivyc divergence**: ivyc uses `open(name + '.ivy')` in CWD (2-step: CWD then stdlib). The LSP uses 4-step with staging as bridge. Step 3 (workspace root) is extra and could resolve files ivyc wouldn't find.

**Known bug — Errno 17**: `build_partitioned_staging()` at line 446 calls `os.symlink()` without `os.path.lexists()` guard, producing `[Errno 17] File exists` errors. The main `create_staging_directory()` has this guard (line 265) but the partitioned variant does not.

**Edge cases**:
- ~50 basename collisions between APT and standard models (e.g., `ivy_quic_client.ivy` in both `quic/` and `apt/quic/`) — `.ivyworkspace` v2 `include_paths: ["protocol-testing"]` includes both
- ~30 additional collisions within QUIC (e.g., `byte_stream.ivy` 3x, `file.ivy` 3x)
- Dynamic file additions after staging creation miss new files until re-index
- No VFS abstraction — raw symlink management with no atomic refresh, reference counting, or lifecycle encapsulation

**Gaps**: (a) Collisions logged but not surfaced as LSP diagnostics. (b) Errno 17 bug in partitioned staging. (c) No VFS abstraction layer. (d) APT/standard workspace separation needed (v3 schema).

#### Layer 3: Two-Phase Indexing (`workspace_indexer.py`, ~1400 lines) — Good Tradeoff

**Implementation**: Phase 1 = fast lexer scan via regex/PLY (1-3s for 202 QUIC files, immediate LSP readiness). Phase 2 = background full parse from test entry points (files with exports, ~40 in QUIC, 10-30s). Thread-safe symbol swapping under `_table_lock` with atomic reference swap for concurrent reads.

**Edge cases**:
- Phase 2 interruption gracefully degrades to Phase 1 quality
- Phase 2 removes Phase 1 requirements before adding full ones — mid-failure leaves gaps (caught by error handler)
- `_source_cache` thread safety relies on Python GIL (safe but implicit)

**Gap**: No incremental per-declaration re-indexing. Full re-index per file change.

#### Layer 4: Test Scope Model (`test_scope.py`, 328 lines) — Novel, Strong

**Implementation**: `TestScope` frozen dataclass with `include_closure` (FrozenSet), `exported_actions`, `imported_actions`, `tester_role`. `ScopedRequirementModel` extends `RequirementGraph` with per-test caching and proper invalidation. NCT classification: `_generating` -> TESTER_ONLY, `after/around` mixin -> GUARANTEE, `ensure/assert` -> GUARANTEE, else ASSUMPTION.

**Quantitative**: ~40 test files, each closure 15-40 files. O(T x C) ~ 1000 graph lookups — fast.

**Edge cases**:
- Phantom test scope: shared behavior files with `export` create their own scope
- Role detection heuristic fails for protocols not using `server_behavior`/`client_behavior` naming
- `_generating` detection is string match in `formula_text` — reliable for Ivy convention but fragile if text unavailable

**Gap**: No cross-scope invariant checking.

#### Layer 5: Semantic Model (`analysis_pipeline.py` ~1000 lines, `model.py` 296 lines) — Adequate

**Implementation**: T1 (<50ms, syntactic, RFC annotation parsing), T2 (<200ms, AST-enriched), T3 (background compiler). Thread-safe `SemanticModel` with RLock, tier-aware updates (higher overwrites lower). Generation tracking for stale T3 result rejection.

**Gap**: No per-position semantic data (Lean 4 InfoTree equivalent).

#### Layer 6: MCP Tools (`tools/`, 6 modules, ~130KB) — Novel, Strong

**Implementation**: 34 registered `@mcp.tool()` functions — **15 primary tools + 19 legacy aliases** (per indexing-improvements audit). `test_file` scoping correctly implements endpoint-mirror: `abs_test = ctx.validate_path(test_file)` -> `scope = graph.get_test_scope(abs_test)` -> filter to `scope.include_closure`. Path traversal prevention. Lazy model construction with async lock and 30s cooldown.

**Edge cases**:
- MCP standalone vs LSP mode model divergence (different code paths)
- If `test_file` not yet indexed, fallback filters to just the test file itself, losing scope
- `ivy_quality(mode="suggestions")` `_resolve_scope` does not derive testFile from filePath (P8 bug)

**Gaps**: (a) 19 legacy aliases bloat prompt ~56% (34->15 after removal, per arXiv:2510.14537 tool taxonomy research). (b) No CC evidence export format. (c) No taxonomy-based categorization for 6-category LLM tool selection guidance.

#### Layer 7: Plugin Integration (`panther-ivy-plugin`) — Novel Architecture

**Implementation**: 10 hook points, 15 observability scripts, `block-direct-ivy.sh` PreToolUse enforcement, `lint-before-verify.sh` PostToolUse auto-lint. `/nct-validate` with 55 checks across 7 phases. 4 agents (spec-analyst, methodology-guide, model-reviewer, traceability-agent), 11 skills, 9 commands.

**Edge cases**:
- Hook timeout (2-10s) — large logs cause silent timeout
- `${CLAUDE_PLUGIN_ROOT}` must be correctly set by Claude Code

**Gap**: No iterative verification skill, no LLM diff-checker.

### 2.3 Alternative Approaches Analysis

#### Workspace Scoping

| Approach | Verdict | Reasoning |
|----------|---------|-----------|
| **Endpoint-mirror (current)** | **Keep** | NCT-aligned, matches PANTHER runtime, enables per-test coverage |
| Module-based (Lean 4 style) | Incompatible | Ivy `include` is textual inclusion (like C `#include`), not module import — would require language changes |
| Project-wide | Loses NCT alignment | Can't answer "which tests cover this requirement?" Cross-protocol pollution |
| On-demand/lazy (Coq Fleche) | Incompatible with agent workflow | Agent needs workspace-wide views (coverage matrices); lazy indexing would materialize views per query |

#### Include Resolution

| Approach | Verdict | Reasoning |
|----------|---------|-----------|
| **Flat symlink staging (current)** | **Keep** | Faithful to ivyc, manageable complexity |
| FUSE/overlay FS | Reject | macOS FUSE deprecated, Linux needs container privileges |
| Rewrite-based | Reject | Changes file semantics, breaks ivyc compilation |
| Compiler-integrated | Reject (hybrid possible) | ivyc global state, subprocess per include too slow. Use T3 to validate T2 resolution as hybrid. |

#### Indexing Strategy

| Approach | Verdict | Reasoning |
|----------|---------|-----------|
| **Two-phase lexer+parser (current)** | **Keep** | Best latency/correctness tradeoff for agent workflow |
| Single-phase full parse | Reject | 30-60s startup blocks agent |
| Incremental per-declaration | Future enhancement | Requires tree-sitter or custom parser — major effort |
| Demand-driven | Reject | First coverage query triggers full parse anyway |

#### MCP Tool Design

| Approach | Verdict | Reasoning |
|----------|---------|-----------|
| **Mode-based consolidation (15 tools)** | **Keep** | Sweet spot of discoverability vs context efficiency (~1500 tokens) |
| One-tool-per-operation (30+) | Reject | ~3000 tokens overhead, agent may choose wrong tool |
| GraphQL-style single query | Reject | Shifts complexity to query construction, opaque errors |

#### Plugin Architecture

| Approach | Verdict | Reasoning |
|----------|---------|-----------|
| **Full plugin (skills + agents + hooks + commands)** | **Keep** | Essential enforcement and guidance for agent workflow |
| Pure-MCP (tools only) | Loses enforcement | No hooks, no agents, no skills, no observability |
| IDE extension (VS Code) | Complementary | No agent enforcement, no MCP access — targets humans, not AI |

### 2.4 Threats to Validity

| # | Threat | Prob | Severity | Mitigation In Place | Mitigation Needed |
|---|--------|------|----------|---------------------|-------------------|
| T1 | Basename collision -> wrong include resolution | MED | HIGH | Collision map, partitioned staging with graph coloring | Validate staging vs ivyc per test file (F5) |
| T2 | Phase 1 regex misses includes | LOW | MED | Regex covers all standard Ivy; Phase 2 validates | None |
| T3 | NCT classification incorrectness | MED | HIGH | Tested in `test_nct_classification.py`; `_generating` is reliable Ivy convention | Cross-validate against manual annotation |
| T4 | MCP/LSP semantic model divergence | MED | MED | `build_semantic_model` shared code | Add test comparing both models |
| T5 | Role detection heuristic brittleness | LOW (QUIC), HIGH (new protocols) | MED | Returns "unknown" when no heuristic matches | Explicit role annotation support |
| T6 | Single-protocol evaluation | HIGH | MED | QUIC only | Demonstrate on CoAP by P6 submission |
| T7 | Ground truth staleness | MED | MED | nct-validate checks 55 items | Automated ground truth from ivyc (I4) |
| T8 | Std lib version mismatch | MED | MED | LSP selects highest version; ivyc selects lowest >= language version — different! | Fix LSP to match ivyc selection logic |
| T9 | Agent context window saturation | HIGH | MED | Skills on demand; CLAUDE.md single page; mode consolidation | Token budget tracking |
| T10 | Observability event-loss | LOW | LOW | `atexit` handlers | Event-loss detection (D5) |

### 2.5 Related Work Comparison

| System | Language | Scoping | Incremental | MCP/Agent | RFC Traceability | CC Evidence |
|--------|----------|---------|-------------|-----------|------------------|-------------|
| **ivy-lsp** | Ivy 1.7 | Endpoint-mirror | Per-file | 15 MCP + 4 agents | Bracket tags + manifests | Planned |
| Lean 4 LSP | Lean 4 | Module | Per-declaration | No | N/A | No |
| Coq Fleche | Coq | Document | Per-sentence | No | N/A | No |
| DafnyPro | Dafny | Function | No | No | N/A | No |
| lean-lsp-mcp | Lean 4 | Module | Reuses Lean | MCP wrapper (5 tools) | N/A | No |
| SpecGen | Multiple | N/A | N/A | LLM loop | N/A | No |

**Key differentiators**:
- **vs Lean 4 LSP**: Finer granularity (per-declaration vs per-file) but no MCP, hooks, agent coordination, or RFC traceability. Per-declaration snapshots are gold standard for incrementality.
- **vs Coq Fleche**: Viewport-following incompatible with MCP-first agent workflow. Per-sentence caching could inspire per-action caching.
- **vs DafnyPro**: 86% correct proofs with Claude 3.5. Evaluation methodology (iterations-to-fix, per-complexity success rates) should inform P6. Fully automated loop vs our "guided convergence."
- **vs lean-lsp-mcp**: Same MCP-wrapped-LSP pattern but 5 thin wrappers vs 15 deep-integrated tools. No traceability, quality gates, or visualization.
- **vs SpecGen**: Mutation-based repair (syntactic) vs counterexample-guided repair (semantic). No traceability.

---

## 3. Improvement Roadmap

### Phase 0: Immediate — Remove Legacy Debt & Fix Bugs

#### F0a: Remove 19 Legacy MCP Tool Aliases (34 -> 15 tools)

**Problem**: 19 backward-compatibility `@mcp.tool()` aliases duplicate the 15 primary consolidated tools. They bloat the MCP prompt ~56% and confuse tool selection. Plugin docs already use consolidated names only.

**Aliases to delete** (4 files):

| Module | Aliases | Lines |
|--------|---------|-------|
| `traceability.py` | `ivy_requirement_coverage`, `ivy_coverage_gaps`, `ivy_traceability_matrix`, `ivy_query_symbol`, `ivy_impact_analysis`, `ivy_cross_references`, `ivy_generate_manifest` | 1241-1294 |
| `visualization.py` | `ivy_action_dependency_graph`, `ivy_state_machine_view`, `ivy_layered_overview`, `ivy_action_requirements` | 313-342 |
| `patterns.py` | `ivy_pattern_analysis`, `ivy_scaffold_check` | 282-297 |
| `quality.py` | `ivy_smart_suggestions`, `ivy_quality_gate` | 368-383 |

**Verification**: `pytest tests/`, `/nct-validate` (update tool count ground truth), `/nct-health`.

**Effort**: 1 day.

#### F0b: Fix Errno 17 Symlink Bug

`build_partitioned_staging()` at `include_resolver.py:446` — add `if os.path.lexists(link_path): os.unlink(link_path)` before `os.symlink()`. Add startup cleanup for stale `ivy-lsp-stage-*` dirs.

**Effort**: 1 hour.

#### F0c: Fix ivy_quality Context Scoping (P8)

`_resolve_scope` in `visualization.py` — when testFile is None and filePath is provided, derive scope via `graph.get_tests_for_file(file_path)`.

**Effort**: 2 hours.

#### F0d: Demand-Driven Deep Parse for Shared Modules (P4)

Add `deep_parse_on_demand(filepath)` to `WorkspaceIndexer`. Wire into hover, goto-def, and document-symbols handlers. Shared libraries get AST-quality symbols on first interaction.

**Effort**: 1-2 days.

---

### Phase 1: Foundation (Months 1-2) — LSP Core + LLM Safety

#### F1: Incremental Per-File Re-Indexing

**Problem**: `_remove_file_symbols()` rebuilds entire SymbolTable by copying all symbols except target — O(n) for 10,000+ symbols. `_compute_test_scopes()` clears all 200+ cache entries on every single-file reindex.

**Changes**:
1. `symbols.py` — Add `SymbolTable.remove_file(filepath) -> int` using in-place `_by_file.pop()` + prune `_by_name`/`_all`. O(k) vs O(n).
2. `workspace_indexer.py:1091-1099` — Replace body with `self._symbol_table.remove_file(filepath)`.
3. `workspace_indexer.py:1324` — `_compute_test_scopes(dirty_files=None)`. When provided, only invalidate cache entries whose `include_closure` intersects `dirty_files`.
4. Wire: `reindex_file()` -> `_compute_test_scopes(dirty_files={abs_path})`.

**Example**: Editing `quic_connection.ivy` — before: rebuild 10,000+ symbols, clear 200+ caches. After: remove ~50 symbols, clear ~12 affected caches.

**Effort**: 2-3 weeks. **Enables**: D3, D4. **Impact**: P6 + P3.

#### F2: Basename Collision Diagnostics

**Changes**:
1. `diagnostics.py` — New `_emit_collision_diagnostics()` emitting Warning on ambiguous `include` statements.
2. `analysis.py` — Add `collisions` field to `ivy_include_graph` response.
3. `include_resolver.py` — Add `get_collision_report() -> dict`.

**Effort**: 1 week. **Impact**: P6.

#### F3: LLM Diff-Checker Hook

**Changes**:
1. `hooks.json` — New PreToolUse hook for `Write|Edit` running `check-base-spec-guard.sh`.
2. `.ivyworkspace` — `frozen_files: ["quic_stack/quic_types.ivy", "tls_stack/*.ivy"]`.
3. New `check-base-spec-guard.sh` (~40 lines) — Parse TOOL_USE_INPUT, check against frozen list.

**Minimal**: Glob matching. **Full**: `/nct-freeze`/`/nct-unfreeze` + auto-freeze.

**Effort**: 2 weeks. **Impact**: P3 (gatekeeper).

#### F4: Iterative Verification Skill

**Changes**: New `skills/iterative-verification/SKILL.md` — CEGAR loop:
1. `ivy_lint` (max 3 syntax retries)
2. `ivy_verify(isolate=X)` — if counterexample, go to 3
3. Diagnose via `counterexample-guide`
4. Apply single fix
5. Re-lint, re-verify (back to 1)
6. Termination: pass OR iterations > 5
7. Output: structured log per iteration

**Example**: rfc9000:4.1 in `quic_server_test_stream.ivy` — lint (pass) -> verify (counterexample: `stream_state=idle`) -> fix (`require stream_state = open`) -> re-verify (pass). 2 iterations.

**Effort**: 2 weeks. **Impact**: P3 (core loop).

#### F5: Conformance Tests Against ivyc

**Changes**: New `tests/conformance/` — compare LSP's `TestScope.include_closure` against `ivyc` actual resolution. `@pytest.mark.requires_ivy` skip when ivyc unavailable.

**Effort**: 1 week. **Impact**: P6 (threat T1 mitigation).

### Phase 2: Depth & Trust (Months 3-4) — CC Evidence + Verification Loop

#### D1: CC Evidence Export

**New MCP tool**: `ivy_cc_evidence(mode="adv_fsp"|"ate_fun"|"ava_van"|"ate_cov"|"full")`.

| CC Family | Sub-Component | ivy-lsp Artifact |
|-----------|---------------|------------------|
| ADV_FSP.1-2 | Basic/security-enforcing spec | Exported action signatures + `require` guards |
| ADV_FSP.3-4 | Complete with state model | State var read/write edges |
| ADV_FSP.5-6 | Semi-formal/formal with correspondence | Ivy source + bracket tags + Z3 proofs |
| ATE_FUN.1-2 | Functional/ordered testing | Per-isolate verdicts + 14-layer dependency graph |
| AVA_VAN.1-5 | Vulnerability analysis (levels) | NACT error injection/mutation results |
| ATE_COV.1-3 | Coverage (levels) | Requirement coverage per test scope |

**Effort**: 3-4 weeks. **Impact**: P3 (flagship), WP2 D2.3.

#### D2: Verification Failure Repair Hints

**Changes**: `verification.py` — Add `error_category` and `repair_hints` to `ivy_verify` response:
- `safety_violation` -> suggest `require {var} = {expected_value}`
- `type_error` -> suggest type correction
- `timeout` -> suggest `attribute {isolate}.timeout = 60`

**Effort**: 3 weeks. **Impact**: P3 + P6.

#### D3: Snapshot-Based Incremental Model Updates

**Changes**: `requirement_graph.py` — `update_file_requirements()` for incremental re-wire. `workspace_indexer.py` — use incremental update in `reindex_file()`. Content hash tracking for skip-if-unchanged.

**Benchmark**: Full wire ~100ms -> incremental ~5ms per file.

**Effort**: 4 weeks. **Requires**: F1. **Impact**: P6.

#### D4: Multi-Root Workspace Support

**Changes**: `workspace_indexer.py` — `add_workspace_folder()`/`remove_workspace_folder()`. `server.py` — handle `workspace/didChangeWorkspaceFolders`. `.ivyworkspace` — `roots: [...]`.

**Effort**: 3 weeks. **Impact**: P6.

#### D5: Observability Event-Loss Detection

**Changes**: SessionStart initializes monotonic counter. Each hook increments and logs sequence number. Stop hook compares vs expected, reports gaps.

**Effort**: 1 week. **Impact**: P3.

### Phase 3: Integration & Demo (Months 5-6) — Polish

#### I1: LSIF Export

New `ivy_lsp/lsif/exporter.py` (LSIF 0.4). MCP tool `ivy_lsif_export()`. CLI `--lsif-dump`.

**Effort**: 3 weeks. **Impact**: P6 (artifact).

#### I2: End-to-End Demo

Scripted: lint -> verify (counterexample) -> fix -> re-verify (pass) -> coverage -> quality gate -> CC evidence. New `/nct-demo` command.

**Effort**: 2 weeks. **Impact**: P3 + WP2.

#### I3: Paper Evaluation Infrastructure

New `evaluation/` with latency/accuracy/convergence benchmarks. See RQ1-RQ4 in Section 4.

**Effort**: 3 weeks. **Impact**: P6 (evaluation section).

#### I4: Automated Ground Truth from ivyc

Script that captures ivyc include resolution per test entry point, generates `quic-workspace.yaml`. CI integration.

**Effort**: 1 week. **Impact**: P6 + nct-validate.

---

## 4. Academic Positioning

### 4.1 P6 Paper Evaluation Methodology

**RQ1: Endpoint-mirror scoping accuracy vs project-wide**
- Compare `ivy_coverage(mode="stats")` globally vs per `test_file`
- Metrics: false positive rate, phantom coverage inflation
- Expected: Project-wide inflates by 10-20% due to cross-scope tag bleeding
- Ground truth: Manual verification of 20 random requirements

**RQ2: LSP response latency across workspace sizes**
- Synthetic workspaces: 10, 50, 100, 200, 500 files
- Thresholds: Interactive <100ms p95, analysis <500ms p95, index <5s for 200 files
- Report p50/p95/p99 for each tool

**RQ3: Agent verification loop effectiveness (F4)**
- 20 QUIC MUST requirements not yet formalized
- Metrics: iterations-to-fix, success rate, time-to-fix, manual intervention rate
- Expected: lint first-pass 85-90%, verify first-pass 40-60%, mean iterations 2-4, 75-85% within 5
- Comparison: DafnyPro's 2.3 mean iterations (POPL 2026)

**RQ4: Requirement extraction accuracy**
- Compare `ivy_extract_requirements` vs manual `rfc9000_requirements.yaml` (90 reqs)
- Metrics: precision (60-70%), recall (70-80%), F1, level accuracy (90%+)

### 4.2 Novelty Claims

1. **Endpoint-mirror workspace partitioning** — No prior art for test-entry-point-based workspace scoping in formal LSPs. Closest: contract-based hardware verification but not LSP-integrated.
   - *Objection*: "QUIC-specific." *Response*: 14 layers map to general protocol engineering concepts.

2. **Flat-symlink staging with graph-coloring partition isolation** — Novel for languages with CWD-relative includes.
   - *Objection*: "Why not fix the language?" *Response*: Ivy is maintained by Microsoft Research; we build on top.

3. **Three-tier progressive analysis pipeline** — T1<50ms, T2<200ms, T3 background.
   - *Objection*: "Lean 4 does this better." *Response*: Per-file is appropriate for Ivy's smaller workspaces.

4. **MCP-wrapped formal verification with RFC traceability** — 15 tools with bracket tags, coverage matrices, quality gates.
   - *Objection*: "lean-lsp-mcp also wraps LSP." *Response*: 5 thin wrappers vs 15 deep-integrated tools.

5. **Agent-as-a-Guide for CC evidence** — No published work automates the full CC pipeline from formal specs.
   - *Objection*: "Engineering, not research." *Response*: Novel architectural patterns for safety-critical applications.

### 4.3 WP2 Deliverable Mapping

| Deliverable | What ivy-lsp Provides | Roadmap Items |
|-------------|----------------------|---------------|
| D2.1: Agent Architecture | "Agent-as-a-Guide" spec | F3, F4 |
| D2.2: Tool Integration | MCP API, hooks, observability | F2, D5 |
| D2.3: Evidence Generation | CC evidence (ADV_FSP + ATE_FUN + AVA_VAN + ATE_COV) | D1 |
| D2.4: Evaluation | Benchmarks (RQ1-RQ4), iteration metrics | I2, I3 |

### 4.4 CC Certification Detailed Mapping

**ADV_FSP evidence format** (per exported action):
```
TSF Interface: quic_connection.open
  Security Function: Connection establishment
  Guard: require conn_state = closed  [rfc9000:4.1]
  Effect: ensure conn_state = open  [rfc9000:4.1]
  State Modified: conn_state, conn_seen
  Verification: PASS (Z3, 2.3s, no counterexample)
```

**ATE_FUN evidence format** (per verified isolate):
```
Test Case: quic_server_test_stream/stream_send_isolate
  SFR Traced: rfc9000:4.1, rfc9000:8.1
  Verdict: PASS
  Z3 Time: 2.3s
  Dependencies: quic_types, quic_frame, quic_packet
```

**ATE_COV evidence format** (per test scope):
```
Protocol: QUIC (RFC 9000)
  Total MUST: 52, Covered: 47 (90.4%)
  Uncovered: [rfc9000:17.2.3, rfc9000:17.2.5, rfc9000:19.5, rfc9000:21.1, rfc9000:21.2]
  Delta: +3 newly covered since last assessment
```

---

## 5. Critical Files

| File | Purpose | Roadmap Items |
|------|---------|---------------|
| `ivy_lsp/tools/traceability.py` | MCP coverage/requirements + 7 legacy aliases | **F0a**, D1, I4 |
| `ivy_lsp/tools/visualization.py` | MCP visualization + 4 legacy aliases + `_resolve_scope` | **F0a**, **F0c** |
| `ivy_lsp/tools/patterns.py` | MCP patterns + 2 legacy aliases | **F0a** |
| `ivy_lsp/tools/quality.py` | MCP quality + 2 legacy aliases | **F0a** |
| `ivy_lsp/indexer/include_resolver.py` | Include resolution, staging, Errno 17 bug | **F0b**, F2, F5, T8 |
| `ivy_lsp/indexer/workspace_indexer.py` | Central indexer, deep_parse_on_demand | **F0d**, F1, D3, D4 |
| `ivy_lsp/features/hover.py` | Hover — wire demand-driven deep parse | **F0d** |
| `ivy_lsp/features/definition.py` | Goto-def — wire demand-driven deep parse | **F0d** |
| `ivy_lsp/features/document_symbols.py` | Outline — wire demand-driven deep parse | **F0d** |
| `ivy_lsp/analysis/test_scope.py` | NCT test scope model | Core novelty |
| `ivy_lsp/workspace_detection.py` | Workspace auto-detection | D4 |
| `ivy_lsp/semantic/analysis_pipeline.py` | 3-tier progressive analysis | D3 |
| `ivy_lsp/tools/verification.py` | ivy_verify, error parsing | D2, F4 |
| `panther-ivy-plugin/hooks/hooks.json` | Hook definitions | F3, D5 |
| `panther-ivy-plugin/CLAUDE.md` | Operating guide | All |
| `panther_ivy/ivy_command_mixin.py` | PANTHER workspace init | F5 validation |
| `.ivyworkspace` | Workspace config (v2) | F3, D4 |
