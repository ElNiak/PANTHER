# Ivy Tooling Audit Results — LSP Navigation & MCP Tools

**Date**: 2026-03-13
**Auditor**: Claude (automated)
**Scope**: 25 MCP tools + 14 LSP features across 6 protocols
**Protocols tested**: quic (202 files), apt (361), bgp (39), coap (36), minip (18), new_prot (10)

---

## Executive Summary

The audit reveals a **two-tier quality landscape**:

- **Well-built tools** (Group 6 — Pattern & Architecture): `ivy_pattern_scaffold` (4.6/5), `ivy_pattern_analysis` (4.4/5), `ivy_scaffold_check` (4.4/5), `ivy_quality_gate` (4.2/5), and `ivy_extract_requirements` (4.6/5) are production-quality with correct parameter handling and useful output.

- **Systematically broken tools** (Group 5 — Visualization): ALL 7 tools ignore the `test_file` parameter, producing 65KB–2.18MB unscoped dumps. `ivy_smart_suggestions` ignores ALL parameters entirely.

- **LSP navigation** is partially functional: `documentSymbol` and `findReferences` work reasonably well, but `hover` is nearly broken (1/6 correct), `workspaceSymbol` returns unfiltered dumps, and 9 of 14 features are untestable via Claude Code's LSP tool.

**Critical blockers found**: 8
**Total improvement candidates**: 42

---

## Quality Scorecard

### MCP Tools

| Tool | Correct | Complete | Useful | Err Handle | Param Adeq | Avg | Group |
|------|:-------:|:--------:|:------:|:----------:|:----------:|:---:|-------|
| **ivy_lint** | 2 | 1 | 1 | 3 | 3 | **2.0** | G1 |
| **ivy_verify** | 2 | 1 | 1 | 3 | 3 | **2.0** | G1 |
| **ivy_compile** | 2 | 1 | 1 | 3 | 3 | **2.0** | G1 |
| **ivy_model_info** | 2 | 1 | 1 | 3 | 4 | **2.2** | G1 |
| **ivy_capabilities** | 4 | 2 | 3 | 4 | 3 | **3.2** | G2 |
| **ivy_include_graph** | 2 | 3 | 3 | 2 | 2 | **2.4** | G2 |
| **ivy_diagnostics** | 4 | 3 | 4 | 4 | 3 | **3.6** | G3 |
| **ivy_traceability_matrix** | 2 | 3 | 2 | 3 | 2 | **2.4** | G4 |
| **ivy_requirement_coverage** | 2 | 4 | 2 | 3 | 2 | **2.6** | G4 |
| **ivy_impact_analysis** | 2 | 3 | 2 | 4 | 3 | **2.8** | G4 |
| **ivy_extract_requirements** | 5 | 4 | 5 | 5 | 4 | **4.6** | G4 |
| **ivy_generate_manifest** | 4 | 3 | 4 | 4 | 4 | **3.8** | G4 |
| **ivy_cross_references** | 2 | 4 | 2 | 3 | 1 | **2.4** | G4 |
| **ivy_query_symbol** | 3 | 3 | 3 | 4 | 3 | **3.2** | G4 |
| **ivy_action_requirements** | 2 | 4 | 2 | 3 | 2 | **2.6** | G5 |
| **ivy_model_summary** | 2 | 4 | 2 | 3 | 2 | **2.6** | G5 |
| **ivy_coverage_gaps** | 2 | 3 | 2 | 3 | 1 | **2.2** | G5 |
| **ivy_action_dependency_graph** | 2 | 4 | 2 | 3 | 2 | **2.6** | G5 |
| **ivy_state_machine_view** | 3 | 4 | 3 | 3 | 3 | **3.2** | G5 |
| **ivy_layered_overview** | 3 | 4 | 2 | 3 | 2 | **2.8** | G5 |
| **ivy_smart_suggestions** | 1 | 3 | 1 | 2 | 1 | **1.6** | G5 |
| **ivy_pattern_analysis** | 5 | 4 | 4 | 4 | 5 | **4.4** | G6 |
| **ivy_pattern_scaffold** | 4 | 5 | 5 | 5 | 4 | **4.6** | G6 |
| **ivy_scaffold_check** | 4 | 4 | 5 | 4 | 5 | **4.4** | G6 |
| **ivy_quality_gate** | 4 | 4 | 4 | 4 | 5 | **4.2** | G6 |

**Group averages**: G1=2.1, G2=2.8, G3=3.6, G4=3.1, G5=2.5, G6=4.4

### LSP Features

