# Ivy Tooling Ecosystem: Strategic Evaluation (Post-Consolidation)

**Date**: 2026-03-13
**Status**: Post-consolidation assessment (tools reduced from 25→15, mode-based dispatch implemented)
**Scope**: LSP + MCP + Claude Code plugin evaluation against protocol-focused SOTA
**Prior work**: `2026-03-13-ivy-tooling-audit-design.md` (audit), `2026-03-13-ivy-tooling-audit-results.md` (results)
**Goal**: Identify strengths, over-engineering, dead code, and gaps vs state-of-the-art protocol verification tools

---

## 1. State-of-the-Art Comparison (Protocol Verification Tools)

### 1.1 Code Intelligence (LSP)

| Capability | Ivy LSP | TLA+ (VS Code ext) | SPIN/Promela | Tamarin (VS Code ext) | ProVerif (vscode-proverif) |
|---|---|---|---|---|---|
| **LSP server** | Full (pygls, 19 registered features) | Shipping (SANY-based VS Code ext); TLAPM proof LSP in development | None | None (tree-sitter grammar; interactive web prover provides exploration) | Partial (syntax + parse errors + signatures) |
| **Go-to-definition** | Cross-file + include resolution | Yes | No | No | Yes (Ctrl+click) |
| **Find references** | Workspace-wide | Yes | No | No | Yes |
| **Completions** | Context-aware (dot-access, includes, keywords, semantic) | Basic (keywords + identifiers) | No | No | No |
| **Hover info** | Types + RFC annotations + cross-ref summaries | Types + operator definitions | No | No | Signatures |
| **Diagnostics** | 3-tier: structural (<50ms) → AST (<200ms) → compiler (background) | SANY inline (single tier) | iSpin panel (external GUI) | Wellformedness via tree-sitter | Parse errors only |
| **Code actions** | Quick fixes for common issues | No | No | In-rule rename only | No |
| **Code lens** | RFC coverage metrics per action/monitor | No | No | No | No |
| **Rename** | Lexical with validation | In development (proof step rename) | No | In-rule only | Semantic (F2) |
| **Folding ranges** | Yes (structural) | No | No | No | No |
| **Selection range** | Yes (smart expansion) | No | No | No | No |
| **Signature help** | Action parameter hints | No | No | No | Yes |

