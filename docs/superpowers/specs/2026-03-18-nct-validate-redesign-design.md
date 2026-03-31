# nct-validate Redesign: Scenario-Based Sequential Validation

**Date**: 2026-03-18
**Status**: Draft
**Scope**: `/nct-validate` command in panther-ivy-plugin

## Problem Statement

The current `/nct-validate` command has structural issues that reduce its reliability and maintainability:

1. **Hard-coded ground truth** — A YAML file with exact expected values (97 requirements, 680 files, cid at line 29, etc.) drifts as the model evolves and requires manual maintenance.
2. **Synthetic API checks** — Checks call tools in isolation ("call ivy_query, check field exists") rather than simulating real user workflows.
3. **Parallel execution prevents cross-validation** — Agents dispatch in parallel batches, so later checks cannot reference earlier results.
4. **Weak agent validation** — Keyword matching (e.g., "response contains 2 of: `type`, `include`") is trivially passable.
5. **770-line monolith** — All checks in a single file with no modularization.
6. **Mutation testing is unsafe** — File mutations use Write-tool backup/restore, which is vulnerable to race conditions and hook side effects.
7. **7 bugs and 8 coverage gaps** — See Findings section below.

## Findings from Deep Review

### Bugs (7)

| ID | Severity | Description |
|----|----------|-------------|
| BUG-1 | HIGH | `check_lsp_log.py` hook (PreToolUse, matcher `mcp__.*ivy`) exists in hooks.json but is not checked by H2-H11, not in ground truth YAML, not in H12 script list |
| BUG-2 | MEDIUM | Ground truth YAML says `min_mcp_tools: 18` but command fallback says `>=15` — inconsistent threshold |
| BUG-3 | MEDIUM | SR1 consistency check "M9 uncovered = M8 total - covered" is underspecified — M8 does not report a covered count |
| BUG-4 | MEDIUM | Agent keyword matching is trivially passable — A1 keywords include `type` and `include` (common English words), A6 includes `review` and `issue` |
| BUG-5 | LOW | hooks.json structural inconsistency — SessionStart/UserPromptSubmit have no `matcher` field while others have `matcher: ""` — undetected |
| BUG-6 | MEDIUM | L3 (line 4, char 9) and L5 (line 32, char 10) positions are hardcoded in the prompt, not in ground truth YAML — drift detection cannot catch shifts |
| BUG-7 | LOW | Phase 1B depends on P2 (same as Phase 1) but has no independent gate check — if Phase 1 is skipped but Phase 1B runs, no redundant safety |

### Coverage Gaps (8)

| ID | Missing Tool/Feature | Severity |
|----|---------------------|----------|
| GAP-1 | `ivy_compile` — never tested (one of 3 core CLI operations) | HIGH |
| GAP-2 | `ivy_model_info` — never tested (one of 3 core capabilities checked in P2) | HIGH |
| GAP-3 | `ivy_diagnostics` (5-layer) — never tested, only `ivy_lint` (lighter check) is tested | MEDIUM |
| GAP-4 | `ivy_extract_requirements` — never tested (key traceability feature) | MEDIUM |
| GAP-5 | `ivy_visualize` — never tested | LOW |
| GAP-6 | `ivy_scope`, `ivy_manifest` — never tested (listed in capabilities but unvalidated) | LOW |
| GAP-7 | LSP negative tests — none exist (hover on invalid position, symbol on nonexistent file) | MEDIUM |
| GAP-8 | LSP/MCP cross-consistency — not checked (L1 and M6 both query `cid` but results not compared) | MEDIUM |

## Design

### Core Principles

1. **No ground truth YAML** — Eliminate exact-value expectations entirely. Checks validate structure and sanity (tool responded, fields present, count > 0, no stack traces). Actual values are presented to the user for interactive review.
2. **Scenario-based** — Checks are organized by user intent (exploration, coverage audit, debugging) rather than API layer (MCP, LSP).
3. **Sequential with cross-validation** — Every check runs one at a time. Later checks reference and cross-validate earlier results. Claude writes a 1-2 sentence reflection per check connecting the result to prior context.
4. **Interactive review** — After all automated checks, present a consolidated table of all collected values. The user scans and confirms or rejects.

