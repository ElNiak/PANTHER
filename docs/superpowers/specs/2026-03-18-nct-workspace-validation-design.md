# NCT Workspace Model Validation & Improvement Roadmap

**Date**: 2026-03-18
**Status**: Draft
**Scope**: Full-stack validation of ivy-lsp indexing + panther-ivy-plugin integration
**Audience**: Dual-purpose — engineering assessment (6-month POC guide) + academic framing (P6 Ivy LSP Tool Paper, AMC3 WP2 deliverables)

**Prior work this document builds on**:
- `2026-03-13-ivy-tooling-audit-results.md` — 25-tool quality audit (8 critical issues C1-C8)
- `2026-03-16-lsp-mcp-correctness-audit-results.md` — 45-validation correctness audit (FM-D, coverage inflation, semantic graph broken)
- `2026-03-16-ivy-plugin-evaluation-results.md` — 65-test plugin evaluation (72% pass rate)
- `2026-03-17-sota-evaluation-panther-ivy-plugin.md` — SOTA alignment (91.7%, 8 properties at 2/3)
- `2026-03-17-requirement-coverage-redesign.md` — 7-problem coverage redesign (4 phases)
- `2026-03-18-lsp-performance-pipeline-enablers.md` — Pipeline enabler plan (Tasks 1-7, **executed**)
- `2026-03-18-ivy-lsp-indexing-improvements-design.md` — 3-workstream improvement design

---

## 1. Context

The PANTHER/ivy-lsp/panther-ivy-plugin stack implements an "endpoint-mirror-as-workspace" model for NCT (Network-Centric Compositional Testing). Each master test file (e.g., `quic_client_test.ivy`) defines a complete workspace partition via its transitive include closure. The ivy-lsp server indexes this workspace, and the panther-ivy-plugin exposes it to Claude Code via MCP tools, hooks, skills, and agents.

Before AMC3 WP2's 6-month POC sprint (Feb-Aug 2026), this document validates whether:
1. The workspace model is conceptually sound and faithfully implemented
2. The current implementation is competitive with state-of-the-art formal language tooling
3. The gaps can be addressed within the POC timeline

This feeds into P6 (Ivy LSP Tool Paper, TACAS/FSE 2027) and P3 (Agent-Driven Evidence, ICSE 2027 SEIP).

---

## 2. Validation Assessment

### 2.1 Conceptual Validation

**Verdict: Sound, with two documented caveats.**

The model treats each test entry point as defining a complete workspace partition. This mirrors what `ivyc` sees when compiling that test.

**Evidence of correctness**:
- `_compute_test_scopes()` (`workspace_indexer.py`) walks files with exports, computes transitive closure via `IncludeGraph.get_transitive_includes()`, and registers a `TestScope` with `include_closure` (FrozenSet), `exported_actions`, `imported_actions`, and `tester_role`
- Role detection in `detect_test_role()` (`test_scope.py`) implements Ivy's role inversion
- `test_file` parameter in coverage tools filters requirements to `scope.include_closure`, matching the files PANTHER copies into the Docker staging directory

**Caveat 1 — Basename collision semantics**: Flat symlink staging mirrors `ivyc`'s CWD-relative resolution. Partitioned staging via graph coloring handles conflicts. O(T x B x V) complexity — negligible for QUIC (~200 files, ~30 collisions, ~20 test scopes).

**Caveat 2 — No cross-scope invariant checking**: Each test scope is independent. Shared files maintain assume-guarantee contracts by Ivy's compositionality, but not surfaced as verifiable.

### 2.2 Layer-by-Layer Assessment

#### Layer 1: Workspace Detection (`workspace_detection.py`, ~320 lines) — Adequate

**Implementation**: 6-strategy priority chain with v2 `.ivyworkspace` schema.

**Edge cases**: Walk-down returns FIRST marker, not closest. PANTHER heuristic could false-positive.

**Gap**: No multi-root workspace (LSP 3.6). No `.ivyworkspace` v3 with `workspace_layers` for APT separation.

#### Layer 2: Include Resolution (`include_resolver.py`, ~550 lines) — Novel, Strong

**Implementation**: 4-step resolution chain. Flat symlink staging. Partitioned staging via graph coloring.

**Critical finding — ivyc divergence**: LSP step 3 (workspace root) is extra — could resolve files ivyc wouldn't.

