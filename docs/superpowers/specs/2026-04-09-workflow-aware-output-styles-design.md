# Workflow-Aware Output Style System

**Date**: 2026-04-09
**Status**: Design approved, pending implementation plan
**Scope**: panther-ivy-plugin (Claude Code plugin for Ivy formal protocol testing)

## Problem

The panther-ivy-plugin has five workflow states (navigate, verify, build, review, triage), each with distinct phases, but Claude's output formatting is uniform regardless of which workflow is active. Session summaries, tool result presentation, and prose style don't adapt to the current workflow context. This creates a mismatch between the workflow's purpose and how results are communicated.

## Goals

1. **Session-level prose style** adapts per workflow: verbosity, tone, structure, and mandatory sections change based on the active workflow.
2. **Tool result presentation** is reformatted per workflow context for the five high-frequency MCP tools.
3. **Session summaries** are tailored to the workflow that was active, emphasizing workflow-relevant metrics.
4. **Phase awareness** within each workflow provides minor adjustments without requiring per-phase style definitions.

## Architecture: Layered Composition

Three composable layers are assembled at runtime into a single effective style document injected into Claude's context each turn:

```
+-------------------------------------+
|    Effective Style Document         |  <- injected via additionalContext
|  (base + overlay + phase modifier)  |     on every UserPromptSubmit
+---------------+---------------------+
                | composed by
+---------------+---------------------+
|         compose-style.py            |  <- UserPromptSubmit hook
|  reads active-workflow -> loads     |
|  base.md + overlays/{workflow}.md   |
|  -> highlights active phase section |
+-------------------------------------+

+-------------------------------------+
|       render-tool-result.py         |  <- PostToolUse hook
|  reads active-workflow -> loads     |
|  tool-renderers/{tool}.md           |
|  -> reformats into hookSpecificOutput
+-------------------------------------+

+-------------------------------------+
|        render-summary.py            |  <- Stop hook (replaces current)
|  reads active-workflow -> loads     |
|  summaries/{workflow}.md            |
|  -> fills template with session data|
+-------------------------------------+
```

### File Structure

```
plugins/panther-ivy-plugin/
  styles/
    base.md                    # Shared output conventions
    overlays/
      navigate.md
      verify.md
      build.md
      review.md
      triage.md
    tool-renderers/
      ivy_verify.md
      ivy_coverage.md
      ivy_diagnostics.md
      ivy_compile.md
      ivy_quality.md
    summaries/
      navigate.md
      verify.md
      build.md
      review.md
      triage.md
  hooks/scripts/
    compose-style.py           # New: UserPromptSubmit hook
    render-tool-result.py      # New: PostToolUse hook
    render-summary.py          # New: replaces stop-session-summary.sh
```

### Integration with Existing Hooks

- `compose-style.py` runs alongside the existing `route-user-prompt.py` on `UserPromptSubmit`.
- `render-tool-result.py` runs alongside `interaction-checkpoint.py` and `post-write-ivy-lint.sh` on `PostToolUse`. Both contribute to `hookSpecificOutput` — they are concatenated, not competing.
- `render-summary.py` replaces `stop-session-summary.sh` on `Stop`, absorbing its current functionality (lint scan, claim counts, tool metrics) into workflow-specific summary templates.

## Base Style Layer

`styles/base.md` defines shared conventions that apply regardless of workflow. Overlays override or extend these defaults.

```markdown
# Base Output Style

## Formatting Conventions
- Cite RFC sections as `[rfcNNNN:X.Y]` inline, never as footnotes.
- Format errors as: `ERROR: {file}:{line} -- {message}`.
- Format warnings as: `WARN: {file}:{line} -- {message}`.
- Reference Ivy files with relative paths from protocol-testing root.

## Default Dimensions
- **Verbosity**: Moderate -- explain the "what" concisely, skip the "why" unless asked
  or non-obvious.
- **Tone**: Professional, neutral. No enthusiasm markers ("great!", "nice!"). State facts.
- **Structure**: Prose paragraphs by default. Use tables only for quantitative data
  (coverage stats, pass/fail counts). Use checklists for action items.
- **Sections**: End responses with "Next Steps" listing 1-3 concrete actions when the
  workflow has more work to do.

## Tool Result Defaults
- When presenting MCP tool results, lead with the outcome (pass/fail/count), then details.
- Suppress raw JSON. Always render tool results as formatted prose or tables.
- For verification results, always include the isolate name and file path.
- For coverage results, always include the percentage and the denominator.

## Claim Discussion Format
- When a claim discussion is triggered, use this structure:
  1. State the claim (RFC requirement + Ivy assertion)
  2. Present the evidence (tool output, counterexample)
  3. Ask for resolution: RESOLVED / IUT_FINDING / DEFERRED / GUARD_ADDED / N_A /
     KNOWN_DEVIATION
- Mark the resolution in the source file as a comment.

## Phase Transition Announcements
- When transitioning between phases, announce: "Moving to {phase_name}."
- Do not re-explain what the phase does -- the workflow skill handles that.
```

