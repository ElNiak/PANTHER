# Ivy Tooling Ecosystem: Strategic Evaluation & Consolidation

**Date**: 2026-03-13
**Scope**: Full strategic assessment of Ivy formal verification tooling (MCP + LSP + Claude Code integration)
**Inputs**: Audit scorecard (25 MCP tools, 14 LSP features), state-of-the-art survey, over-engineering analysis
**Goal**: Consolidation plan, gap analysis, and implementation roadmap

---

## 1. State of the Art Comparison

This section compares the Ivy tooling ecosystem against established formal verification, specification management, and AI-assisted development platforms across five dimensions. Each dimension surfaces where Ivy leads, where it lags, and where consolidation would sharpen its competitive position.

### Dimension 1: Code Intelligence (LSP)

| Capability | Lean 4 LSP | Dafny VS Code | TLA+ Toolbox | SPARK Ada GPS | Ivy LSP |
|------------|:----------:|:-------------:|:------------:|:-------------:|:-------:|
| Go-to-definition | Full (cross-file, cross-import) | Full | Full | Full | Partial (cross-include works; declarations return "not found"; dotted paths fail) |
| Find references | Full with scope awareness | Full | Find-in-project | Full with read/write distinction | Good cross-file (376 refs for `cid`); self-refs omitted; no read/write split |
| Hover info | Type + tactic state + doc | Type + triggers + verified status | Operator definitions | Type + contracts + SPARK annotations | Nearly broken (1/6 correct); no RFC enrichment active yet |
| Completion | Context-aware (tactics, terms) | Context-aware (keywords, ghost vars) | Action/variable names | Contracts + aspects | Keyword-only (not implemented in current LSP) |
| Diagnostics | Real-time, per-line verification status | Real-time, error squiggles + counterexample gutter marks | Model-check error overlay | Flow analysis + runtime checks | 5-layer graduated analysis (structural, lexer, semantic, coverage, pattern) via MCP; push-based LSP diagnostics not testable |
| Code lens | Proof state per declaration | Verify/debug lenses | N/A | Prove/examine lenses | Not implemented |
| Code actions | Quick fixes for proof failures | Quick fixes, extract method | N/A | Refactoring, proof completion | Not implemented |
| Rename | Full, safe | Full, safe | Basic find-replace | Full with semantic checks | Not tested (not exposed via Claude Code LSP tool); scope detection present |

**Ivy LSP strengths**:
- **3-tier graduated analysis** (structural, semantic, pattern) via `ivy_diagnostics` provides depth no other tool matches for a single diagnostics call
- **RFC annotation enrichment** in hover (when bracket tags exist) is unique -- no other LSP ties code symbols to normative requirements
- **Proximity-based disambiguation** in go-to-definition resolves ambiguous names using include-graph distance, handling Ivy's flat namespace without module qualifiers

**Ivy LSP gaps**:
- No interactive proof state display (Lean 4 and Dafny show tactic goals/verification status per line)
- No verification-as-you-type (Dafny and Lean 4 verify incrementally on keystroke; Ivy requires explicit `ivy_verify` MCP call)
- Keyword-only completion (Lean 4 and Dafny offer context-aware completions including tactic suggestions)
- No per-line verification status gutter marks (Dafny and SPARK show green/red per declaration)

### Dimension 2: Verification Integration

| Capability | Dafny | Lean 4 | TLA+ Toolbox | Tamarin | ProVerif | Ivy MCP |
|------------|:-----:|:------:|:------------:|:-------:|:--------:|:-------:|
| Incremental verification | Yes (per-method, cached) | Yes (per-definition) | Per-model (full re-check) | Per-lemma | Full model | No (full model re-check each time) |
| Counterexample display | Rich: variable values, execution trace, gutter marks | Tactic state at cursor | State graph + trace explorer | Attack graphs with MSC diagrams | Derivation trees | Raw text output only; no structured rendering |
| State space exploration | Bounded model checking | Proof search tree | Explicit-state model checker with state graph | Constraint solving trace | Horn clause resolution | No exploration; binary pass/fail |
| Verification-as-you-type | Yes (background worker, incremental) | Yes (persistent environment) | No (explicit run) | No (explicit run) | No (explicit run) | No (explicit `ivy_verify` call) |
| Docker/container support | No (native or dotnet) | No (native) | No (native Java) | No (native) | No (native) | Yes (Docker-aware pipeline with fallback) |
| Test binary generation | No (verified code is the artifact) | No (extracted code via tactics) | No | No | No | Yes (`ivyc target=test` produces C++ test binaries) |

