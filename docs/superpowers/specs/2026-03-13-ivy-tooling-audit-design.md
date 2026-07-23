# Ivy Tooling Audit Design — LSP Navigation & MCP Tools

**Date**: 2026-03-13
**Scope**: Full evaluation/audit of 25 MCP tools + 14 LSP features (8 navigation + 6 additional)
**Goal**: Quality scorecard per tool + prioritized improvement backlog
**Approach**: Hybrid — tool groups x protocol tiers

---

## Context

The panther-ivy-plugin exposes two tooling surfaces for working with Ivy formal protocol specifications:

1. **MCP Tools** (25 tools via ivy-tools server): verification, linting, diagnostics, traceability, visualization, pattern analysis
2. **LSP Navigation** (8 features via ivy-lsp server): go-to-definition, find references, hover, document symbols, workspace symbols, call hierarchy, rename, document highlight

Both surfaces have been built incrementally. No systematic audit has been performed to evaluate output quality, identify missing parameters, or detect behavioral issues. This audit calls each tool on real protocol models, evaluates outputs, and produces an improvement backlog.

---

## Protocol Tiers

| Tier | Protocol | Files | Manifest | Bracket Tags | Test Specs | Notes |
|------|----------|-------|----------|-------------|------------|-------|
| T1 (mature) | quic | 202 | Yes (101 reqs) | No | ~30 | Gold standard |
| T2 (medium) | apt | 361 | Unknown | Unknown | Unknown | Largest model, explore during audit |
| T2 (medium) | bgp | 39 | No | No | 2 | Complex routing protocol |
| T2 (medium) | coap | 36 | No | No | 0 | Has RFC text file, dir typo |
| T3 (minimal) | minip | 18 | No | No | 2 | Simple ping protocol |
| T3 (minimal) | new_prot | 10 | No | No | 0 | Scaffold/template |
| Special | patterns | 13 | Catalog YAML | No | 0 | Pattern library |

**Execution order per group**: quic first (richest signal), then bgp/coap (medium), then minip/new_prot (sparse/edge cases). `apt` explored opportunistically.

---

## Quality Dimensions (1-5 scale)

1. **Correctness** — output matches ground truth
2. **Completeness** — captures all relevant data
3. **Usefulness** — output is actionable/readable for agent or user
4. **Error handling** — graceful on bad input, missing data, sparse models
5. **Parameter adequacy** — are there missing params that would improve the tool?

---

## Group 1: Core Verification & Linting

### ivy_lint
| # | Protocol | Input | Evaluate |
|---|----------|-------|---------|
| 1 | quic | `quic/quic_stack/quic_types.ivy` | Clean file — 0 diagnostics expected |
| 2 | quic | `quic/quic_stack/quic_frame.ivy` | Large file (86KB) — performance, completeness |
| 3 | bgp | `bgp/bgp_stack/bgp_rib.ivy` | Empty file (1 line) — graceful handling |
| 4 | coap | `coap/coap_stack/coap_message.ivy` | Normal file, no manifest |
| 5 | minip | `minip/minip_stack/ping_types.ivy` | Minimal model |
| 6 | — | `nonexistent.ivy` | Invalid path — error handling |
| 7 | — | `../../../etc/passwd` | Path traversal — security check |

**Focus**: 3 issue types (missing `#lang`, unmatched braces, unresolved includes). Output format consistency. Speed.

**Known improvement candidates**:
- Single-file only — no `protocol` or glob param for batch linting
- No severity filtering param

### ivy_verify
| # | Protocol | Input | Evaluate |
|---|----------|-------|---------|
| 1 | quic | `quic/quic_tests/server_tests/quic_server_test_stream.ivy` | Known test spec — verification completes? |
| 2 | quic | `quic/quic_stack/quic_types.ivy` | Non-test file — behavior? |
| 3 | quic | Test file + `isolate` param | Does isolate narrow scope? |
| 4 | minip | `minip/minip_tests/ping_server_test.ivy` | Simpler model — faster? |
| 5 | — | `nonexistent.ivy` | Error handling |