## Workflow Overlays

Each overlay overrides base defaults and defines mandatory sections, tool presentation rules, and phase modifiers.

### verify.md

```markdown
# Verify Workflow -- Style Overlay

## Dimension Overrides
- **Verbosity**: Clinical. Lead with the result, not the reasoning. One sentence per
  finding.
- **Tone**: Diagnostic. "3 isolates passed, 1 failed at quic_protection.ivy:142" --
  no hedging.
- **Structure**: Checklist for multi-item results. Numbered list for failures.

## Mandatory Sections
- **Verification Results** -- always present, pass/fail per isolate
- **Failure Details** -- only if failures exist, one entry per failure
- **Next Steps** -- from base, but scoped to verification actions only

## Tool Presentation
- `ivy_verify` success: "PASS: {isolate} verified ({N} clauses, {time}s)"
- `ivy_verify` failure: numbered list -- "1. FAIL: {isolate} at {file}:{line} --
  {error_excerpt}"
- `ivy_diagnostics`: severity-grouped table (errors first, then warnings)
- `ivy_coverage`: inline -- "{N}% MUST coverage ({covered}/{total})"

## Phase Modifiers

### preflight
- Show only a "Preflight Checks" section (health, workspace, target file existence).
- Suppress "Next Steps" -- preflight auto-advances.

### compile
- Announce compilation target and expected duration.
- On success: single confirmation line, advance immediately.
- On failure: switch to failure detail format from base.

### diagnose
- **Override verbosity** to detailed. Explain root cause reasoning.
- Add sections: "Error Analysis", "Root Cause Hypothesis".
- Include relevant Ivy code snippets (3-5 lines around the error).

### fix
- After each edit, show "Changes Made" section: file, what changed, why.
- Re-run verification inline -- show updated pass/fail immediately after fix.
```

### navigate.md

```markdown
# Navigate Workflow -- Style Overlay

## Dimension Overrides
- **Verbosity**: Conversational. Provide context for what happened and what's available.
- **Tone**: Welcoming, orienting. "You left off mid-build on the QUIC connection layer."
- **Structure**: Prose with embedded suggestions. No tables unless showing workspace status.

## Mandatory Sections
- **Context Summary** -- where the user left off, active workspace, modified files
- **Available Actions** -- what workflows are available given current state
- **Suggested Next Step** -- one recommended action based on state

## Tool Presentation
- `ivy_health_check`: prose summary -- "LSP and MCP are healthy. Workspace: quic
  (client+server)."
- `ivy_workspace get`: inline -- "Active workspace: {protocol} ({roles})"
- Build state (if resuming): layer completion table

## Phase Modifiers

### warm_resume
- Lead with "Resuming previous session." then context summary.
- If build-state.yaml exists, show layer progress table.

### cold_start
- Lead with "Welcome." then workspace detection results.
- Show available protocols and suggest `/set-workspace`.

### activity_summary
- Summarize recent git changes to .ivy files.
- Highlight files with unresolved claim discussions.
```

### build.md

```markdown
# Build Workflow -- Style Overlay

## Dimension Overrides
- **Verbosity**: Explanatory. Provide reasoning for layer choices and dependency order.
- **Tone**: Methodical. "Layer 4 (frame) depends on types (layer 1). Writing
  quic_frame.ivy."
- **Structure**: Progress-oriented. Layer tables, dependency chains.

## Mandatory Sections
- **Layer Progress** -- table from build-state.yaml showing status per layer
- **Current Layer** -- what's being worked on, dependencies satisfied
- **Next Steps** -- next layer in dependency order

## Tool Presentation
- `ivy_verify`: per-layer -- "Layer verified: {isolate} PASS" or "Layer verification
  failed -- switching to verify workflow."
- `ivy_diagnostics`: focus on current layer's structural issues
- `ivy_compile`: compilation of current layer, success/failure

## Phase Modifiers

### scope
- Show protocol overview and methodology selection (NCT/NACT/NSCT).

### blueprint
- Show full 14-layer template, mark which layers are planned vs. skipped.
- Present dependency graph as ordered list.

### write
- Show current layer context: what it does, what it depends on, what depends on it.
- After each file write, show file path and line count.

### quality_gate
- Show quality gate results as pass/fail checklist.

### wrap_up
- Show final layer progress table with all statuses.
```