**Known bug — Errno 17**: `build_partitioned_staging()` line 446 calls `os.symlink()` without `os.path.lexists()` guard. Main staging has this guard but partitioned variant does not.

**Known bug — `os.path.exists()` vs `lexists()`**: Main staging at line 265 uses `exists`, not `lexists` — misses dangling symlinks.

**Edge cases**: ~50 APT/standard collisions + ~30 intra-QUIC collisions. No VFS abstraction.

**Gaps**: (a) Collisions not surfaced as diagnostics. (b) Errno 17 bug. (c) No VFS abstraction. (d) APT/standard separation needed (v3 schema).

#### Layer 3: Two-Phase Indexing (`workspace_indexer.py`, ~1370 lines) — Good Tradeoff

**Implementation**: Phase 1 = fast lexer scan (1-3s). Phase 2 = background full parse from test entry points (10-30s). Thread-safe symbol swapping.

**Recently completed**: `SymbolTable.remove_file()` (P1, commit `8241397`) and selective mirror-scope cache invalidation (P2, commit `fa45f92`) already implemented via pipeline enablers plan. Demand-driven deep parse for shared modules (P4, commit `f639105`) also complete.

**Remaining gap**: No incremental per-declaration re-indexing. No viewport-aware priority queue for Phase 2.

#### Layer 4: Test Scope Model (`test_scope.py`, ~328 lines) — Novel, Strong

**Implementation**: `TestScope` frozen dataclass. `ScopedRequirementModel` with per-test caching. NCT classification: `_generating` -> TESTER_ONLY, `after/around` -> GUARANTEE, `ensure/assert` -> GUARANTEE, else ASSUMPTION.

**Gap**: No cross-scope invariant checking.

#### Layer 5: Semantic Model (`analysis_pipeline.py` ~940 lines, `model.py` ~295 lines) — Adequate

**Implementation**: T1 (<50ms), T2 (<200ms), T3 (background). Thread-safe with RLock and generation tracking.

**Known bug — semantic graph non-functional** (03-16 audit): `ivy_impact_analysis`, `ivy_cross_references`, and `ivy_action_dependency_graph` all return empty edge lists. The MCP semantic model builds nodes but never computes edges. LSP `findReferences` works (1404 references for `cid`), proving data exists but MCP layer doesn't use it.

**Gap**: No per-position semantic data (Lean 4 InfoTree equivalent). Empty semantic graph edges.

#### Layer 6: MCP Tools (`tools/`, 6 modules, ~130KB) — Novel, Strong

**Implementation**: 33 registered `@mcp.tool()` functions — **18 primary tools + 15 legacy aliases**. `test_file` scoping correctly implements endpoint-mirror. Path traversal prevention. Lazy model construction.

**Recently fixed**: `ivy_quality(mode="suggestions")` context scoping (P8, commit `6f4b504`).

**Known bug — FM-D diagnostic parsing** (03-16 audit, top critical): `parse_ivy_output()` fails on absolute paths in MCP staging mode, causing `ivy_verify`, `ivy_compile`, `ivy_model_info` to return `diagnostics=[]` when errors exist. Structured diagnostics silently dropped.

**Known bug — coverage inflation** (03-16 audit, 03-17 coverage redesign): Bare `# [N]` tags on struct fields are false-positive matched to `rfc9000:N.*` requirements. Coverage stats and gaps tools disagree by 21 requirements. See `2026-03-17-requirement-coverage-redesign.md` for the 7-problem analysis and 4-phase fix design.

**Gaps**: (a) 15 legacy aliases bloat prompt ~45% (33->18 after removal). (b) No CC evidence export. (c) No taxonomy categorization. (d) FM-D diagnostic parsing. (e) Coverage correctness (7 problems per redesign spec).

#### Layer 7: Plugin Integration (`panther-ivy-plugin`) — Novel Architecture

**Implementation**: 10 hook points, 15 observability scripts, CLI enforcement, auto-lint. 4 agents, 11 skills, 9 commands. `/nct-validate` with 55 checks.

**SOTA gaps at 2/3** (per 03-17 evaluation): A1 (verify loop guided but not enforced), A2 (error categorization incomplete), A3 (cross-references broken), A4 (file-level caching only, no per-isolate).