**Focus**: Diagnostic quality, timeout behavior (no configurable timeout param), `success` field reliability.

**Known improvement candidates**:
- No `timeout` param exposed to caller
- No indication of verification duration in output

### ivy_compile
| # | Protocol | Input | Evaluate |
|---|----------|-------|---------|
| 1 | quic | `quic/quic_tests/server_tests/quic_server_test_stream.ivy` | Main compilation path |
| 2 | quic | Same file, `target="test"` | Default target |
| 3 | minip | `minip/minip_tests/ping_server_test.ivy` | Simpler model |
| 4 | — | `nonexistent.ivy` | Error handling |

**Focus**: Docker vs subprocess fallback, `duration_seconds` accuracy, `error_summary` readability.

**Known improvement candidates**:
- No `execution_mode` field in output — caller can't tell if Docker or subprocess was used
- Docker fallback is silent (only logged at debug/warning)

### ivy_model_info
| # | Protocol | Input | Evaluate |
|---|----------|-------|---------|
| 1 | quic | `quic/quic_stack/quic_types.ivy` | Simple types file |
| 2 | quic | `quic/quic_stack/quic_frame.ivy` | Complex file |
| 3 | bgp | `bgp/bgp_stack/bgp_open_message.ivy` | Medium complexity |
| 4 | minip | `minip/minip_stack/ping_types.ivy` | Minimal |
| 5 | quic | With `isolate` param | Isolate filtering |

**Focus**: Output structure, readability, usefulness vs just reading the file. Is raw `ivy_show` output useful or needs parsing?

---

## Group 2: Dependency & Capability

### ivy_capabilities
| # | Scenario | Evaluate |
|---|----------|---------|
| 1 | Call with no params | Correct detection of ivy_check, ivyc, ivy_show |
| 2 | — | Should it report versions? Docker image availability? Python/Z3 version? |

**Known improvement candidates**: Version info, Docker status, Z3 availability.

### ivy_include_graph
| # | Protocol | Input | Evaluate |
|---|----------|-------|---------|
| 1 | quic | `quic/quic_stack/quic_types.ivy` | Base file — `included_by` list |
| 2 | quic | `quic/quic_tests/server_tests/quic_server_test_stream.ivy` | Deep include chain |
| 3 | quic | `None` (full graph) | Full workspace — size, performance, usefulness |
| 4 | bgp | `bgp/bgp_stack/bgp_open_message.ivy` | Medium model |
| 5 | minip | `minip/minip_stack/ping_types.ivy` | Minimal model |
| 6 | coap | `coap/coap_stack/coap_message.ivy` | Cross-directory includes |

**Focus**: Ambiguity detection, transitive closure correctness, `included_by` completeness, full-graph output size.

**Known improvement candidates**: `depth` param for transitive closure limit, `format` param (tree vs flat).

---

## Group 3: Diagnostics

### ivy_diagnostics (5 internal layers)
| # | Protocol | Input | Evaluate |
|---|----------|-------|---------|
| 1 | quic | `quic/quic_stack/quic_types.ivy` | Clean file — minimal diagnostics |
| 2 | quic | `quic/quic_tests/server_tests/quic_server_test_stream.ivy` | Test file — coverage + pattern layers |
| 3 | quic | `quic/quic_stack/quic_frame.ivy` | Large file — all 5 layers |
| 4 | bgp | `bgp/bgp_stack/bgp_rib.ivy` | Empty file — degradation |
| 5 | coap | `coap/coap_stack/coap_message.ivy` | No manifest — semantic/coverage layers |
| 6 | minip | `minip/minip_tests/ping_server_test.ivy` | Test file without manifest |
| 7 | new_prot | Any file | Scaffold — pattern layer |