**Ivy strengths**:
- **Docker-aware pipeline**: Verification, compilation, and test execution all work inside containers, enabling CI/CD integration that no other formal tool offers natively
- **Verification + compilation + test in one toolchain**: `ivy_verify` -> `ivy_compile` -> test binary execution is a unique pipeline; other tools stop at verification or code extraction
- **LLM can orchestrate verification via MCP**: 25 tools with typed JSON schemas let an AI agent drive the entire verification workflow -- no other formal tool has this level of programmatic access

**Ivy gaps**:
- **No incremental verification**: Every `ivy_verify` call re-checks the entire model. For QUIC (202 files), this is prohibitive for iterative development
- **Raw text counterexamples**: When verification fails, output is unstructured text from `ivy_check`. Dafny and TLA+ render counterexamples as interactive execution traces
- **No state space exploration**: The tool reports pass/fail but provides no mechanism to explore why a property holds or what states were checked

### Dimension 3: Specification Traceability

| Capability | IBM DOORS Next | Reqtify | Polarion | Ivy MCP+LSP |
|------------|:--------------:|:-------:|:--------:|:-----------:|
| Requirement extraction | Manual import from documents | Regex-based extraction from documents | Manual + document connectors | Automated: `ivy_extract_requirements` parses MUST/SHOULD/MAY from RFC text with sentence boundary detection (4.6/5 audit score) |
| Annotation syntax | External linking (IDs in tool, not in code) | Pragma comments in code | External linking | Inline bracket tags `[rfc9000:4.1]` embedded directly in Ivy assertions |
| Coverage matrix | Full bidirectional traceability matrix | Forward trace from req to test | Bidirectional with work items | `ivy_traceability_matrix` + `ivy_requirement_coverage`: functional but tag format mismatch (bare `[4]` vs `rfc9000:4.1`) currently breaks matching (0% coverage despite annotations) |
| Gap analysis | Orphan detection both directions | Missing-link reports | Gap analysis dashboards | `ivy_coverage_gaps`: detects unguarded state variables, actions without requirement annotations, missing monitor patterns |
| Impact analysis | Change impact via bidirectional links | File-level impact tracing | Work item dependency graph | `ivy_impact_analysis`: symbol-level impact through semantic graph edges (types, actions, relations, read/write) |
| Integration with code | Separate from code (external tool) | Embedded pragmas, build integration | Separate tool with IDE plugins | **Native**: requirements live in the same `.ivy` files as the specification, verified by the same toolchain |

**Novel contribution**: No other formal verification tool integrates requirement traceability into the specification language itself. IBM DOORS, Reqtify, and Polarion are all external tools that link to code via IDs or pragmas. Ivy's bracket-tag annotation system (`[rfc9000:4.1]`) embeds requirements directly in assertions, enabling the toolchain to verify both the formal property AND its normative coverage simultaneously.

**Current limitation**: The tag format mismatch (C4 in audit backlog) means this capability is architecturally present but operationally broken. Fixing the `[N]` to `rfc9000:N` mapping would unlock what is genuinely a differentiating feature.

### Dimension 4: AI-Assisted Specification

| Capability | GitHub Copilot | Cursor | LLM+Lean (LeanDojo) | LLM+Coq (Proverbot9001) | Ivy MCP+Plugin |
|------------|:--------------:|:------:|:--------------------:|:------------------------:|:--------------:|
| Code completion | Token-level, statistical | Token + semantic (codebase RAG) | Tactic prediction | Tactic prediction | Not implemented (keyword-only LSP completion) |
| Structured semantic access | None (text-only context) | Codebase indexing (AST-level) | Lean server API (JSON) | SerAPI (S-expressions) | **21 MCP tools** with typed JSON schemas providing symbol info, include graphs, dependency analysis, traceability matrices, pattern detection |
| Specification generation | General code generation | General with context | Proof step generation | Proof search | `ivy_pattern_scaffold` generates complete Ivy specification templates for 5 pattern types (serdes, shim, entity, variants, monitors) with documentation |
| Workflow guidance | None | Tab-based suggestions | None | None | 14 Claude Code skills + 9 agents with methodology knowledge (specification creation workflow, quality gates, RFC analysis) |
| Quality enforcement | Linting only | Linting + review | Type checking | Type checking | `ivy_quality_gate` (3-tier: minimal/standard/comprehensive) + `ivy_scaffold_check` (14-layer architecture validation) + `ivy_diagnostics` (5-layer graduated analysis) |

**Ivy is ahead in one critical area**: Structured semantic access for AI agents. The 21 MCP tools provide typed, queryable access to the specification model that goes far beyond what any LLM+prover integration offers. LeanDojo and Proverbot9001 give LLMs access to tactic state; Ivy gives LLMs access to the entire specification architecture (symbols, dependencies, requirements, patterns, coverage, quality metrics).

**Diluted by over-proliferation**: The audit found that many tools overlap significantly (e.g., `ivy_impact_analysis` / `ivy_cross_references` / `ivy_query_symbol` query the same semantic model) and 7 visualization tools ignore their scoping parameters. Consolidation from 25 to ~12 tools would improve AI performance by reducing tool-selection confusion and ensuring each tool does one thing well.