**Gap**: No iterative verification skill, no LLM diff-checker.

### 2.3 Alternative Approaches Analysis

#### Workspace Scoping

| Approach | Verdict | Reasoning |
|----------|---------|-----------|
| **Endpoint-mirror (current)** | **Keep** | NCT-aligned, matches PANTHER runtime, enables per-test coverage |
| Module-based (Lean 4 style) | Incompatible | Ivy `include` is textual inclusion — would require language changes |
| Project-wide | Loses NCT alignment | Can't answer "which tests cover this requirement?" |
| On-demand/lazy (Coq Fleche) | Incompatible with agent workflow | Agent needs workspace-wide views |

#### Include Resolution

| Approach | Verdict | Reasoning |
|----------|---------|-----------|
| **Flat symlink staging (current)** | **Keep** | Faithful to ivyc, manageable complexity |
| FUSE/overlay FS | Reject | macOS FUSE deprecated, Linux needs container privileges |
| Rewrite-based | Reject | Changes file semantics, breaks ivyc |
| Compiler-integrated | Reject (hybrid possible) | Use T3 to validate T2 resolution |

#### Indexing Strategy

| Approach | Verdict | Reasoning |
|----------|---------|-----------|
| **Two-phase lexer+parser (current)** | **Keep** | Best latency/correctness tradeoff |
| Single-phase full parse | Reject | 30-60s startup blocks agent |
| Incremental per-declaration | Future enhancement | Requires tree-sitter or custom parser |
| Demand-driven | Reject | First coverage query triggers full parse anyway |

#### MCP Tool Design

| Approach | Verdict | Reasoning |
|----------|---------|-----------|
| **Mode-based consolidation (18 tools)** | **Keep** | Sweet spot of discoverability vs context efficiency |
| One-tool-per-operation (30+) | Reject | Context overhead, wrong tool selection |
| GraphQL-style single query | Reject | Shifts complexity to query construction |

#### Plugin Architecture

| Approach | Verdict | Reasoning |
|----------|---------|-----------|
| **Full plugin (skills + agents + hooks + commands)** | **Keep** | Essential enforcement and guidance |
| Pure-MCP (tools only) | Loses enforcement | No hooks, agents, skills, observability |
| IDE extension (VS Code) | Complementary | Targets humans, not AI agents |

### 2.4 Threats to Validity

| # | Threat | Prob | Severity | Mitigation In Place | Mitigation Needed |
|---|--------|------|----------|---------------------|-------------------|
| T1 | Basename collision -> wrong include | MED | HIGH | Collision map, partitioned staging | Conformance tests (F5) |
| T2 | Phase 1 regex misses includes | LOW | MED | Regex covers all standard Ivy; Phase 2 validates | None |
| T3 | NCT classification incorrectness | MED | HIGH | Tested; `_generating` is reliable convention | Cross-validate against manual annotation |
| T4 | MCP/LSP semantic model divergence | MED | MED | Shared `build_semantic_model` | Add comparison test |
| T5 | Role detection heuristic brittleness | LOW/HIGH | MED | Returns "unknown" when no match | Explicit role annotation |
| T6 | Single-protocol evaluation | HIGH | MED | QUIC only | Demonstrate on CoAP by P6 |
| T7 | Ground truth staleness | MED | MED | nct-validate 55 checks | Automated ground truth (I4) |
| T8 | Std lib version mismatch | MED | MED | LSP selects highest; ivyc selects lowest >= lang version | Fix LSP algorithm (F6) |
| T9 | Context window saturation | HIGH | MED | Skills on demand; mode consolidation | Token budget tracking |
| T10 | Observability event-loss | LOW | LOW | `atexit` handlers | Event-loss detection (D5) |
| T11 | Coverage inflation (NEW) | HIGH | HIGH | None | Tag disambiguation (coverage redesign Phase 1) |
| T12 | FM-D diagnostic parsing (NEW) | HIGH | HIGH | Errors in `raw_output` field | Fix `parse_ivy_output()` absolute path handling |

### 2.5 Related Work Comparison

