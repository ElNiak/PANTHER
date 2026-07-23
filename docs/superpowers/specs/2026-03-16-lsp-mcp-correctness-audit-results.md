# LSP & MCP Tool Correctness Audit Results

**Date**: 2026-03-16
**Target**: QUIC protocol models in `protocol-testing/quic/`
**Ground truth**: Multi-source (CLI commands, manual file reading, grep, LSP cross-validation)

## Executive Summary

**45 tool validations performed. 15 PASS, 17 PARTIAL, 8 FAIL, 5 not fully evaluated (oversized output).**

### Critical Findings

1. **Diagnostic parsing broken (FM-D)**: `ivy_verify`, `ivy_compile`, `ivy_model_info` all return `diagnostics=[]` and `diagnostic_count=0` when errors exist. Errors are captured in `raw_output` and `error_summary` but structured diagnostics are lost. Root cause: `parse_ivy_output()` fails on absolute paths produced in MCP staging mode.

2. **Coverage numbers are inflated by false positive tag matching**: Bare `# [N]` tags on struct fields (serialization ordinals) are false-positive matched to `rfc9000:N.*` requirements. The reported 70.3% coverage is significantly overstated. Tags in commented-out code are also counted.

3. **Semantic reference graph is non-functional**: `ivy_impact_analysis`, `ivy_cross_references`, and `ivy_action_dependency_graph` all return empty edge lists. The MCP semantic model builds nodes but never computes edges. Meanwhile, the LSP `findReferences` correctly finds 1404 references for `cid` across 167 files — proving the data exists but the MCP layer doesn't use it.

4. **Coverage tools disagree**: `ivy_coverage(mode=stats)` reports 30 uncovered requirements, `ivy_coverage_gaps()` reports 51 uncovered. A 21-requirement discrepancy on the same dataset.

5. **Scaffold checker has false negatives**: Reports `recovery` and `extensions` layers as missing when both directories exist with files. Reports `has_manifest=false` when `rfc9000_requirements.yaml` exists.

---

## Detailed Results by Phase

### Phase 1: Foundation Tools

| # | Tool | Verdict | Details |
|---|------|---------|---------|
| 1.1 | `ivy_capabilities()` | **PASS** | All 3 tools (ivy_check, ivyc, ivy_show) correctly detected on PATH |
| 1.2 | `ivy_lint(quic_types.ivy)` | **PASS** | 0 diagnostics; #lang present, braces balanced, no includes |
| 1.3 | `ivy_lint(quic_frame.ivy)` | **PASS** | 0 diagnostics; 5 includes all resolved correctly |
| 1.4 | `ivy_include_graph(quic_connection.ivy)` | **PASS** | All 11 includes found, resolved to correct paths. Correctly ignores commented includes. |
| 1.5 | `ivy_include_graph()` (full) | **PASS** | 680 files matches actual count. 2629 include edges. |

**Notes**: Include graph shows `candidates` from both `quic/` and `apt/` directories for each module (FM-B risk), but resolves correctly to closest path.

### Phase 2: Subprocess Verification

| # | Tool | Verdict | Details |
|---|------|---------|---------|
| 2.1 | `ivy_verify(quic_types.ivy)` | **PARTIAL** | `success=false` correct; `error_summary` correct; **`diagnostics=[]` WRONG** (should have 1 error) |
| 2.2 | `ivy_compile(quic_types.ivy)` | **PARTIAL** | Same FM-D bug: structured diagnostics lost |
| 2.3 | `ivy_model_info(quic_types.ivy)` | **PARTIAL** | Same FM-D bug: structured diagnostics lost |
| 2.4 | `ivy_verification_dashboard()` | **FAIL** | Crash: `_find_ivy_files() missing 1 required positional argument: 'search_root'` |

**Root cause (FM-D)**: `parse_ivy_output()` regex fails when ivy_check outputs absolute paths (which happens in MCP staging mode). The error format `<absolute_path>: line N: error: message` doesn't match the expected pattern.

### Phase 3: Semantic Model Tools

| # | Tool | Verdict | Details |
|---|------|---------|---------|
| 3.1 | `ivy_query_symbol("cid")` | **PARTIAL** | Found in correct file; **line=28, expected 29-30** (off by 1-2); inconsistent response schema (`type_info` vs `symbol_info`) |
| 3.2 | `ivy_query_symbol("quic_packet_type")` | **PARTIAL** | **kind="module"** should be "object"; **line=125** should be 126-127; **references: incoming=0, outgoing=0** (dead graph) |
| 3.3 | `ivy_impact_analysis("frame")` | **FAIL** | Resolved to **minip/ping_frame.ivy** instead of quic/quic_frame.ivy (FM-B: first-match across workspace, no protocol scoping). Edge lists empty. |
| 3.4 | `ivy_cross_references("cid")` | **FAIL** | With plain name: "Node not found". With full node_id format: found=true but **incoming=[], outgoing=[]**. LSP finds 1404 references for same symbol. |
| 3.5 | `ivy_coverage(mode=stats)` | **PARTIAL** | Level counts match manifest exactly (101 total, MUST=45, etc.); but **coverage values inflated by false positive tag matching** (bare `# [N]` ordinals matched to RFC sections) |
| 3.6 | `ivy_coverage(mode=matrix)` | **PARTIAL** | Structure correct; consistent with stats; 80 "annotations" for rfc9000:4.1 includes field ordinal `# [4]` on struct fields |
| 3.7 | `ivy_coverage_gaps()` | **FAIL** | Reports **51 uncovered** vs stats' 30 — 21-requirement discrepancy |
| 3.8 | `ivy_requirement_coverage()` | **PASS** | Identical to stats output; internally consistent |
| 3.9 | `ivy_traceability_matrix()` | **PASS** | Structurally correct; consistent with matrix |