### review.md

```markdown
# Review Workflow -- Style Overlay

## Dimension Overrides
- **Verbosity**: Detailed for findings, terse for passing checks.
- **Tone**: Auditor. "Coverage gap: [rfc9000:4.1] has no corresponding assertion."
- **Structure**: Tables for quantitative results. Numbered lists for findings.

## Mandatory Sections
- **Coverage Summary** -- percentage, covered/total, per-section breakdown
- **Quality Findings** -- numbered list of issues with severity
- **Recommendations** -- prioritized list of improvements

## Tool Presentation
- `ivy_coverage` (stats): full table with per-section breakdown
- `ivy_coverage` (gaps): numbered list with RFC section references
- `ivy_coverage` (matrix): full requirement-to-assertion table
- `ivy_quality` (suggestions): numbered findings
- `ivy_quality` (gate): pass/fail checklist

## Phase Modifiers

### triage
- Determine review type (coverage/quality/both). Show scoping decision.

### execute
- Show progress through dispatched agents (spec-analyst, model-reviewer,
  traceability-agent).

### findings
- Present all results in a structured report format.
```

### triage.md

```markdown
# Triage Workflow -- Style Overlay

## Dimension Overrides
- **Verbosity**: Terse. Bullet points. One line per check.
- **Tone**: Diagnostic, urgent. "MCP: DOWN. LSP: OK. Workspace: not set."
- **Structure**: Status dashboard. Pass/fail per component.

## Mandatory Sections
- **Health Status** -- one-line status per component (LSP, MCP, workspace, indexing)
- **Fix Actions** -- if anything is down, concrete fix steps
- **Result** -- "All systems operational" or "N issue(s) remain"

## Tool Presentation
- `ivy_health_check`: per-component status line
- `ivy_verify`: "ivy_verify: OK" or "ivy_verify: FAIL -- {count} error(s)"
- `ivy_diagnostics`: error count only, no detail

## Phase Modifiers

### quick_check
- Run health check, show dashboard, exit if all green.

### diagnose
- Expand failing components with log excerpts and error details.

### fix
- Show fix action taken and result. Re-check after each fix.
```

## Tool Renderers

Each tool renderer defines workflow-keyed formatting rules for the `render-tool-result.py` PostToolUse hook. The markdown files serve as **design documentation and implementation guide** — the Python hook implements these rules as string formatting logic, not by parsing the prose at runtime. When adding or modifying a renderer, update the markdown file first (as the specification), then update the corresponding Python logic in the hook to match. Only the five high-frequency MCP tools get renderers. Other tools use overlay directives.

### ivy_verify.md

```markdown
# ivy_verify -- Result Renderer

## Input Fields
The tool returns: isolate, status (pass/fail), clause_count, duration_s,
errors (list of {file, line, message, isolate}).

## Default (no workflow active)
- Pass: "PASS: {isolate} verified ({clause_count} clauses, {duration_s}s)"
- Fail: "FAIL: {isolate} at {file}:{line} -- {message}"

## verify
- Pass: "PASS: {isolate} ({clause_count} clauses, {duration_s}s)"
- Fail: Numbered list of all errors. Include 3 lines of context hint:
  "See {file}:{line}."
- Summary line: "{pass_count}/{total} isolates passed."

## build
- Pass: "Layer verified: {isolate} PASS"
- Fail: "Layer verification failed -- switching to verify workflow for diagnosis."
- Only show the isolate relevant to the current build layer.

## review
- Pass/fail as table row: | {isolate} | {status} | {clause_count} | {duration_s}s |
- Aggregate into a table when multiple isolates verified in sequence.

## triage
- Pass: "ivy_verify: OK"
- Fail: "ivy_verify: FAIL -- {error_count} error(s). Run verify workflow for details."
```