### Dimension 5: Protocol-Specific Analysis

| Capability | Tamarin | ProVerif | Scyther | UPPAAL | Ivy PANTHER |
|------------|:-------:|:--------:|:-------:|:------:|:-----------:|
| Security property verification | Yes (Dolev-Yao, equational theories) | Yes (Horn clauses, unbounded) | Yes (bounded, automatic) | Timed automata only | Partial (safety properties, invariants, not cryptographic) |
| Compliance testing | No (security properties only) | No (security properties only) | No (security properties only) | No (timed properties only) | **Yes**: RFC requirement-level compliance with bracket-tag traceability |
| Attack visualization | MSC attack traces | Derivation graphs | Attack graphs | Simulation traces | Raw text only (no structured attack rendering) |
| Test generation | No (model checking only) | No (analysis only) | No (analysis only) | Test generation from traces | **Yes**: `ivyc target=test` generates executable C++ test binaries |
| Deployment integration | No (standalone analysis) | No (standalone analysis) | No (standalone analysis) | No (standalone analysis) | **Yes**: Docker-aware, integrated with PANTHER CI/CD pipeline, tests run against real implementations |
| Multi-protocol | No (one model per analysis) | No (one model per analysis) | Multi-protocol (limited) | Component-based | **Yes**: QUIC, BGP, CoAP, custom protocols in unified workspace |

**Ivy's niche**: Protocol compliance testing with deployment integration. Tamarin, ProVerif, and Scyther excel at cryptographic security analysis but produce no executable tests and cannot check RFC compliance. UPPAAL handles timed systems but not protocol specifications. Ivy PANTHER uniquely bridges formal specification to executable conformance testing against real protocol implementations in Docker containers.

**Ivy's weakness**: Security property verification. Tamarin and ProVerif handle Dolev-Yao attackers, equational theories, and unbounded sessions -- capabilities fundamentally absent from Ivy's first-order logic framework. Ivy's `quic_attacks_stack/` models MitM scenarios but at a much coarser granularity.

---

## 2. Over-Engineering Assessment

This section evaluates the current tooling surface for over-engineering: features that add complexity without proportional value, and identifies what to consolidate, cut, or keep.

### 2.1 MCP Tool Proliferation (25 -> 12)

**Problem**: 25 MCP tools cause tool-selection confusion for AI agents. The audit found:
- 3 tools query the same semantic model with overlapping results (`ivy_impact_analysis`, `ivy_cross_references`, `ivy_query_symbol`)
- `ivy_lint` is a strict subset of `ivy_diagnostics` (structural layer)
- 7 visualization tools share broken `test_file` handling code
- Several tools produce unusably large output without working scoping parameters

**Consolidation table**:

| Current Tool(s) | Merged Into | Rationale |
|-----------------|-------------|-----------|
| `ivy_lint` + `ivy_diagnostics` | **`ivy_diagnostics`** (add `layers` param) | ivy_lint is structural layer only; diagnostics is superset. Keep lint logic as fast path when `layers=["structural"]`. |
| `ivy_impact_analysis` + `ivy_cross_references` + `ivy_query_symbol` | **`ivy_symbol_info`** | All three query the semantic graph for a symbol. Merge into one tool: symbol name -> type info + edges + references. Accept both symbol names and node_ids. |
| `ivy_traceability_matrix` + `ivy_requirement_coverage` | **`ivy_traceability`** | Both query the same requirement manifest + annotation data. Matrix is the detail view, coverage is the summary. One tool with `detail` param. |
| `ivy_action_requirements` + `ivy_coverage_gaps` | **`ivy_coverage`** | Both analyze action-to-requirement mapping. Action_requirements shows what's covered; coverage_gaps shows what's missing. One tool with `mode=covered|gaps|both`. |
| `ivy_model_summary` + `ivy_layered_overview` | **`ivy_overview`** | Both produce high-level model summaries with different grouping. One tool with `group_by=file|module|layer`. |
| `ivy_action_dependency_graph` + `ivy_state_machine_view` | **`ivy_graph`** | Both produce graph structures over actions and state. One tool with `view=dependencies|state_machine`. |
| `ivy_scaffold_check` + `ivy_quality_gate` | **`ivy_quality`** | Scaffold_check evaluates 14-layer completeness; quality_gate checks 3-tier pass/fail. Both assess model maturity. One tool with `mode=check|gate`, `level=minimal|standard|comprehensive`. |
| `ivy_smart_suggestions` | **Cut entirely** | All parameters ignored (1.6/5 audit score). Returns identical 114KB dump regardless of input. Resurrect only after implementing actual context-awareness. |
| `ivy_verify` | **Keep** | Core verification, no overlap |
| `ivy_compile` | **Keep** | Core compilation, no overlap |
| `ivy_capabilities` | **Keep** | Environment introspection, no overlap |
| `ivy_include_graph` | **Keep** | Unique include-chain analysis |
| `ivy_model_info` | **Keep** | Raw `ivy_show` output, useful for debugging |
| `ivy_extract_requirements` | **Keep** | RFC text parsing, highest audit score (4.6/5) |
| `ivy_generate_manifest` | **Keep** | Manifest generation from RFC text |
| `ivy_pattern_analysis` | **Keep** | Pattern detection/validation/comparison, high audit score (4.4/5) |
| `ivy_pattern_scaffold` | **Keep** | Template generation, highest audit score (4.6/5) |

