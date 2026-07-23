# Smart Routing Architecture for panther-ivy-plugin

**Date:** 2026-04-07
**Status:** Design approved. Implementation plan: `docs/superpowers/plans/2026-04-08-smart-routing-implementation.md`
**Scope:** Complete architectural redesign of panther-ivy-plugin's routing, workflows, and component structure

## Problem Statement

The panther-ivy-plugin has 36 user-facing components (5 agents, 20 skills, 11 commands; plus 12 hook event types) with no clear funnel. A user expressing intent like "verify my QUIC handshake spec" could land on any of four different components. Methodology content is duplicated between agents and skills, tool documentation lives in three places, and review can be triggered via three independent paths. The result is a plugin that is comprehensive but hard to navigate.

## Design Goals

1. Users express intent in natural language and get routed to the right workflow automatically
2. Reduce user-facing surface area from 37 components to 9 entry points
3. Agents and knowledge skills become internal implementation details, invisible to users
4. Multi-session workflows persist state for context recovery
5. Power users retain shortcut commands for direct tool access

## Architecture Overview

### Two-Tier Routing Model

Every user message passes through two routing tiers.

**Tier 1 -- Deterministic (`UserPromptSubmit` hook).** A hook script reads the user's prompt and matches against a `routing-rules.json` config file containing keyword lists, regex patterns, and file-path triggers. On a confident match, it injects a directive into context telling Claude which workflow to activate. Handles approximately 95% of cases.

**Tier 2 -- LLM fallback (CLAUDE.md dispatch table).** A markdown table in CLAUDE.md maps intent categories to workflows. Claude reads this at session start and uses it when Tier 1 produces no match. Handles novel phrasing that no keyword list would catch.

**Ambiguity resolution.** When neither tier produces a confident match, the system routes to the `navigate` workflow, which resolves ambiguity through context scanning or one clarifying question.

### Routing Rules Config

Single file at the plugin root: `routing-rules.json`.

```json
{
  "workflows": {
    "verify": {
      "keywords": ["verify", "check", "test", "pass", "fail", "debug", "counterexample", "invariant violation"],
      "intentPatterns": ["(does|did|will).*pass", "(why|what).*fail", "run.*test"],
      "fileTriggers": ["*.ivy"],
      "priority": "high"
    },
    "build": {
      "keywords": ["build", "scaffold", "create", "model", "add pattern", "propagate", "new spec", "write spec"],
      "intentPatterns": ["(create|build|write|design).*?(model|spec|protocol)", "(add|implement).*?(layer|pattern|frame)"],
      "fileTriggers": [],
      "priority": "medium"
    },
    "review": {
      "keywords": ["review", "audit", "coverage", "RFC gaps", "quality", "traceability"],
      "intentPatterns": ["(how much|what).*cover", "(check|audit).*quality"],
      "fileTriggers": [],
      "priority": "medium"
    },
    "triage": {
      "keywords": ["health", "broken", "connection error", "MCP", "LSP", "server down", "not working"],
      "intentPatterns": ["(why|what).*(broken|error|crash|down)"],
      "fileTriggers": [],
      "priority": "critical"
    },
    "navigate": {
      "keywords": ["what next", "where was I", "what should I", "confused", "help me decide"],
      "intentPatterns": ["(what|where).*(next|start|do)"],
      "fileTriggers": [],
      "priority": "low"
    }
  },
  "learning_injection": {
    "keywords": ["teach", "explain", "how does", "what is NCT", "what is NACT", "methodology", "learn"],
    "intentPatterns": ["(teach|explain|how does).*?(NCT|NACT|NSCT|ivy|formal)"],
    "knowledge_skills": ["methodology-reference", "ivy-toolkit", "ivy-writing-guide"]
  }
}
```

**Priority resolution:** When multiple workflows match, highest priority wins. Triage always wins (if the stack is broken, nothing else matters). An intentPattern match takes precedence over a keyword-only match at the same priority level. Same-priority ties with the same match type: the hook injects both matches and lets the LLM pick using the CLAUDE.md table.

**Learning injection** is separate from workflows. It injects knowledge skills into context without activating a workflow, allowing Claude to answer methodology questions conversationally.

### CLAUDE.md Dispatch Table

Embedded in the plugin's CLAUDE.md for LLM-based Tier 2 routing:

```markdown
## Workflow Routing

When a user expresses intent, activate the matching workflow skill.
If ambiguous, activate navigate.

| User Intent | Workflow | Examples |
|---|---|---|
| Verify, test, debug failure | verify | "check my spec", "why did it fail", "run tests on handshake" |
| Create model, add layers, propagate changes | build | "model QUIC connection", "add frame variants", "I changed a type" |
| Audit quality, check coverage, review | review | "RFC coverage?", "review my model", "quality issues?" |
| Toolchain broken, health check | triage | "MCP won't connect", "nothing works", "health check" |
| Unclear intent, session resume, what's next | navigate | "where was I?", "what should I do?", "I'm new here" |

### Rules
1. If a workflow is already active (check `<protocol-directory>/.panther-ivy/active-workflow`; see State Management below), stay in it unless the user explicitly asks to switch.
2. Direct tool requests ("call ivy_verify on X") use shortcut commands, not workflows.
3. Learning questions ("how does NCT work?") are answered using loaded knowledge skills, no workflow activation.
4. Every workflow returns to navigate on completion.
```

## Workflows

Five workflows, each implemented as a skill file. Workflows are the only user-facing dispatch targets.

### verify

The test-compile-execute cycle with failure diagnosis.

**Phase 1 -- Preflight.** Silent MCP health check (reuses triage logic). Detects target protocol from workspace context or asks. If MCP is down, redirects to triage workflow.

**Phase 2 -- Test Selection.** Scans existing test specs for the target protocol. Presents options: run existing tests, pick specific ones, or design a new test inline (pulling ivy-writing-guide and specification-patterns knowledge). Gate checkpoint: user confirms which test(s) to run or create.

**Phase 3 -- Compile.** Calls `ivy_compile` on selected tests. On compile error, dispatches spec-analyst agent to diagnose. Presents fix suggestion, loops back to compile on fix.

**Phase 4 -- Execute.** Runs the compiled test via `ivy_verify`. On PASS, reports success and offers follow-ups (review, coverage audit). On FAIL, moves to Phase 5.

**Phase 5 -- Diagnose.** Pulls counterexample-guide knowledge. Dispatches spec-analyst agent with the failure trace. Classifies failure (invariant violation, type error, structural issue). On structural issue, escalates to model-reviewer for deeper audit. Gate checkpoint: "Fix it yourself, or want me to attempt the fix?"

**Phase 6 -- Fix (optional).** If user accepts, applies fix, loops back to Phase 3 (recompile and rerun). Loops Phase 3-6 until PASS or user stops.

**On completion:** Returns to navigate.

### build

Multi-session protocol model construction. The heaviest workflow.

**Phase 1 -- Scope.** Detects methodology context (NCT/NACT/NSCT from keywords or asks). Pulls methodology-reference knowledge. Identifies target protocol, RFC, and aspect. Gate checkpoint: confirms understanding.

**Phase 2 -- Blueprint.** Pulls specification-patterns knowledge. Scans existing specs for the target protocol. Proposes layer structure (which layers apply: frame variants, serdes, monitors, etc.). Gate checkpoint: user approves structure. Persists the blueprint as `.panther-ivy/build-state.yaml` in the protocol directory.

**Phase 3 -- Write.** Pulls ivy-writing-guide knowledge. Generates spec files incrementally (one layer at a time). After each layer: compile check via `ivy_compile`. Handles compile errors inline using spec-analyst agent and counterexample-guide knowledge (no workflow switch). Inform-and-continue checkpoint between layers.

**Phase 4 -- Verify.** Invokes the verify workflow on the files just written. Full test selection, compile, execute, diagnose cycle.

**Phase 5 -- Quality Gate.** Dispatches model-reviewer and traceability-agent in parallel. model-reviewer: structural correctness, type safety, invariants, anti-patterns. traceability-agent: RFC coverage check against the blueprint's target RFC. Aggregates findings. Gate checkpoint on critical issues.

**Phase 6 -- Wrap-up.** Summary of what was built. Returns to navigate (which will offer next steps based on updated context).

**Multi-session state:** The build-state file is written at Phase 2 and records the blueprint and design decisions. Actual progress (which layers are done) is inferred from the file system on session resume. Navigate reads this file for warm resume mode.

### review

Quality and coverage auditing with intent-based triage.

**Phase 1 -- Triage.** Detects review type from user intent: coverage-focused ("RFC gaps", "how much do I cover"), quality-focused ("review my model", "issues"), or both (ambiguous or explicit). Detects target protocol from workspace or asks.

**Phase 2 -- Execute.** Branches by review type:

- *Coverage path:* Dispatches traceability-agent. Extracts RFC requirements or reads existing manifest from build-state. Scans `.ivy` files for bracket-tag annotations. Reports coverage by priority (MUST/SHOULD/MAY), lists gaps.
- *Quality path:* Dispatches model-reviewer and spec-analyst in parallel. model-reviewer: 6-category structural audit. spec-analyst: verification readiness, include traces, layer coherence. Aggregates findings by severity.
- *Both:* Runs both paths in parallel, aggregates all findings.

**Phase 3 -- Findings.** Presents findings with severity classification. Gate checkpoint on critical issues. Offers: "Fix these issues now? Run verify on flagged files?"

**On completion:** Returns to navigate.

### triage

Stack health diagnostics and recovery. Also exported as a reusable preflight phase.

**Phase 1 -- Quick check (< 5 seconds).** Checks PID files for stale processes. Pings MCP server (ivy-tools). Pings Serena server. Checks LSP process. Branches: if everything alive, reports "stack is healthy" and redirects to the appropriate workflow. If something dead, moves to Phase 2.

**Phase 2 -- Diagnose.** Identifies what is dead (MCP, LSP, Serena, or combination). Checks logs for crash reason. Checks port conflicts. Presents diagnosis and offers restart.

**Phase 3 -- Fix.** Restarts dead services. Re-runs Phase 1 to confirm recovery. If still broken, escalates with full diagnostic dump.

**Preflight export:** Verify, build, and review silently call triage Phase 1 before their first MCP tool invocation. If preflight fails, the workflow redirects to triage automatically.

**On completion:** Returns to navigate.

### navigate

The central hub. Every workflow returns here on completion.

**Phase 1 -- Silent context scan.** Reads `.panther-ivy/build-state.yaml` (any active build?). Checks git log for recent `.ivy` changes. Reads session JSONL logs (last session activity). Runs triage preflight (is the stack healthy?).

**Branches by context:**

- *Warm resume (active build-state found):* Presents progress summary. "You're in the middle of building QUIC connection model. Phase 3, layer 3/4 done. Last session ended with a compile error on quic_serdes.ivy. Pick up there? Or do something else?" Dispatches to the appropriate workflow.
- *Activity summary (recent activity, no build-state):* Presents what happened last session. "Last session you ran verify on quic_frame.ivy (PASS) and reviewed coverage (72% of RFC 9000 MUST requirements). Biggest gaps: connection termination, flow control. Want to build those missing pieces? Review again?" Dispatches based on user choice.
- *Cold start (no context):* Interviews the user with 1-3 questions (protocol, goal, methodology). Dispatches to the appropriate workflow.

**Sub-workflow rule:** When a workflow is invoked by another workflow (e.g., build Phase 4 invokes verify), the called workflow returns to its caller, not to navigate. This is enforced via the `invocation_depth` and `caller` fields in the active-workflow flag file (see State Management). The calling workflow increments `invocation_depth` and sets `caller` before dispatching. The called workflow decrements on completion and reads `caller` to determine where to return.

**On completion:** Navigate does not return to itself. It dispatches to a workflow, which eventually returns to navigate, creating the guided session loop.

## Agents

Three internal agents. Never user-facing; dispatched by workflows.

### spec-analyst

Specification navigation and verification diagnostics. Dispatched by: verify (failure diagnosis), build (compile errors inline), review (verification readiness).

Traces include paths, reads error output, interprets counterexamples, classifies failure type (invariant violation, type error, structural issue).

Tools: Read, Grep, Glob, Bash, ToolSearch.

### model-reviewer

Adversarial model quality audits. Dispatched by: build (Phase 5 quality gate), review (quality audit).

Six-category checklist: structural correctness, type safety, invariant completeness, action well-formedness, initialization, organization. Detects anti-patterns.

Tools: Read, Grep, Glob, Bash, ToolSearch.

### traceability-agent

RFC requirement extraction and coverage auditing. Dispatched by: build (Phase 5 coverage check), review (coverage audit).

Extracts RFC requirements (MUST/SHOULD/MAY), scans bracket-tag annotations in `.ivy` files, generates coverage reports, identifies gaps by priority.

Tools: Bash, Read, Write, Glob, Grep, WebFetch, ToolSearch.

## Knowledge Skills

Seven internal knowledge skills. Consumed by agents and workflows; never user-triggered.