**Per-layer evaluation**:
- **Structural**: Same as lint — redundant?
- **Lexer**: What does it catch that structural doesn't?
- **Semantic**: RFC annotation validation — useful without bracket tags?
- **Coverage**: Without manifest, empty or still provides value?
- **Pattern**: `_finalize` detection, unmonitored exports — accuracy?

**Key question**: Is `ivy_diagnostics` a superset of `ivy_lint`? Should `ivy_lint` be deprecated or should `ivy_diagnostics` have a `layers` param?

---

## Group 4: Semantic Traceability

### ivy_traceability_matrix
| # | Protocol | Input | Evaluate |
|---|----------|-------|---------|
| 1 | quic | `None` (full workspace) | Full matrix — 101 requirements, coverage accuracy |
| 2 | quic | Scoped to one test file | Per-file coverage |
| 3 | bgp | `None` | No manifest — behavior? |
| 4 | minip | `None` | No manifest — graceful degradation? |

**Focus**: Text truncation at 120 chars, `assertions` accuracy, coverage counts.

### ivy_requirement_coverage
| # | Protocol | Input | Evaluate |
|---|----------|-------|---------|
| 1 | quic | `None` | Overall MUST/SHOULD/MAY breakdown |
| 2 | quic | Scoped to file | Per-file coverage |
| 3 | bgp | `None` | No manifest behavior |

**Focus**: `by_layer` grouping accuracy, `coverage_percent` calculation, output format usefulness.

### ivy_impact_analysis
| # | Protocol | Symbol | Evaluate |
|---|----------|--------|---------|
| 1 | quic | `cid` | Heavily-used type — many edges |
| 2 | quic | `frame.stream.handle` | Action edges |
| 3 | quic | `stream_seen` | Relation read/write edges |
| 4 | quic | `nonexistent_symbol` | Missing symbol handling |
| 5 | bgp | `bgp_open_message_event` | Cross-protocol |

**Focus**: First-match limitation (ambiguous names). Edge type accuracy. `total_references` usefulness.

### ivy_extract_requirements
| # | Input | Evaluate |
|---|-------|---------|
| 1 | Section from RFC 9000 | Correct MUST/SHOULD/MAY extraction |
| 2 | Section from RFC 7252 (CoAP) | Different RFC style |
| 3 | Empty string | Edge case |
| 4 | Text with MUST NOT / SHOULD NOT | Level normalization |

**Focus**: Regex accuracy, false positives, sentence boundary detection.

### ivy_generate_manifest
| # | Input | Evaluate |
|---|-------|---------|
| 1 | RFC 9000 text, `rfc_name="RFC9000"`, `protocol="quic"` | Compare with existing manifest |
| 2 | RFC 7252 text, `protocol="coap"` | Generate for protocol without manifest |
| 3 | With `base_section="4"` | Section numbering |

**Focus**: YAML format correctness, `suggested_path` accuracy, `layer` field (always empty — useful?), quality vs hand-curated manifest.

### ivy_cross_references
| # | Input | Evaluate |
|---|-------|---------|
| 1 | Valid node_id `quic_types.ivy:30:cid` | Graph neighborhood |
| 2 | Invalid node_id | Error handling |
| 3 | Node with many edges | Completeness |

**Focus**: Node ID format discoverability. Overlap with `ivy_impact_analysis`.

### ivy_query_symbol
| # | Symbol | Evaluate |
|---|--------|---------|
| 1 | `cid` | Type lookup — variants, sort_name |
| 2 | `frame.stream.handle` | Action — params, return_sort |
| 3 | `stream_seen` | Relation |
| 4 | `nonexistent` | Missing symbol |

**Focus**: SymbolNode vs TypeNode dual lookup clarity. Reference counts. Overlap with `ivy_impact_analysis`.

**Group 4 cross-cutting**:
- `ivy_impact_analysis` vs `ivy_cross_references` vs `ivy_query_symbol` — significant overlap, consolidation candidate?
- Node ID format for `ivy_cross_references` — how does user discover correct format?
- Graceful failure when semantic model can't be built?