**Result**: 25 tools -> 12 tools (7 merged pairs, 1 cut, 10 kept, 1 new merged tool)

### 2.2 Agent Proliferation (9 -> 4)

**Problem**: 9 specialized agents fragment the workflow. An LLM choosing between 9 agents faces the same combinatorial confusion as choosing between 25 tools.

| Current Agents | Merged Into | Rationale |
|----------------|-------------|-----------|
| `spec-author`, `spec-reviewer`, `pattern-advisor` | **`specification-agent`** | All three operate on specification creation/editing. One agent with mode switching. |
| `verification-runner`, `diagnostics-analyst` | **`verification-agent`** | Both drive verification tools and interpret results. |
| `coverage-tracker`, `traceability-auditor` | **`compliance-agent`** | Both analyze requirement coverage and traceability. |
| `scaffold-generator`, `quality-assessor` | **`quality-agent`** | Both evaluate and improve model quality/completeness. |
| `workflow-orchestrator` | **Cut** | Meta-agent that dispatches to other agents; with 4 well-scoped agents, orchestration is simpler and can be handled by the primary Claude conversation. |

**Result**: 9 agents -> 4 agents

### 2.3 Skill Proliferation (16 -> 6)

**Problem**: 16 skills create a large surface area where many skills overlap or are thin wrappers around a single MCP tool call.

| Current Skills | Merged Into | Rationale |
|----------------|-------------|-----------|
| `create-spec`, `create-from-rfc`, `scaffold-protocol` | **`/spec-create`** | All produce new specification files. One skill with `--from-rfc`, `--from-pattern`, `--blank` flags. |
| `run-verification`, `run-diagnostics`, `run-lint` | **`/verify`** | All invoke verification/analysis tools. One skill with `--mode verify|diagnostics|lint`. |
| `check-coverage`, `check-traceability`, `check-quality` | **`/assess`** | All evaluate model quality from different angles. One skill combining all checks with summary. |
| `generate-manifest`, `extract-requirements` | **`/rfc-tools`** | Both process RFC text. One skill with subcommands. |
| `show-model`, `show-graph`, `show-overview` | **`/inspect`** | All display model information. One skill with `--view model|graph|overview|symbols`. |
| `pattern-detect`, `pattern-scaffold` | **`/patterns`** | Both work with the pattern catalog. One skill with `--detect` and `--scaffold` modes. |
| Remaining standalone skills | **Keep individually if distinct** | Skills that map to unique workflows (e.g., `fix-diagnostics`, `explain-error`) remain if they provide genuine multi-step orchestration. |

**Result**: 16 skills -> 6 skills

### 2.4 SubagentStop Quality Gates: Cut

**Current behavior**: A `SubagentStop` hook kills sub-agents if quality thresholds are not met.

**Cut rationale**:
- Produces confusing UX when agents are terminated mid-task
- Quality enforcement is better handled at the _result_ level (reject output, don't kill the worker)
- The consolidated `ivy_quality` tool provides the same gate checks on demand
- Agents should be allowed to complete and report, with quality issues surfaced in the response

### 2.5 PreToolUse Hook: Soften to Warning

**Current behavior**: A `PreToolUse` hook blocks tool calls that violate preconditions (e.g., calling `ivy_verify` without an active test file).

**Soften rationale**:
- Blocking tool calls disrupts agent workflow and produces cryptic "tool call rejected" errors
- The underlying tools already have error handling (audit scored 3-4/5 on error handling)
- Better approach: emit a warning in the tool response (e.g., `"warning": "No active test file set; results may be workspace-global"`) and let the agent decide
- Keep the hook for genuinely dangerous operations (path traversal is already handled by `_validate_path`)

### 2.6 Borderline (Keep but Simplify)

| Component | Current State | Simplification |
|-----------|---------------|----------------|
| **14-layer template architecture** | Scaffold_check evaluates 14 layers (types, packet, frame, connection, crypto, shim, behavior, monitors, properties, test_specs, application, recovery, extensions, documentation). | Keep the layer model -- it's architecturally sound and unique. But simplify scoring: instead of binary present/absent per layer, add weighted scoring based on layer importance for the target protocol. Not every protocol needs all 14 layers. |
| **Docker executor in MCP** | `ivy_compile` and `ivy_verify` spawn Docker containers when tools aren't on PATH. Silent fallback. | Keep Docker execution (it's a competitive advantage). Add `"execution_mode": "docker"|"subprocess"` to response (M2 from audit backlog). Log fallback at INFO. |
| **Slash command routing** | 16 slash commands route to skills via Claude Code's skill system. | Reduce to 6 slash commands (matching consolidated skills). Ensure each maps to a genuine multi-step workflow, not a single tool call. |