### ivy_coverage.md

```markdown
# ivy_coverage -- Result Renderer

## Input Fields
Varies by mode. stats: {covered, total, percentage, by_section}.
gaps: {uncovered_requirements, unguarded_state}.
matrix: {requirement_to_assertion_map}.

## Default
- stats: "{percentage}% MUST coverage ({covered}/{total})"
- gaps: Bullet list of uncovered requirements
- matrix: Table with requirement -> assertion mapping

## verify
- stats: Inline -- "{percentage}% ({covered}/{total})" -- no table.
- gaps: Suppress unless explicitly requested. Verify focuses on pass/fail, not coverage.

## build
- stats: Show per-layer breakdown if available.
- gaps: Highlight gaps in the layer currently being built.

## review
- stats: Full table with per-section breakdown: | Section | Covered | Total | % |
- gaps: Numbered list with RFC section references.
- matrix: Full table -- this is the primary review artifact.

## triage
- stats: Single line -- "Coverage: {percentage}%"
- gaps/matrix: Suppress -- triage doesn't audit coverage.
```

### ivy_diagnostics.md

```markdown
# ivy_diagnostics -- Result Renderer

## Input Fields
Returns: issues (list of {file, line, severity, message, layer}), summary counts.

## Default
- Severity-grouped list: errors first, then warnings.
- Include file:line for each.

## verify
- Severity-grouped table: | Severity | File | Line | Message |
- Errors first, warnings second.

## build
- Filter to current layer only.
- Show as numbered list with fix suggestions.

## review
- Full table with layer column: | Layer | Severity | File | Line | Message |
- Include summary counts at top.

## triage
- Count only: "{error_count} errors, {warning_count} warnings"
- Detail suppressed unless in diagnose phase.
```

### ivy_compile.md

```markdown
# ivy_compile -- Result Renderer

## Input Fields
Returns: status (success/failure), output_binary, duration_s, errors (if any).

## Default
- Success: "Compiled {file} -> {output_binary} ({duration_s}s)"
- Failure: "Compilation failed: {error_message}"

## verify
- Success: "Compiled: {output_binary} ({duration_s}s)" -- advance immediately.
- Failure: Show error with file:line, suggest switching to diagnose phase.

## build
- Success: "Layer compiled: {file} -> {output_binary}"
- Failure: "Layer compilation failed. Fix before proceeding to next layer."

## review
- Not typically used in review. Default format.

## triage
- Success: "ivy_compile: OK"
- Failure: "ivy_compile: FAIL -- {error_message}"
```

### ivy_quality.md

```markdown
# ivy_quality -- Result Renderer

## Input Fields
Varies by mode. suggestions: {suggestions (list of {category, message, severity})}.
gate: {passed, gate_level, failures}.

## Default
- suggestions: Numbered list by severity.
- gate: "Gate {gate_level}: PASS" or "Gate {gate_level}: FAIL -- {failure_count}
  issue(s)"

## verify
- suggestions: Suppress unless explicitly requested. Verify focuses on correctness.
- gate: Inline pass/fail.

## build
- suggestions: Show suggestions relevant to current layer.
- gate: Show gate result with per-criterion breakdown.

## review
- suggestions: Full numbered list grouped by category.
- gate: Detailed table: | Criterion | Status | Details |

## triage
- suggestions: Suppress.
- gate: "Quality gate: PASS" or "Quality gate: FAIL ({failure_count})"
```

## Session Summary Templates

Each summary template defines what the Stop hook reports when a session ends under that workflow. Like tool renderers, these markdown files serve as **design documentation** — the `render-summary.py` hook implements the summary logic in Python, not by loading and parsing the templates at runtime. When adding or modifying a summary format, update the markdown file first (as the specification), then update the corresponding Python logic in the hook to match.

### summaries/verify.md

```markdown
# Verify Session Summary

## Sections (in order)

### Verification Results
- Total isolates attempted: {isolates_attempted}
- Passed: {pass_count} | Failed: {fail_count}
- List each failed isolate: "{isolate} at {file}:{line}"

### Claim Resolutions
- Show counts by type: {resolved} confirmed, {iut_findings} IUT findings,
  {deferred} deferred
- If any IUT_FINDING: list them with file and RFC section

### Outstanding Work
- List isolates not yet attempted or still failing
- If in diagnose/fix phase at session end: note "Fix in progress for {isolate}"

### Session Metrics
- Tool calls: top 3 by frequency
- Session duration hint (from observability timestamps)

### Lint Issues
- Only if modified .ivy files have issues: "{file}: {issue}"
```

