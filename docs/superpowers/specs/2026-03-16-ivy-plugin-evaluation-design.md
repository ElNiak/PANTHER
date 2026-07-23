# Ivy Plugin Evaluation Framework: Quality, Effectiveness, and Integration

**Date**: 2026-03-16
**Status**: Design specification
**Scope**: End-to-end evaluation of ivy-lsp + panther-ivy-plugin Claude Code plugins
**Prior work**: `2026-03-13-ivy-tooling-audit-results.md` (42 improvement items), `2026-03-13-ivy-tooling-evaluation.md` (SOTA comparison)
**Goal**: Produce an AMC3 WP2 deliverable, fix pre-release issues, and establish a repeatable quality framework

---

## 1. Problem Statement

The PANTHER project has built two Claude Code plugins for Ivy formal protocol verification:

- **ivy-lsp** (2 files): LSP language server config for `.ivy` files
- **panther-ivy-plugin** (35+ files): 4 agents, 5 commands, 11 skills, 3 hooks, 1 MCP server (15+ tools), CLAUDE.md

These plugins address 6 AMC3 research problems:
1. Steep learning curve for formal methods
2. Up-front modeling effort (2-4x informal docs)
3. Missing specifications for legacy systems
4. Confidentiality constraints (proprietary code)
5. Maintenance burden (spec-code synchronization)
6. Partial coverage and abstraction gaps

A prior audit (2026-03-13) scored MCP tools and LSP features individually but did not evaluate:
- Plugin-level completeness vs Claude Code capabilities
- Effectiveness at solving the 6 AMC3 problems
- Integration quality across LSP↔MCP↔hooks↔agents↔skills
- Alignment with PANTHER's build workflow (flatten→compile→mirror)
- Comparison with official Claude Code plugins (pyright-lsp, plugin-dev)

This evaluation fills those gaps.

---

## 2. Evaluation Architecture

### 2.1 Four Dimensions × Two Modes

| Dimension | Static (offline, no Ivy env) | Live (Ivy environment required) |
|-----------|------------------------------|----------------------------------|
| **A. Correctness** | Schema validation, frontmatter parsing, script analysis | LSP operations, MCP tool calls, hook execution |
| **B. Completeness** | Feature gap matrix vs Claude Code capabilities | Parameter functionality, workflow coverage |
| **C. Effectiveness** | Baseline estimation from prior audit | Timed workflows mapped to AMC3 Problems 1-6 |
| **D. Integration** | Cross-reference integrity, version consistency | End-to-end workflow chains, workspace coherence |

### 2.2 Relationship to Prior Audit

| Prior Audit (2026-03-13) | This Evaluation Adds |
|---|---|
| 42 MCP/LSP improvement items scored 1-5 | Regression tracking + aggregate dimension scoring |
| Tool-by-tool quality scorecards | Plugin-level correctness + completeness |
| SOTA comparison (TLA+, SPIN, Tamarin, ProVerif) | Claude Code plugin ecosystem comparison |
| MCP tool correctness only | Full plugin evaluation (agents, skills, hooks, commands, CLAUDE.md) |
| No effectiveness measurement | Timed scenarios with AMC3 success thresholds |
| No PANTHER integration testing | Build workflow alignment (flatten, mirror, role inversion) |

---

## 3. Dimension A: Correctness

**Question**: Do the plugins work as documented?

### 3.1 Static Tests (A.S1–A.S14)

**Plugin manifest validation:**

