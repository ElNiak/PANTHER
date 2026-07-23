# Ivy Plugin Evaluation Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Execute the evaluation framework defined in `docs/superpowers/specs/2026-03-16-ivy-plugin-evaluation-design.md` across all 4 dimensions and produce the AMC3 WP2 deliverable report.

**Architecture:** Phase-based execution: static analysis first (no Ivy env needed), then live testing, effectiveness scenarios, integration workflows, and report generation. Each phase produces a section of the final report. Phases 1-4 are independent and can run in parallel.

**Tech Stack:** Bash scripts for static validation, MCP tool calls for live testing, LSP tool calls for LSP tests, Claude Code conversation analysis for effectiveness scenarios.

**Spec:** `docs/superpowers/specs/2026-03-16-ivy-plugin-evaluation-design.md`

---

## File Structure

All evaluation outputs go to a single report file built incrementally:

| File | Purpose |
|------|---------|
| `docs/superpowers/specs/2026-03-16-ivy-plugin-evaluation-results.md` | Final evaluation report (AMC3 deliverable) |
| `docs/superpowers/specs/2026-03-16-ivy-plugin-evaluation-design.md` | Design spec (already written) |

No test scripts are created — all tests are executed inline using existing tools (Bash, MCP, LSP) and results recorded directly in the report.

---

## Chunk 1: Phase 1 — Static Analysis (Dimensions A.S, B.S, D.S)

### Task 1: Plugin Manifest Validation (A.S1–A.S5)

**Files:**
- Read: `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/ivy-lsp/.claude-plugin/plugin.json`
- Read: `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/ivy-lsp/.lsp.json`
- Read: `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/.claude-plugin/plugin.json`
- Read: `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/.mcp.json`
- Read: `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/hooks/hooks.json`

- [ ] **Step 1: Read and validate ivy-lsp/plugin.json (A.S1)**

Read the file. Check: valid JSON, contains `name`, `version`, `author` fields. Record PASS/FAIL.

- [ ] **Step 2: Read and validate ivy-lsp/.lsp.json (A.S2)**

Read the file. Check: valid JSON, has `ivy` key with `command`, `extensionToLanguage` mapping `.ivy` → `ivy`. Record PASS/FAIL.

- [ ] **Step 3: Read and validate panther-ivy-plugin/plugin.json (A.S3)**

Read the file. Check: valid JSON, contains `name`, `version`, `author` fields. Record PASS/FAIL.

- [ ] **Step 4: Read and validate panther-ivy-plugin/.mcp.json (A.S4)**

Read the file. Check: valid JSON, has `mcpServers.ivy-tools.command` using `${CLAUDE_PLUGIN_ROOT}`. Record PASS/FAIL.

- [ ] **Step 5: Read and validate hooks/hooks.json (A.S5)**

Read the file. Check: has 3 hook events (PreToolUse, PostToolUse, SessionStart). PreToolUse matcher is `Bash`. PostToolUse matcher is `Write|Edit`. SessionStart has no matcher. Record PASS/FAIL.

- [ ] **Step 6: Record manifest validation results**

Create the results report file with Section 3.1 (Static Correctness) containing an A.S1-A.S5 results table.

### Task 2: Agent Frontmatter Validation (A.S6–A.S9)

**Files:**
- Read: `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/agents/methodology-guide.md`
- Read: `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/agents/model-reviewer.md`
- Read: `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/agents/spec-analyst.md`
- Read: `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/agents/traceability-agent.md`

- [ ] **Step 1: Read all 4 agent files and extract YAML frontmatter**

For each agent, verify: YAML frontmatter contains `name`, `description`, `tools` fields. Verify `tools` is a JSON array of valid Claude Code tool names.

- [ ] **Step 2: Validate tool lists per agent**

- methodology-guide: must have Read, Grep, Glob, Bash, Write, Edit, ToolSearch
- model-reviewer: must NOT have Write or Edit (read-only reviewer)
- spec-analyst: must have Write, Edit (can modify files)
- traceability-agent: must have WebFetch (needs to fetch RFCs)