| Skill | Purpose | Consumed by |
|---|---|---|
| counterexample-guide | Trace interpretation on verification failure | verify (Phase 5), build (Phase 3 errors) |
| specification-patterns | Layer selection, pattern scaffolding templates | build (Phase 2 blueprint) |
| propagation-patterns | Type change impact analysis | build (Phase 3 propagation) |
| ivy-writing-guide | Ivy syntax, declarations, module system, RFC annotation | build (Phase 3), verify (test design) |
| ivy-toolkit | 22-tool catalog, parameter matrix, selection guide | All workflows needing MCP tool calls |
| claim-discussion | Structured decision trees for verification/coverage claims | review (Phase 3 findings) |
| methodology-reference | Merged NCT/NACT/NSCT methodology and workflow guidance | build (Phase 1), learning injection |

### Knowledge Loading Mechanism

When a workflow says it "pulls" a knowledge skill, the mechanism is **Skill tool invocation**. The workflow skill instructs the LLM to call the Skill tool with the knowledge skill name at the specific phase where that knowledge is needed. The knowledge skill content is then loaded into context for that phase only.

This approach was chosen over inline embedding (which would make workflow skills extremely large and waste context on phases that don't need the knowledge) and over pre-loading all knowledge at workflow start (which would consume context budget before it's needed).

**Example from build workflow Phase 2:** "Invoke the `specification-patterns` skill to load pattern templates. Use the loaded patterns to propose a layer structure for the target protocol."

Knowledge skills are never invoked by the user directly. Their descriptions in the skill registry should include "Internal knowledge skill" to prevent Claude Code's auto-triggering from surfacing them on user queries.

## Shortcut Commands

Four power-user commands that bypass workflows for direct tool access.

| Command | MCP Tool | Purpose |
|---|---|---|
| `/nct-check` | `ivy_verify` | Quick single-file verification |
| `/nct-compile` | `ivy_compile` | Quick compilation |
| `/nct-model-info` | `ivy_model_info` | Inspect model structure |
| `/nct-observability` | reads JSONL | Query session logs (always available, never suppressed by active workflows) |

## State Management

### Build State File

Path: `<protocol-directory>/.panther-ivy/build-state.yaml`

Written once at build Phase 2 when the blueprint is created. Contains the workflow name, protocol, methodology, layer plan with per-layer status, and key design decisions. Actual progress is inferred from the file system (which `.ivy` files exist, their compilation status). Navigate reads this file on session start for warm resume.

```yaml
workflow: build
protocol: quic-connection
methodology: nct
started: 2026-04-07
layers:
  frame_variants: { status: complete, file: quic_frame.ivy }
  serdes: { status: complete, file: quic_serdes.ivy }
  connection_monitor: { status: in_progress, file: quic_connection_monitor.ivy }
  handshake_monitor: { status: pending }
decisions:
  - "Using 14-layer NCT template, skipping entity layer (single-endpoint focus)"
  - "Frame variants based on RFC 9000 Section 17"
```

### Active Workflow Flag

Path: `<protocol-directory>/.panther-ivy/active-workflow`

YAML file written when a workflow starts, cleared when it returns to navigate at the top level. Hooks check this file to decide whether to suppress suggestions (workflow-aware hook behavior).

```yaml
workflow: verify
phase: 3
invocation_depth: 0
started: "2026-04-07T14:30:00Z"
caller: null
```

**Phase tracking.** Workflow skills update the `phase` field at each phase transition. This survives context compaction: when the LLM resumes after compaction, it reads the flag file to determine which phase it is in rather than relying on in-context memory. Each workflow skill begins with: "Read `.panther-ivy/active-workflow` to determine your current phase before proceeding."

**Invocation depth.** When a workflow is invoked by another workflow (e.g., build Phase 4 invokes verify), `invocation_depth` is incremented and `caller` records the invoking workflow. On completion: if `invocation_depth > 0`, decrement depth and return to `caller` (not to navigate). If `invocation_depth == 0`, clear the flag and return to navigate.

**Staleness cleanup.** The `SessionStart` hook checks the `started` timestamp. If the flag is older than 2 hours, it is treated as stale from an interrupted session: the hook clears the flag and logs a notice. Navigate then sees a cold or activity-summary start instead of a corrupt warm resume.

## Hook Architecture

### Routing Hooks

- **`UserPromptSubmit`** -- Reads prompt, matches against `routing-rules.json`, injects workflow activation directive. Falls through to LLM Tier 2 on no match.

### Safety Hooks (unchanged)

- **`PreToolUse[Write|Edit]`** -- `check-workspace-scope.py`. Blocks cross-protocol edits. Workflow-aware: suppresses if active workflow is handling scope.
- **`PreToolUse[Bash]`** -- `block-direct-ivy.sh`. Warns against direct CLI usage of `ivy_check`, `ivyc`, `ivy_show`.
- **`PreToolUse[mcp__.*ivy]`** -- MCP health check, LSP log check, indexing readiness check.