### 2.7 Well-Designed (Keep As-Is)

These components scored well in the audit and represent genuine engineering value:

| Component | Why Keep | Audit Evidence |
|-----------|----------|----------------|
| **RFC traceability system** | Unique in formal verification space. Bracket-tag annotations + manifest + coverage matrix = novel contribution. | `ivy_extract_requirements` scored 4.6/5. Architecture is sound; only tag format matching needs fixing (C4). |
| **Semantic graph** | Powers symbol resolution, impact analysis, cross-references. Lightweight regex-based but effective for Ivy's syntax. | Correctly resolves types, actions, relations, functions. Sparse edges are a known limitation, not a design flaw. |
| **3-tier graduated analysis** | Structural (fast, no state) -> Semantic (model-aware) -> Pattern (architecture-aware). Each layer adds cost and depth. | `ivy_diagnostics` scored 3.6/5, best in G3. 182 diagnostics for quic_frame.ivy across 5 layers shows depth. |
| **Include resolver** | Handles Ivy's include-path-based module system with ambiguity detection and proximity ranking. | Powers go-to-definition (cross-include works), findReferences (376 results for `cid`), and the include graph. |
| **Lazy initialization** | Semantic model, include graph, and file index built on first access, not on server startup. | Prevents 680-file indexing on cold start. Tools that don't need the semantic model don't pay for it. |
| **PostToolUse lint hook** | Runs `ivy_lint` automatically after file modifications to catch structural errors immediately. | Fast feedback loop. Lint is cheap (sub-millisecond for structural checks). Keeps the "break early" philosophy. |
| **SessionStart detection** | Detects workspace layout, available protocols, and tool capabilities at session start. | Provides context to agents/skills without requiring explicit initialization calls. |
| **Path traversal protection** | `_validate_path()` uses `os.path.realpath` + prefix check. Rejects `../../../etc/passwd`. | Confirmed working in audit (security scenario 7). Correct approach. |

---

## 3. Missing Capabilities (Post-Consolidation)

After consolidation reduces noise, these are the genuine capability gaps that, if filled, would move Ivy tooling from "useful" to "competitive with state-of-the-art."

### Priority 1: Incremental Verification Feedback

**Gap**: Every `ivy_verify` call re-checks the entire model. For QUIC (202 files), this means multi-minute verification cycles even for single-line changes. Lean 4 and Dafny verify incrementally per-definition.

**Proposed approach**:
- Track file modification timestamps and include-graph edges
- On `ivy_verify`, compute the "dirty set" (modified files + their transitive dependents)
- If dirty set is small, pass only affected isolates to `ivy_check`
- Cache verification results keyed by file content hash + dependency hashes
- Expose `"incremental": true|false` and `"cached_isolates": N` in response

**Complexity**: High. Requires understanding Ivy's isolate boundaries and which checked properties depend on which definitions. May require cooperation with `ivy_check` itself (currently treats the model as monolithic).

**Impact**: Transforms the development loop from "edit -> wait minutes -> see result" to "edit -> wait seconds -> see result." This is the single biggest productivity gap versus Lean 4 and Dafny.

### Priority 2: Counterexample Rendering

**Gap**: When `ivy_verify` fails, the output is raw `ivy_check` text. Dafny shows variable values at each step; TLA+ shows a state graph; Tamarin shows MSC attack traces.

**Proposed approach**:
- Parse `ivy_check` failure output to extract: failing property, counterexample trace (variable assignments per step), and the violated invariant
- Structure as JSON: `{"property": "...", "trace": [{"step": 1, "state": {"var": "val", ...}}, ...], "violated_invariant": "..."}`
- For protocol-specific rendering: map state variables to protocol concepts (e.g., `stream_seen` -> "Stream X is in state Y")
- Optionally generate Mermaid sequence diagrams for protocol traces

**Complexity**: Medium. `ivy_check` output format is semi-structured. Parsing requires pattern matching but not compiler-level analysis.

**Impact**: Makes verification failures actionable. Currently, an LLM receiving raw counterexample text must guess at the structure. Structured traces let the agent explain failures and suggest fixes.