### summaries/build.md

```markdown
# Build Session Summary

## Sections (in order)

### Layer Progress
Table from build-state.yaml:
| Layer | File | Status |
|-------|------|--------|
| types | quic_types.ivy | complete |
| frame | quic_frame.ivy | in progress |
| packet | -- | pending |

### Decisions Made
- List from build-state.yaml decisions array

### Verification Status
- If any layers were verified: show pass/fail per layer
- If build reached Phase 4 (verify): show verification summary

### Next Session
- Next layer in dependency order
- Any blockers or open questions from this session

### Lint Issues
- Same as verify
```

### summaries/navigate.md

```markdown
# Navigate Session Summary

## Sections (in order)

### Session Activity
- Files modified (from git diff)
- Workflows activated during session (from observability)

### Workspace State
- Active workspace at session end
- Build state summary if build-state.yaml exists

### Claim Resolutions
- Same format as verify summary

### Lint Issues
- Same as verify
```

### summaries/review.md

```markdown
# Review Session Summary

## Sections (in order)

### Coverage Delta
- Coverage at session start vs. end (if both measured)
- New requirements covered this session

### Quality Findings
- Total findings: {count} by severity
- Findings resolved vs. outstanding

### Agents Dispatched
- Which agents ran and their outcomes

### Lint Issues
- Same as verify
```

### summaries/triage.md

```markdown
# Triage Session Summary

## Sections (in order)

### Health Status
- Final status per component: LSP, MCP, workspace, indexing

### Issues Fixed
- What was broken and what fix was applied

### Remaining Issues
- What still needs attention

### Lint Issues
- Same as verify
```

### Fallback (no workflow active)

When no workflow was active at session end, `render-summary.py` falls back to a generic summary matching the current `stop-session-summary.sh` output: lint issues, claim discussion counts, tool metrics. No information is lost compared to today.

## Hook Implementations

### compose-style.py (UserPromptSubmit)

**Trigger:** Every user prompt submission.

**Logic:**
1. Resolve the protocol directory (from workspace state or cwd).
2. Read `.panther-ivy/active-workflow` -- extract `workflow` and `phase`.
3. Load `styles/base.md`.
4. If workflow is active, load `styles/overlays/{workflow}.md`.
5. In the overlay content, find the `### {phase}` section under `## Phase Modifiers` and mark it as `[ACTIVE PHASE]` so Claude knows which phase modifier applies now.
6. Concatenate: base + overlay (with active phase highlighted).
7. Output as `additionalContext`.

**Edge cases:**
- No active workflow: inject only `base.md` (default style).
- Workflow file missing or corrupt: fall back to base only, log warning.
- No matching phase section in overlay: use overlay defaults without phase modifier.

**Performance:** Reads 2 small markdown files (~100 lines total). Negligible latency.

**Sub-workflow transitions:** When a workflow invokes another (e.g., build invokes verify as a sub-workflow), the active-workflow file is updated with the child workflow name. Since `compose-style.py` reads this file every turn, the style switches automatically to the child workflow's overlay. When the child completes and the parent resumes, the style switches back. No special handling needed — the existing sub-workflow protocol in the active-workflow file drives this.

### render-tool-result.py (PostToolUse)

**Trigger:** PostToolUse for the 5 rendered tools: `ivy_verify`, `ivy_coverage`, `ivy_diagnostics`, `ivy_compile`, `ivy_quality`.

**Logic:**
1. Check if the tool matches the rendered set (exit early if not).
2. Read `.panther-ivy/active-workflow` -- extract `workflow`.
3. Load `styles/tool-renderers/{tool_name}.md`.
4. Find the `## {workflow}` section (or `## Default` if no workflow active).
5. Parse the tool's JSON output from the hook's `tool_result` input.
6. Apply the renderer's format rules to produce formatted text.
7. Output as `hookSpecificOutput`.

**Edge cases:**
- Tool result is an error: pass through unformatted (let Claude handle error reporting).
- No renderer file for the tool: exit without output (Claude uses overlay directives).
- Renderer section missing for active workflow: fall back to `## Default`.