### Phase 4: Diagnostics

| # | Tool | Verdict | Details |
|---|------|---------|---------|
| 4.1 | `ivy_diagnostics(quic_types.ivy)` | **PARTIAL** | Reports 0 diagnostics, but `ivy_verify` found `zero_rtt_allowed` undefined at line 134. Diagnostics uses lightweight analysis, missing compilation-level errors. |

### Phase 5: Visualization & Summary

| # | Tool | Verdict | Details |
|---|------|---------|---------|
| 5.1 | `ivy_visualize(dependencies)` | **FAIL** | 32 action nodes, **edges=[] always empty** |
| 5.2 | `ivy_visualize(state_machine)` | **PARTIAL** | `max_items=10` not respected; 1M+ char output |
| 5.3 | `ivy_visualize(layers)` | **PARTIAL** | 130 layers found; `module=null` for all; action names unqualified (14 "handle" duplicates) |
| 5.5 | `ivy_model_summary(summary)` | **PARTIAL** | 164 actions found; **rfcTagsCovered=50** vs stats' 71 covered — another coverage counting inconsistency |
| 5.7 | `ivy_action_dependency_graph()` | **FAIL** | 32 nodes, **edges=[] empty** (identical to 5.1) |
| 5.8 | `ivy_state_machine_view(connected)` | **PARTIAL** | Filter doesn't sufficiently reduce output (94K chars) |

### Phase 6: Patterns & Quality

| # | Tool | Verdict | Details |
|---|------|---------|---------|
| 6.1 | `ivy_patterns(quic, analyze)` | **PARTIAL** | Returns 463K chars of data, no output size control |
| 6.4 | `ivy_scaffold_check(quic)` | **FAIL** | **False negatives**: recovery and extensions reported as missing (both exist). `has_manifest=false` when rfc9000_requirements.yaml exists. |
| 6.6 | `ivy_quality_gate(quic, standard)` | **PASS** | Correctly identifies 4 missing #lang files and 24 unresolved includes (tls_msg, serdes). File count 202 matches. |
| 6.7 | `ivy_smart_suggestions(quic_types.ivy)` | **FAIL** | **571 suggestions all same type** (unguarded_state), massive duplication (port 8x, interface 7x). Not scoped to requested file — returns workspace-wide results. |

### Phase 8: LSP Features

| # | Feature | Verdict | Details |
|---|---------|---------|---------|
| 8.1 | `hover("cid")` | **PARTIAL** | Correct file; display text duplicated: "type cid type cid" |
| 8.2 | `hover("quic_packet_type")` | **PARTIAL** | Correct file; display text duplicated: "object quic_packet_type quic_packet_type = {" |
| 8.3 | `documentSymbol(quic_types.ivy)` | **PARTIAL** | 17 types correct with lines; **alias `aid` line=39 should be 43** (fallback matched comment); **definition names garbled** as "def211169" |
| 8.6 | `goToDefinition(include quic_types)` | **PASS** | Correctly resolves to quic_types.ivy |
| 8.7 | `findReferences(cid)` | **PASS** | **1404 references across 167 files** — correct and comprehensive |
| 8.9 | `workspaceSymbol` | **PARTIAL** | Returns 100 symbols; alphabetical truncation means only apt/ files shown |

---

## Bug Taxonomy

### Severity: Critical (Silently Wrong Answers)

| ID | Bug | Tools Affected | Impact |
|----|-----|---------------|--------|
| **C1** | `parse_ivy_output()` fails on absolute paths → `diagnostics=[]` | ivy_verify, ivy_compile, ivy_model_info | Users see "0 errors" when errors exist |
| **C2** | Bare `# [N]` tags false-positive matched to RFC requirements | ivy_coverage, ivy_traceability_matrix, ivy_requirement_coverage | Coverage inflated from ~40% to 70.3% |
| **C3** | Semantic edge graph never computed | ivy_impact_analysis, ivy_cross_references, ivy_action_dependency_graph | Reference/dependency analysis returns empty data |
| **C4** | Coverage stats vs gaps disagree by 21 requirements | ivy_coverage(stats) vs ivy_coverage_gaps | Contradictory answers from related tools |