### Two-Tier Check Model

**Tier 1 — Automated (PASS/FAIL/SKIPPED)**: Validates structure and health only.

- Tool returned a response (no timeout, no crash)
- Response has expected fields/keys
- No stack traces in output
- Sanity: count > 0, list non-empty, file path exists
- For negative tests: graceful handling (no crash on bad input)
- For mutation tests: lint detected the error, restoration succeeded

**Tier 2 — Interactive (CONFIRM/REJECT)**: After all automated checks, present a single review table:

```markdown
## Interactive Review

| # | Check | Value | Confirm? |
|---|-------|-------|----------|
| 1 | A7: quic_connection includes | 11 modules: [quic_types, ...] | |
| 2 | F3: workspace total files | 683 | |
| 3 | A8: cid location | quic_types.ivy:29 | |
| 4 | B1: total requirements | 97 (MUST:42, MUST_NOT:12, ...) | |
| ... | ... | ... | |

Reply with the row numbers to reject, or "all good" to confirm.
```

### 5-Pass Architecture

```
Pass 0: Pre-flight    — Gate checks: LSP alive, MCP healthy, LSP responding (3 checks)
Pass 1: Scenarios     — 6 workflow scenarios + negative tests (34 scenario + 8 negative = 42 checks)
Pass 2: Gap Sweep     — 1 structural call per uncovered tool (~6 checks)
Pass 3: Non-workflow   — Hooks, surface, agents (14 hooks + 4 surface + 5 agents = 23 checks)
Pass 4: Interactive    — Consolidated review table for user confirmation (no automated checks)
```

Total: ~75 checks. Pass 0 always runs first and gates Passes 1-3.

### Pass 0: Pre-flight (3 checks) — always runs first

Pre-flight gates all subsequent passes. If LSP or MCP is down, downstream checks are SKIPPED rather than producing cascading failures.

```
P1. pgrep -f ivy_lsp
    → PASS if PIDs returned. FAIL → skip all LSP checks in Pass 1 and Pass 3.

P2. ivy_capabilities()
    → PASS if ivy_check, ivyc, ivy_show capabilities present. FAIL → skip all MCP checks.

P3. LSP hover(quic_types.ivy, line 1, char 0)
    → PASS if any response. FAIL → skip all LSP checks.
```

### Pass 1: Scenarios (42 checks: 34 scenario + 8 negative)

All checks run sequentially. Each check includes a reflection that references prior results.

#### Scenario A: Exploration — "I'm new, show me the QUIC model" (8 checks)

Simulates a user opening a spec file and navigating through the model to understand its structure.

```
A1. ivy_model_info(quic_types.ivy)
    → structural: response present, has type/action information
    → record: list of types and actions reported

A2. documentSymbol(quic_types.ivy)
    → structural: returns list, each entry has name + range, line numbers >= 0
    → reflection: compare symbol names with A1 types — do they overlap?

A3. hover(quic_types.ivy, on cid type)
    → structural: has contents field, non-empty
    → reflection: does hover mention a type from A2's symbol list?

A4. goToDefinition(quic_types.ivy, on cid)
    → structural: returns uri + range, target file exists
    → cross-check: target file consistent with A2's symbol location?

A5. findReferences(cid)
    → structural: returns > 1 reference across > 1 file
    → reflection: cid is a fundamental type, expect widespread usage

A6. workspaceSymbol("cid")
    → structural: >= 1 result with name and location
    → cross-check: location matches A3 hover and A4 definition?

A7. include_graph(quic_connection.ivy)
    → structural: non-empty include list, all resolved_path values non-null
    → reflection: note include count, check if quic_types appears (it should — cid is used)

A8. ivy_query(info, cid, quic)
    → structural: found=true, has file and line
    → cross-check: file+line consistent with A3, A4, A6? (4-way agreement on cid location)
```

#### Scenario B: Coverage Audit — "What's our RFC coverage?" (6 checks)

Simulates a user reviewing requirement coverage and finding gaps.