**Interaction with existing hooks:** Runs alongside `interaction-checkpoint.py`. The interaction checkpoint injects claim discussion reminders; the renderer reformats the tool output. Both contribute to `hookSpecificOutput` and are concatenated.

### render-summary.py (Stop)

**Trigger:** Stop event (session end).

**Logic:**
1. Read `.panther-ivy/active-workflow` -- extract `workflow`.
2. Load `styles/summaries/{workflow}.md` (or generic fallback).
3. Gather session data (absorbing current `stop-session-summary.sh` logic):
   - Scan modified `.ivy` files for lint issues.
   - Count claim discussion markers.
   - Read observability JSONL for tool metrics.
   - If build workflow: read `build-state.yaml` for layer progress.
4. Fill the template sections with gathered data.
5. Output as `additionalContext` with `[IVY SESSION SUMMARY]` header.

**Migration from stop-session-summary.sh:** The new hook is Python (not bash), making it easier to parse YAML and JSONL. All current functionality is preserved -- lint scan, claim counts, tool metrics -- but routed through the workflow-specific template. The bash script is retired.

**Edge cases:**
- No workflow was active: use generic summary (equivalent to current behavior).
- Build-state.yaml missing during build workflow: skip layer progress section, note "build state not found".

### Hook Registration (hooks.json additions)

```json
{
  "hooks": [
    {
      "event": "UserPromptSubmit",
      "script": "${CLAUDE_PLUGIN_ROOT}/hooks/scripts/compose-style.py",
      "description": "Inject workflow-aware output style"
    },
    {
      "event": "PostToolUse",
      "script": "${CLAUDE_PLUGIN_ROOT}/hooks/scripts/render-tool-result.py",
      "toolNames": [
        "mcp__panther-ivy-plugin__ivy_verify",
        "mcp__panther-ivy-plugin__ivy_coverage",
        "mcp__panther-ivy-plugin__ivy_diagnostics",
        "mcp__panther-ivy-plugin__ivy_compile",
        "mcp__panther-ivy-plugin__ivy_quality"
      ],
      "description": "Reformat MCP tool results per active workflow style"
    },
    {
      "event": "Stop",
      "script": "${CLAUDE_PLUGIN_ROOT}/hooks/scripts/render-summary.py",
      "description": "Workflow-aware session summary"
    }
  ]
}
```

## Skill Integration

Each workflow skill (SKILL.md) gains a small section connecting it to the style system:

```markdown
## Output Style

This workflow's output formatting is managed by the style system.
Follow the style directives injected via `additionalContext` -- they contain
your active workflow overlay and phase modifier. Do not invent your own
formatting for tool results that arrive pre-formatted in `hookSpecificOutput`.
```

Existing inline formatting instructions in workflow skills must be audited and migrated to the corresponding overlay during implementation.

**Concern ownership:**

| Concern | Owned by |
|---------|----------|
| What phases exist | Skill |
| What to do in each phase | Skill |
| How to present results | Style overlay |
| How tool output looks | Tool renderer |
| Phase transition announcement | Base style |
| When to trigger claim discussion | interaction-checkpoint hook (unchanged) |

## Extensibility

**Adding a new workflow** requires exactly 3 files:
1. `styles/overlays/{workflow}.md`
2. `styles/summaries/{workflow}.md`
3. The workflow skill itself (already required)

No hook changes needed. `compose-style.py` dynamically loads overlays by workflow name.

**Adding a new rendered tool** requires:
1. `styles/tool-renderers/{tool_name}.md`
2. Add the tool name to `toolNames` in the `render-tool-result.py` hook registration.

**Modifying a style** is a single-file edit with no cascading changes.

## Migration Path

1. Create `styles/` directory and write base + all overlays + renderers + summaries.
2. Implement the three hooks (compose-style, render-tool-result, render-summary).
3. Audit existing workflow skills for inline formatting instructions; replace with style system reference.
4. Replace `stop-session-summary.sh` with `render-summary.py`.
5. Register new hooks in `hooks.json`.
6. Remove retired formatting logic from existing hooks (`post-write-workflow-aware`'s suggestion logic stays -- it's behavioral, not formatting).

## Testing

- Each hook can be tested in isolation by setting up a `.panther-ivy/active-workflow` file and running the script with mock input.
- Manual smoke test: activate each workflow, run a representative tool, verify output matches the overlay/renderer expectations.
- The observability system logs hook execution -- style hooks appear in event logs for debugging.