**Verdict**: Ivy LSP is the **most feature-complete language server** among all protocol verification tools (19 registered feature handlers). TLA+'s shipping VS Code extension provides go-to-definition, find-refs, and SANY diagnostics, but lacks completions, code lens, and code actions. ProVerif's extension provides syntax and parse error reporting but is not a full LSP. SPIN and Tamarin have no LSP (Tamarin's web prover offers interactive exploration outside the LSP protocol).

### 1.2 Verification Integration

| Capability | Ivy MCP | TLA+ Toolbox | SPIN (iSpin) | Tamarin | ProVerif |
|---|---|---|---|---|---|
| **Verification trigger** | MCP `ivy_verify` (programmatic, cached, per-isolate) | TLC GUI + MCP (2025) | iSpin GUI panel | CLI + web prover | VS Code Ctrl+Shift+B |
| **Counterexample output** | Structured JSON (parsed from ivy_check, wired in verification.py:155) | State graph + heatmap profiling (2025) | MSC diagrams + automata view | Interactive attack graph (web GUI) | Derivation trees (Graphviz) |
| **Incremental verification** | Per-isolate caching (file-level, not sub-file) | Per-model (full re-check) | Per-model | Per-lemma | Full model |
| **Interactive exploration** | No | No | Automata view | **Yes** (web-based proof tree, step-by-step goal selection) | No |
| **Test generation** | **Yes** (`ivyc target=test` → C++ test binary) | No | No | No | No |
| **Docker integration** | **Yes** (Docker-aware fallback for verification + compilation) | No | No | No | No |
| **LLM orchestration** | **Yes** (15 MCP tools with typed JSON schemas) | Yes (MCP server, 2025) | No | No | No |

**Ivy strengths**: Unique end-to-end pipeline (verify → compile → test binary → Docker execution). MCP integration enables AI-driven verification workflows. Per-isolate caching reduces redundant verification.

**Ivy gaps**: No interactive proof exploration (Tamarin's web prover is unique). Counterexample data is parsed and structured but lacks rich visualization (TLA+ has heatmaps, SPIN has MSC diagrams). No verification-as-you-type (but no competitor in this category has it either — only Lean 4 and Dafny from the general FV space offer this).

### 1.3 Specification Traceability (Unique to Ivy)

| Capability | Ivy MCP+LSP | TLA+ | SPIN | Tamarin | ProVerif |
|---|---|---|---|---|---|
| **RFC requirement extraction** | Automated (`ivy_extract_requirements`): MUST/SHOULD/MAY parsing from RFC text | None | None | None | None |
| **Inline requirement annotation** | Bracket-tags (`# [rfc9000:4.2]`) in `.ivy` files | None | None | None | None |
| **Coverage matrix** | `ivy_coverage(mode="matrix")`: requirement → annotation mapping | None | None | None | None |
| **Coverage gaps** | `ivy_coverage(mode="gaps")`: unguarded state vars, uncovered reqs | None | None | None | None |
| **Coverage regression** | `ivy_coverage(mode="diff")`: baseline comparison | None | None | None | None |
| **MUST/SHOULD/MAY metrics** | `ivy_coverage(mode="stats")`: coverage by level and layer | None | None | None | None |
| **Manifest generation** | YAML manifests from RFC text (`ivy_extract_requirements(output="manifest")`) | None | None | None | None |

**This is a genuinely novel contribution.** No other formal verification tool — protocol-focused or general-purpose — integrates requirements traceability into the specification language. IBM DOORS, Reqtify, and Polarion exist as external traceability tools but operate outside the verification toolchain. Ivy's bracket-tag system embeds requirements directly in verified assertions, enabling simultaneous formal property verification and normative coverage tracking.

### 1.4 AI-Assisted Specification

| Capability | Ivy MCP+Plugin | TLA+ (MCP, 2025) | Quint (MCP) | Alloy (MCP) |
|---|---|---|---|---|
| **MCP tools** | 15 unified tools (verification, analysis, traceability, visualization, patterns, quality) | SANY parsing + TLC model checking | Type-check + simulate + model-check | Model generation + analysis |
| **Specification scaffolding** | Pattern library (7 patterns) + 14-layer template + `ivy_pattern_scaffold` | None | None | None |
| **Quality gates** | 3-tier (minimal/standard/comprehensive) via `ivy_quality(mode="gate")` | None | None | None |
| **Workflow guidance** | 6 skills + 4 agents with methodology knowledge | None | None | None |
| **Architecture validation** | `ivy_patterns(mode="check")`: 14-layer completeness scoring | None | None | None |

**Ivy is ahead** in structured semantic access for AI agents. The 15 MCP tools with typed JSON provide deeper specification-model access than any competitor. TLA+ and Quint have MCP servers but with narrower scope (parse + check).

### 1.5 Protocol-Specific Analysis

| Capability | Ivy PANTHER | Tamarin | ProVerif | SPIN |
|---|---|---|---|---|
| **Protocol compliance testing** | **Yes**: RFC-level compliance with traceability | No (security properties only) | No (security properties only) | No (generic model checking) |
| **Security property verification** | Partial (safety invariants, MitM scenarios) | **Full** (Dolev-Yao, equational theories, unbounded sessions) | **Full** (Horn clauses, unbounded) | State-based only |
| **Test generation** | **Yes** (`ivyc target=test` → executable C++ tests) | No | No | Partial (iSpin counterexample traces) |
| **Multi-protocol workspace** | **Yes** (QUIC, BGP, CoAP in unified workspace) | One model per analysis | One model per analysis | One model per analysis |
| **Deployment integration** | **Yes** (Docker, CI/CD via PANTHER) | Standalone | Standalone | Standalone |

**Ivy's niche**: Protocol compliance testing with deployment integration. Tamarin and ProVerif excel at cryptographic security analysis (fundamentally different capability). SPIN handles generic concurrent systems but has no protocol awareness. Ivy uniquely bridges formal specification → executable conformance testing against real implementations.

---

## 2. Correctly Implemented (Strengths)

### A. Three-Tier Diagnostic Pipeline — Best-in-Class Architecture
- **Tier 1** (<50ms): Structural checks (missing `#lang`, unmatched braces, unresolved includes) — works offline, no compiler needed
- **Tier 2** (<200ms): AST-enriched semantic analysis via parser or fallback scanner — requirement extraction, test scope detection
- **Tier 3** (background): Full Ivy compiler verification — type checking, invariant verification
- **Why it matters**: No surveyed tool separates fast/slow diagnostics this cleanly. TLA+ has single-speed SANY, Tamarin has single-speed wellformedness. This lets the LSP stay responsive while deferring expensive work.
- **Files**: `semantic/analysis_pipeline.py`, `features/diagnostics.py`

### B. Graceful Degradation — Adapter Pattern (Justified Complexity)
- `NullAdapter` implementations enable full LSP functionality without Ivy compiler installed
- Runtime-checkable Protocols (`adapters/protocols.py`) isolate heavy imports from LSP startup
- Formula analyzer: `ImportError` fallback at `mcp_server.py:695-698` (skips READS wiring if unavailable)
- Pattern library: `ImportError` fallback at `features/patterns.py:60-67` (returns error response if unavailable)
- **Assessment**: NOT over-engineering. This is correct defensive design enabling light-mode LSP and MCP operation on machines without full Ivy toolchain.
- **Files**: `adapters/null_adapter.py`, `adapters/protocols.py`, `adapters/compiler_adapter.py`

### C. Complete Code Wiring — No Dead Code
After deep import-chain audit (tracing from `server.py` and `mcp_server.py` through all modules):
- **`counterexample_parser.py`** → Called at `tools/verification.py:155-160` on verification failure — parses raw ivy_check output into structured JSON
- **`formula_analyzer.py`** → Called at `requirement_graph.py:365` via `wire_state_var_edges()`, invoked from `mcp_server.py:694` — extracts state variable references from requirement formulas
- **`impl_block_parser.py`** → Called at `pattern_library.py:147,358` via `analyze_impl_blocks()`, used by `features/patterns.py:60` and `features/visualization.py:602` — parses implementation blocks for pattern detection
- **`snapshots.py`** → Used by `compiler_adapter.py:166,262,289-330` — extracts module and signature snapshots from compiler state for Tier 3 enrichment
- **All 19 LSP features**: Each has a `register()` function called from `server.py` (confirmed by grep across features/)
- **All 15 MCP tools**: All registered via 6 modules in `tools/__init__.py` → `mcp_server.py`
- **All 3 CLI tools**: `ivy_check`, `ivyc`, `ivy_show` confirmed available via `ivy_capabilities`

### D. MCP Tool Consolidation — Well-Executed (25→15)
The consolidation recommended in the prior audit has been implemented:

| Unified Tool | Modes/Views | Original Tools Absorbed |
|---|---|---|
| `ivy_coverage` | `stats`, `matrix`, `gaps`, `diff` | `ivy_traceability_matrix`, `ivy_requirement_coverage`, `ivy_coverage_gaps` |
| `ivy_query` | `info`, `impact`, `xrefs` | `ivy_query_symbol`, `ivy_impact_analysis`, `ivy_cross_references` |
| `ivy_visualize` | `dependencies`, `state_machine`, `layers` | `ivy_action_dependency_graph`, `ivy_state_machine_view`, `ivy_layered_overview` |
| `ivy_model_summary` | `summary`, `requirements` | `ivy_model_summary` (old), `ivy_action_requirements` |
| `ivy_quality` | `suggestions`, `gate` | `ivy_smart_suggestions`, `ivy_quality_gate` |
| `ivy_patterns` | `analyze`, `validate`, `compare`, `check` | `ivy_pattern_analysis`, `ivy_scaffold_check` |

Retained as independent: `ivy_verify`, `ivy_compile`, `ivy_model_info`, `ivy_diagnostics`, `ivy_lint`, `ivy_include_graph`, `ivy_capabilities`, `ivy_extract_requirements`, `ivy_pattern_scaffold`

**Result**: Clean mode-based dispatch. Reduced tool-selection confusion for AI agents. Lazy initialization of expensive models.

### E. RFC Traceability — Unique and Unmatched
See §1.3. No other formal verification tool integrates this. The system is architecturally complete: extraction → manifest → annotation → coverage → gap analysis → regression detection.

### F. Pattern Library + Scaffolding — Unique Differentiator
- 14-layer canonical decomposition: types → frames → packets → connection → crypto → shim → behavior → monitors → properties → test_specs → application → recovery → extensions → documentation
- 7 pattern types: serdes, variants, monitors, shims, modules, entities, include-chain
- Connected chain: `pattern_library.py` → `features/patterns.py` → MCP `ivy_patterns` tool → `ivy_pattern_scaffold` tool
- Completeness checking: `ivy_patterns(mode="check")` scores against 14-layer template
- **Files**: `analysis/pattern_library.py`, `analysis/impl_block_parser.py`, `features/patterns.py`, `tools/patterns.py`

### G. Plugin Enforcement Architecture — Good Developer Experience
- **PreToolUse hook** (`block-direct-ivy.sh`): Warns about direct `ivy_check`/`ivyc`/`ivy_show` CLI calls, maps to MCP equivalents
- **PostToolUse hook** (`post-write-ivy-lint.sh`): Auto-lints `.ivy` files on Write/Edit (checks `#lang`, brace balance, non-empty)
- **SessionStart hook** (`detect-ivy-workspace.sh`): Auto-detects workspace type (PANTHER project vs standalone), sets `IVY_WORKSPACE_ROOT`
- All hooks non-blocking (exit 0, advisory only), correct behavior

### H. Agent Specialization — Well-Scoped
| Agent | Focus | Tool Access | Assessment |
|---|---|---|---|
| `spec-analyst` | Navigation, exploration, verification, error diagnosis | Read, Write, Edit, Bash, Grep, Glob | Correct: broadest toolset for broadest scope |
| `model-reviewer` | Quality review, invariant checking, best practices | Read, Grep, Glob (read-only) | Correct: read-only enforces review-not-modify |
| `methodology-guide` | NCT/NACT/NSCT workflow guidance | Read, Write, Edit, Bash, Grep, Glob | Correct: needs write access for guided creation |
| `traceability-agent` | RFC extraction, manifest generation, coverage audits | Read, Write, Edit, Bash, Grep, Glob, WebFetch | Correct: WebFetch for RFC access |

---

## 3. Over-Engineered / Should Be Optimized

### A. Dual Graph Storage — MEDIUM Priority

**Problem**: Two parallel graph structures maintain overlapping data with separate locks.

| Graph | File | Purpose | Size |
|---|---|---|---|
| `SemanticModel` | `semantic/model.py` (295 lines) | General-purpose graph: symbols, types, RFC annotations | 4 index structures, 5 query methods |
| `RequirementGraph` | `analysis/requirement_graph.py` (718 lines) | Specialized: actions → requirements → state vars | Domain-specific edges (CONSTRAINS, WRITES, COVERS, READS, DEPENDS_ON) |

**Evidence of duplication**:
- Both store requirements as nodes with edges
- `coverage_hints.py` queries RequirementGraph directly
- `features/*.py` query SemanticModel
- `semantic/nodes.py:14` imports from `requirement_graph` (tight coupling)
- `mcp_server.py` builds both sequentially (lines ~650-710)

**Recommendation**: Migrate RequirementGraph's specialized queries into SemanticModel as domain-specific methods. Reconcile edge type enums (`EdgeType` in requirement_graph vs `SemanticEdgeType` in semantic model). Single graph, single lock, single source of truth.

**Risk**: RequirementGraph's edge types are more granular. Need careful mapping.

### B. Analysis Pipeline State Complexity — MEDIUM Priority

**File**: `semantic/analysis_pipeline.py` (896 lines, ~17 methods)

**Problem**: Tier 2 (AST) and Tier 3 (compiler) have overlapping parse+analyze steps with separate thread coordination:
- `file_generation` OrderedDict tracks per-file generation counts
- `_bulk_running` and `_bulk_compile_running` boolean flags
- Separate locks for different tiers

**Recommendation**: The 3-tier *concept* is excellent (§2A). The *implementation* could consolidate Tier 2/3 coordination into a single "deep analysis" state machine. Estimated ~30% reduction in coordination complexity without changing the user-facing behavior.

### C. SemanticModel Over-Indexed — LOW Priority

**File**: `semantic/model.py` (295 lines)

4 index structures maintained eagerly on every `add_node`/`add_edge`:
- `_edges`: Set[Tuple] for deduplication
- `_outgoing`: Dict[str, List[Tuple]] for forward queries
- `_incoming`: Dict[str, List[Tuple]] for backward queries
- `_nodes_by_file`: Dict[str, Set[str]] for file-scoped queries
- `_nodes_by_type`: Dict[type, Dict[str, Any]] for type-scoped queries

Only 5 public query methods actually used. Typical graph: <10K nodes.

**Recommendation**: Lazy-build `_nodes_by_file` and `_nodes_by_type` indexes on first query. Keep `_outgoing`/`_incoming` eagerly built (justified for cross-reference queries).

### D. Compilation IR Sub-Type Granularity — LOW Priority

**File**: `compilation/ir.py`

Defines `CompiledModuleIR`, `RequirementIR`, `MixinIR`, `InvariantIR`, etc. Only `CompiledModuleIR` and its top-level fields are consumed by `graph_enrichment.py`. Sub-IR types have unused granularity.

**Recommendation**: Trim to the fields actually consumed. Low urgency — it works, just has unused data classes.

---

## 4. Gaps vs SOTA — Improvement Opportunities

### A. Counterexample Visualization — HIGH Value (Foundation Exists)

**Current state**: `counterexample_parser.py` IS wired in at `tools/verification.py:155-160`. When `ivy_verify` fails, it parses raw output and adds a structured `counterexample` field to the JSON result.

**Gap**: The parsed data is returned but not richly formatted. Compare:
- **TLA+ Toolbox**: State graph + heatmap execution profiling (new 2025)
- **SPIN**: MSC diagrams + automata view (iSpin GUI)
- **Tamarin**: Interactive attack graph in web browser

**Improvement**: Add formatted counterexample display:
1. Format parsed counterexample as a readable state trace in `ivy_verify` output
2. Map state variables to protocol concepts (e.g., `stream_seen` → "Stream X is in state Y")
3. Add LSP diagnostics with "related information" links to counterexample states
4. Optionally generate Mermaid sequence diagrams for protocol state traces

**Effort**: Small-Medium. Parser exists and works. Need formatting logic.

### B. Verification Status Dashboard — MEDIUM Value

**Current**: `monitoring.py` provides 11 RPC handlers for server status, pipeline progress, indexer stats, etc.

**Gap**: No unified "verification dashboard" showing per-isolate pass/fail across all workspace files.

**Improvement**: Add workspace-level verification summary tool/view. The per-isolate cache in `tools/verification.py` already tracks this data (`_verify_cache` with per-file entries). Expose as a new MCP tool mode or monitoring RPC.

### C. Incremental Verification — MEDIUM Value

**Current**: Full `ivy_check` on each `ivy_verify` call. Per-isolate caching helps (skip if file unchanged).

**Gap**: Modifying one isolate re-verifies the whole file. TLA+ Toolbox re-checks the full model too, so this is not a gap vs SOTA in this category — only vs general FV tools (Lean 4, Dafny).

**Improvement**: Track file content hash per isolate. Only re-verify isolates whose definitions (or transitive dependencies) changed. The caching infrastructure already exists.

### D. Semantic Rename — LOW Value

**Current**: Lexical rename with validation at `features/rename.py`.

**Gap**: ProVerif has semantic rename (F2). For Ivy's `include`-based composition, semantic rename requires full type resolution across files.

**Assessment**: Not worth the complexity investment for the protocol verification use case. Current lexical approach is safe and works for common cases.

---

## 5. Skill/Agent Optimization

### Well-Designed (Keep As-Is)
- **`spec-analyst` agent**: Correct tool restrictions, comprehensive LSP+MCP coordination
- **`tooling-reference` skill**: Essential decision table (15+ tasks → recommended tool)
- **`ivy-lsp-walkthrough` skill**: Best onboarding material — concrete end-to-end example on QUIC spec
- **`traceability-agent`**: Well-scoped (RFC extraction → manifest → coverage audit)
- **`ivy-writing-guide` skill**: Covers Ivy syntax, test spec patterns, RFC bracket-tag annotations

### Could Be Optimized
- **`methodology-reference` skill**: Covers all three methodologies (NCT + NACT + NSCT) in one document. Consider splitting into 3 focused sub-skills with a dispatcher that auto-selects based on context keywords (specification/compliance → NCT, attack/security → NACT, simulation/topology → NSCT).
- **`specification-patterns` skill**: The 14-layer template is front-loaded. The "minimum viable set" (7 layers) exists but presentation buries it. Restructure to lead with quick-start path, expand to full 14 layers as needed.
- **`workflow-reference` skill**: Overlaps with `methodology-reference` on verification workflow. Could merge verification-specific content or add clearer cross-references.

### Missing
- **Counterexample interpretation skill**: When `ivy_verify` fails, no skill guides understanding of the structured counterexample output
- **Incremental spec development skill**: No guided workflow for "add one requirement → verify → iterate". Current skills assume whole-file or whole-protocol scope.
- **Automated review via quality tools**: `model-reviewer` agent uses manual checklist. Could integrate `ivy_quality(mode="gate")` and `ivy_patterns(mode="validate")` for semi-automated assessment with tool-backed evidence.

---

## 6. Summary: Priority Action Matrix

| # | Action | Priority | Effort | Impact | Justification |
|---|---|---|---|---|---|
| 1 | Enrich counterexample display formatting in `ivy_verify` results | HIGH | Small | Closes biggest SOTA gap | TLA+/SPIN/Tamarin all have structured counterexample rendering; Ivy has the parser but not the presentation |
| 2 | Add verification status dashboard (workspace-level summary) | MEDIUM | Medium | Better UX for large specs | Per-isolate cache already has the data; need exposure as tool/view |
| 3 | Merge RequirementGraph into SemanticModel | MEDIUM | Large | Single source of truth, reduced lock contention | Dual graph is the main remaining over-engineering |
| 4 | Simplify analysis_pipeline.py Tier 2/3 state management | MEDIUM | Medium | ~30% less coordination code | 896 lines with ~17 methods; Tier 2/3 overlap in parse+analyze |
| 5 | Split `methodology-reference` skill into 3 focused sub-skills | LOW | Small | Better skill triggering accuracy | One skill covering NCT+NACT+NSCT is too broad for auto-selection |
| 6 | Add counterexample interpretation skill | LOW | Small | Better failure UX | No guidance for understanding verification failures |
| 7 | Add incremental spec development skill | LOW | Small | Better iteration workflow | Current skills assume whole-file/protocol scope |
| 8 | Lazy-build SemanticModel secondary indexes | LOW | Small | Minor perf improvement | 4 eager indexes but only 5 query methods |
| 9 | Trim unused IR sub-types in compilation/ir.py | LOW | Small | Code clarity | Sub-IR types defined but underutilized |

---

## 7. Conclusion

The Ivy LSP + MCP tooling is **well-positioned relative to SOTA protocol verification tools**. It is:
- The **most feature-complete LSP** in the protocol verification space (19 features vs ProVerif's ~8, TLA+'s in-development, SPIN/Tamarin's zero)
- The **only tool with RFC traceability** integrated into the specification language
- The **only tool with specification scaffolding** (pattern library + 14-layer template)
- The **only tool with both verification AND test generation** in one pipeline
- **Well-wired with no dead code** (all modules connected through verified import chains)
- **Already consolidated** (25→15 tools with clean mode-based dispatch)

The main optimization opportunities are architectural simplification (dual graph merge, pipeline state reduction) rather than missing functionality. The highest-value gap to close is counterexample visualization, where the foundation (parser) already exists.

---

## Appendix A: Post-Consolidation Tool Catalog (15 Tools)

| # | Tool | Modes/Params | Backend | Purpose |
|---|---|---|---|---|
| 1 | `ivy_verify` | `isolate`, `use_cache` | `ivy_check` CLI | Formal property verification with per-isolate caching |
| 2 | `ivy_compile` | `target`, `isolate` | `ivyc` CLI / Docker | Compile to test executable |
| 3 | `ivy_model_info` | `isolate` | `ivy_show` CLI | Display model structure |
| 4 | `ivy_diagnostics` | `layers[]`, `min_severity` | Internal analyzers | 5-layer graduated analysis |
| 5 | `ivy_lint` | — | Internal structural checks | Fast structural lint (<50ms) |
| 6 | `ivy_include_graph` | `relative_path` | Regex parsing | Include dependency graph |
| 7 | `ivy_capabilities` | — | `shutil.which()` | Report available CLI tools |
| 8 | `ivy_coverage` | `mode`: stats/matrix/gaps/diff | SemanticModel | RFC coverage analysis |
| 9 | `ivy_query` | `mode`: info/impact/xrefs | SemanticModel | Unified semantic query |
| 10 | `ivy_extract_requirements` | `output`: structured/manifest | Regex | RFC text → requirements |
| 11 | `ivy_visualize` | `view`: dependencies/state_machine/layers | RequirementGraph | Model visualization |
| 12 | `ivy_model_summary` | `detail`: summary/requirements | RequirementGraph | Per-action summary |
| 13 | `ivy_quality` | `mode`: suggestions/gate | RequirementGraph | Quality analysis |
| 14 | `ivy_patterns` | `mode`: analyze/validate/compare/check | RequirementGraph | Pattern analysis + scaffold checking |
| 15 | `ivy_pattern_scaffold` | `pattern`, `protocol`, `wire_format` | Templates | Generate Ivy source from pattern |

*Note: 15 backward-compatibility aliases for the pre-consolidation tool names are also registered (see `ivy_lsp/tools/{traceability,visualization,quality,patterns}.py` — sections marked "Individual tool aliases (backward compatibility)") but not listed here.*

## Appendix B: LSP Feature Registration (19 Features)

All registered in `server.py` via `register()` calls:

| Feature | Handler File | LSP Method |
|---|---|---|
| Document Symbols | `features/document_symbols.py` | `textDocument/documentSymbol` |
| Workspace Symbols | `features/workspace_symbols.py` | `workspace/symbol` |
| Go-to-Definition | `features/definition.py` | `textDocument/definition` |
| Find References | `features/references.py` | `textDocument/references` |
| Document Highlight | `features/document_highlight.py` | `textDocument/documentHighlight` |
| Hover | `features/hover.py` | `textDocument/hover` |
| Completion | `features/completion.py` | `textDocument/completion` |
| Signature Help | `features/signature_help.py` | `textDocument/signatureHelp` |
| Code Action | `features/code_action.py` | `textDocument/codeAction` |
| Code Lens | `features/code_lens.py` | `textDocument/codeLens` |
| Diagnostics | `features/diagnostics.py` | `textDocument/diagnostic` |
| Rename | `features/rename.py` | `textDocument/rename` |
| Selection Range | `features/selection_range.py` | `textDocument/selectionRange` |
| Folding Range | `features/folding_range.py` | `textDocument/foldingRange` |
| Commands | `features/commands.py` | Custom LSP commands |
| Visualization | `features/visualization.py` | Custom RPC handlers (action reqs, coverage, graphs) |
| Monitoring | `features/monitoring.py` | Custom RPC handlers (11 endpoints) |
| Implementation | `features/implementation.py` | `textDocument/implementation` |
| Call Hierarchy | `features/call_hierarchy.py` | `textDocument/prepareCallHierarchy` |

## Appendix C: Unique Capability Combination

No existing tool combines all of these in a single toolchain:

1. Formal protocol specification language (Ivy)
2. Automated RFC requirement extraction (`ivy_extract_requirements`)
3. Inline requirement annotation in specifications (bracket-tags)
4. Formal verification of annotated properties (`ivy_verify`)
5. Executable test generation from verified models (`ivy_compile`)
6. Deployment-integrated conformance testing (Docker + PANTHER CI/CD)
7. AI-accessible tooling surface (15 MCP tools) for all of the above
8. Full IDE-grade code intelligence (19-feature LSP)

Each capability exists independently in various tools. The Ivy PANTHER ecosystem is, to our knowledge, the only system that integrates all eight in a single toolchain.