---

## Group 5: Visualization & Model Analysis

### ivy_action_requirements
| # | Protocol | Params | Evaluate |
|---|----------|--------|---------|
| 1 | quic | `action_name=None` | Full output — size, readability |
| 2 | quic | `action_name="frame.stream.handle"` | Single action — before/after monitors |
| 3 | quic | `file_path=<test_file>` | Scoped to test |
| 4 | quic | `test_file=<test_file>` | `test_file` vs `file_path` — difference? |
| 5 | bgp | `action_name="bgp_open_message_event"` | Cross-protocol |
| 6 | minip | `action_name=None` | Minimal model |

**Focus**: `file_path` vs `test_file` param confusion. Before/after accuracy. Requirement kind classification.

### ivy_model_summary
| # | Protocol | Params | Evaluate |
|---|----------|--------|---------|
| 1 | quic | `test_file=None` | Full summary table |
| 2 | quic | Scoped to test file | Per-test summary |
| 3 | bgp | `test_file=None` | Medium model |
| 4 | minip | `test_file=None` | Minimal model |

**Focus**: Per-action counts accuracy. State variable detection. JSON vs markdown format. RFC coverage with no bracket tags.

### ivy_coverage_gaps
| # | Protocol | Params | Evaluate |
|---|----------|--------|---------|
| 1 | quic | `test_file=None` | Full gap analysis |
| 2 | quic | Scoped to test file | Per-test gaps |
| 3 | bgp | `test_file=None` | No manifest — RFC gaps reported or skipped? |
| 4 | minip | `test_file=None` | Minimal model |
| 5 | new_prot | `test_file=None` | Scaffold — mostly gaps |

**Focus**: "Nonexistent actions" detection. "Unguarded" state var definition. Actionability on sparse models.

### ivy_action_dependency_graph
| # | Protocol | Params | Evaluate |
|---|----------|--------|---------|
| 1 | quic | `include_state_vars=False` | Action-only graph size |
| 2 | quic | `include_state_vars=True` | With state vars — output size explosion? |
| 3 | quic | Scoped to test file | Smaller graph |
| 4 | bgp | `include_state_vars=False` | Medium model |
| 5 | minip | `include_state_vars=True` | Should be small |

**Focus**: Graph format (adjacency list? nodes+edges?). Shared-state edge accuracy. Output consumability. Need for `max_depth`/`filter` param?

### ivy_state_machine_view
| # | Protocol | Params | Evaluate |
|---|----------|--------|---------|
| 1 | quic | `state_var_filter=None` | Full SM — likely very large |
| 2 | quic | `state_var_filter="stream_seen"` | Filtered to one variable |
| 3 | quic | Scoped to test file | Smaller |
| 4 | minip | `state_var_filter=None` | Small, digestible |
| 5 | bgp | `state_var_filter="open_message_recv"` | BGP state |

**Focus**: Representation format. Guard capture accuracy. Is it actually a state machine or a labeled graph?

### ivy_layered_overview
| # | Protocol | Params | Evaluate |
|---|----------|--------|---------|
| 1 | quic | `group_by="file"` | File-based grouping |
| 2 | quic | `group_by="module"` | Module-based grouping |
| 3 | bgp | `group_by="file"` | Medium model |
| 4 | minip | `group_by="module"` | Minimal |
| 5 | coap | `group_by="file"` | Cross-directory structure |

**Focus**: Hierarchy depth. 14-layer architecture visibility. Overlap with `ivy_scaffold_check`.

### ivy_smart_suggestions
| # | Protocol | Params | Evaluate |
|---|----------|--------|---------|
| 1 | quic | `file_path=<types_file>`, no line/context | File-level |
| 2 | quic | Test file, `context="monitor"` | Monitor-specific |
| 3 | quic | `line=30`, specific file | Cursor-local |
| 4 | bgp | `file_path=None` | Workspace-level? |
| 5 | minip | `context="property"` | Property suggestions |
| 6 | — | All params empty | Edge case |