| Feature | Correct | Complete | Useful | Err Handle | Param Adeq | Avg | Testable? |
|---------|:-------:|:--------:|:------:|:----------:|:----------:|:---:|-----------|
| **documentSymbol** | 3 | 4 | 3 | 5 | 4 | **3.8** | Yes |
| **workspaceSymbol** | 1 | 1 | 1 | 3 | 1 | **1.4** | Partial |
| **goToDefinition** | 2 | 2 | 2 | 4 | 4 | **2.8** | Yes |
| **findReferences** | 3 | 3 | 3 | 5 | 4 | **3.6** | Yes |
| **hover** | 1 | 1 | 1 | 4 | 4 | **2.2** | Yes |
| **rename** | — | — | — | — | — | — | No (not in LSP tool) |
| **documentHighlight** | — | — | — | — | — | — | No (not in LSP tool) |
| **selectionRange** | — | — | — | — | — | — | No (not in LSP tool) |
| **completion** | — | — | — | — | — | — | No (not in LSP tool) |
| **signatureHelp** | — | — | — | — | — | — | No (not in LSP tool) |
| **codeAction** | — | — | — | — | — | — | No (not in LSP tool) |
| **codeLens** | — | — | — | — | — | — | No (not in LSP tool) |
| **foldingRange** | — | — | — | — | — | — | No (not in LSP tool) |
| **publishDiagnostics** | — | — | — | — | — | — | No (push-based) |
| **callHierarchy** | — | — | — | — | — | — | Not implemented |

**Only 5 of 14 features fully testable via Claude Code's LSP tool.**

---

## Improvement Backlog

### Critical (8 items)

| # | Tool(s) | Issue | Proposed Change |
|---|---------|-------|-----------------|
| C1 | G1: ivy_lint, ivy_verify, ivy_compile, ivy_model_info | **Workspace root misconfiguration**: paths without `protocol-testing/` prefix get "File not found". MCP server uses `os.getcwd()` which points to panther_ivy root, not protocol-testing/. | Add resolved absolute path to error messages: `"File not found: {path} (resolved: {abs_path}, root: {root})"`. Document expected path format. |
| C2 | G5: ALL 7 visualization tools | **`test_file` parameter is completely ignored** across action_requirements, model_summary, coverage_gaps, action_dependency_graph, state_machine_view, layered_overview, smart_suggestions. Output is always full unscoped global dump. | Fix the shared visualization handler code path that processes `test_file`. The param is accepted but never applied as a filter. |
| C3 | ivy_smart_suggestions | **ALL parameters ignored**: `file_path`, `line`, `context` have zero effect. Returns identical ~114KB global dump regardless of inputs. | Implement file/line/context filtering in `handle_smart_suggestions()`. |
| C4 | ivy_traceability_matrix, ivy_requirement_coverage | **0% coverage despite annotations**: Bracket tags in code use `[4]`, `[3]` format, but manifest uses `rfc9000:4.1` IDs. Matching fails. | Normalize tag format: either accept bare numeric tags or teach the scanner to map `[N]` to `rfc9000:N` based on manifest context. |
| C5 | ivy_include_graph | **Path key mismatch bug**: `graph.get(relative_path)` fails because graph keys have `protocol-testing/` prefix but user paths don't. `includes` always `[]` for individual queries. | Normalize graph keys to match user-supplied relative paths, or normalize lookup key to include prefix. |
| C6 | LSP: hover | **Nearly broken**: 5 of 6 scenarios return nothing or wrong info. Hovering on declarations fails. Cross-file resolution returns wrong symbols. | Fix symbol resolution at declaration sites. Return type signature, params, return type for all symbol kinds. |
| C7 | LSP: workspaceSymbol | **No query filtering**: Returns identical unfiltered 100-symbol dump regardless of query text. Claude Code LSP tool also doesn't expose query parameter. | Implement substring/fuzzy matching on query. Coordinate with Claude Code LSP tool to pass query text. |
| C8 | ivy_action_requirements | **`file_path` returns empty**: Passing `file_path` scoping returns `{"actions": []}` with `scoped: false` instead of filtering. | Fix `file_path` filter in `handle_action_requirements()`. |

### High Priority (10 items)