Record PASS/FAIL per agent.

- [ ] **Step 3: Update results report with A.S6-A.S9**

### Task 3: Command Frontmatter Validation (A.S10)

**Files:**
- Read: `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/commands/nct-check.md`
- Read: `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/commands/nct-compile.md`
- Read: `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/commands/nct-model-info.md`
- Read: `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/commands/nct-scaffold.md`
- Read: `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/commands/nct-add-pattern.md`

- [ ] **Step 1: Read all 5 command files and extract YAML frontmatter**

For each command, verify: has `name`, `description`, and `arguments` array.

- [ ] **Step 2: Validate argument schemas**

- nct-check: `file` (required), `isolate` (optional)
- nct-compile: `file` (required), `target` (optional), `isolate` (optional)
- nct-model-info: `file` (required), `isolate` (optional)
- nct-scaffold: `type` (required), `name` (optional), `protocol` (optional), `role` (optional)
- nct-add-pattern: verify arguments present

Record PASS/FAIL per command.

- [ ] **Step 3: Verify commands reference MCP tools (B.S7, D.S3)**

Read each command body. Verify it references the corresponding MCP tool:
- nct-check → `ivy_verify`
- nct-compile → `ivy_compile`
- nct-model-info → `ivy_model_info`
- nct-scaffold → `ivy_pattern_scaffold`
- nct-add-pattern → pattern tools

No command should contain `ivy_check`, `ivyc`, or `ivy_show` CLI invocations.

- [ ] **Step 4: Update results report with A.S10, B.S7, D.S3**

### Task 4: Skill Frontmatter Validation (A.S11–A.S13)

**Files:**
- Read: All 11 SKILL.md files in `plugins/panther-ivy-plugin/skills/*/SKILL.md`

- [ ] **Step 1: Read all 11 skill files**

Skills to validate: counterexample-guide, incremental-spec-dev, ivy-lsp-walkthrough, ivy-writing-guide, methodology-reference, nact-methodology, nct-methodology, nsct-methodology, specification-patterns, tooling-reference, workflow-reference.

- [ ] **Step 2: Validate each skill**

For each: verify YAML frontmatter has `name`, `description`. Verify content body > 500 characters. Record PASS/FAIL per skill.

- [ ] **Step 3: Cross-reference integrity check (B.S6)**

For each skill, grep for MCP tool names (`ivy_verify`, `ivy_compile`, `ivy_lint`, etc.), agent names (`methodology-guide`, `spec-analyst`, etc.), command names (`/nct-check`, `/nct-compile`, etc.), and other skill names. Verify each referenced artifact exists as an actual file.

- [ ] **Step 4: Update results report with A.S11-A.S13, B.S6**

### Task 5: Hook Script Validation (A.S14)

**Files:**
- Read: `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/hooks/scripts/block-direct-ivy.sh`
- Read: `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/hooks/scripts/post-write-ivy-lint.sh`
- Read: `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/hooks/scripts/detect-ivy-workspace.sh`
- Read: `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/scripts/workspace-common.sh`

- [ ] **Step 1: Read all 3 hook scripts + workspace-common.sh**

- [ ] **Step 2: Validate block-direct-ivy.sh**

Check: has shebang, reads JSON from stdin, checks for `ivy_check|ivyc|ivy_show|ivy_to_cpp` patterns, exits 0 (non-blocking). Record findings.

- [ ] **Step 3: Validate post-write-ivy-lint.sh**

Check: has shebang, filters for `.ivy` files, checks `#lang` header, counts brace balance. Record findings.

- [ ] **Step 4: Validate detect-ivy-workspace.sh**

Check: has shebang, sources `workspace-common.sh`, calls `detect_ivy_workspace()`, handles 3 workspace types (panther/standalone/fallback). Record findings.

- [ ] **Step 5: Validate workspace-common.sh**

Check: defines `find_panther_ivy()`, `detect_ivy_workspace()`, `resolve_ivy_lsp_source()`. Verify depth limits (10 for panther, 8 for standalone). Record findings.