| System | Language | Scoping | Incremental | MCP/Agent | RFC Traceability | CC Evidence |
|--------|----------|---------|-------------|-----------|------------------|-------------|
| **ivy-lsp** | Ivy 1.7 | Endpoint-mirror | Per-file | 18 MCP + 4 agents | Bracket tags + manifests | Planned |
| Lean 4 LSP | Lean 4 | Module | Per-declaration | No | N/A | No |
| Coq Fleche | Coq | Document | Per-sentence | No | N/A | No |
| DafnyPro | Dafny | Function | No | No | N/A | No |
| lean-lsp-mcp | Lean 4 | Module | Reuses Lean | MCP wrapper (5 tools) | N/A | No |
| SpecGen | Multiple | N/A | N/A | LLM loop | N/A | No |

**Key differentiators**: See prior version for full comparison prose (vs Lean 4, Coq Fleche, DafnyPro, lean-lsp-mcp, SpecGen).

### 2.6 Known Bug Index

Cross-reference of unfixed bugs from prior audits with roadmap items or status:

| Bug ID | Source | Description | Status / Roadmap Item |
|--------|--------|-------------|----------------------|
| C1 | 03-13 audit | Workspace root misconfiguration (path without `protocol-testing/` prefix) | Partially mitigated by `validate_path` fallback |
| C2 | 03-13 audit | `test_file` ignored on all visualization tools | **Fixed** (mode-based consolidation + scoping) |
| C3 | 03-13 audit | `ivy_smart_suggestions` all params ignored | **Fixed** (P8, commit `6f4b504`) |
| C4 | 03-13 audit | 0% coverage despite annotations (tag format mismatch) | Coverage redesign Phase 1 |
| C5 | 03-13 audit | `ivy_include_graph` path key mismatch | **Fixed** (normalize graph keys) |
| C6 | 03-13 audit | hover nearly broken | **Partially fixed** (03-16 work); hover text duplication remains |
| C7 | 03-13 audit | workspaceSymbol no filtering | **Fixed** (scope-ranking, commit series) |
| C8 | 03-13 audit | `ivy_action_requirements` file_path empty | **Fixed** (consolidated into `ivy_model_summary`) |
| FM-D | 03-16 audit | Diagnostic parsing broken on absolute paths | **Unfixed** — D2 partially addresses; needs dedicated fix (T12) |
| FM-B | 03-16 audit | Cross-workspace symbol disambiguation | APT workspace separation (D4) |
| -- | 03-16 audit | Semantic graph edges all empty | **Unfixed** — needs dedicated fix (D6) |
| -- | 03-16 audit | Coverage stats/gaps disagree by 21 reqs | Coverage redesign Phase 1 |
| -- | 03-16 audit | Scaffold checker false negatives | **Unfixed** — low priority |
| P1-P7 | 03-17 coverage redesign | 7 coverage correctness problems | Coverage redesign Phases 1-4 |

---

## 3. Improvement Roadmap

### Completed Work (Pipeline Enablers Plan, executed)

The following items from `2026-03-18-lsp-performance-pipeline-enablers.md` are already implemented:

| Task | Description | Commit |
|------|-------------|--------|
| P1 | `SymbolTable.remove_file()` in-place removal | `8241397` |
| P2 | Mirror-scope selective cache invalidation | `fa45f92` |
| P4 | Demand-driven deep parse for shared modules | `f639105` |
| P8 | `ivy_quality` context scoping fix | `6f4b504` |

### Phase 0: Immediate — Remove Legacy Debt & Fix Bugs

#### F0a: Remove 15 Legacy MCP Tool Aliases (33 -> 18 tools)

**Problem**: 15 backward-compatibility `@mcp.tool()` aliases duplicate the 18 primary consolidated tools. They bloat the MCP prompt ~45% and confuse tool selection. Plugin docs already use consolidated names only (verified by `test_documentation.py`).

**Aliases to delete** (4 files, 33 total registrations -> 18 after removal):

| Module | Current Count | Aliases to Delete | After |
|--------|--------------|-------------------|-------|
| `traceability.py` | 11 | `ivy_requirement_coverage`, `ivy_coverage_gaps`, `ivy_traceability_matrix`, `ivy_query_symbol`, `ivy_impact_analysis`, `ivy_cross_references`, `ivy_generate_manifest` (7) | 4 |
| `visualization.py` | 6 | `ivy_action_dependency_graph`, `ivy_state_machine_view`, `ivy_layered_overview`, `ivy_action_requirements` (4) | 2 |
| `patterns.py` | 4 | `ivy_pattern_analysis`, `ivy_scaffold_check` (2) | 2 |
| `quality.py` | 3 | `ivy_smart_suggestions`, `ivy_quality_gate` (2) | 1 |