| # | Tool(s) | Issue | Proposed Change |
|---|---------|-------|-----------------|
| H1 | G5: ALL visualization tools | **No `protocol` parameter**: Without it, all tools dump entire multi-protocol model (65KB–2.18MB). | Add `protocol` parameter to all Group 5 tools for scoping output to a single protocol directory. |
| H2 | G5: action_requirements | **Pagination fields exist but non-functional**: `offset`, `limit`, `hasMore` in schema but always 0/false. | Implement actual pagination backed by these fields. |
| H3 | G5: ALL tools | **Absolute worktree paths inflate output 2-5x**: Every JSON object contains full absolute paths. | Use relative paths with a single `root` field at top level. |
| H4 | LSP: findReferences | **Self-references systematically omitted**: References in the queried file itself are excluded. `stream_seen` has 8 usages in quic_frame.ivy, all missed. | Include same-file references in results. |
| H5 | LSP: goToDefinition | **Include resolution returns references instead of target**: `include collections` shows all OTHER files that include collections, not the collections.ivy file itself. | Navigate to the included file, not to other includers. |
| H6 | LSP: goToDefinition | **Local declarations return "No definition found"**: Cursor on `relation stream_seen(...)` declaration returns nothing. | Return self-location or "already at definition" for declarations. |
| H7 | ivy_cross_references | **node_id format requires full absolute paths**: Documented short-form `file.ivy:line:symbol` doesn't work. Users can't discover valid node_ids without calling other tools first. | Accept short-form paths and symbol names as alternatives to absolute-path node_ids. |
| H8 | ivy_quality_gate | **`includes_resolve` always fails**: Ivy stdlib files (order, collections, ip) are never in search path. No protocol passes even `minimal` gate. | Exempt known stdlib modules from include resolution check, or add stdlib to search path. |
| H9 | ivy_diagnostics | **No layer/severity filtering**: 182 diagnostics for quic_frame.ivy. | Add optional `layers` (list) and `min_severity` params. |
| H10 | ivy_impact_analysis + ivy_query_symbol | **Dotted names don't resolve**: `frame.stream.handle` returns "not found" in all semantic tools. | Implement qualified name resolution for dotted paths. |

### Medium Priority (14 items)

| # | Tool(s) | Issue | Proposed Change |
|---|---------|-------|-----------------|
| M1 | ivy_verify, ivy_compile | **No `timeout` parameter**: ivy_compile has hardcoded 300s Docker timeout; ivy_verify has no explicit timeout. | Expose `timeout` param (default: 120s for verify, 300s for compile). |
| M2 | ivy_compile | **No `execution_mode` field**: Caller can't tell if Docker or subprocess was used. Fallback is silent. | Add `"execution_mode": "docker"|"subprocess"` to response. Log fallback at INFO level. |
| M3 | ivy_capabilities | **Only reports presence, not versions**: No Docker status, Z3 availability, workspace root. | Add tool versions, Docker image availability, Z3 status, current workspace_root. |
| M4 | ivy_traceability_matrix | **Text truncated at 120 chars**: May lose important context. | Increase to 200 chars or add `full_text` param. |
| M5 | ivy_traceability_matrix, ivy_requirement_coverage | **`relative_path` scoping non-functional**: Returns identical results with/without file scope. | Implement actual file-scope filtering in the semantic model query. |
| M6 | ivy_impact_analysis | **First-match limitation**: Returns only first symbol for ambiguous names. `cid` found in apt/ but not main quic/. | Return all matches with disambiguation info, or accept file context to scope. |
| M7 | ivy_query_symbol | **Inconsistent response schema**: Types return `type_info` with `is_enum/variants`; relations return `symbol_info` with `kind/params/references`. | Normalize to single response shape with optional fields. |
| M8 | ivy_generate_manifest | **`layer` field always empty**: Protocol name passed but layer inference doesn't work. `testable` always true. | Implement basic layer inference from requirement context. |
| M9 | ivy_pattern_scaffold | **`variant_names` and `roles` not substituted**: Params accepted but generated code uses generic placeholders. | Wire params into template substitution. |
| M10 | ivy_scaffold_check | **Scoring too binary**: minip (19 files) scores same 71% as BGP (39 files). | Add quality-weighted scoring (not just layer presence/absence). |
| M11 | LSP: documentSymbol | **Included-file symbols noise**: stdlib symbols (collections, order) flood the symbol list, all at Line 1. | Add option to exclude included-file symbols. Or filter stdlib symbols. |
| M12 | LSP: documentSymbol | **Synthetic definition names**: `def211193`, `prop211892` instead of meaningful names. | Use actual Ivy names or inferred names for unnamed definitions. |
| M13 | LSP: documentSymbol | **Line number errors**: Some symbols report Line 1 instead of actual line (e.g., `aid` at Line 1 instead of Line 43). | Fix line number tracking for all symbol kinds. |
| M14 | ivy_lint, ivy_diagnostics | **ivy_lint is a strict subset of ivy_diagnostics**: Structural layer in diagnostics is identical to ivy_lint. | Consider deprecating ivy_lint or adding a `layers` param to ivy_diagnostics. Keep ivy_lint only if sub-millisecond speed matters (hook use case). |