```
B1. ivy_coverage(stats, quic/)
    → structural: total > 0, level breakdown present
    → consistency: total = sum of MUST + MUST_NOT + SHOULD + SHOULD_NOT + MAY?

B2. ivy_coverage(gaps, quic)
    → structural: returns list
    → cross-check: is there a meaningful relationship with B1 totals?

B3. ivy_query(info, first uncovered symbol or requirement from B2)
    → SKIP if B2 returned empty gaps list (no uncovered requirements)
    → structural: response present (found or not found — both valid)
    → reflection: can we navigate to where this gap lives?
    → note: if B2 returns requirement IDs rather than symbol names, use the
      requirement's associated file/action as the query target instead

B4. ivy_coverage(matrix, quic/)
    → structural: non-empty requirement-to-assertion mapping
    → cross-check: covered count from matrix consistent with B1 stats?

B5. ivy_extract_requirements(sample RFC text)
    → structural: returns parsed requirements with categories
    → reflection: does extraction produce MUST/SHOULD/MAY categories matching RFC 2119?

B6. ivy_model_summary(quic/)
    → structural: non-empty, has per-action data
    → cross-check: action count > 0, relates to B1 coverage scope?
```

#### Scenario C: Debug Verification Failure — "ivy_verify failed, now what?" (5 checks)

Simulates the debugging workflow after a verification failure. Uses the known error in quic_types.ivy.

**Branching logic**: C1 determines the path. If verify fails (expected), C2-C5 trace the error. If verify succeeds (the known error was fixed), C2-C5 SKIP with reason "no failure to debug — verification succeeded."

```
C1. ivy_verify(quic_types.ivy)
    → structural: returns result with success field (true or false both valid)
    → record: if failure, capture which symbol/line is reported in error output
    → if success=true: record this, C2-C5 will be SKIPPED

C2. ivy_query(info, symbol from C1 error)      [SKIP if C1 succeeded]
    → structural: found=true (or graceful not-found)
    → reflection: can we locate the failing symbol? does query agree with verify's error location?

C3. hover(file from C2, line from C2)           [SKIP if C1 succeeded]
    → structural: has contents field
    → cross-check: hover info relates to the type/action from C1's error?

C4. findReferences(symbol from C1)              [SKIP if C1 succeeded]
    → structural: returns results
    → reflection: how widely is this symbol used?

C5. ivy_query(impact, symbol from C1)           [SKIP if C1 succeeded]
    → structural: non-empty impact result
    → cross-check: C4 returns lexical references (occurrences), C5 returns dependency edges
      (modules). These are different quantities — C5 edges will typically be much fewer than
      C4 references. Check that both are non-empty and that C5 files are a subset of C4 files.
```

#### Scenario D: Edit-Verify Loop — "I'm adding a monitor" (4 checks + 2 actions)

Simulates editing a spec file and verifying the change. Uses git-safe mutation.

D3 and D5 are mutation/restore **actions**, not checks — they do not produce PASS/FAIL.
If D3 (mutation) fails to apply, D4-D6 are SKIPPED. If D5 (restore) fails, report FAIL with remediation.

```
D1. ivy_lint(quic_types.ivy)                              [CHECK]
    → structural: diagnostic_count = 0 (baseline — file must be clean to proceed)

D2. ivy_diagnostics(quic_types.ivy)                       [CHECK]
    → structural: returns layered result with layer names
    → cross-check: consistent with D1 — both report clean?

D3. [ACTION: MUTATE — insert "include nonexistent_module_xyzzy" after line 1]
    → method: git stash, then Edit tool (see Mutation Safety section)
    → if Edit fails: SKIP D4-D6

D4. ivy_lint(quic_types.ivy)                              [CHECK]
    → structural: diagnostic_count > 0 (mutation detected)
    → reflection: is the error message actionable? does it name the bad include?

D5. [ACTION: RESTORE — git checkout -- <file>, then git stash drop]
    → if restore fails: FAIL with "file may be corrupted — run git diff"

D6. ivy_lint(quic_types.ivy)                              [CHECK]
    → structural: diagnostic_count = 0 (recovered)
    → cross-check: matches D1 baseline
```

#### Scenario E: Pre-commit Health — "Is the model ready?" (6 checks)

Simulates the checks a user would run before committing changes.