### Severity: High (Incorrect Data)

| ID | Bug | Tools Affected | Impact |
|----|-----|---------------|--------|
| **H1** | Line numbers off by 1-2 in symbol extraction | ivy_query_symbol | Wrong line reference for navigation |
| **H2** | `object` declarations reported as `kind="module"` | ivy_query_symbol | Wrong symbol classification |
| **H3** | `ivy_impact_analysis` resolves to wrong protocol | ivy_impact_analysis | Returns data for minip instead of quic |
| **H4** | `ivy_scaffold_check` reports existing layers as missing | ivy_scaffold_check | False negative layer detection |
| **H5** | `ivy_scaffold_check` reports manifest as missing when it exists | ivy_scaffold_check | Wrong manifest detection |

### Severity: Medium (Cosmetic/Usability)

| ID | Bug | Tools Affected | Impact |
|----|-----|---------------|--------|
| **M1** | Hover text duplicated ("type cid type cid") | LSP hover | Confusing display |
| **M2** | `alias` line number wrong (matches comment, not declaration) | LSP documentSymbol | Wrong navigation target |
| **M3** | `definition` names garbled as "def211169" | LSP documentSymbol | Unintelligible names |
| **M4** | `smart_suggestions` not file-scoped, massive duplicates | ivy_smart_suggestions | 571 duplicate workspace-wide suggestions for file query |
| **M5** | `max_items` not respected for state_machine view | ivy_visualize | Output explosion (1M+ chars) |
| **M6** | Layer action names unqualified (14 "handle" duplicates) | ivy_visualize(layers) | Can't distinguish actions |
| **M7** | `module` field always null in layers view | ivy_visualize(layers) | Missing module grouping |

### Severity: Low (Crashes/Missing Features)

| ID | Bug | Tools Affected | Impact |
|----|-----|---------------|--------|
| **L1** | `_find_ivy_files()` missing argument | ivy_verification_dashboard | Tool crashes |
| **L2** | workspaceSymbol returns alphabetically truncated results | LSP workspaceSymbol | Only apt/ symbols visible |

---

## Recommendations

### Immediate Fixes (Critical)

1. **Fix `parse_ivy_output()` to handle absolute paths** — The regex should strip/normalize the path prefix before matching. This affects all verification tools.

2. **Fix tag normalization to distinguish RFC annotations from field ordinals** — Require explicit RFC prefix (e.g., `# [rfc9000:8]` or `# [RFC:8]`) or use a different syntax for field ordinals. Alternatively, only match tags that appear on `require`/`ensure`/`assume` lines, not struct field declarations.

3. **Compute semantic edges** — The model builds symbol nodes but never adds edges. Wire up the edge computation using include-graph transitivity and symbol reference data (the LSP indexer has this data already — 1404 references for `cid`).

4. **Reconcile coverage stats and gaps** — Both tools should use the same coverage calculation. One off-by-21 discrepancy means one is wrong.

### High Priority Fixes

5. **Fix line number computation** — `source[:m.start()].count("\n")` appears off by 1-2. Verify 0-based vs 1-based indexing across all consumers.

6. **Fix scaffold_check layer detection** — Use directory name matching in addition to file content patterns. Detect `rfc*requirements*.yaml` as manifest.

7. **Fix `ivy_impact_analysis` to scope by protocol** — Add protocol parameter or use proximity resolution.

### Medium Priority

8. **Deduplicate hover text** — Remove the duplicated keyword+name in hover display.
9. **Scope `smart_suggestions` to requested file** — Respect `file_path` parameter.
10. **Enforce `max_items` for all visualization views** — State machine view ignores it.

---

## Ground Truth Reference Values

### T1: quic_types.ivy
- Types: 17 (cid, itoken, version, pkt_num, microsecs, error_code, stream_kind, type_bits, cid_length, cid_seq, microseconds, seconds, milliseconds, reset_token, port, ipv4, ipv6)
- Aliases: 1 (aid = cid, line 43)
- Objects: 3 (bit, role, quic_packet_type)
- Enums: 3 (stream_kind, role.this, quic_packet_type.this)
- Actions: 1 (quic_packet_type.next, line 133)
- Individuals: 2 (bit.zero line 78, bit.one line 79)
- Includes: 0
- #lang: present (line 1)

### T3: quic_connection.ivy
- Includes: 11 (quic_types, quic_transport_error_code, quic_time, quic_application, quic_security, quic_frame, quic_packet, quic_packet_retry, quic_packet_vn, quic_packet_0rtt, quic_packet_coal_0rtt)
- Commented includes: 2 (quic_fsm_sending, quic_fsm_receiving)

### T6: rfc9000_requirements.yaml
- Total requirements: 101
- MUST: 45, MUST NOT: 12, SHOULD: 17, SHOULD NOT: 3, MAY: 24
- Total .ivy files in quic/: 202
- Total .ivy files in workspace: 680

### LSP Reference Counts
- `cid` type: 1404 references across 167 files (includes both quic/ and apt/)
