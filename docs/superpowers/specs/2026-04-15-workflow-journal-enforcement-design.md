# Workflow Journal Enforcement Design

**Date:** 2026-04-15
**Status:** Draft
**Scope:** panther-ivy-plugin workflow state system

## Problem

The `ivy_workflow_state` MCP tool currently tracks active workflow phase and build state, but only updates at workflow start (via PostToolUse hook) and at explicit phase transitions inside skills. Six categories of lifecycle events go unrecorded:

1. **Intermediate decisions** — design/implementation choices made mid-workflow
2. **Session end** — whether a session ended cleanly or was interrupted
3. **Session pause/resume** — detecting interrupted vs. intentionally paused sessions
4. **Phase sub-steps** — finer-grained progress within a phase
5. **Error/blocker events** — failures or blockers encountered mid-workflow
6. **Context switches** — when the user shifts focus away from the active workflow

This degrades warm-resume quality (navigate skill lacks context), causes stale build-state (tracks marked `in_progress` indefinitely), and loses decision rationale across sessions.

## Approach

**Hybrid enforcement** using the existing two-tier architecture:
- **Hooks** handle mechanical events (session lifecycle, phase transitions, errors) automatically via the local Python API
- **Skills** handle semantic events (decisions, progress, context switches) where Claude's reasoning context is needed

State is recorded in a new **append-only journal file**, separate from the existing `active-workflow` and `build-state.yaml` files.

## Design

### 1. Journal File Format & Storage

**File:** `.panther-ivy/workflow-journal.yaml` (per protocol directory)

**Event schema:**

```yaml
- ts: "2026-04-14T15:28:00Z"    # ISO 8601 UTC
  type: <event_type>             # one of the types below
  workflow: "build"              # current workflow name
  phase: "blueprint-done"       # current phase at time of event
  payload: {}                   # type-specific data
```

**Event types and payloads:**

| Type | Payload | Source |
|------|---------|--------|
| `session_start` | `{resumed_from: <phase or null>}` | Hook (SessionStart) |
| `session_end` | `{clean: bool, phase_at_exit: str}` | Hook (Stop) |
| `decision` | `{summary: str, context: str or null}` | Skill (Claude writes) |
| `phase_transition` | `{from: str, to: str}` | Hook (PostToolUse on set action) |
| `progress` | `{detail: str}` | Skill (Claude writes) |
| `error` | `{summary: str, recoverable: bool}` | Hybrid |
| `context_switch` | `{away_from: str, reason: str or null}` | Skill (Claude detects) |

**Rotation:** When journal exceeds 200 entries, the oldest half is archived to `.panther-ivy/journal-archive/YYYY-MM-DD.yaml`. Navigate reads only the current journal (last ~100 entries) for warm-resume.

### 2. MCP Tool Extensions

Two new actions added to `ivy_workflow_state`:

| Action | Parameters | Behavior |
|--------|-----------|----------|
| `append_journal` | `protocol`, `type`, `payload` (JSON string) | Appends one event to journal. Auto-fills `ts`, `workflow`, `phase` from current active-workflow. |
| `get_journal` | `protocol`, `last_n` (int, default 20) | Returns the last N journal entries. |

Validation: `append_journal` rejects if `type` is not in the allowed set. If no active workflow exists, it still appends (to capture `session_start` events before workflow activation).

### 3. Hook Enforcement (Automatic Events)

**3a. SessionStart hook** (extend `cleanup-stale-workflow.py`)
- After staleness check, append `session_start` event with `resumed_from: <phase>` if a workflow was active, or `null` if starting fresh.

**3b. Stop hook** (new: `record-session-end.py`)
- Fires when Claude's turn ends. Reads active-workflow; if a workflow is active, appends `session_end` with `clean: true` and `phase_at_exit`. No-ops if no workflow is active.

**3c. PostToolUse hook** (extend `track-workflow-skill.py`)
- When `ivy_workflow_state(action="set")` is intercepted, append `phase_transition` event with `from`/`to` phases.

**3d. PostToolUse hook for errors** (new: `record-workflow-error.py`)
- When tool results contain error indicators (non-zero exit, compilation failures, verification failures) during an active workflow, append `error` event with `summary` extracted from the output and `recoverable: true`.
- Skills can later enrich with more context via `append_journal(type="error", ...)`.

### 4. Skill Enforcement (Semantic Events)

**4a. Decisions** — Each workflow skill (build, verify, review, triage) gets an instruction block:

> When you make or confirm a design/implementation choice, immediately call `ivy_workflow_state(action="append_journal", type="decision", payload={"summary": "<what>", "context": "<why>"})`.

**4b. Progress** — For long-running phases:

> After completing a meaningful sub-step within a phase, call `append_journal(type="progress", payload={"detail": "<what completed>"})`.

**4c. Context switches** — Extend `route-user-prompt.py` to append `context_switch` when user prompt doesn't match active workflow. Skills also instruct Claude to record context switches when detected.

### 5. Navigate Integration (Warm Resume)

Extend navigate's warm-resume branch (Branch A) to call `get_journal(last_n=20)` and present a session context summary:

> "Last session (2026-04-14, 45min): reached phase `blueprint-done`. 3 decisions recorded: [Group D deferred, implementation order B→E→C→A, peer_type configurable]. Ended cleanly. No errors or blockers."

Navigate uses journal data to:
1. **Skip redundant questions** — recorded decisions aren't re-asked
2. **Surface unfinished work** — highlight in-progress items from last session
3. **Flag errors** — present recent `error` events upfront
4. **Detect interrupted sessions** — no `session_end` for last `session_start` = crash/timeout

### 6. Summary Audit (End-of-Session Quality Gate)

Extend `render-summary.py` with a lightweight audit:

1. **Decision gap** — build-state modified but no `decision` events journaled → warning
2. **Phase gap** — phase changed but no `phase_transition` event → warning
3. **Missing session_end** — detected on next SessionStart, flagged as interrupted

Warnings only, not blocking errors. Surfaces gaps without frustrating the user.

## Files to Create or Modify

### New files:
- `hooks/scripts/record_session_end.py` — Stop hook for session_end events
- `hooks/scripts/record_workflow_error.py` — PostToolUse hook for error events

### Modified files:
- `ivy_lsp/mcp/tools/workflow_state.py` — add `append_journal` and `get_journal` actions
- `hooks/scripts/workflow_state.py` — add `append_journal_event()`, `get_journal_entries()`, `rotate_journal()` helper functions
- `hooks/scripts/cleanup-stale-workflow.py` — append `session_start` event
- `hooks/scripts/track-workflow-skill.py` — append `phase_transition` event
- `hooks/scripts/render-summary.py` — add journal audit checks
- `hooks/scripts/route-user-prompt.py` — append `context_switch` event
- `skills/navigate/SKILL.md` — read journal for warm-resume context
- `skills/build/SKILL.md` — add decision/progress journaling instructions
- `skills/verify/SKILL.md` — add decision/progress journaling instructions
- `skills/review/SKILL.md` — add decision/progress journaling instructions
- `skills/triage/SKILL.md` — add decision/progress journaling instructions
- `tests/test_workflow_state.py` — add journal tests

## Out of Scope

- Changing the existing `active-workflow` or `build-state.yaml` schemas
- Cross-protocol journal aggregation
- UI/dashboard for journal visualization
- Journal encryption or access control