```
E1. ivy_lint(quic_frame.ivy)
    → structural: diagnostic_count = 0 (clean file)

E2. ivy_quality(gate, quic, standard)
    → structural: gate result present, has file count and checks
    → reflection: how many files reported? are monitors present?

E3. ivy_patterns(check, quic)
    → structural: layers and completeness report present
    → reflection: are key layers (recovery, extensions) present?

E4. ivy_compile(server test file)
    → structural: compilation result returned (success or failure with clear error)
    → reflection: if failure, is the error message actionable?

E5. ivy_visualize(dependencies, test file)
    → structural: returns visualization data (non-empty)
    → reflection: does the dependency structure look reasonable?

E6. ivy_diagnostics(quic_frame.ivy)
    → structural: returns layered diagnostics
    → cross-check: consistent with E1 lint result on same file?
```

#### Scenario F: Impact Analysis — "What breaks if I change quic_packet_type?" (5 checks)

Simulates assessing the blast radius of a type change.

```
F1. ivy_query(info, quic_packet_type)
    → structural: found=true, has kind field

F2. ivy_query(impact, quic_packet_type)
    → structural: non-empty impact result with edges
    → reflection: how many incoming/outgoing edges? is this a high-impact type?

F3. include_graph(full workspace, no path)
    → structural: total_files > 0
    → reflection: workspace size — is the count reasonable?

F4. findReferences(quic_packet_type)
    → structural: returns multiple references
    → cross-check: reference count roughly consistent with F2 impact edge count?

F5. goToDefinition(quic_packet_type)
    → structural: resolves to a file
    → cross-check: same file as F1 query result?
```

### Pass 1 Negative Tests (integrated into scenarios)

Fixture-based negative tests are appended after the 6 scenarios but still in Pass 1. They test edge-case handling without needing cross-validation chains.

```
FX1. ivy_query(info, nonexistent_xyzzy_42)
     → structural: found=false or graceful empty, no stack traces

FX2. ivy_coverage(stats, new_prot/)
     → structural: total=0 or graceful empty, no stack traces

FX3. include_graph(standalone file: quic_h3_error_code.ivy)
     → structural: empty or very small includes list, no crash

FX4. ivy_model_summary(non-test file: quic_transport_error_code.ivy)
     → structural: graceful result (even if empty), no crash

FX5. ivy_coverage(gaps, new_prot)
     → structural: empty gaps or graceful empty, no stack traces

FX6. LSP hover(quic_types.ivy, line 9999, char 0)
     → structural: empty hover or graceful null, no crash

FX7. LSP documentSymbol(nonexistent_file.ivy)
     → structural: empty list or graceful error, no crash

FX8. LSP goToDefinition(quic_types.ivy, line 9999, char 0)
     → structural: empty result or graceful null, no crash
```

### Pass 2: Gap Sweep (~6 checks)

One structural call per MCP tool or LSP operation not exercised in Pass 1. The gap sweep dynamically determines which tools were missed by tracking calls during Pass 1.

```
GS1. ivy_scope (if uncalled)
     → structural: responds without error

GS2. ivy_manifest (if uncalled)
     → structural: responds without error

GS3. ivy_pattern_scaffold (if uncalled)
     → structural: responds without error

GS4. ivy_verification_dashboard (if uncalled)
     → structural: responds without error

GS5. LSP prepareCallHierarchy (if uncalled)
     → structural: responds without error (may return empty — documented limitation)

GS6. LSP goToImplementation (if uncalled)
     → structural: responds without error (may return empty)
```

After the gap sweep, present a tool coverage matrix:

```markdown
## Tool Coverage Matrix

| Tool                    | Scenario | Gap Sweep | Status |
|-------------------------|----------|-----------|--------|
| ivy_lint                | D, E     |           | covered |
| ivy_verify              | C        |           | covered |
| ivy_compile             | E        |           | covered |
| ivy_model_info          | A        |           | covered |
| ivy_diagnostics         | D, E     |           | covered |
| ivy_query(info)         | A, B, C, F |         | covered |
| ivy_query(impact)       | C, F     |           | covered |
| ivy_coverage(stats)     | B        |           | covered |
| ivy_coverage(gaps)      | B        |           | covered |
| ivy_coverage(matrix)    | B        |           | covered |
| ivy_extract_requirements| B        |           | covered |
| ivy_include_graph       | A, F     |           | covered |
| ivy_visualize           | E        |           | covered |
| ivy_model_summary       | B        |           | covered |
| ivy_quality             | E        |           | covered |
| ivy_patterns            | E        |           | covered |
| ivy_capabilities        | (P0)     |           | covered |
| ivy_scope               |          | GS1       | covered |
| ivy_manifest            |          | GS2       | covered |
| ivy_pattern_scaffold    |          | GS3       | covered |
| ivy_verification_dashboard |       | GS4       | covered |
| LSP hover               | A, C     |           | covered |
| LSP documentSymbol      | A        |           | covered |
| LSP goToDefinition      | A, F     |           | covered |
| LSP findReferences      | A, C, F  |           | covered |
| LSP workspaceSymbol     | A        |           | covered |
| LSP goToImplementation  |          | GS6       | covered |
| LSP callHierarchy       |          | GS5       | covered |
```

### Pass 3: Non-Workflow Checks (23 checks)

Pre-flight runs in Pass 0 (see above). Pass 3 contains hooks, surface, and agents only.

#### Hooks (14 checks)

```
H1.  SessionStart: detect-ivy-workspace.sh fired — look for [ivy-workspace] in session context
H2.  SessionStart: obs_session_start.py registered in hooks.json    [I5 FIX]
H3.  PreToolUse: matcher "Bash" → block-direct-ivy.sh
H4.  PreToolUse: matcher "ivy_verify" → lint-before-verify.sh
H5.  PreToolUse: matcher "mcp__.*ivy" → check_lsp_log.py           [BUG-1 FIX]
H6.  PreToolUse: matcher "" → obs_pre_tool_use.py
H7.  PostToolUse: matcher "Write|Edit" → post-write-ivy-lint.sh
H8.  PostToolUse: matcher "" → obs_post_tool_use.py
H9.  PostToolUseFailure → obs_post_tool_use_failure.py
H10. SessionEnd → obs_session_end.py
H11. Stop: stop-session-summary.sh + obs_stop.py (both registered)  [I5 FIX]
H12. SubagentStart + SubagentStop → obs_subagent_start.py, obs_subagent_stop.py
H13. Remaining hooks: PreCompact, UserPromptSubmit, Notification, PermissionRequest
H14. All hook scripts exist and are readable (shebangs present)
```

Notes:
- H2 is new — checks `obs_session_start.py` registration (previously only `detect-ivy-workspace.sh` was checked via H1).
- H5 is new — addresses BUG-1 (missing `check_lsp_log.py` hook validation).
- H11 now checks both Stop scripts (previously only `stop-session-summary.sh`).

#### Surface (4 checks)

```
S1. Commands: glob commands/*.md, verify count and YAML frontmatter
S2. Skills: glob skills/*/SKILL.md, verify count and YAML frontmatter
S3. MCP tools: ivy_capabilities tool count (sanity: > 0)
S4. Observability logs: check for JSONL files, validate format if present
```

#### Agents (5 checks, sequential, cross-validated)

Each agent receives a task requiring actual tool use. Validation is structural (response length, no stack traces) plus cross-validation against earlier scenario results.

```
AG1. spec-analyst (exploration):
     Prompt: "List all types defined in quic_types.ivy with their line numbers"
     → structural: response > 50 chars, no stack traces
     → cross-check: response mentions type names seen in Scenario A (A1, A2)?

AG2. spec-analyst (verification):
     Prompt: "Run ivy_verify on quic_types.ivy and explain the failure"
     → structural: response > 50 chars, no stack traces
     → cross-check: mentions same error context as Scenario C (C1)?

AG3. methodology-guide (NCT):
     Prompt: "I have an uncovered MUST requirement from RFC 9000.
              What NCT step should I follow to add a monitor?"
     → structural: response > 100 chars, coherent advice, no stack traces

AG4. model-reviewer (review):
     Prompt: "Review quic_types.ivy for specification quality issues"
     → structural: identifies at least 1 concrete observation, references file content
     → no stack traces

AG5. traceability-agent (coverage):
     Prompt: "What is the RFC 9000 coverage breakdown for QUIC?"
     → structural: response > 50 chars, mentions requirement categories
     → cross-check: coverage numbers roughly consistent with Scenario B (B1)?
```