**Focus**: Context-awareness vs generic boilerplate. Suggestion actionability. `context` param impact on output.

**Group 5 cross-cutting**:
- `test_file` vs `file_path` naming inconsistency
- JSON output for all — some could benefit from markdown/mermaid format option
- Requirement graph vs semantic model — same thing or different?
- Output size for QUIC full model — any tools produce unusably large output?

---

## Group 6: Pattern & Architecture

### ivy_pattern_analysis
| # | Protocol | Params | Evaluate |
|---|----------|--------|---------|
| 1 | quic | `mode="detect"` | Patterns in gold standard |
| 2 | quic | `mode="validate"`, `pattern="serdes"` | Specific pattern validation |
| 3 | quic | `mode="compare"`, `reference_protocol="minip"` | Cross-protocol diff |
| 4 | bgp | `mode="detect"` | Medium model |
| 5 | coap | `mode="detect"` | CoAP patterns |
| 6 | minip | `mode="validate"`, `pattern="monitors"` | Minimal model |
| 7 | new_prot | `mode="detect"` | Scaffold patterns |

**Focus**: Detection accuracy per pattern type. Validation criteria. Compare mode usefulness.

### ivy_pattern_scaffold
| # | Params | Evaluate |
|---|--------|---------|
| 1 | `pattern="serdes"`, `wire_format="binary"` | Binary serdes |
| 2 | `pattern="serdes"`, `wire_format="json"` | JSON variant |
| 3 | `pattern="shim"`, `wire_format="udp"` | UDP shim |
| 4 | `pattern="shim"`, `wire_format="tcp"` | TCP shim |
| 5 | `pattern="entity"`, `role_type="asymmetric"`, `roles=["client","server"]` | Entity |
| 6 | `pattern="variants"`, `variant_names=["ping","pong"]` | Variants |
| 7 | `pattern="monitors"` | Monitors |
| 8 | `pattern="invalid_pattern"` | Error handling |

**Focus**: Generated code syntactic validity (passes `ivy_lint`?). Placeholder substitution. Template completeness — usable as-is?

### ivy_scaffold_check
| # | Protocol | Evaluate |
|---|----------|---------|
| 1 | quic | Gold standard — high score, which layers present/missing? |
| 2 | bgp | Expected gaps |
| 3 | coap | Compare with bgp |
| 4 | minip | Low score expected |
| 5 | new_prot | Lowest score |
| 6 | apt | Unknown — interesting |

**Focus**: Completeness score accuracy. 14-layer detection via filename+content patterns. Suggestion quality. QUIC-centric bias for other protocols?

### ivy_quality_gate
| # | Protocol | Level | Evaluate |
|---|----------|-------|---------|
| 1 | quic | `minimal` | Should pass all 3 checks |
| 2 | quic | `standard` | Has test specs, behaviors, monitors, exports |
| 3 | quic | `comprehensive` | Manifest yes, bracket tags no — pass or fail? |
| 4 | bgp | `minimal` | Headers/includes/braces OK |
| 5 | bgp | `standard` | Has test specs + behavior |
| 6 | bgp | `comprehensive` | No manifest — should fail |
| 7 | minip | `minimal` | Should pass |
| 8 | minip | `standard` | Minimal monitors — borderline |
| 9 | minip | `comprehensive` | No manifest — should fail |
| 10 | coap | `standard` | No test specs — should fail? |
| 11 | new_prot | `minimal` | Scaffold — headers/braces OK? |

**Focus**: Pass/fail vs count reporting. 3-tier division adequacy. Artifact count thresholds. Should integrate `ivy_scaffold_check`?

**Group 6 cross-cutting**:
- Pattern detection vs catalog — what if protocol uses unlisted pattern?
- `ivy_scaffold_check` is QUIC-centric — does it penalize different architectures?
- `ivy_quality_gate` + `ivy_scaffold_check` integration?

---

## Group 7: LSP Navigation