- [ ] **Step 6: Update results report with A.S14**

### Task 6: Completeness Gap Analysis (B.S1–B.S5, B.S8–B.S12)

**Files:**
- Read: `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/CLAUDE.md`
- Read: `panther/plugins/services/testers/panther_ivy/ivy_command_mixin.py`
- Read: `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/scripts/start-ivy-tools.sh`

- [ ] **Step 1: LSP operation gap matrix (B.S1)**

Cross-reference the 9 Claude Code LSP operations against ivy-lsp features. Document: 5/9 implemented (goToDefinition, findReferences, hover, documentSymbol, workspaceSymbol). 4/9 missing (goToImplementation, prepareCallHierarchy, incomingCalls, outgoingCalls).

- [ ] **Step 2: Hook event gap matrix (B.S2)**

Document: 3/6+ used (PreToolUse, PostToolUse, SessionStart). Unused: Notification, Stop, SubagentStop. Note opportunities for each unused event.

- [ ] **Step 3: Plugin schema gap matrix (B.S3)**

Compare both plugin.json files against official schema. Document missing optional fields (repository, license, keywords).

- [ ] **Step 4: CLAUDE.md accuracy check (B.S4)**

Read CLAUDE.md. Extract every tool, command, agent, skill name mentioned. Cross-reference each against actual files. Record any dangling references or undocumented features.

- [ ] **Step 5: Agent tool access check (B.S5)**

Verify every tool in each agent's `tools` list is a valid Claude Code tool name. Valid tools: Read, Grep, Glob, Bash, Write, Edit, ToolSearch, WebFetch, WebSearch, NotebookRead, etc.

- [ ] **Step 6: Version divergence analysis (B.S8)**

Compare submodule version against installed marketplace version. Check file counts (agents, skills, commands) in both locations.

Run: `ls ~/.claude/plugins/marketplaces/*/plugins/panther-ivy-plugin/ 2>/dev/null || echo "Not installed from marketplace"`

- [ ] **Step 7: MCP tool parameter effectiveness regression (B.S9)**

Check that documented parameters in Group 5 tools (`test_file`, `file_path`) have observable effect on output. This is a regression check for prior audit items C2 and C3. Read the `tooling-reference/SKILL.md` to identify which MCP tools accept `test_file`/`file_path` parameters. For each, note whether the parameter is documented as functional or flagged as broken in the prior audit.

- [ ] **Step 8: PANTHER build alignment (B.S10, D.S6)**

Read `panther/plugins/services/testers/panther_ivy/ivy_command_mixin.py` flatten logic (`_build_ivy_model_setup_commands`). Verify MCP workspace detection in `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/scripts/start-ivy-tools.sh` resolves to the same `protocol-testing/` directory that the flatten step targets. This also covers D.S6 (build model alignment).

- [ ] **Step 9: Role/mirror coverage (B.S11, D.S7)**

Check if any command or agent handles role-specific behavior (server/client/mim). Check if `/nct-scaffold` generates role-specific shim includes. This also covers D.S7 (mirror/role support).

- [ ] **Step 10: Error message quality (B.S12)**

Grep all hook scripts for error handling patterns. Verify error messages are actionable (not empty exits or generic messages).

- [ ] **Step 11: Update results report with all B.S results (B.S1-B.S12) including D.S6 and D.S7 coverage**

### Task 7: Integration Static Tests (D.S1, D.S2, D.S4, D.S5, D.S8)

**Note:** D.S3 covered in Task 3 Step 3 (B.S7). D.S6 covered in Task 6 Step 8 (B.S10). D.S7 covered in Task 6 Step 9 (B.S11).

- [ ] **Step 1: Count LSP↔MCP coordination workflows (D.S1)**

Read `tooling-reference/SKILL.md` and `ivy-lsp-walkthrough/SKILL.md`. Count documented workflows that combine LSP and MCP operations. Target: ≥3.

- [ ] **Step 2: Check hook→MCP references (D.S2)**