### Pass 4: Interactive Review

After all automated checks complete, present a consolidated table. Group values by scenario for readability.

```markdown
# Interactive Review

## Scenario A: Exploration
| # | Check | Value |
|---|-------|-------|
| 1 | A1: model_info types | [cid, quic_packet_type, role, bit, ...] |
| 2 | A2: documentSymbol count | 14 symbols |
| 3 | A3: hover on cid | "type cid" |
| 4 | A5: findReferences cid | 47 references across 12 files |
| 5 | A7: include_graph count | 11 modules |
| 6 | A8: cid location | quic_types.ivy:29 |

## Scenario B: Coverage
| # | Check | Value |
|---|-------|-------|
| 7 | B1: total requirements | 97 (MUST:42, MUST_NOT:12, SHOULD:16, SHOULD_NOT:3, MAY:24) |
| 8 | B2: uncovered gaps | 23 uncovered requirements |
| 9 | B4: matrix covered | 74 requirements mapped |
| 10| B6: action count | 31 actions |

## Scenario C: Debug
| # | Check | Value |
|---|-------|-------|
| 11| C1: verify error | FAIL on zero_rtt_allowed (line 42) |
| 12| C5: impact edges | 8 incoming, 3 outgoing |

[... etc for D, E, F ...]

## Cross-Validation Summary
| Pair | Agreement |
|------|-----------|
| A3+A4+A6+A8 cid location | all agree: quic_types.ivy:29-30 |
| D1+D6 lint baseline/recovery | both: 0 diagnostics |
| B1 total vs level sum | 97 = 42+12+16+3+24 = 97 |
| C4 refs vs C5 impact | 12 refs ~ 11 edges (close) |
| E1+E6 lint vs diagnostics | both clean |

Reply with row numbers to REJECT, or "all good" to confirm all values.
```

### Mutation Safety

Mutations in Scenario D use git operations for atomic restore:

```
1. git stash push -m "nct-validate-mutation-$(date +%s)" -- <file>  # unique message
2. Record the stash ref from output (e.g., stash@{0})
3. Edit tool: apply mutation (insert bad include)
4. Run ivy_lint (expect diagnostic_count > 0)
5. git checkout -- <file>                          # atomic restore
6. Run ivy_lint (expect diagnostic_count = 0)
7. git stash drop <recorded-ref>                   # drop the exact stash
```

If step 5 fails, fall back to `git stash pop`. If both fail, report FAIL with "file may be corrupted — run `git diff` to check".

The stash message includes a timestamp to avoid collisions with leftover stashes from crashed runs. Step 2 records the exact ref to avoid dropping the wrong stash in step 7.

Only 1 mutation type (bad include insertion) in the default flow. The other 2 mutations (missing `#lang` header, unmatched brace) are available via `error-injection=full` argument.

### Fast Mode

`/nct-validate fast` skips:

- Scenario D (mutations)
- Pass 2 (gap sweep)
- Pass 3 agents (AG1-AG5)
- Pass 4 interactive review (prints results directly without waiting for user confirmation)

Keeps: Pass 0 (pre-flight) + Scenarios A, B, C, E, F + negative tests (FX1-FX8) + hooks + surface. Negative tests are cheap (no mutations, no agents) and always included. Estimated runtime: 2-3 minutes.

### SR1: Self-Review (simplified)

No ground truth means no drift detection. SR1 becomes:

1. **Completeness**: every check has PASS/FAIL/SKIPPED (no undefined)
2. **Cross-validation consistency**: flag any cross-checks that disagreed (see list below)
3. **Reflection quality**: all reflections are present and non-empty
4. **Tool coverage**: present the coverage matrix, flag any uncovered tools
5. **Score**: `100 * (pass_rate * 0.7 + cross_validation_agreement * 0.3)` where pass_rate excludes SKIPPED

**Cross-validation pairs** (used to compute `cross_validation_agreement`):