### Priority 3: Coverage Regression Detection

**Gap**: No mechanism detects when code changes reduce requirement coverage. The `ivy_traceability` tools report current coverage but don't compare against a baseline.

**Proposed approach**:
- Store coverage snapshots as JSON baselines (per-protocol, per-commit)
- On `ivy_coverage --mode=regression`, diff current coverage against baseline
- Report: newly uncovered requirements, newly covered requirements, coverage delta percentage
- Integrate with PANTHER CI/CD: fail the pipeline if coverage drops below threshold

**Complexity**: Low-medium. Coverage computation already exists. The addition is baseline storage and diffing.

**Impact**: Prevents silent requirement de-coverage during model evolution. Essential for any project using Ivy for compliance testing.

### Priority 4: Guided Spec Creation Wizard

**Gap**: Creating a new protocol specification requires knowing the 14-layer architecture, naming conventions, include patterns, and requirement annotation syntax. Currently, `ivy_pattern_scaffold` generates individual files but doesn't orchestrate the full creation workflow.

**Proposed approach**:
- Interactive multi-step workflow (via Claude Code skill):
  1. Input: protocol name, RFC document(s), target layers
  2. Extract requirements from RFC (`ivy_extract_requirements`)
  3. Generate manifest (`ivy_generate_manifest`)
  4. Scaffold each requested layer (`ivy_pattern_scaffold`)
  5. Run quality gate (`ivy_quality` in `gate` mode)
  6. Report: created files, coverage baseline, next steps
- Store the result as a new protocol directory with proper structure

**Complexity**: Medium. All building blocks exist. The addition is orchestration logic and state management across steps.

**Impact**: Lowers the barrier to entry for new protocol models. Currently requires deep Ivy expertise; the wizard would make it accessible to protocol engineers who know their RFC but not Ivy syntax.

---

## 4. Implementation Roadmap

### Phase 1: Consolidation (2-3 weeks)

| Step | Action | Files Affected | Risk |
|------|--------|----------------|------|
| 1 | **Merge `ivy_lint` into `ivy_diagnostics`**: Add `layers` parameter. When `layers=["structural"]`, use fast path. Deprecate `ivy_lint` tool registration. | `tools/verification.py`, `tools/analysis.py`, `mcp_server.py` | Low. Lint logic already exists in diagnostics structural layer. |
| 2 | **Merge semantic query tools**: Combine `ivy_impact_analysis` + `ivy_cross_references` + `ivy_query_symbol` into `ivy_symbol_info`. Accept both symbol names and node_ids. Return unified response with type info, edges, and references. | `tools/traceability.py`, `tools/analysis.py`, `mcp_server.py` | Medium. Three different response schemas must be unified. |
| 3 | **Merge traceability tools**: Combine `ivy_traceability_matrix` + `ivy_requirement_coverage` into `ivy_traceability` with `detail` parameter. | `tools/traceability.py` | Low. Both already query the same data. |
| 4 | **Merge visualization tools**: Combine overlapping pairs (`action_requirements`+`coverage_gaps`, `model_summary`+`layered_overview`, `dependency_graph`+`state_machine_view`). Cut `ivy_smart_suggestions`. Fix `test_file` filtering for all remaining tools. | `tools/visualization.py`, `features/visualization.py` | High. 7 tools with shared broken code. Fix the filtering first, then merge. |
| 5 | **Merge quality tools**: Combine `ivy_scaffold_check` + `ivy_quality_gate` into `ivy_quality`. | `tools/quality.py`, `features/quality_gates.py` | Low. Distinct logic, just needs unified entry point. |

### Phase 2: Gap Filling (3-4 weeks)

| Step | Action | Dependencies | Risk |
|------|--------|--------------|------|
| 6 | **Fix critical bugs (C1-C8)**: Workspace root misconfiguration, `test_file` parameter ignored, tag format mismatch, include graph path mismatch, hover broken, workspaceSymbol unfiltered, `file_path` returns empty, `includes_resolve` always fails. | Phase 1 Step 4 fixes C2/C3. Others are independent. | Medium. C1 and C5 require path normalization changes that could break existing users. |
| 7 | **Implement counterexample rendering (Priority 2)**: Parse `ivy_check` failure output into structured JSON. | Independent of Phase 1. | Medium. Output format parsing is fragile. |
| 8 | **Implement coverage regression detection (Priority 3)**: Baseline storage, diffing, CI integration. | Phase 1 Step 3 (merged traceability tool). | Low. Incremental addition to existing coverage logic. |

### Phase 3: Design Document (1 week)

| Step | Action | Dependencies |
|------|--------|--------------|
| 9 | **Write strategic evaluation document** (this document). Produce consolidated architecture diagram, updated tool catalog, and handoff notes for incremental verification (Priority 1) and guided spec wizard (Priority 4) as future work. | Phases 1-2 for validation data. |

