# nct-validate Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the 785-line `/nct-validate` prompt command with a scenario-based sequential validation (v3) that eliminates ground truth YAML, adds cross-validation chains, covers 75% of tools (up from 27%), and provides interactive manual review.

**Architecture:** The command is a markdown prompt file (`commands/nct-validate.md`) interpreted by Claude at runtime. It is NOT traditional code — there are no unit tests. Validation is done by running the command itself. The redesign restructures from 7 phase-based sections into a 5-pass architecture: pre-flight gate, 6 workflow scenarios + negative tests, gap sweep, non-workflow checks (hooks/surface/agents), and interactive review.

**Tech Stack:** Markdown (Claude Code plugin command format), YAML frontmatter, Claude Code tools (LSP, MCP, Agent, Bash, Read, Glob)

**Spec:** `docs/superpowers/specs/2026-03-18-nct-validate-redesign-design.md`

**Plugin root:** `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/`

---

### Task 1: Frontmatter, Argument Parsing, and General Rules

**Files:**
- Modify: `commands/nct-validate.md:1-62`

This task replaces the YAML frontmatter and the preamble sections (argument parsing, ground truth loading, pre-mutation safety check, general rules) with the v3 equivalents. The key change: remove `ground-truth` loading entirely, add `fast` mode argument, update phase mapping to 5-pass architecture.

- [ ] **Step 1: Back up the current file**

```bash
cp commands/nct-validate.md commands/nct-validate.md.bak
```

- [ ] **Step 2: Write the new frontmatter and preamble**

Replace lines 1-62 of `commands/nct-validate.md` with:

```markdown
---
name: nct-validate
description: Scenario-based validation of Ivy LSP, MCP tools, hooks, agents, and surface coverage (~75 checks across 5 passes) with cross-validation, interactive review, and optional mutation testing
arguments:
  - name: phase
    description: "Comma-separated passes to run: preflight, scenarios, gapsweep, nonworkflow, interactive. Default: all"
    required: false
  - name: scenario
    description: "Comma-separated scenarios: A, B, C, D, E, F, FX. Default: all in selected passes"
    required: false
  - name: check
    description: "Comma-separated check IDs: P1, A3, B1, FX2, H5, AG1, S1. Default: all in selected scenarios"
    required: false
  - name: mode
    description: "fast (skip mutations, agents, gap sweep, interactive confirmation) or full (default)"
    required: false
  - name: error-injection
    description: "full = 3 mutation types (header, brace, include). Default: 1 mutation (include only). false = skip all."
    required: false
---

Run a scenario-based validation of the Ivy LSP, MCP tools, plugin hooks, agents, and surface coverage. Unlike `/nct-health` (connectivity), this command checks **correctness** by simulating real user workflows — exploring the model, auditing coverage, debugging failures, editing specs — with cross-validation between tools and interactive manual review.

## Instructions

### Argument Parsing

1. **`mode`**: `fast` or `full` (default: `full`).
   - `fast` skips: Scenario D (mutations), Pass 2 (gap sweep), Pass 3 agents (AG1-AG5), Pass 4 interactive confirmation (prints values directly).
   - `fast` keeps: Pass 0, Scenarios A/B/C/E/F, negative tests (FX1-FX8), hooks, surface.

2. **`phase`**: If provided, split by comma and map:
   - `preflight` → Pass 0 (always runs as gate regardless)
   - `scenarios` → Pass 1 (all scenarios + negative tests)
   - `gapsweep` → Pass 2
   - `nonworkflow` → Pass 3 (hooks + surface + agents)
   - `interactive` → Pass 4
   - If omitted, run **all** passes.

3. **`scenario`**: If provided, split by comma. Only run matching scenarios within Pass 1. Pass 0 still runs as gate.
   - Valid values: `A`, `B`, `C`, `D`, `E`, `F`, `FX` (negative tests)

4. **`check`**: If provided, split by comma. Only run checks whose ID matches. Pass 0 still runs as gate.

5. **`error-injection`**: Controls mutation tests in Scenario D.
   - `false` → skip all mutations (D3-D6 become SKIPPED)
   - Default (no arg) → 1 mutation type (bad include insertion)
   - `full` → all 3 mutation types (missing header, unmatched brace, bad include)

### General Rules

- For each check: call the specified tool, validate response **structure** (fields present, no stack traces, sane values), record PASS/FAIL/SKIPPED with a 1-2 sentence **reflection** connecting the result to prior checks.
- **No ground truth comparison.** Checks validate structure and sanity only. Actual values are collected for the interactive review table in Pass 4.
- **Never abort early.** If a check fails, record FAIL and continue. If a subsystem is unavailable, mark dependent checks as SKIPPED and continue.
- **Cross-validation**: When a check references a prior result, explicitly compare and note agreement or disagreement.
- Track all results for SR1 (self-review meta-analysis) and Pass 4 (interactive table).
```