**Verification**: `pytest tests/`, `/nct-validate` (update tool count ground truth), `/nct-health`.

**Effort**: 1 day.

#### F0b: Fix Errno 17 Symlink Bug

`build_partitioned_staging()` at `include_resolver.py:446` — add `if os.path.lexists(link_path): os.unlink(link_path)` before `os.symlink()`. Also fix main staging to use `lexists` instead of `exists` (line 265) to catch dangling symlinks. Add startup cleanup for stale `ivy-lsp-stage-*` dirs.

**Effort**: 1 hour.

#### F0c: Fix FM-D Diagnostic Parsing (T12)

`parse_ivy_output()` fails on absolute paths in MCP staging mode. `ivy_verify`, `ivy_compile`, `ivy_model_info` return `diagnostics=[]` silently. Fix regex to handle absolute paths.

**Effort**: 2-3 hours.

---

### Phase 1: Foundation (Months 1-2) — LSP Core + LLM Safety

#### F1: Coverage Correctness (Tag Disambiguation + Manifest Validation)

**Problem**: 7 coverage problems identified in `2026-03-17-requirement-coverage-redesign.md`. False-positive bare numeric tags inflate coverage. Orphan detection inconsistent. Missing manifest = silent zero.

**Changes**: Implement Phases 1-2 of the coverage redesign:
- Phase 1a: Filter false-positive bare numeric tags in `parse_file_rfc_annotations()`
- Phase 1b: Align orphan detection with coverage computation
- Phase 1c: Manifest field validation
- Phase 1d: Missing manifest warning
- Phase 1e: Ambiguous tag warning
- Phase 2: RFC fetcher + section-aware parser

**Effort**: 3 weeks. **Impact**: P6 (credible coverage data for paper), P3 (CC evidence accuracy).

#### F2: Basename Collision Diagnostics

Surface collision map as LSP Warning diagnostics + `collisions` field in `ivy_include_graph` response.

**Effort**: 1 week. **Impact**: P6.

#### F3: LLM Diff-Checker Hook

PreToolUse hook for `Write|Edit` with `frozen_files` in `.ivyworkspace`.

**Effort**: 2 weeks. **Impact**: P3 (gatekeeper).

#### F4: Iterative Verification Skill

New `skills/iterative-verification/SKILL.md` — CEGAR loop with structured iteration logging. Addresses SOTA property A1 (verify loop enforcement).

**Effort**: 2 weeks. **Impact**: P3 (core loop), SOTA A1.

#### F5: Conformance Tests Against ivyc

New `tests/conformance/` — compare LSP include closure against `ivyc` actual resolution.

**Effort**: 1 week. **Impact**: P6 (threat T1 mitigation).

#### F6: Fix Std Lib Version Selection (T8)

Fix `_get_std_include_dir` in `include_resolver.py` to match ivyc's algorithm: select lowest version >= language version, not highest.

**Effort**: 2 hours. **Impact**: T8 mitigation.

### Phase 2: Depth & Trust (Months 3-4) — CC Evidence + Verification Loop

#### D1: CC Evidence Export

New MCP tool `ivy_cc_evidence(mode="adv_fsp"|"ate_fun"|"ava_van"|"ate_cov"|"full")`.

| CC Family | ivy-lsp Artifact |
|-----------|------------------|
| ADV_FSP.1-6 | Exported actions + guards + state model + Ivy source + Z3 proofs |
| ATE_FUN.1-2 | Per-isolate verdicts + 14-layer dependency graph |
| AVA_VAN.1-5 | NACT error injection/mutation results |
| ATE_COV.1-3 | Requirement coverage per test scope |

**Effort**: 3-4 weeks. **Impact**: P3 (flagship), WP2 D2.3.

#### D2: Verification Failure Repair Hints

Add `error_category` enum and `repair_hints` to `ivy_verify` response. Addresses SOTA property A2.

**Effort**: 3 weeks. **Impact**: P3 + P6, SOTA A2.

#### D3: Snapshot-Based Incremental Model Updates

Incremental `requirement_graph.update_file()` + content hash tracking.

**Effort**: 4 weeks. **Impact**: P6.