### documentSymbol (file outline)
| # | Protocol | File | Evaluate |
|---|----------|------|---------|
| 1 | quic | `quic/quic_stack/quic_types.ivy` | Types, relations, functions |
| 2 | quic | `quic/quic_stack/quic_frame.ivy` | Large file — performance, hierarchy |
| 3 | quic | `quic/quic_tests/server_tests/quic_server_test_stream.ivy` | Exports, before/after |
| 4 | bgp | `bgp/bgp_stack/bgp_open_message.ivy` | Medium |
| 5 | minip | `minip/minip_stack/ping_frame.ivy` | Minimal |
| 6 | bgp | `bgp/bgp_stack/bgp_rib.ivy` | Empty file |

**Focus**: Symbol kind accuracy. Nesting hierarchy. Performance. before/after as children?

### workspaceSymbol (cross-workspace search)
| # | Query | Evaluate |
|---|-------|---------|
| 1 | `cid` | Common type — result count, ranking |
| 2 | `frame.stream` | Dotted qualified name handling |
| 3 | `handle` | Very common — performance |
| 4 | `bgp_open` | Protocol-specific prefix |
| 5 | `nonexistent_symbol_xyz` | Empty results |
| 6 | `ping` | Crosses minip and quic |

**Focus**: Case-insensitive substring. Ranking. Performance with 680+ files. Qualified names.

### goToDefinition
| # | Protocol | Symbol | From | Evaluate |
|---|----------|--------|------|---------|
| 1 | quic | `cid` | `quic_frame.ivy` | Jumps to `quic_types.ivy:30`? |
| 2 | quic | `frame.stream.handle` | test file | Frame definition? |
| 3 | quic | `order` | include statement | Stdlib resolution? |
| 4 | quic | `stream_seen` | behavior file | Relation declaration |
| 5 | bgp | `autonomous_system` | `bgp_speaker.ivy` | Cross-file BGP |
| 6 | minip | `ping_endpoint` | behavior file | Cross-file minip |
| 7 | quic | `collections` | include | Stdlib |

**Focus**: Cross-include resolution. Stdlib disambiguation. Multiple definitions. Deep include chains.

### findReferences
| # | Protocol | Symbol | Evaluate |
|---|----------|--------|---------|
| 1 | quic | `cid` | High-usage — many references |
| 2 | quic | `stream_seen` | Reads vs writes? |
| 3 | quic | `_finalize` | Test-scoped |
| 4 | bgp | `bgp_header_message_event` | Tests + behavior |
| 5 | minip | `ping_frame_pending` | Small model |

**Focus**: Completeness across included files. Scope awareness. Performance on `cid`. File grouping.

### hover
| # | Protocol | Symbol | Evaluate |
|---|----------|--------|---------|
| 1 | quic | `cid` | Type definition |
| 2 | quic | `frame.stream.handle` | Action params, return type |
| 3 | quic | `stream_seen` | Relation signature |
| 4 | quic | `endpoint_to_pid` | Function |
| 5 | bgp | `bgp_open_message` | Struct/object |
| 6 | minip | `estimated_latency` | Function |

**Focus**: Information richness. RFC visibility (if tags existed). Format. Usefulness vs reading declaration.

### prepareCallHierarchy + incomingCalls / outgoingCalls
| # | Protocol | Symbol | Direction | Evaluate |
|---|----------|--------|-----------|---------|
| 1 | quic | `frame.stream.handle` | incoming | Callers |
| 2 | quic | `frame.stream.handle` | outgoing | Callees |
| 3 | quic | `packet_event` | incoming | Many callers |
| 4 | quic | `_finalize` | incoming | Framework calls? |
| 5 | bgp | `bgp_open_message_event` | both | Medium model |
| 6 | minip | `app_send_event` | both | Simple chain |

**Focus**: Static analysis accuracy. Depth. before/after as "callers"? Performance.