| Pair | What must agree |
|------|-----------------|
| A1 (model_info) ↔ A2 (documentSymbol) | Type names overlap |
| A3 (hover cid) ↔ A4 (goToDefinition cid) ↔ A6 (workspaceSymbol cid) ↔ A8 (ivy_query cid) | All locate cid in same file |
| D1 (lint baseline) ↔ D6 (lint recovery) | Both report 0 diagnostics |
| D1 (lint) ↔ D2 (diagnostics) | Both report clean on same file |
| E1 (lint) ↔ E6 (diagnostics) | Both report clean on same file |
| B1 (coverage total) ↔ B1 (level sum) | total = MUST + MUST_NOT + SHOULD + SHOULD_NOT + MAY |
| C4 (findReferences) ↔ C5 (impact) | Both non-empty, C5 files subset of C4 files |
| F1 (query info) ↔ F5 (goToDefinition) | Same file |
| F2 (impact) ↔ F4 (findReferences) | Both non-empty for same symbol |

`cross_validation_agreement = pairs_that_agree / total_pairs_evaluated` (pairs where one side is SKIPPED are excluded from the denominator).

### Result Presentation Format

```markdown
# Ivy Integration Validation Report (v3)

**Date**: {timestamp}
**Workspace**: {detected workspace root}
**Command**: `/nct-validate {args}`
**Mode**: full / fast
**Passes run**: {list}

## Summary

| Pass | Name | Checks | Passed | Failed | Skipped |
|------|------|--------|--------|--------|---------|
| 0 | Pre-flight | 3 | ? | ? | ? |
| 1 | Scenarios + Negatives | 42 | ? | ? | ? |
|   | - A: Exploration | 8 | ? | ? | ? |
|   | - B: Coverage | 6 | ? | ? | ? |
|   | - C: Debug | 5 | ? | ? | ? |
|   | - D: Edit-Verify | 4 (+2 actions) | ? | ? | ? |
|   | - E: Pre-commit | 6 | ? | ? | ? |
|   | - F: Impact | 5 | ? | ? | ? |
|   | - Negative tests | 8 | ? | ? | ? |
| 2 | Gap Sweep | ~6 | ? | ? | ? |
| 3 | Non-workflow | 23 | ? | ? | ? |
|   | - Hooks | 14 | ? | ? | ? |
|   | - Surface | 4 | ? | ? | ? |
|   | - Agents | 5 | ? | ? | ? |
| 4 | Interactive | - | - | - | - |
| SR | Self-Review | 1 | ? | ? | ? |
| **Total** | | **~75** | **?** | **?** | **?** |

**Quality Score**: NN/100
```

Per-check detail uses this format:

```markdown
### {ID}: {Title}
- **Tool**: {tool name and params}
- **Status**: PASS / FAIL / SKIPPED
- **Value**: {actual value returned}
- **Reflection**: {1-2 sentences connecting to prior results}
- **Cross-validation**: {if applicable, comparison with prior check}
```

### Comparison with Current Design

| Aspect | Current (v2) | Redesign (v3) |
|--------|-------------|---------------|
| Organization | 7 phases by API layer | 5 passes: pre-flight, scenarios, gap sweep, non-workflow, interactive |
| Total checks | ~55 | ~75 |
| Ground truth | YAML with exact values | Eliminated — structural checks + manual review |
| Execution | Parallel where possible | Fully sequential with cross-validation |
| Cross-validation | None | 9 defined cross-validation pairs + per-check reflection |
| Tool coverage | 6/22 MCP tools (27%) | ~21/28 tools+LSP ops (75%) via scenarios + gap sweep |
| Agent checks | 8 with keyword matching | 5 with structural + cross-validated checks |
| Mutations | 3 separate, Write-tool restore | 1 realistic (Scenario D), git-safe restore |
| Negative tests | 6 MCP-only | 8 including LSP negative tests |
| Hook checks | 12 (missed check_lsp_log.py, obs_stop.py, obs_session_start.py) | 14 (all hooks covered) |
| Fast mode | None | `fast` argument skips mutations, agents, interactive confirmation |
| Bugs fixed | 0 | 7 (BUG-1 through BUG-7) |
| Interactive review | None | Consolidated value table for user confirmation |