### Low Priority (10 items)

| # | Tool(s) | Issue | Proposed Change |
|---|---------|-------|-----------------|
| L1 | ivy_include_graph | **Full graph exceeds MCP output limits (118KB, 680 files)**: No pagination. | Add `max_depth`, `limit`, and `protocol` params. |
| L2 | ivy_include_graph | **No file existence check**: Returns empty data silently for nonexistent files. | Validate file existence and return distinct error. |
| L3 | ivy_include_graph | **Path prefix inconsistency**: `included_by` paths have `protocol-testing/` prefix but `file` field echoes user input. | Normalize all paths in response. |
| L4 | ALL MCP tools | **No error codes**: All errors are `{"success": false, "message": "..."}`. | Add `error_code` field for programmatic handling. |
| L5 | ivy_pattern_analysis | **QUIC detect mode: 463KB**: Needs summary mode. | Add `summary` mode that returns counts instead of full details. |
| L6 | ivy_scaffold_check | **`has_manifest` always false**: Even QUIC (which has a manifest) shows false. | Fix manifest detection path. |
| L7 | ivy_state_machine_view | **Cross-protocol contamination with `state_var_filter`**: Filtering by `stream_seen` returns guards from ALL protocols mixed together. | Scope filter output to the owning protocol. |
| L8 | LSP: goToDefinition | **Dotted attribute paths not supported**: `frame.crypto.handle.weight` returns "No definition found". | Support goToDefinition on dotted paths. |
| L9 | ivy_capabilities | **`success` always true even if no tools found**: Should be false if core tools missing. | Return `success: false` if ivy_check, ivyc, or ivy_show not found. |
| L10 | LSP | **Call hierarchy not implemented**: Server returns "Method Not Found" for prepareCallHierarchy. | Implement call hierarchy using Ivy's action/before/after patterns. |

---

## Cross-Cutting Findings

### 1. `test_file` vs `file_path` naming and functionality
- **Naming inconsistency**: Some tools use `test_file`, others `file_path`, some have both. No documented difference.
- **Both are broken**: `test_file` is ignored in all Group 5 tools. `file_path` in `ivy_action_requirements` returns empty.
- **Recommendation**: Unify to single `scope_file` parameter. Fix the underlying filtering code.

### 2. Tool overlap — consolidation candidates
Three tools query the same semantic model from different angles with significant redundancy:
- `ivy_impact_analysis` (symbol name → edges)
- `ivy_cross_references` (node_id → edges)
- `ivy_query_symbol` (symbol name → type info + ref counts)

**Recommendation**: Merge `impact_analysis` + `query_symbol` into `ivy_symbol_info` returning both type info and edge data. Make `cross_references` accept symbol names as alternative to node_ids.

### 3. Output size problem
22 of ~170 total invocations exceeded 50KB. Group 5 tools are the worst offenders:
- `ivy_action_requirements` no-params: **2.18 MB**
- `ivy_state_machine_view` no-params: **975 KB**
- `ivy_pattern_analysis` quic detect: **463 KB**
- `ivy_coverage_gaps` no-params: **263 KB**

**Root cause**: No working scoping parameters + absolute paths inflate output.
**Recommendation**: (1) Fix `test_file` scoping, (2) add `protocol` param, (3) use relative paths, (4) implement pagination.

### 4. Semantic model completeness
The lazy-built semantic model has significant gaps:
- `cid` (fundamental QUIC type) found by `query_symbol` but not by `impact_analysis` — different search paths
- `stream_seen` found but with 0 references despite widespread use
- Dotted qualified names (`frame.stream.handle`) fail everywhere
- Edge data is sparse — many found symbols show 0 incoming/outgoing edges

**Root cause**: Lightweight regex-based parsing misses complex declarations and qualified references.

### 5. APT model contamination
Both MCP tools and LSP features resolve symbols preferentially from the `apt/` model directory (361 files, the largest model). This causes:
- `ivy_query_symbol("cid")` resolves to apt/quic_types.ivy instead of quic/quic_types.ivy
- LSP hover on BGP symbol returns info from apt/ variant
- `findReferences` includes apt/ matches (inflating counts)

**Recommendation**: Consider model-tree scoping — tools should prefer symbols from the same protocol directory as the query context.