Read `post-write-ivy-lint.sh` output messages. Verify it suggests `ivy_lint` MCP tool for deeper analysis.

- [ ] **Step 3: Check agent→skill coherence (D.S4)**

For each of 4 agents, read body text. Verify each references at least 1 relevant skill by name.

- [ ] **Step 4: Version consistency (D.S5)**

Compare version fields in both plugin.json files. Both should be "0.4.0".

- [ ] **Step 5: Prior audit regression tracking (D.S8)**

Read `docs/superpowers/specs/2026-03-13-ivy-tooling-audit-results.md`. Extract the 8 critical items (C1-C8). For each, document current status: fixed, in-progress, or still-open.

- [ ] **Step 6: Update results report with D.S1-D.S8 and comparison section**

- [ ] **Step 7: Commit Phase 1 results**

```bash
git add docs/superpowers/specs/2026-03-16-ivy-plugin-evaluation-results.md
git commit -m "feat: Phase 1 static analysis results for ivy plugin evaluation"
```

---

## Chunk 2: Phase 2 — Live Functional Tests (Dimensions A.L, B.L)

### Task 8: LSP Server Tests (A.L1–A.L5)

**Prerequisite:** ivy-lsp MCP server and LSP server must be running. Check `/tmp/ivy-lsp.log` exists and shows initialization.

- [ ] **Step 1: Verify LSP server is running (A.L1)**

Check if `/tmp/ivy-lsp.log` exists and contains initialization messages. If not running, document as SKIP.

- [ ] **Step 2: Test documentSymbol (A.L2)**

Use LSP tool to get document symbols for a QUIC .ivy file. Verify returns hierarchical symbol list with type declarations. Record output and PASS/FAIL.

- [ ] **Step 3: Test goToDefinition (A.L3)**

Use LSP tool to go to definition of a known symbol (e.g., `cid`) in a QUIC file. Verify it jumps to the correct definition file. Record output and PASS/FAIL.

- [ ] **Step 4: Test findReferences (A.L4)**

Use LSP tool to find references of a known symbol. Verify cross-file results returned. Record output and PASS/FAIL.

- [ ] **Step 5: Test hover (A.L5)**

Use LSP tool for hover on a known action. Record whether it returns action signature or nothing (known C6 issue). Record output and PASS/FAIL.

- [ ] **Step 6: Update results report with A.L1-A.L5**

### Task 9: MCP Tool Tests (A.L6–A.L9)

- [ ] **Step 1: Test ivy_lint (A.L6)**

Call `ivy_lint` MCP tool on `quic_types.ivy`. Verify: valid JSON response with 0 diagnostics. Record output and PASS/FAIL.

- [ ] **Step 2: Test ivy_verify (A.L7)**

Call `ivy_verify` MCP tool on a QUIC test file. Verify: JSON response with `success` field. Record output and PASS/FAIL.

- [ ] **Step 3: Test ivy_compile (A.L8)**

Call `ivy_compile` MCP tool with target=test on a test file. Verify: success or structured error. Record output and PASS/FAIL.

- [ ] **Step 4: Test ivy_model_info (A.L9)**

Call `ivy_model_info` MCP tool on `quic_types.ivy`. Verify: lists types, relations, actions. Record output and PASS/FAIL.

- [ ] **Step 5: Update results report with A.L6-A.L9**

### Task 10: Hook Tests (A.L10–A.L12)

- [ ] **Step 1: Test PreToolUse hook (A.L10)**

Run `block-direct-ivy.sh` with mock JSON stdin containing `"ivy_check"` in command field:
```bash
echo '{"tool_name":"Bash","tool_input":{"command":"ivy_check quic_types.ivy"}}' | bash panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/hooks/scripts/block-direct-ivy.sh
```
Verify: warning output suggesting MCP tool. Exit code 0.

- [ ] **Step 2: Test PostToolUse hook (A.L11)**