- [ ] **Step 3: Verify the new preamble reads correctly**

Read the modified file, confirm:
- YAML frontmatter has all 5 arguments (phase, scenario, check, mode, error-injection)
- No mention of `ground-truth`, `quic-workspace.yaml`, or `fallback` values
- Fast mode documented
- General rules mention reflection and cross-validation

- [ ] **Step 4: Commit**

```bash
git add commands/nct-validate.md
git commit -m "refactor(nct-validate): replace frontmatter and preamble with v3 design

Remove ground truth loading, add fast mode argument, add scenario/check
filtering, update general rules for structural checks with reflection
and cross-validation."
```

---

### Task 2: Pass 0 — Pre-flight Gate

**Files:**
- Modify: `commands/nct-validate.md` (append after preamble)

Write the pre-flight section. This is nearly identical to the current Phase 0 but explicitly states it gates ALL subsequent passes (not just individual phases).

- [ ] **Step 1: Write Pass 0**

Append after the General Rules section:

```markdown
---

## Pass 0: Pre-flight (3 checks)

**Always runs first**, regardless of `phase` argument. Gates all downstream passes.

### P1: LSP process alive

Run via Bash:
```
pgrep -f ivy_lsp
```

- If PIDs returned: **PASS** — report PID(s).
- If no output or error: **FAIL** — "No ivy_lsp process found."
- **Impact**: All LSP checks in Pass 1 and Pass 3 are SKIPPED.

### P2: MCP server health

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_capabilities` with no arguments.

- If `ivy_check: true`, `ivyc: true`, `ivy_show: true` all present: **PASS**.
- Otherwise: **FAIL**.
- **Impact**: All MCP tool checks in Pass 1 and Pass 3 are SKIPPED.

### P3: LSP responding

Use the `LSP` tool to request `hover` on `quic/quic_stack/quic_types.ivy` at line 1, character 0 (resolve to absolute path in the detected workspace).

- If any response (even empty hover): **PASS** — LSP is responding.
- If timeout or error: **FAIL**.
- **Impact**: All LSP checks in Pass 1 are SKIPPED.
```

- [ ] **Step 2: Verify**

Read the file, confirm Pass 0 is between the preamble and the next section. Confirm all 3 checks have clear PASS/FAIL criteria and impact statements.

- [ ] **Step 3: Commit**

```bash
git add commands/nct-validate.md
git commit -m "refactor(nct-validate): add Pass 0 pre-flight gate"
```

---

### Task 3: Pass 1 — Scenarios A, B, C

**Files:**
- Modify: `commands/nct-validate.md` (append after Pass 0)

Write the first three scenario sections. These are the most cross-validation-heavy scenarios. Copy the check definitions directly from the spec, adjusting the format to match the command's instruction style.

- [ ] **Step 1: Write Scenario A (Exploration, 8 checks)**

Append the Scenario A section from the spec (lines 113-149). Use the command's per-check format:

```markdown
### A1: Model info (quic_types)

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_model_info` with:
- `relative_path`: `quic/quic_stack/quic_types.ivy`

- **Structural**: Response present, contains type or action information.
- **Record**: List of types and actions reported (for cross-validation with A2).
- If valid response: **PASS**. Otherwise: **FAIL**.
```

For each check A1-A8, B1-B6, C1-C5: copy the check definition from the spec (`docs/superpowers/specs/2026-03-18-nct-validate-redesign-design.md` — Scenario A: lines 117-149, Scenario B: lines 155-182, Scenario C: lines 188-213). Adapt the tool name to the full MCP identifier format shown in the A1 example above (e.g., `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_coverage` for ivy_coverage). For LSP checks (A2-A6), use the `LSP` tool with the appropriate operation name.

For each check, include:
- The exact MCP/LSP tool call with parameters
- Structural validation criteria (what fields must exist)
- Reflection instruction (what to compare with prior checks)
- Cross-validation instruction (if applicable)
- PASS/FAIL criteria