### Lifecycle Hooks (unchanged)

- **`SessionStart`** -- Cleanup stale PIDs, detect workspace, wait for indexing. Extended to inject workspace context for the CLAUDE.md dispatch table.
- **`SessionEnd`** -- Cleanup LSP.
- **`Stop`** -- Session summary.
- **Observability hooks** -- Trace execution events to JSONL (pre/post/failure).

### Workflow-Aware Behavior

The `PostToolUse[Write|Edit]` hook currently runs lint and suggests `/nct-review`. In the new architecture, it checks the active-workflow flag file. If a workflow is active, it suppresses the suggestion (the workflow handles lint errors inline). If no workflow is active, it suggests the relevant workflow.

## Migration Map

### Agents (5 to 3)

| Current | Fate |
|---|---|
| navigator | Eliminated -- becomes `navigate` workflow skill |
| spec-analyst | Kept -- internal agent |
| model-reviewer | Kept -- internal agent |
| methodology-guide | Eliminated -- becomes `methodology-reference` knowledge skill |
| traceability-agent | Kept -- internal agent |

### Skills (20 to 12)

| Current | Fate |
|---|---|
| ivy-workflow-orchestrator | Eliminated -- phase logic absorbed into `build` workflow |
| adaptive-interview | Eliminated -- absorbed into `navigate` workflow |
| healthcheck | Eliminated -- absorbed into `triage` workflow |
| incremental-spec-dev | Eliminated -- absorbed into `build` Phase 3 write loop |
| interaction-patterns | Eliminated -- checkpoint definitions inlined into each workflow |
| nct-methodology | Eliminated -- merged into `methodology-reference` knowledge skill |
| nact-methodology | Eliminated -- merged into `methodology-reference` knowledge skill |
| nsct-methodology | Eliminated -- merged into `methodology-reference` knowledge skill |
| workspace-management | Eliminated -- workspace management stays as hooks only |
| ivy-lsp-walkthrough | Eliminated -- reference example folded into ivy-toolkit or CLAUDE.md |
| lsp-patterns | Eliminated -- LSP usage patterns folded into ivy-toolkit |
| ivy-protocol-model-builder | Eliminated -- phased creation logic absorbed into `build` workflow |
| workflow-reference | Eliminated -- merged into `methodology-reference` knowledge skill |
| counterexample-guide | Kept -- knowledge skill |
| specification-patterns | Kept -- knowledge skill |
| propagation-patterns | Kept -- knowledge skill |
| ivy-writing-guide | Kept -- knowledge skill |
| ivy-toolkit | Kept -- knowledge skill |
| claim-discussion | Kept -- knowledge skill |
| methodology-reference | Kept -- absorbs 3 methodology skills, methodology-guide agent, workflow-reference |

### Commands (11 to 4)

| Current | Fate |
|---|---|
| /nct-check | Kept -- shortcut command |
| /nct-compile | Kept -- shortcut command |
| /nct-model-info | Kept -- shortcut command |
| /nct-observability | Kept -- shortcut command |
| /nct-health | Eliminated -- becomes `triage` workflow |
| /nct-review | Eliminated -- becomes `review` workflow |
| /nct-scaffold | Eliminated -- becomes `build` workflow |
| /nct-add-pattern | Eliminated -- absorbed into `build` workflow |
| /nct-propagate | Eliminated -- absorbed into `build` workflow |
| /nct-validate | Eliminated -- absorbed into `verify` workflow |
| /nct-serena-health | Eliminated -- absorbed into `triage` workflow |

### Hooks

All existing hooks kept. Added: `UserPromptSubmit` routing hook. Modified: `PostToolUse[Write|Edit]` becomes workflow-aware. New state files: `build-state.yaml`, `active-workflow` flag.

## Summary

| Category | Before | After |
|---|---|---|
| Agents | 5 | 3 (internal) |
| Skills | 20 | 12 (5 workflow + 7 knowledge) |
| Commands | 11 | 4 (shortcuts) |
| Hook event types | 12 | 13 (adds routing hook) |
| User-facing entry points | 36 | 9 (5 workflows + 4 commands) |
| Routing | None (ad hoc) | Two-tier (deterministic hook + LLM table) |
| State persistence | None | Build-state file + active-workflow flag |
| Workflow-aware hooks | No | Yes |