Run `post-write-ivy-lint.sh` with mock JSON stdin for a `.ivy` file write:
```bash
echo '{"tool_name":"Write","tool_input":{"file_path":"test.ivy","content":"type foo"}}' | bash panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/hooks/scripts/post-write-ivy-lint.sh
```
Verify: lint result (missing `#lang` header detection).

- [ ] **Step 3: Test SessionStart hook (A.L12)**

Run `detect-ivy-workspace.sh` in the PANTHER project directory:
```bash
bash panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/hooks/scripts/detect-ivy-workspace.sh
```
Verify: detects "panther" workspace type.

- [ ] **Step 4: Update results report with A.L10-A.L12**

### Task 11: Command Tests (A.L13–A.L14)

- [ ] **Step 1: Test /nct-check (A.L13)**

Invoke `/nct-check file=protocol-testing/quic/quic_stack/quic_types.ivy`. Verify: produces structured verification report.

- [ ] **Step 2: Test /nct-model-info (A.L14)**

Invoke `/nct-model-info file=protocol-testing/quic/quic_stack/quic_types.ivy`. Verify: produces model structure display.

- [ ] **Step 3: Update results report with A.L13-A.L14**

### Task 12: Live Completeness Tests (B.L1–B.L8)

- [ ] **Step 1: Test ivy_coverage stats (B.L1)**

Call `ivy_coverage` with mode="stats". Verify: returns MUST/SHOULD/MAY percentages.

- [ ] **Step 2: Test ivy_coverage gaps with scoping (B.L2)**

Call `ivy_coverage` with mode="gaps" and a test_file parameter. Check if output is scoped (C2 regression). Record current behavior.

- [ ] **Step 3: Test ivy_extract_requirements (B.L3)**

Call `ivy_extract_requirements` with sample RFC text containing MUST/SHOULD/MAY statements. Verify structured output.

- [ ] **Step 4: Test ivy_pattern_scaffold (B.L4)**

Call `ivy_pattern_scaffold` with pattern="monitors". Verify generated Ivy code is syntactically valid.

- [ ] **Step 5: Test ivy_quality gate (B.L5)**

Call `ivy_quality` with mode="gate", level="minimal". Verify pass/fail with dimension scores.

- [ ] **Step 6: Test ivy_patterns check (B.L6)**

Call `ivy_patterns` with mode="check" on quic. Verify 14-layer completeness score returned.

- [ ] **Step 7: Test /nct-scaffold (B.L7)**

Invoke `/nct-scaffold type=protocol name=test_eval`. Verify directory and files created.

- [ ] **Step 8: Test /nct-add-pattern (B.L8)**

Invoke `/nct-add-pattern protocol=test_eval pattern=serdes`. Verify pattern added.

- [ ] **Step 9: Update results report with B.L1-B.L8**

- [ ] **Step 10: Commit Phase 2 results**

```bash
git add docs/superpowers/specs/2026-03-16-ivy-plugin-evaluation-results.md
git commit -m "feat: Phase 2 live functional test results for ivy plugin evaluation"
```

---

## Chunk 3: Phase 3 — Effectiveness Scenarios (Dimension C)

### Task 13: Problem 1 — Learning Curve (C.1a–C.1c)

- [ ] **Step 1: Navigation speed test (C.1a)**

Baseline: Use Grep to find all files containing `conn_total_data` in protocol-testing/quic/. Time the search.
Plugin: Use LSP findReferences + ivy_coverage(mode="matrix"). Time the search.
Record both times and completeness of results.

- [ ] **Step 2: Skill triggering test (C.1b)**

Test 5 queries and check skill activation:
1. "How do I write a before monitor?" → expect ivy-writing-guide
2. "What is the NCT workflow?" → expect nct-methodology
3. "Help me add a pattern to my protocol" → expect specification-patterns
4. "Explain this counterexample" → expect counterexample-guide
5. "Walk me through using LSP and MCP together" → expect ivy-lsp-walkthrough

Record: correct/incorrect per query.

- [ ] **Step 3: Agent MCP routing test (C.1c)**