Key details for each check:
- **A2**: Use `LSP` tool for `documentSymbol`. Reflection: compare with A1 types.
- **A3**: Use `LSP` tool for `hover` on cid. Reflection: mention type from A2.
- **A4**: Use `LSP` tool for `goToDefinition` on cid. Cross-check: consistent with A2.
- **A5**: Use `LSP` tool for `findReferences` on cid. Expect >1 ref across >1 file.
- **A6**: Use `LSP` tool for `workspaceSymbol("cid")`. Cross-check: matches A3, A4.
- **A7**: Call `ivy_include_graph` for quic_connection.ivy. Reflection: quic_types should appear.
- **A8**: Call `ivy_query(info, cid, quic)`. Cross-check: 4-way agreement with A3, A4, A6.
- **B1**: Call `ivy_coverage(stats, quic/)`. Consistency: total = sum of levels.
- **B2**: Call `ivy_coverage(gaps, quic)`. Cross-check: relationship with B1.
- **B3**: Call `ivy_query(info, ...)` on first gap from B2. SKIP if B2 gaps empty.
- **B4**: Call `ivy_coverage(matrix, quic/)`. Cross-check: consistent with B1.
- **B5**: Call `ivy_extract_requirements` with sample RFC text. Structural: returns categories.
- **B6**: Call `ivy_model_summary(quic/)`. Cross-check: action count relates to B1.
- **C1**: Call `ivy_verify(quic_types.ivy)`. Record error symbol if failure. If success, SKIP C2-C5.
- **C2-C5**: Chain that traces the error from C1 through query, hover, findReferences, impact.

- [ ] **Step 2: Verify Scenarios A, B, C**

Read the file. For each scenario, confirm:
- Check count matches spec (A=8, B=6, C=5)
- Every check has tool call, structural criteria, and reflection/cross-validation
- Scenario C has branching logic for C1 success
- B3 has SKIP logic for empty gaps
- No ground truth values referenced

- [ ] **Step 3: Commit**

```bash
git add commands/nct-validate.md
git commit -m "refactor(nct-validate): add Pass 1 Scenarios A (exploration), B (coverage), C (debug)"
```

---

### Task 4: Pass 1 — Scenarios D, E, F

**Files:**
- Modify: `commands/nct-validate.md` (append after Scenario C)

Write the remaining three scenarios. Scenario D includes the mutation safety protocol (git-based).

- [ ] **Step 1: Write Scenario D (Edit-Verify Loop, 4 checks + 2 actions)**

Key: D3 and D5 are labeled as `[ACTION]`, not `[CHECK]`. Include the full mutation safety protocol:

```markdown
#### Scenario D: Edit-Verify Loop — "I'm adding a monitor" (4 checks + 2 actions)

**Skip entirely if `mode=fast` or `error-injection=false`.**

D3 and D5 are mutation/restore **actions**, not checks — they do not produce PASS/FAIL.
If D3 fails, D4-D6 are SKIPPED. If D5 fails, report FAIL with remediation.

### D1: Lint baseline (quic_types)

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_lint` with:
- `relative_path`: `quic/quic_stack/quic_types.ivy`