### rename (read-only evaluation)
| # | Protocol | Symbol | Evaluate |
|---|----------|--------|---------|
| 1 | — | — | `prepareRename` support check |
| 2 | quic | `stream_seen` | Cross-file scope report |
| 3 | minip | `ping_frame_pending` | Smaller scope |

**Focus**: Is rename safe for Ivy? Scope detection. Should it be disabled?

### documentHighlight / selectionRange
| # | Protocol | Target | Evaluate |
|---|----------|--------|---------|
| 1 | quic | `cid` in `quic_types.ivy` | All occurrences |
| 2 | quic | Selection on `before` block | Smart expansion |
| 3 | minip | `ping_endpoint` in its file | Small file validation |

**Focus**: Same-name/different-scope handling. Block structure understanding.

**Group 7 cross-cutting**:
- LSP warm-up/indexing period — results reliable on cold start?
- Cold vs warm consistency
- Files outside `IVY_LSP_INCLUDE_PATHS` — what happens?
- Indexing status check before queries?

---

## Execution Plan

### Pre-flight
1. Verify LSP server running and indexed
2. Call `ivy_capabilities` to check tool availability
3. Note indexing status and file count

### Execution order
1. **Group 1** — Core Verification: `ivy_lint` (fast) → `ivy_model_info` → `ivy_verify`/`ivy_compile` (slow, skip if tools not on PATH)
2. **Group 2** — Dependency: `ivy_capabilities`, `ivy_include_graph`
3. **Group 3** — Diagnostics: `ivy_diagnostics`, compare with `ivy_lint` results
4. **Group 4** — Semantic: Traceability tools, compare quic (manifest) vs others (no manifest)
5. **Group 5** — Visualization: All 7 tools
6. **Group 6** — Pattern/Architecture: Across all protocols
7. **Group 7** — LSP: All 8 navigation features

### Per-tool procedure
1. Run the specified test scenarios
2. Record raw output (or representative excerpt for large outputs)
3. Score on 5 quality dimensions
4. Note issues, improvement ideas, surprises
5. Flag cross-tool observations

---

## Deliverables

### 1. Quality Scorecard
Per tool, one row:

| Tool | Correctness | Completeness | Usefulness | Error Handling | Param Adequacy | Notes |
|------|:-----------:|:------------:|:----------:|:--------------:|:--------------:|-------|
| ivy_lint | 1-5 | 1-5 | 1-5 | 1-5 | 1-5 | ... |
| ... | | | | | | |

### 2. Improvement Backlog
Prioritized list:

| # | Priority | Tool(s) | Issue | Proposed Change |
|---|----------|---------|-------|-----------------|
| 1 | High | ... | ... | ... |

Priority:
- **High**: Incorrect output, misleading results, security concern
- **Medium**: Missing useful params, output format improvements
- **Low**: Nice-to-have, cosmetic, minor UX

### 3. Cross-cutting Findings
- Naming inconsistencies (`test_file` vs `file_path`)
- Semantic model failure modes
- Tool overlap / consolidation candidates
- Output format standardization opportunities
- LSP + MCP integration gaps

---

## Already-identified Improvement Candidates

From code review during design:

| Tool | Issue | Category |
|------|-------|----------|
| ivy_compile | No `execution_mode` field — caller can't tell Docker vs subprocess | Medium |
| ivy_lint | Single-file only — no batch/glob param | Medium |
| ivy_verify | No `timeout` param | Medium |
| ivy_capabilities | Only reports presence, not versions | Low |
| ivy_traceability_matrix | Text truncated at 120 chars | Low |
| ivy_impact_analysis | Returns only first match for ambiguous names | Medium |
| ivy_diagnostics vs ivy_lint | Potential redundancy — superset relationship | Medium |
| ivy_cross_references | Node ID format not discoverable | Medium |
| Group 4 | `ivy_impact_analysis` / `ivy_cross_references` / `ivy_query_symbol` overlap | Medium |
| Group 5 | `test_file` vs `file_path` param naming inconsistency | Low |