### Timeline Summary

```
Week 1-2:  Phase 1 Steps 1-3 (low-risk merges)
Week 2-3:  Phase 1 Steps 4-5 (visualization merge + quality merge)
Week 3-5:  Phase 2 Step 6 (critical bug fixes, parallelizable with Step 5)
Week 5-6:  Phase 2 Steps 7-8 (counterexample rendering + coverage regression)
Week 7:    Phase 3 Step 9 (this document finalized, architecture review)
```

---

## 5. Verification Checklist

### After Phase 1 (Consolidation)

- [ ] Tool count reduced from 25 to 12 (verify with `ivy_capabilities`)
- [ ] All deprecated tool names return a helpful deprecation message pointing to the replacement
- [ ] `ivy_diagnostics` with `layers=["structural"]` produces identical output to old `ivy_lint`
- [ ] `ivy_symbol_info` with symbol name returns type info + edges (formerly 3 separate calls)
- [ ] `ivy_traceability` with `detail=true` returns full matrix; `detail=false` returns coverage summary
- [ ] `ivy_coverage` with `mode=covered` matches old `ivy_action_requirements`; `mode=gaps` matches old `ivy_coverage_gaps`
- [ ] `ivy_overview` with `group_by=file` matches old `ivy_model_summary`; `group_by=layer` matches old `ivy_layered_overview`
- [ ] `ivy_graph` with `view=dependencies` matches old `ivy_action_dependency_graph`; `view=state_machine` matches old `ivy_state_machine_view`
- [ ] `ivy_quality` with `mode=check` matches old `ivy_scaffold_check`; `mode=gate` matches old `ivy_quality_gate`
- [ ] `ivy_smart_suggestions` is removed; no tool registered under that name
- [ ] All 12 remaining tools have working `protocol` parameter for scoping
- [ ] All visualization tools correctly filter by `test_file` when provided
- [ ] Output size for QUIC full model < 100KB for any single tool call (relative paths, proper scoping)
- [ ] Existing test suite passes (adjust for new tool names)
- [ ] Claude Code plugin configuration updated: 6 skills, 4 agents

### After Phase 2 (Gap Filling)

- [ ] C1 fixed: `ivy_verify`/`ivy_compile`/`ivy_lint`/`ivy_model_info` resolve paths with `protocol-testing/` prefix fallback; error messages include resolved absolute path
- [ ] C4 fixed: `ivy_traceability` correctly maps bare numeric bracket tags `[N]` to manifest requirement IDs `rfc9000:N`; QUIC coverage > 0%
- [ ] C5 fixed: `ivy_include_graph` path keys normalized; individual file queries return non-empty `includes` list
- [ ] C6 fixed: LSP hover returns correct info for at least 4/6 original test scenarios
- [ ] C7 fixed: LSP workspaceSymbol filters results by query text
- [ ] H8 fixed: `ivy_quality` gate `includes_resolve` exempts known Ivy stdlib modules; QUIC passes `minimal` gate
- [ ] H10 fixed: Dotted names (`frame.stream.handle`) resolve correctly in `ivy_symbol_info`
- [ ] Counterexample rendering: `ivy_verify` failure response includes `"counterexample": {"trace": [...], "violated_property": "..."}` when available
- [ ] Coverage regression: `ivy_traceability --mode=regression --baseline=<path>` correctly reports coverage delta
- [ ] No regressions in audit scores: re-run audit scenarios for merged tools, all scores >= original tool scores

---

## Appendix A: Current Tool Inventory (Pre-Consolidation)

For reference, the full list of 25 MCP tools with their audit scores and consolidation target:

| # | Current Tool | Avg Score | Group | Consolidation Target |
|---|-------------|:---------:|:-----:|---------------------|
| 1 | ivy_lint | 2.0 | G1 | Merge into `ivy_diagnostics` |
| 2 | ivy_verify | 2.0 | G1 | **Keep** |
| 3 | ivy_compile | 2.0 | G1 | **Keep** |
| 4 | ivy_model_info | 2.2 | G1 | **Keep** |
| 5 | ivy_capabilities | 3.2 | G2 | **Keep** |
| 6 | ivy_include_graph | 2.4 | G2 | **Keep** |
| 7 | ivy_diagnostics | 3.6 | G3 | **Keep** (absorbs ivy_lint) |
| 8 | ivy_traceability_matrix | 2.4 | G4 | Merge into `ivy_traceability` |
| 9 | ivy_requirement_coverage | 2.6 | G4 | Merge into `ivy_traceability` |
| 10 | ivy_impact_analysis | 2.8 | G4 | Merge into `ivy_symbol_info` |
| 11 | ivy_extract_requirements | 4.6 | G4 | **Keep** |
| 12 | ivy_generate_manifest | 3.8 | G4 | **Keep** |
| 13 | ivy_cross_references | 2.4 | G4 | Merge into `ivy_symbol_info` |
| 14 | ivy_query_symbol | 3.2 | G4 | Merge into `ivy_symbol_info` |
| 15 | ivy_action_requirements | 2.6 | G5 | Merge into `ivy_coverage` |
| 16 | ivy_model_summary | 2.6 | G5 | Merge into `ivy_overview` |
| 17 | ivy_coverage_gaps | 2.2 | G5 | Merge into `ivy_coverage` |
| 18 | ivy_action_dependency_graph | 2.6 | G5 | Merge into `ivy_graph` |
| 19 | ivy_state_machine_view | 3.2 | G5 | Merge into `ivy_graph` |
| 20 | ivy_layered_overview | 2.8 | G5 | Merge into `ivy_overview` |
| 21 | ivy_smart_suggestions | 1.6 | G5 | **Cut** |
| 22 | ivy_pattern_analysis | 4.4 | G6 | **Keep** |
| 23 | ivy_pattern_scaffold | 4.6 | G6 | **Keep** |
| 24 | ivy_scaffold_check | 4.4 | G6 | Merge into `ivy_quality` |
| 25 | ivy_quality_gate | 4.2 | G6 | Merge into `ivy_quality` |

## Appendix B: Post-Consolidation Tool Catalog (12 Tools)

| # | Tool | Source(s) | Key Parameters | Purpose |
|---|------|-----------|----------------|---------|
| 1 | `ivy_verify` | Keep | `file_path`, `isolate`, `timeout` | Run formal verification via `ivy_check` |
| 2 | `ivy_compile` | Keep | `file_path`, `target`, `timeout` | Compile Ivy model to C++ test binary |
| 3 | `ivy_model_info` | Keep | `file_path`, `isolate` | Raw `ivy_show` model structure output |
| 4 | `ivy_capabilities` | Keep | (none) | Report available tools, versions, Docker status |
| 5 | `ivy_include_graph` | Keep | `file_path`, `protocol`, `max_depth` | Include chain analysis with transitive closure |
| 6 | `ivy_diagnostics` | Keep + ivy_lint | `file_path`, `protocol`, `layers[]`, `min_severity` | Graduated 5-layer analysis |
| 7 | `ivy_symbol_info` | impact_analysis + cross_references + query_symbol | `symbol`, `node_id`, `protocol` | Unified symbol lookup: type info + edges + references |
| 8 | `ivy_traceability` | traceability_matrix + requirement_coverage | `protocol`, `scope_file`, `detail`, `mode` | Requirement coverage matrix and summary |
| 9 | `ivy_coverage` | action_requirements + coverage_gaps | `protocol`, `scope_file`, `mode` | Action-to-requirement mapping (covered/gaps/both) |
| 10 | `ivy_overview` | model_summary + layered_overview | `protocol`, `scope_file`, `group_by` | High-level model structure view |
| 11 | `ivy_graph` | action_dependency_graph + state_machine_view | `protocol`, `scope_file`, `view`, `include_state_vars`, `state_var_filter` | Dependency and state machine graph views |
| 12 | `ivy_quality` | scaffold_check + quality_gate | `protocol`, `mode`, `level` | Model maturity assessment (check/gate) |

Plus 5 standalone tools kept as-is:
- `ivy_extract_requirements` (4.6/5)
- `ivy_generate_manifest` (3.8/5)
- `ivy_pattern_analysis` (4.4/5)
- `ivy_pattern_scaffold` (4.6/5)

**Total**: 12 merged/kept + 5 standalone = 17. Further consolidation of the 5 standalone tools is not recommended as they each serve distinct, high-scoring functions.

*Correction*: The 5 standalone tools are counted within the 12 above. The final tool count is **12** unique tools total (7 merged entries + 5 kept as-is = 12, after cutting `ivy_smart_suggestions` and absorbing `ivy_lint`).

---

## Appendix C: Comparison with Prior Art in Combined Verification+Traceability

No existing tool combines:
1. Formal protocol specification language
2. Automated RFC requirement extraction
3. Inline requirement annotation in specifications
4. Formal verification of annotated properties
5. Executable test generation from verified models
6. Deployment-integrated conformance testing
7. AI-accessible tooling surface (MCP) for all of the above

Each capability exists independently in various tools (Dafny for #1/#4, DOORS for #2/#3, Tamarin for #1/#4, PANTHER for #5/#6, LeanDojo for #7). The Ivy PANTHER ecosystem is, to our knowledge, the only system that integrates all seven in a single toolchain.

The consolidation proposed in this document does not reduce this capability set. It reduces the _surface area_ through which these capabilities are accessed, making the system easier to use for both human engineers and AI agents.