- **Structural**: `diagnostic_count = 0` (file must be clean to proceed).
- If clean: **PASS**. If not clean: **FAIL** — skip D2-D6 (can't run mutation on dirty file).

### D2: Diagnostics baseline (quic_types)

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_diagnostics` with:
- `relative_path`: `quic/quic_stack/quic_types.ivy`

- **Structural**: Returns layered result with layer names.
- **Cross-check**: Consistent with D1 — both report clean.
- If valid: **PASS**. Otherwise: **FAIL**.

### D3: [ACTION] Mutate file

1. Run via Bash: `git stash push -m "nct-validate-mutation-$(date +%s)" -- <absolute-path-to-quic_types.ivy>`
2. Record the stash ref from output.
3. Use the `Edit` tool to insert `include nonexistent_module_xyzzy` as a new line after line 1 (`#lang ivy1.7`).
4. If Edit fails: SKIP D4-D6.

### D4: Lint detects mutation

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_lint` with:
- `relative_path`: `quic/quic_stack/quic_types.ivy`

- **Structural**: `diagnostic_count > 0` (lint detected the injected error).
- **Reflection**: Is the error message actionable? Does it name the bad include?
- If diagnostics found: **PASS**. If `diagnostic_count = 0`: **FAIL** — "Lint did not detect bad include."

### D5: [ACTION] Restore file

1. Run via Bash: `git checkout -- <absolute-path-to-quic_types.ivy>`
2. Run via Bash: `git stash drop <recorded-stash-ref>`
3. If git checkout fails: fall back to `git stash pop`. If both fail: report **FAIL** with "file may be corrupted — run `git diff` to check".

### D6: Lint recovery

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_lint` with:
- `relative_path`: `quic/quic_stack/quic_types.ivy`

- **Structural**: `diagnostic_count = 0` (file restored to clean state).
- **Cross-check**: Matches D1 baseline exactly.
- If clean: **PASS**. Otherwise: **FAIL** — "File restoration failed."
```

- [ ] **Step 2: Write Scenario E (Pre-commit Health, 6 checks)**

From spec lines 246-273. Key checks:
- E1: ivy_lint on quic_frame.ivy
- E2: ivy_quality(gate, quic, standard)
- E3: ivy_patterns(check, quic)
- E4: ivy_compile on a server test file (e.g., `quic/quic_tests/server_tests/quic_server_test_stream.ivy`)
- E5: ivy_visualize(dependencies, test file)
- E6: ivy_diagnostics on quic_frame.ivy — cross-check with E1

- [ ] **Step 3: Write Scenario F (Impact Analysis, 5 checks)**

From spec lines 275-298. Key checks:
- F1: ivy_query(info, quic_packet_type)
- F2: ivy_query(impact, quic_packet_type)
- F3: include_graph(full workspace)
- F4: findReferences(quic_packet_type) — cross-check with F2
- F5: goToDefinition(quic_packet_type) — cross-check with F1

- [ ] **Step 4: Verify Scenarios D, E, F**

Read the file. Confirm:
- D has 4 checks + 2 actions, correctly labeled
- D has skip logic for fast mode and error-injection=false
- Mutation safety uses git stash with timestamp
- E4 uses ivy_compile (GAP-1 fix)
- E5 uses ivy_visualize (GAP-5 fix)
- F cross-validation chains are explicit

- [ ] **Step 5: Commit**

```bash
git add commands/nct-validate.md
git commit -m "refactor(nct-validate): add Scenarios D (edit-verify), E (pre-commit), F (impact)

Scenario D uses git-safe mutation with stash/checkout restore.
Scenario E covers ivy_compile and ivy_visualize (GAP-1, GAP-5 fixes).
Scenario F adds impact analysis with cross-validation chains."
```

---

### Task 5: Pass 1 Negative Tests + Pass 2 Gap Sweep

**Files:**
- Modify: `commands/nct-validate.md` (append after Scenario F)

- [ ] **Step 1: Write negative tests FX1-FX8**

From spec lines 300-328. These include 3 new LSP negative tests (FX6-FX8) not in the current v2.

Key: each FX check validates graceful handling of bad input. PASS criteria: no crash, no stack trace, empty or zero result.

- FX1: ivy_query for nonexistent symbol
- FX2: ivy_coverage for nonexistent protocol
- FX3: include_graph for standalone file
- FX4: ivy_model_summary for non-test file
- FX5: ivy_coverage gaps for nonexistent protocol
- FX6: LSP hover at line 9999 (invalid position)
- FX7: LSP documentSymbol for nonexistent file
- FX8: LSP goToDefinition at line 9999 (invalid position)

- [ ] **Step 2: Write Pass 2 Gap Sweep**

From spec lines 330-389. Write the gap sweep section:

```markdown
## Pass 2: Gap Sweep (~6 checks)

**Skip if `mode=fast`.**

One structural call per MCP tool or LSP operation NOT exercised in Pass 1. The gap sweep ensures no tool is completely untested.

### GS1-GS6

For each uncalled tool, make one call and verify it responds without error:
- GS1: `ivy_scope` — responds without error
- GS2: `ivy_manifest` — responds without error
- GS3: `ivy_pattern_scaffold` — responds without error
- GS4: `ivy_verification_dashboard` — responds without error
- GS5: LSP `prepareCallHierarchy` — responds (may be empty, documented limitation)
- GS6: LSP `goToImplementation` — responds (may be empty)

After the sweep, present the **Tool Coverage Matrix** showing which tools were called by which scenario and which by the gap sweep.
```

Include the full coverage matrix from the spec.

- [ ] **Step 3: Verify**

Read the file. Confirm:
- 8 negative tests (FX1-FX8), including 3 new LSP ones
- Gap sweep has 6 entries including ivy_verification_dashboard
- Coverage matrix lists all 28 tools/LSP ops

- [ ] **Step 4: Commit**

```bash
git add commands/nct-validate.md
git commit -m "refactor(nct-validate): add negative tests (FX1-FX8) and gap sweep (Pass 2)

Add 3 new LSP negative tests (FX6-FX8, GAP-7 fix).
Add gap sweep for ivy_scope, ivy_manifest, ivy_pattern_scaffold,
ivy_verification_dashboard, LSP callHierarchy, LSP goToImplementation.
Include tool coverage matrix."
```

---

### Task 6: Pass 3 — Hooks, Surface, Agents

**Files:**
- Modify: `commands/nct-validate.md` (append after Pass 2)

- [ ] **Step 1: Write hooks section (H1-H14)**

From spec lines 395-417. Key changes from v2:
- H2: NEW — checks `obs_session_start.py` registration (I5 fix)
- H5: NEW — checks `check_lsp_log.py` with matcher `mcp__.*ivy` (BUG-1 fix)
- H11: Now checks BOTH Stop scripts: `stop-session-summary.sh` AND `obs_stop.py` (I5 fix)
- H14: All hook scripts exist check — include `check_lsp_log.py` and `obs_session_start.py` in the script list

For each H-check, specify:
- The hooks.json key to look for (event type)
- The matcher value (if applicable)
- The script name to find in the command field
- PASS/FAIL criteria

- [ ] **Step 2: Write surface section (S1-S4)**

From spec lines 419-426. Key change: S3 uses sanity check (count > 0) instead of exact threshold.

```markdown
### S3: MCP tools count

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_capabilities` and count the reported tools.

- **Structural**: Count > 0.
- **Record**: Actual count for interactive review.
- If count > 0: **PASS** — report actual count. Otherwise: **FAIL**.
```

- [ ] **Step 3: Write agents section (AG1-AG5)**

From spec lines 428-457. Key changes from v2:
- Reduced from 8 to 5 agents
- Sequential dispatch (no batching)
- Cross-validation against Scenario A, B, C results instead of keyword matching
- Each agent prompt asks for a specific verifiable artifact

For each AG check, specify:
- Agent subagent_type
- Exact prompt text
- Structural criteria (response length, no stack traces)
- Cross-validation instruction (compare with earlier scenario)
- Note: "Skip if `mode=fast`"

- [ ] **Step 4: Verify Pass 3**

Read the file. Confirm:
- 14 hook checks (H1-H14), not 12
- H2, H5, H11 are new/updated per BUG-1 and I5 fixes
- 5 agents (not 8), sequential, with cross-validation references
- Agents skip in fast mode

- [ ] **Step 5: Commit**

```bash
git add commands/nct-validate.md
git commit -m "refactor(nct-validate): add Pass 3 hooks (14), surface (4), agents (5)

Fix BUG-1: add H5 for check_lsp_log.py hook validation.
Fix I5: add H2 for obs_session_start.py, update H11 for obs_stop.py.
Reduce agents from 8 to 5, replace keyword matching with cross-validation."
```

---

### Task 7: Pass 4, SR1, and Result Presentation

**Files:**
- Modify: `commands/nct-validate.md` (append after Pass 3)

- [ ] **Step 1: Write Pass 4 Interactive Review**

From spec lines 459-502. Write the interactive review template:
- Group values by scenario (A, B, C, D, E, F)
- Include cross-validation summary table
- End with: `Reply with row numbers to REJECT, or "all good" to confirm all values.`
- Note: in fast mode, print the table without waiting for user confirmation.

- [ ] **Step 2: Write SR1 Self-Review**

From spec lines 535-559. Key changes from v2:
- No ground truth drift detection
- Cross-validation agreement score using 9 defined pairs
- Formula: `100 * (pass_rate * 0.7 + cross_validation_agreement * 0.3)`
- Include the cross-validation pairs table

- [ ] **Step 3: Write Result Presentation Format**

From spec lines 561-606. Include:
- v3 report header (Date, Workspace, Command, Mode, Passes)
- Summary table with 5-pass structure
- Per-check detail format (with Reflection and Cross-validation fields)
- Suggested actions for each failure type (update log path to `/tmp/ivy-lsp-latest.log`)
- Remove all references to ground truth comparison table

- [ ] **Step 4: Verify the complete file**

Read the entire file end-to-end. Verify:
- No references to `ground-truth`, `quic-workspace.yaml`, `fallback` values
- No references to the old phase numbering (Phase 1, Phase 1B, Phase 2, etc.)
- All check IDs are unique and correctly numbered
- Summary table totals: Pass 0 (3) + Pass 1 (42) + Pass 2 (~6) + Pass 3 (23) + SR1 (1) = ~75
- Fast mode skip logic is mentioned in all affected sections
- All 7 bugs addressed (BUG-1 through BUG-7)
- All 8 coverage gaps addressed (GAP-1 through GAP-8)
- Suggested actions section uses `/tmp/ivy-lsp-latest.log` (not `/tmp/ivy-lsp.log`)

- [ ] **Step 5: Commit**

```bash
git add commands/nct-validate.md
git commit -m "refactor(nct-validate): add Pass 4 interactive review, SR1, result format

Complete v3 rewrite. Interactive review with grouped value table.
SR1 uses cross-validation agreement score (9 pairs).
Remove all ground truth references."
```

---

### Task 8: Delete Ground Truth YAML and Clean Up

**Files:**
- Delete: `tests/ground-truth/quic-workspace.yaml`
- Modify: `commands/nct-validate.md` (if any stale references remain)

- [ ] **Step 1: Delete the ground truth file**

```bash
git rm tests/ground-truth/quic-workspace.yaml
```

- [ ] **Step 2: Check for any remaining stale references**

Search the entire plugin directory for references to the deleted file or old v2 concepts:

```bash
grep -r "quic-workspace.yaml\|ground.truth\|fallback:" commands/ skills/ agents/ CLAUDE.md
```

Fix any references found. The CLAUDE.md should not reference ground truth for nct-validate.

- [ ] **Step 3: Remove the backup file**

```bash
rm -f commands/nct-validate.md.bak
```

- [ ] **Step 4: Verify the final file line count**

```bash
wc -l commands/nct-validate.md
```

Expected: ~650-750 lines (comparable to v2's 785, but better organized).

- [ ] **Step 5: Commit**

```bash
git add -u
git commit -m "refactor(nct-validate): delete ground truth YAML, clean up stale references

Ground truth validation replaced by structural checks + interactive
manual review. quic-workspace.yaml no longer needed."
```

---

### Task 9: Smoke Test

**Files:** None (runtime verification)

- [ ] **Step 1: Run fast mode**

```
/nct-validate fast
```

Verify:
- Pre-flight (P1-P3) runs and passes
- Scenarios A, B, C, E, F run sequentially with reflections
- Scenario D is skipped (fast mode)
- Negative tests (FX1-FX8) run
- Gap sweep is skipped (fast mode)
- Hooks (H1-H14) run
- Surface (S1-S4) runs
- Agents are skipped (fast mode)
- SR1 runs and produces a score
- Results are printed without interactive confirmation prompt
- No references to ground truth in the output

- [ ] **Step 2: Check for structural issues in the output**

Review the report for:
- All checks have PASS/FAIL/SKIPPED status
- Reflections are present and reference prior checks
- Cross-validation comparisons are present
- Summary table totals are correct
- No stack traces or error messages from the command itself

- [ ] **Step 3: If issues found, fix and re-run**

Fix any issues in `commands/nct-validate.md` and re-run `/nct-validate fast`.

- [ ] **Step 4: Commit any fixes**

```bash
git add commands/nct-validate.md
git commit -m "fix(nct-validate): address smoke test findings"
```

---

### Task 10: Full Mode Validation (optional)

**Files:** None (runtime verification)

- [ ] **Step 1: Run full mode**

```
/nct-validate
```

This runs all 5 passes including mutations, gap sweep, agents, and interactive review.

Verify additionally:
- Scenario D mutation runs with git stash/checkout
- File is restored cleanly after mutation
- Gap sweep calls uncovered tools
- Agents dispatch sequentially and produce cross-validated responses
- Interactive review table is presented
- User can respond with row numbers or "all good"

- [ ] **Step 2: Verify agent cross-validation**

Check that:
- AG1 response mentions types seen in Scenario A
- AG2 response references the same error as Scenario C
- AG5 coverage numbers are roughly consistent with Scenario B

- [ ] **Step 3: Commit any final fixes**

```bash
git add commands/nct-validate.md
git commit -m "fix(nct-validate): address full validation findings"
```