| ID | File | Checks | Pass Criteria |
|----|------|--------|---------------|
| A.S1 | `ivy-lsp/.claude-plugin/plugin.json` | Valid JSON; `name`, `version`, `author` fields | All required fields present, JSON parses without error |
| A.S2 | `ivy-lsp/.lsp.json` | Valid JSON; `command`, `extensionToLanguage` | `.ivy` → `ivy` mapping; `uvx` command present |
| A.S3 | `panther-ivy-plugin/.claude-plugin/plugin.json` | Valid JSON; `name`, `version`, `author` | Same as A.S1 |
| A.S4 | `panther-ivy-plugin/.mcp.json` | Valid JSON; `mcpServers.ivy-tools` | Uses `${CLAUDE_PLUGIN_ROOT}` in command path |
| A.S5 | `panther-ivy-plugin/hooks/hooks.json` | 3 hook events; valid matchers | PreToolUse→`Bash`, PostToolUse→`Write\|Edit`, SessionStart (no matcher) |

**Agent frontmatter validation (A.S6–A.S9):**

| ID | Agent File | Required Fields | Additional Checks |
|----|-----------|-----------------|-------------------|
| A.S6 | `agents/methodology-guide.md` | `name`, `description`, `tools` | tools list includes Read, Grep, Glob, Bash, Write, Edit, ToolSearch |
| A.S7 | `agents/model-reviewer.md` | `name`, `description`, `tools` | tools list is read-only subset (no Write/Edit) |
| A.S8 | `agents/spec-analyst.md` | `name`, `description`, `tools` | tools list includes Write, Edit |
| A.S9 | `agents/traceability-agent.md` | `name`, `description`, `tools` | tools list includes WebFetch |

**Command frontmatter validation (A.S10):**

All 5 commands (`nct-check`, `nct-compile`, `nct-model-info`, `nct-scaffold`, `nct-add-pattern`) must have:
- YAML frontmatter with `name`, `description`
- `arguments` array with `name`, `description`, `required` for each arg
- nct-check: `file` (required), `isolate` (optional)
- nct-compile: `file` (required), `target` (optional, default="test"), `isolate` (optional)
- nct-scaffold: `type` (required), `name` (optional), `protocol` (optional), `role` (optional)

**Skill frontmatter validation (A.S11–A.S13):**

All 11 skills must have:
- YAML frontmatter with `name`, `description`
- Content body > 500 characters
- Skills: counterexample-guide, incremental-spec-dev, ivy-lsp-walkthrough, ivy-writing-guide, methodology-reference, nact-methodology, nct-methodology, nsct-methodology, specification-patterns, tooling-reference, workflow-reference

**Hook script validation (A.S14):**

| Script | Checks |
|--------|--------|
| `block-direct-ivy.sh` | Has shebang; reads JSON stdin; checks for `ivy_check\|ivyc\|ivy_show\|ivy_to_cpp`; exits 0 |
| `post-write-ivy-lint.sh` | Has shebang; filters `.ivy` files; checks `#lang` header; counts braces |
| `detect-ivy-workspace.sh` | Has shebang; sources `workspace-common.sh`; detects 3 workspace types |

### 3.2 Live Tests (A.L1–A.L14)