### 6. Group 6 quality gap
Group 6 (Pattern & Architecture) tools score 4.2-4.6/5 vs Group 5 (Visualization) at 1.6-3.2/5. This suggests:
- Group 6 was developed more recently or with better testing
- Group 6 uses `protocol` parameter correctly for scoping
- Group 5 shares a broken `test_file` code path that Group 6 doesn't use

### 7. LSP Claude Code interface limitations
9 of 14 LSP features cannot be tested because Claude Code's LSP tool only supports: goToDefinition, findReferences, hover, documentSymbol, workspaceSymbol, goToImplementation, prepareCallHierarchy, incomingCalls, outgoingCalls. Missing: rename, completion, signatureHelp, codeAction, codeLens, foldingRange, documentHighlight, selectionRange. Also, workspaceSymbol doesn't expose a `query` parameter.

### 8. Security — path traversal protection works
The `_validate_path()` function correctly rejects `../../../etc/passwd` with a distinct error message using `os.path.realpath` + prefix check. This is the secure approach.

---

## Tool Rankings

### Top 5 (by average score)
1. **ivy_extract_requirements** — 4.6/5 — Perfect text parsing, clean edge cases
2. **ivy_pattern_scaffold** — 4.6/5 — Excellent templates with documentation
3. **ivy_pattern_analysis** — 4.4/5 — All modes work, protocol scoping correct
4. **ivy_scaffold_check** — 4.4/5 — Actionable 14-layer completeness scoring
5. **ivy_quality_gate** — 4.2/5 — Good 3-tier system (blocked by stdlib issue)

### Bottom 5 (by average score)
1. **ivy_smart_suggestions** — 1.6/5 — ALL parameters ignored
2. **ivy_lint** — 2.0/5 — Workspace root issue blocks all use
3. **ivy_verify** — 2.0/5 — Same workspace root issue
4. **ivy_compile** — 2.0/5 — Same workspace root issue
5. **ivy_model_info** — 2.2/5 — Same workspace root issue

### LSP Rankings (testable features only)
1. **documentSymbol** — 3.8/5 — Best LSP feature, noisy but functional
2. **findReferences** — 3.6/5 — Strong cross-file, misses self-refs
3. **goToDefinition** — 2.8/5 — Wrong include semantics, many misses
4. **hover** — 2.2/5 — Nearly broken, 1/6 correct
5. **workspaceSymbol** — 1.4/5 — No query filtering

---

## Verification Checklist

- [x] All 25 MCP tools called at least once and scored
- [x] 5 of 14 LSP features fully tested (9 untestable via Claude Code LSP tool, 1 confirmed missing)
- [x] All 6 protocols with .ivy files used in at least one test
- [x] Quality scorecard complete with no empty cells (for testable tools)
- [x] Improvement backlog has clear priorities (8 critical, 10 high, 14 medium, 10 low)
- [x] Cross-cutting findings address: naming consistency, tool overlap, output format, semantic model failures

---

## Appendix: Notable Raw Outputs

### ivy_diagnostics on quic_frame.ivy (182 diagnostics)
- 61 warnings: "Orphaned RFC tag: [N] does not match any loaded requirement manifest"
- 102 hints: "Assertion without RFC bracket tag annotation"
- 19 hints: "State var 'X' is written but not guarded by any requirement"

### ivy_scaffold_check scores across protocols
| Protocol | Score | Layers | Files | Missing |
|----------|-------|--------|-------|---------|
| quic | 86% | 12/14 | 202 | recovery, extensions |
| bgp | 71% | 10/14 | 39 | packet, connection, recovery, extensions |
| coap | 71% | 10/14 | 36 | packet, test_specs, recovery, extensions |
| minip | 71% | 10/14 | 19 | packet, connection, recovery, extensions |
| apt | 71% | 10/14 | 361 | connection, application, recovery, extensions |
| new_prot | 14% | 2/14 | 10 | 12 layers missing |

### ivy_quality_gate — no protocol passes minimal
All protocols fail `includes_resolve` check because Ivy stdlib (order, collections, ip, deserializer) is not in search path.

### ivy_extract_requirements — perfect extraction
```json
{"requirements":[
  {"text":"The implementation MUST NOT ignore this.","level":"MUST NOT","offset":0},
  {"text":"It SHOULD handle gracefully.","level":"SHOULD","offset":40},
  {"text":"Clients MAY retry.","level":"MAY","offset":69}
],"total":3,"by_level":{"MAY":1,"MUST NOT":1,"SHOULD":1}}
```

### findReferences for `cid` — 376 references across 124 files
Comprehensive cross-workspace search covering quic_stack, quic_attacks_stack, apt models, bgp, coap, minip, and patterns.