This is observational — note during D.L3 and D.L4 whether agents correctly use MCP tools vs CLI.

- [ ] **Step 4: Update results report with C.1a-C.1c**

### Task 14: Problem 2 — Modeling Effort (C.2a–C.2b)

- [ ] **Step 1: Scaffolding test (C.2a)**

Run `/nct-scaffold type=protocol name=eval_proto`. Count generated files. Run `ivy_lint` on each. Record: file count, lint pass rate.

- [ ] **Step 2: Pattern insertion test (C.2b)**

Run `ivy_pattern_scaffold(pattern="serdes", protocol="eval_proto")`. Verify generated code is syntactically valid.

- [ ] **Step 3: Update results report with C.2a-C.2b**

### Task 15: Problem 3 — Missing Specs (C.3a–C.3b)

- [ ] **Step 1: Requirement extraction test (C.3a)**

Prepare sample RFC text with known MUST/SHOULD/MAY statements. Run `ivy_extract_requirements`. Compare extracted requirements against ground truth. Calculate precision and recall.

- [ ] **Step 2: Coverage audit test (C.3b)**

Baseline: Run grep for bracket tags `rfc9000` in QUIC spec. Count manually.
Plugin: Run `ivy_coverage(mode="stats")`. Compare times and accuracy.

- [ ] **Step 3: Update results report with C.3a-C.3b**

### Task 16: Problems 4-6 (C.4a, C.5a, C.5b, C.6a, C.6b)

- [ ] **Step 1: Privacy audit (C.4a)**

During MCP tool calls, check that the ivy-lsp process does not make external network connections. Run: `lsof -i -P -n | grep ivy_lsp` (or check `/tmp/ivy-lsp.log` for any HTTP requests). Record finding. Target: 0 external bytes.

- [ ] **Step 2: Regression detection latency (C.5a)**

Observational — during D.L1 workflow, note PostToolUse hook timing after .ivy writes. Record: time between file write and lint feedback, time between edit and ivy_verify feedback.

- [ ] **Step 3: Incremental modification test (C.5b)**

Execute the incremental-spec-dev 9-step loop for adding 1 RFC requirement:
1. Identify a gap using `ivy_coverage(mode="gaps")`
2. Choose appropriate pattern (before/after monitor)
3. Write the assertion with bracket tag
4. Run `ivy_lint` (PostToolUse hook should fire)
5. Run `ivy_verify`
6. Check coverage delta with `ivy_coverage(mode="stats")`
7. Verify no regressions (coverage should not decrease for existing requirements)
Record: time for full loop, number of verification iterations, any regressions introduced.

- [ ] **Step 4: Coverage audit accuracy (C.6a)**

Run `ivy_coverage(mode="stats")` on the QUIC protocol. Compare the reported MUST/SHOULD/MAY counts against a manual sample check (count bracket tags in 5 representative files via grep, extrapolate). Record: plugin accuracy relative to manual count. Target: ≥98% accuracy.

- [ ] **Step 5: Quality gate progression (C.6b)**

Run `ivy_quality(mode="gate")` at minimal, standard, comprehensive levels on the same protocol. Verify monotonic progression (passing higher gate implies passing all lower gates).

- [ ] **Step 6: Update results report with C.4a-C.6b**

- [ ] **Step 5: Commit Phase 3 results**

```bash
git add docs/superpowers/specs/2026-03-16-ivy-plugin-evaluation-results.md
git commit -m "feat: Phase 3 effectiveness scenario results for ivy plugin evaluation"
```

---

## Chunk 4: Phase 4 — Integration & E2E (Dimension D.L)

### Task 17: End-to-End Workflow Tests (D.L1–D.L4)

- [ ] **Step 1: Requirement addition workflow (D.L1)**

Execute the 8-step workflow from the ivy-lsp-walkthrough skill:
1. LSP documentSymbol on a QUIC file
2. LSP goToDefinition on a symbol
3. LSP findReferences to trace usage
4. MCP ivy_coverage(mode="stats")
5. (Simulated) Write new monitor with bracket tag
6. Observe PostToolUse hook lint
7. MCP ivy_verify on file
8. MCP ivy_coverage(mode="matrix") — check coverage delta