#### D4: APT Workspace Separation (`.ivyworkspace` v3)

`.ivyworkspace` v3 schema with `workspace_layers` (per indexing-improvements WS3-3.1). Eliminates ~50 APT/standard collisions at source. Per-layer staging directories.

**Effort**: 3 weeks. **Impact**: P6, T1 mitigation.

#### D5: Observability Event-Loss Detection

Monotonic event counter + sequence numbering + gap detection at Stop.

**Effort**: 1 week. **Impact**: P3.

#### D6: Fix Semantic Graph Edge Computation (NEW)

The MCP semantic model builds nodes but never computes edges. `ivy_impact_analysis`, `ivy_cross_references`, `ivy_action_dependency_graph` return empty results. LSP `findReferences` proves the data exists. Bridge LSP reference data into MCP semantic model. Addresses SOTA property A3.

**Effort**: 2-3 weeks. **Impact**: P6 (visualization tools), SOTA A3.

### Phase 3: Integration & Demo (Months 5-6) — Polish

#### I1: LSIF Export

New `ivy_lsp/lsif/exporter.py` (LSIF 0.4). MCP tool + CLI.

**Effort**: 3 weeks. **Impact**: P6 (artifact).

#### I2: End-to-End Demo

Scripted: lint -> verify -> fix -> re-verify -> coverage -> quality gate -> CC evidence. New `/nct-demo` command.

**Effort**: 2 weeks. **Impact**: P3 + WP2.

#### I3: Paper Evaluation Infrastructure

New `evaluation/` with latency/accuracy/convergence benchmarks. See RQ1-RQ4.

**Effort**: 3 weeks. **Impact**: P6.

#### I4: Automated Ground Truth from ivyc

Script that captures ivyc include resolution, generates `quic-workspace.yaml`. CI integration.

**Effort**: 1 week. **Impact**: P6 + nct-validate.

### Deferred / Out of Scope for 6-Month POC

| Item | Source | Reason |
|------|--------|--------|
| VFS abstraction layer (`IvyVFS` protocol) | Indexing improvements WS1-1.2 | Major refactor; Errno 17 fix (F0b) is sufficient for POC |
| Viewport-aware indexing priority queue | Indexing improvements WS1-1.3 | Demand-driven deep parse (P4, done) covers the primary use case |
| Qualified includes proposal (`include quic.quic_types`) | Indexing improvements WS3-3.2 | Academic/long-term; doesn't affect POC pipeline |
| Tool taxonomy categorization (6 categories) | Indexing improvements WS2-2.2 | Nice-to-have; CLAUDE.md already provides structured guidance |
| Per-isolate verification caching (SOTA A4) | SOTA eval | Significant effort; file-level caching adequate for POC |
| Scaffold presets (P3) | Pipeline enablers Task 5 | Plugin UX improvement, not on critical path |
| Skill prerequisites frontmatter (P13) | Pipeline enablers Task 6 | Plugin UX improvement, not on critical path |
| Coverage redesign Phases 3-4 (lifecycle, multi-protocol) | Coverage redesign | Phase 1-2 sufficient for POC; Phases 3-4 are post-POC |

---

## 4. Academic Positioning

### 4.1 P6 Paper Evaluation Methodology

**RQ1: Endpoint-mirror scoping accuracy vs project-wide**
- Compare `ivy_coverage(mode="stats")` globally vs per `test_file`
- Metrics: false positive rate, phantom coverage inflation
- Expected: Project-wide inflates by 10-20% due to cross-scope tag bleeding
- Ground truth: Manual verification of 30 random requirements (from 97 total in `rfc9000_requirements.yaml`)

**RQ2: LSP response latency across workspace sizes**
- Synthetic workspaces: 10, 50, 100, 200, 500 files
- Thresholds: Interactive <100ms p95, analysis <500ms p95, index <5s for 200 files
- Report p50/p95/p99 for each tool

**RQ3: Agent verification loop effectiveness (F4)**
- 30 QUIC MUST requirements not yet formalized
- Metrics: iterations-to-fix, success rate, time-to-fix, manual intervention rate
- Expected: lint first-pass 85-90%, verify first-pass 40-60%, mean iterations 2-4, 75-85% within 5
- Comparison: DafnyPro's 2.3 mean iterations (POPL 2026)