| ID | Test | Input | Expected Result | Prior Audit Item |
|----|------|-------|-----------------|------------------|
| A.L1 | LSP server lifecycle | Start via `.lsp.json` uvx command | `/tmp/ivy-lsp.log` shows init within 30s | — |
| A.L2 | LSP documentSymbol | `quic_types.ivy` | Type declarations returned, hierarchical | M11-M13 (noise) |
| A.L3 | LSP goToDefinition | `cid` in `quic_frame.ivy` | Jumps to `quic_types.ivy` | H5, H6 |
| A.L4 | LSP findReferences | `stream_seen` | Cross-file results | H4 (self-ref) |
| A.L5 | LSP hover | `map_cids` in `quic_application.ivy` | Action signature | C6 (broken) |
| A.L6 | MCP ivy_lint | `quic_types.ivy` | 0 diagnostics, valid JSON | C1 (path) |
| A.L7 | MCP ivy_verify | `quic_server_test_stream.ivy` | `success` field in JSON | C1 (path) |
| A.L8 | MCP ivy_compile | `quic_server_test_stream.ivy`, target=test | Success or structured error | C1 (path) |
| A.L9 | MCP ivy_model_info | `quic_types.ivy` | Lists types, relations, actions | C1 (path) |
| A.L10 | Hook PreToolUse | JSON stdin with `"ivy_check"` in command | Warning suggesting MCP tool | — |
| A.L11 | Hook PostToolUse | JSON stdin with `.ivy` file_path | Lint result (checks #lang, braces) | — |
| A.L12 | Hook SessionStart | Run in PANTHER project dir | Detects "panther" workspace type | — |
| A.L13 | /nct-check | `file=quic_types.ivy` | Structured verification report | — |
| A.L14 | /nct-model-info | `file=quic_types.ivy` | Model structure display | — |

---

## 4. Dimension B: Completeness

**Question**: Are all Claude Code capabilities properly utilized?

### 4.1 Static Gap Analysis (B.S1–B.S12)

**B.S1 — LSP operation coverage:**

| Claude Code LSP Operation | ivy-lsp Support | Status |
|---|---|---|
| `goToDefinition` | Yes (cross-include) | Near parity (H5/H6 bugs) |
| `findReferences` | Yes (workspace-wide) | Near parity (H4 self-ref) |
| `hover` | Yes (nearly broken) | Below parity (C6) |
| `documentSymbol` | Yes (with noise) | Near parity (M11-M13) |
| `workspaceSymbol` | Yes (no filtering) | Below parity (C7) |
| `goToImplementation` | Not implemented | Gap |
| `prepareCallHierarchy` | Not implemented | Gap |
| `incomingCalls` | Not implemented | Gap |
| `outgoingCalls` | Not implemented | Gap |

**Score**: 5/9 implemented. Parity definition: ≥80% correct = parity, 60-79% = near, <60% = below.

**B.S2 — Hook event coverage:**

| Hook Event | Used | Implementation | Gap/Opportunity |
|---|---|---|---|
| PreToolUse | Yes | Warns about direct CLI | — |
| PostToolUse | Yes | Lints .ivy after Write/Edit | — |
| SessionStart | Yes | Workspace detection | — |
| Notification | No | — | Could notify on verification completion |
| Stop | No | — | Could report session coverage summary |
| SubagentStop | No | — | Could aggregate agent results |

**Score**: 3/6 used.

**B.S3 — plugin.json schema completeness:**

| Field | ivy-lsp | panther-ivy-plugin | Official Schema |
|---|---|---|---|
| name | Present | Present | Required |
| description | Present | Present | Recommended |
| version | "0.4.0" | "0.4.0" | Recommended |
| author | Present | Present | Optional |
| repository | Missing | Missing | Optional |
| license | Missing | Missing | Optional |
| keywords | Missing | Missing | Optional |

**B.S4 — CLAUDE.md cross-reference accuracy:**
Every tool name, command name, agent name, and skill name mentioned in CLAUDE.md must correspond to an actual artifact file.

**B.S5 — Agent tool access validity:**
Every tool in each agent's `tools` list must be a valid Claude Code tool name (Read, Grep, Glob, Bash, Write, Edit, ToolSearch, WebFetch, etc.).

**B.S6 — Skill cross-reference integrity:**
Every MCP tool, agent, command, or skill referenced inside a SKILL.md must exist as an actual plugin artifact.

**B.S7 — Command→MCP routing:**
All 5 commands must reference MCP tools (`ivy_verify`, `ivy_compile`, `ivy_model_info`, `ivy_pattern_scaffold`) and never invoke CLI directly.

**B.S8 — Version divergence (submodule vs installed marketplace):**
Compare file counts, agent names, command names between the submodule at `panther_ivy/submodules/panther-ivy-plugin/` and the installed marketplace version.

**B.S9 — MCP tool parameter effectiveness (prior audit regression):**
Verify that documented parameters (`test_file`, `file_path` in Group 5 tools) have observable effect on output — prior audit C2/C3 flagged these as ignored.

**B.S10 — PANTHER build alignment:**
MCP workspace root must point to `protocol-testing/` (or its parent containing it). The flatten step copies all `.ivy` files to `$IVY_INCLUDE/1.7/` — LSP and MCP must resolve symbols consistent with this structure.

**B.S11 — Role/mirror coverage:**
Commands and tools must handle all endpoint types: `server` (Ivy acts as client), `client` (Ivy acts as server), `mim` (Ivy acts as man-in-the-middle). Scaffold output must adapt shim includes per role.

**B.S12 — Error message quality:**
All error paths in hook scripts and MCP responses must produce actionable messages (not silent failures or generic "error occurred").

### 4.2 Live Coverage Tests (B.L1–B.L8)

| ID | Test | Input | Expected |
|----|------|-------|----------|
| B.L1 | ivy_coverage(mode="stats") | QUIC protocol | MUST/SHOULD/MAY percentages by layer |
| B.L2 | ivy_coverage(mode="gaps") | QUIC + test_file scoping | Scoped output (C2 regression check) |
| B.L3 | ivy_extract_requirements | RFC 9000 §4 text | Structured requirement list |
| B.L4 | ivy_pattern_scaffold | pattern="monitors" | Valid Ivy code |
| B.L5 | ivy_quality(mode="gate") | level="minimal" | Pass/fail with dimension scores |
| B.L6 | ivy_patterns(mode="check") | protocol="quic" | 14-layer completeness score |
| B.L7 | /nct-scaffold | type=protocol, name=test_eval | Directory created with template files |
| B.L8 | /nct-add-pattern | protocol=test_eval, pattern=serdes | Pattern added to scaffolded protocol |

---

## 5. Dimension C: Effectiveness

**Question**: Do the plugins reduce the learning curve, speed up specification work, and improve quality?

### 5.1 Problem 1 — Learning Curve Reduction

**C.1a — Navigation speed (LSP vs grep):**
- Task: "Find all monitors constraining `conn_total_data` in QUIC"
- Baseline: `grep -rn conn_total_data protocol-testing/quic/` + manual file reading
- Plugin: LSP `findReferences` + `ivy_coverage(mode="matrix")`
- Metric: Time to complete answer, completeness (monitors found / total)
- Target: Plugin ≤50% baseline time

**C.1b — Skill triggering accuracy:**
- Test 5 queries per skill, check if correct skill activates
- Example queries: "How do I write a before monitor?" → `ivy-writing-guide`; "What is the NCT workflow?" → `nct-methodology`
- Target: ≥70% correct first-attempt trigger

**C.1c — Agent MCP routing:**
- Issue 5 tasks to agents (e.g., "Verify quic_types.ivy" to spec-analyst)
- Check: does agent use MCP `ivy_verify` or Bash `ivy_check`?
- Target: ≥90% MCP usage; PreToolUse hook must warn about any CLI fallback

### 5.2 Problem 2 — Modeling Effort Reduction

**C.2a — Scaffolding completeness:**
- Task: Scaffold a minimal protocol spec
- Baseline: Create 7+ files manually with correct naming and structure
- Plugin: `/nct-scaffold type=protocol name=eval_proto`
- Metrics: Files generated (target: ≥7/14 layers), lint pass rate (target: ≥5/7 lint-clean)
- Target: Plugin time <10% of baseline

**C.2b — Pattern insertion:**
- Task: Add serdes (serialization/deserialization) pattern to existing protocol
- Baseline: Study `quic_ser.ivy`/`quic_deser.ivy`, manually adapt
- Plugin: `ivy_pattern_scaffold(pattern="serdes", protocol="eval_proto")`
- Target: Plugin <30% baseline time, generated code is syntactically valid

### 5.3 Problem 3 — Missing Specification Coverage

**C.3a — Requirement extraction accuracy:**
- Input: RFC 9000 Section 4 text (~12 normative statements)
- Plugin: `ivy_extract_requirements` MCP tool
- Metrics: Precision ≥85% (correct / returned), Recall ≥75% (found / total)
- Ground truth: expert-curated list of all normative statements

**C.3b — Coverage audit speed:**
- Task: Identify which RFC 9000 §4 MUST requirements are covered in QUIC spec
- Baseline: `grep` for bracket tags `rfc9000:4`, manually cross-reference
- Plugin: `ivy_coverage(mode="stats")` + `ivy_coverage(mode="gaps")`
- Target: Plugin <10% baseline time, gap accuracy ≥80%

### 5.4 Problem 4 — Confidentiality

**C.4a — Privacy audit:**
- Task: Run full workflow (navigate, lint, verify, coverage) while monitoring network traffic
- Method: Monitor LSP and MCP process network activity (lsof or equivalent)
- Target: 0 bytes sent to external servers by LSP/MCP processes
- Note: Claude Code LLM API calls are expected (that's the LLM conversation); only LSP/MCP tool traffic is audited

### 5.5 Problem 5 — Maintenance Burden

**C.5a — Regression detection latency:**
- Task: Modify a `before` guard in `quic_frame.ivy` to be less restrictive (simulate drift)
- Baseline: Must manually remember to run `ivy_check`
- Plugin: PostToolUse hook fires lint immediately; next `ivy_verify` detects invariant violation
- Target: Detection within same editing session (<5 min)

**C.5b — Incremental modification:**
- Task: Add 1 new RFC requirement using `incremental-spec-dev` workflow
- Baseline: Add requirement, batch-verify later
- Plugin: 9-step loop (identify gap → choose pattern → write assertion → lint → verify → coverage → quality gate → commit)
- Target: No regressions introduced during addition

### 5.6 Problem 6 — Partial Coverage

**C.6a — Coverage audit accuracy:**
- Task: Full QUIC specification coverage audit
- Baseline: Manual cross-reference of bracket tags against requirement list
- Plugin: `ivy_coverage(mode="stats")` + `ivy_coverage(mode="matrix")`
- Target: Plugin accuracy ≥98% of ground truth, time <5% of baseline

**C.6b — Quality gate progression:**
- Task: Check quality at 3 levels (minimal → standard → comprehensive)
- Plugin: `ivy_quality(mode="gate")` at each level
- Target: Monotonic progression (passing higher gate implies passing all lower gates)

---

## 6. Dimension D: Integration Quality

**Question**: Is the LSP↔MCP↔hooks↔agents↔skills coordination well-designed?

### 6.1 Static Architecture Tests (D.S1–D.S8)

| ID | Test | Acceptance Criteria |
|----|------|---------------------|
| D.S1 | LSP↔MCP coordination docs | ≥3 documented workflows in `tooling-reference` + `ivy-lsp-walkthrough` skills |
| D.S2 | Hook→MCP references | `post-write-ivy-lint.sh` output mentions `ivy_lint` MCP tool for deeper analysis |
| D.S3 | Command→MCP routing | All 5 commands reference MCP tools by name, never invoke CLI |
| D.S4 | Agent→skill coherence | Each of 4 agents references ≥1 relevant skill in its body |
| D.S5 | Version consistency | Both plugin.json files at same version (currently 0.4.0) |
| D.S6 | Build model alignment | MCP workspace root consistent with `protocol-testing/` prefix in flatten step |
| D.S7 | Mirror/role support | At least 1 agent or command handles role="server", "client", "mim" |
| D.S8 | Prior audit regression | 8 critical items (C1-C8) tracked with current resolution status |

### 6.2 Live End-to-End Workflows (D.L1–D.L8)

**D.L1 — Requirement addition workflow** (from `ivy-lsp-walkthrough` skill):
1. LSP documentSymbol on target file
2. LSP goToDefinition to find symbol
3. LSP findReferences to trace usage
4. MCP ivy_coverage(mode="stats") for current coverage
5. Write new monitor with bracket tag
6. PostToolUse hook fires → lint result
7. MCP ivy_verify on modified file
8. MCP ivy_coverage(mode="matrix") → coverage delta matches expected (+1)

**D.L2 — Protocol scaffolding + pattern workflow:**
1. `/nct-scaffold type=protocol name=eval_proto`
2. `ivy_lint` on each generated file
3. `ivy_patterns(mode="check")` on eval_proto → completeness score
4. `/nct-add-pattern protocol=eval_proto pattern=monitors`
5. `ivy_verify` on generated test specification

**D.L3 — Agent→MCP delegation (spec-analyst):**
Ask spec-analyst to "verify quic_types.ivy". Must use MCP `ivy_verify`, not Bash `ivy_check`.

**D.L4 — Agent→MCP delegation (traceability-agent):**
Ask traceability-agent to "extract requirements from RFC 9000 section 4.1". Must use MCP `ivy_extract_requirements`.

**D.L5 — Workspace detection coherence:**
Compare workspace root reported by: (a) SessionStart hook, (b) MCP server `start-ivy-tools.sh`, (c) LSP `.lsp.json` env vars. All three must agree.

**D.L6 — Error propagation:**
Start with `uvx` unavailable (rename binary). Must produce user-visible error within 10s with actionable guidance.

**D.L7 — PANTHER build flow alignment:**
Run the flatten→compile→role-inversion pipeline on a QUIC server test. Verify:
- All `.ivy` files copied to `$IVY_INCLUDE/1.7/`
- `ivyc target=test quic_server_test_stream.ivy` produces binary
- Binary uses client shim (role inversion from server→client)

**D.L8 — Cross-plugin coordination:**
Use ivy-lsp LSP operations (documentSymbol, goToDefinition) and panther-ivy-plugin MCP operations (ivy_model_info, ivy_verify) on the same `.ivy` file. Both must resolve the same symbols consistently.

---

## 7. Comparison Methodology

### 7.1 vs Official Claude Code LSP Plugins

Official plugins (pyright-lsp, typescript-lsp, gopls-lsp) are README-only — LSP config is built into Claude Code core. The comparison is asymmetric:

| Dimension | Official Plugins | ivy-lsp + panther-ivy-plugin |
|---|---|---|
| Plugin artifacts | README only | 35+ files |
| LSP operations | 9/9 (built-in) | 5/9 implemented |
| MCP tools | 0 | 15+ |
| Agents | 0 | 4 |
| Skills | 0 | 11 |
| Hooks | 0 | 3 |
| Domain guidance | 0 | CLAUDE.md (580+ lines) |

### 7.2 Beyond-Parity Features

Features unique to ivy ecosystem (no equivalent in any official plugin):
1. MCP tool surface (15+ structured analysis tools)
2. RFC traceability system (extraction→annotation→coverage→gaps)
3. Pattern library + scaffolding (14-layer template, 6 pattern types)
4. Domain-specific agent system (4 agents)
5. CLI interception hook (PreToolUse enforcement)

### 7.3 SOTA Comparison Extension

Extends the prior evaluation's SOTA comparison (TLA+, SPIN, Tamarin, ProVerif) with Claude Code-specific dimensions (plugin quality, agent design, hook patterns).

---

## 8. PANTHER Build Workflow Integration

### 8.1 Flatten→Compile→Mirror Flow

```
protocol-testing/quic/
├── quic_stack/     ─┐
├── quic_tests/     ─┤── find *.ivy → cp to $IVY_INCLUDE/1.7/ (flat)
├── quic_shims/     ─┤
├── quic_entities/  ─┤
└── quic_utils/     ─┘
```

**Role inversion (mirror):**
- `role=server` → test from `server_tests/` → include client shim → Ivy acts as client
- `role=client` → test from `client_tests/` → include server shim → Ivy acts as server
- `role=mim` → test from `mim_tests/` → include both shims → Ivy acts as MiM

**Key code paths:**
- Flatten: `ivy_command_mixin.py` `_build_ivy_model_setup_commands()` — `find ... -name '*.ivy' -exec cp`
- Role inversion: `_shared.py` `oppose_role()` — returns "client" for "server" and vice versa
- Template selection: `ivy_command_mixin.py` `_build_test_compilation_commands()` — `{role}_tests` directory

### 8.2 Alignment Checks

| Check | What | Why |
|---|---|---|
| MCP workspace root | Must resolve `protocol-testing/` paths | C1 critical: prefix mismatch breaks G1 tools |
| LSP include paths | Must index all flattened subdirs | LSP must find symbols across quic_stack/, quic_shims/, etc. |
| ivy_include_graph paths | Must normalize keys consistently | C5 critical: graph keys vs user paths mismatch |
| ivy_verify scope | Must handle relative and absolute paths | Pre-flatten vs post-flatten path references |
| Role-specific coverage | ivy_coverage should distinguish test directories | server_tests/ vs client_tests/ have different requirement sets |
| Mirror in scaffolding | Pattern tools should adapt shim includes per role | Scaffold output must generate correct role-specific includes |

---

## 9. AMC3 WP2 Report Structure

```
1. Executive Summary
   - Key findings (pass/fail per dimension)
   - AMC3 problem coverage matrix

2. Methodology
   - Four dimensions × two modes
   - Comparison approach
   - Scoring criteria

3. Correctness Results
   - Static: A.S1–A.S14
   - Live: A.L1–A.L14

4. Completeness Results
   - Static gap analysis: B.S1–B.S12
   - Live coverage: B.L1–B.L8
   - Gap matrices (LSP operations, hook events, schema fields)

5. Effectiveness Results
   - Per-problem findings: C.1a–C.6b
   - AMC3 problem mapping table

6. Integration Quality Results
   - Static: D.S1–D.S8
   - Live workflows: D.L1–D.L8

7. Comparison with Official Claude Code Plugins + SOTA

8. PANTHER Build Workflow Alignment

9. Prior Audit Regression Status (42 items: 8 critical, 10 high, 14 medium, 10 low)

10. Improvement Backlog (prioritized by dimension impact)

11. AMC3 Evidence Summary
    - P1: Learning curve addressed by skills, agents, LSP
    - P2: Modeling effort addressed by scaffolding, patterns
    - P3: Missing specs addressed by RFC extraction, traceability
    - P4: Confidentiality addressed by on-premise tooling
    - P5: Maintenance addressed by hooks, quality gates
    - P6: Coverage addressed by gap analysis, multi-level verification

Appendix A: Full test case results
Appendix B: Quality scorecards (per-tool 1-5 scale)
Appendix C: Reproducibility guide
```

---

## 10. Success Thresholds

| Dimension | Aggregate Pass Criteria |
|---|---|
| A. Correctness | ≥90% of tests pass (≥25/28) |
| B. Completeness | All critical gaps documented; ≥70% coverage of Claude Code capabilities |
| C. Effectiveness | ≥4/6 AMC3 problems show measurable improvement over baseline |
| D. Integration | ≥6/8 live workflows complete end-to-end without broken links |

| AMC3 Problem | Key Metric | Target |
|---|---|---|
| P1 Learning Curve | Time to answer navigation queries | ≤50% of baseline |
| P2 Modeling Effort | Scaffolding generates ≥7/14 layers | ≥5 lint-clean |
| P3 Missing Specs | Requirement extraction precision/recall | ≥85% / ≥75% |
| P4 Confidentiality | External bytes from LSP/MCP processes | 0 |
| P5 Maintenance | Regression detection latency | <5 minutes |
| P6 Coverage | Coverage audit accuracy vs ground truth | ≥98% |