Record: which steps completed, which failed, any broken links in the chain.

- [ ] **Step 2: Protocol scaffolding workflow (D.L2)**

Execute: scaffold → lint → patterns(check) → add-pattern → verify. Record results.

- [ ] **Step 3: Agent→MCP delegation tests (D.L3, D.L4)**

These are observational — launch spec-analyst and traceability-agent agents with specific tasks and observe tool usage patterns.

- [ ] **Step 4: Update results report with D.L1-D.L4**

### Task 18: Infrastructure Tests (D.L5–D.L8)

- [ ] **Step 1: Workspace detection coherence (D.L5)**

Compare workspace root from: SessionStart hook output, MCP server start-ivy-tools.sh detection, LSP .lsp.json env vars. All should agree.

- [ ] **Step 2: Error propagation (D.L6)**

Observational — note any error scenarios encountered during testing and whether messages were actionable.

- [ ] **Step 3: PANTHER build flow (D.L7)**

Read `ivy_command_mixin.py` flatten logic. Verify MCP tool paths align with post-flatten directory structure. This is primarily a static analysis of path consistency.

- [ ] **Step 4: Cross-plugin coordination (D.L8)**

Use both ivy-lsp LSP operations and panther-ivy-plugin MCP operations on the same .ivy file. Verify consistent symbol resolution.

- [ ] **Step 5: Update results report with D.L5-D.L8**

- [ ] **Step 6: Commit Phase 4 results**

```bash
git add docs/superpowers/specs/2026-03-16-ivy-plugin-evaluation-results.md
git commit -m "feat: Phase 4 integration test results for ivy plugin evaluation"
```

---

## Chunk 5: Phase 5 — Report Generation

### Task 19: Compile Final Report

- [ ] **Step 1: Write Executive Summary (Section 1)**

Summarize: overall pass rates per dimension, AMC3 problem coverage matrix, top 5 findings.

- [ ] **Step 2: Write Methodology section (Section 2)**

Document: 4 dimensions, 2 modes, 76 total test cases, comparison approach, scoring criteria.

- [ ] **Step 3: Compile Comparison section (Section 7)**

Write the official vs ivy plugin comparison table and the SOTA extension from the prior evaluation.

- [ ] **Step 4: Write PANTHER Build Alignment section (Section 8)**

Document: flatten→compile→mirror flow, path consistency findings, role-specific coverage.

- [ ] **Step 5: Compile Prior Audit Regression section (Section 9)**

Status of all 8 critical items (C1-C8) from the 2026-03-13 audit.

- [ ] **Step 6: Write Improvement Backlog (Section 10)**

Prioritized list of all issues found, organized by: critical (blocking), high (v1.0), medium (v1.1), low (future).

- [ ] **Step 7: Write AMC3 Evidence Summary (Section 11)**

Per-problem summary mapping evaluation findings to AMC3 goals.

- [ ] **Step 8: Calculate aggregate scores and check success thresholds**

Calculate pass rates per dimension:
- A. Correctness: target ≥90% (≥25/28 tests pass)
- B. Completeness: target ≥70% coverage of Claude Code capabilities
- C. Effectiveness: target ≥4/6 AMC3 problems show measurable improvement
- D. Integration: target ≥6/8 live workflows complete end-to-end

Check per-problem thresholds from design spec Section 10. Document: which thresholds met, which missed, overall evaluation verdict.

- [ ] **Step 9: Write Appendices**

Appendix A (full test results table), Appendix B (quality scorecards), Appendix C (reproducibility guide).

- [ ] **Step 10: Final commit**

```bash
git add docs/superpowers/specs/2026-03-16-ivy-plugin-evaluation-results.md
git add docs/superpowers/specs/2026-03-16-ivy-plugin-evaluation-design.md
git commit -m "feat: complete ivy plugin evaluation framework — design spec + results report"
```