**RQ4: Requirement extraction accuracy**
- Compare `ivy_extract_requirements` vs manual `rfc9000_requirements.yaml` (97 reqs)
- Metrics: precision (60-70%), recall (70-80%), F1, level accuracy (90%+)
- Note: Must run AFTER F1 (tag disambiguation) to avoid false-positive inflation

### 4.2 Novelty Claims

1. **Endpoint-mirror workspace partitioning** — No prior art for test-entry-point-based workspace scoping in formal LSPs.
   - *Objection*: "QUIC-specific." *Response*: 14 layers map to general protocol engineering concepts.

2. **Flat-symlink staging with graph-coloring partition isolation** — Novel for flat-include languages.
   - *Objection*: "Why not fix the language?" *Response*: Ivy is maintained by Microsoft Research.

3. **Three-tier progressive analysis for flat-include languages** — T1<50ms, T2<200ms, T3 background. The unique constraint: include graph must be materialized before semantic analysis can begin (no hierarchical module system to guide ordering).
   - *Objection*: "Lean 4 does this better." *Response*: Lean 4's per-declaration model assumes hierarchical modules. Our flat-include constraint makes the problem fundamentally different.

4. **MCP-wrapped formal verification with RFC traceability** — 18 tools with bracket tags, coverage matrices, quality gates.
   - *Objection*: "lean-lsp-mcp also wraps LSP." *Response*: 5 thin wrappers vs 18 deep-integrated tools with traceability.

5. **Agent-as-a-Guide for CC evidence** — First system to compose LSP + MCP + agent hooks to produce CC-compliant evidence chains from formal specifications.
   - *Objection*: "Engineering, not research." *Response*: The gatekeeper pattern (untrusted LLM -> LSP+Ivy -> trusted human) with observability analytics is a novel architectural contribution for safety-critical systems.

### 4.3 WP2 Deliverable Mapping

| Deliverable | What ivy-lsp Provides | Roadmap Items |
|-------------|----------------------|---------------|
| D2.1: Agent Architecture | "Agent-as-a-Guide" spec | F3, F4 |
| D2.2: Tool Integration | MCP API, hooks, observability | F0a, F2, D5 |
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

**ATE_COV evidence format** (per test scope):
```
Protocol: QUIC (RFC 9000)
  Total MUST: 45, Covered: 42 (93.3%)
  Manifest: rfc9000_requirements.yaml (97 requirements)
  Uncovered: [rfc9000:17.2.3, rfc9000:17.2.5, rfc9000:19.5]
```

---

## 5. Critical Files

| File | Purpose | Roadmap Items |
|------|---------|---------------|
| `ivy_lsp/tools/traceability.py` | MCP coverage/requirements + 7 legacy aliases | **F0a**, F1, D1, I4 |
| `ivy_lsp/tools/visualization.py` | MCP visualization + 4 legacy aliases | **F0a** |
| `ivy_lsp/tools/patterns.py` | MCP patterns + 2 legacy aliases | **F0a** |
| `ivy_lsp/tools/quality.py` | MCP quality + 2 legacy aliases | **F0a** |
| `ivy_lsp/tools/verification.py` | ivy_verify, diagnostic parsing | **F0c**, D2, F4 |
| `ivy_lsp/indexer/include_resolver.py` | Include resolution, staging, Errno 17 | **F0b**, F2, F5, F6, T8 |
| `ivy_lsp/indexer/workspace_indexer.py` | Central indexer | D3, D4 |
| `ivy_lsp/semantic/rfc_annotations.py` | Tag parsing, coverage computation | F1 (coverage correctness) |
| `ivy_lsp/features/visualization.py` | `_resolve_scope`, smart_suggestions | Already fixed (P8) |
| `ivy_lsp/analysis/test_scope.py` | NCT test scope model | Core novelty |
| `ivy_lsp/workspace_detection.py` | Workspace auto-detection | D4 |
| `ivy_lsp/semantic/analysis_pipeline.py` | 3-tier progressive analysis | D3, D6 |
| `panther-ivy-plugin/hooks/hooks.json` | Hook definitions | F3, D5 |
| `panther-ivy-plugin/CLAUDE.md` | Operating guide | F0a (update tool refs) |
| `.ivyworkspace` | Workspace config (v2, upgrade to v3) | F3, D4 |
