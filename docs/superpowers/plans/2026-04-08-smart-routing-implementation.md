# Smart Routing Architecture -- Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the smart routing architecture from `docs/superpowers/specs/2026-04-07-smart-routing-architecture-design.md`, consolidating 36 user-facing components into 9 entry points (5 workflow skills + 4 shortcut commands) with two-tier routing.

**Prerequisite:** v0.8.0 (`docs/superpowers/plans/2026-04-07-panther-ivy-plugin-v0.8.0.md`) must be completed first. It provides: `hook_utils.py`, consolidated observability (`observe.py`), platform feature adoption (skill/agent frontmatter, `settings.json`).

**Tech Stack:** Bash, Python 3.10+, JSON, YAML, Markdown (Claude Code plugin system)

**Plugin root:** `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/`

Throughout this plan, all file paths are relative to the plugin root unless prefixed with a repository-level path.

---

## File Map

### Files to Create

| File | Responsibility | Phase |
|------|---------------|-------|
| `hooks/scripts/workflow_state.py` | Workflow state read/write utilities | 1 |
| `tests/test_workflow_state.py` | Tests for state utilities | 1 |
| `hooks/scripts/cleanup-stale-workflow.py` | SessionStart staleness cleanup | 1 |
| `routing-rules.json` | Routing config (keywords, patterns, triggers) | 2 |
| `hooks/scripts/route-user-prompt.py` | UserPromptSubmit routing hook | 2 |
| `tests/test_routing.py` | Routing tests | 2 |
| `skills/navigate/SKILL.md` | Navigate workflow (central hub) | 4 |
| `skills/triage/SKILL.md` | Triage workflow (stack diagnostics) | 4 |
| `skills/verify/SKILL.md` | Verify workflow (test-compile-execute) | 5 |
| `skills/build/SKILL.md` | Build workflow (protocol model construction) | 6 |
| `skills/review/SKILL.md` | Review workflow (quality and coverage audit) | 6 |
| `hooks/scripts/post-write-workflow-aware.py` | Workflow-aware PostToolUse | 7 |
| `tests/test_workflow_aware_hooks.py` | Tests for workflow-aware hooks | 7 |

### Files to Modify

| File | Phases | Changes |
|------|--------|---------|
| `hooks/hooks.json` | 1, 2, 7 | Add SessionStart cleanup, UserPromptSubmit routing, PostToolUse workflow-aware |
| `.gitignore` | 1 | Add `.panther-ivy/` |
| `skills/methodology-reference/SKILL.md` | 3 | Absorb 4 skills, mark internal |
| `skills/ivy-toolkit/SKILL.md` | 3 | Absorb LSP patterns, mark internal |
| 5 other knowledge skills | 3 | Mark internal, remove stale `loads:` |
| 13 deprecated skills | 3 | Mark deprecated |
| `agents/navigator.md` | 4, 9 | Transition note, then deprecate |
| `agents/spec-analyst.md` | 9 | Mark internal, update dispatch context |
| `agents/model-reviewer.md` | 9 | Mark internal, update dispatch context |
| `agents/traceability-agent.md` | 9 | Mark internal, update dispatch context |
| `agents/methodology-guide.md` | 9 | Deprecate |
| 4 kept commands | 8 | Add shortcut notes |
| 7 deprecated commands | 8 | Mark deprecated |
| `hooks/scripts/interaction-checkpoint.py` | 7 | Add workflow-awareness check |
| `CLAUDE.md` | 10 | Section rewrite for routing model |
| `agents/README.md` | 11 | Update catalog |
| `.claude-plugin/plugin.json` | 11 | Version bump |

### Files to Delete (Phase 11 only)

| Category | Count | Files |
|----------|-------|-------|
| Skills | 13 dirs | nct-methodology, nact-methodology, nsct-methodology, workflow-reference, lsp-patterns, ivy-lsp-walkthrough, workspace-management, interaction-patterns, adaptive-interview, incremental-spec-dev, ivy-workflow-orchestrator, ivy-protocol-model-builder, healthcheck |
| Commands | 7 files | nct-health, nct-review, nct-scaffold, nct-add-pattern, nct-propagate, nct-validate, nct-serena-health |
| Agents | 2 files | navigator, methodology-guide |

---

## Phase 1: State Management Foundation

**Goal:** Introduce the active-workflow flag and build-state infrastructure. No behavioral changes yet. Existing plugin continues to work identically.

**Why first:** Every subsequent phase depends on reading/writing the active-workflow flag.

### Task 1.1: Create workflow state utilities

- [ ] **Create `hooks/scripts/workflow_state.py`**

```python
"""Read/write utilities for workflow state files.

State files live at <protocol_dir>/.panther-ivy/ and track:
- active-workflow: which workflow is running, at which phase
- build-state.yaml: multi-session build progress
"""
import os
import yaml
from datetime import datetime, timezone, timedelta
from pathlib import Path


def find_protocol_dir() -> str | None:
    """Find the protocol directory from IVY_WORKSPACE_ROOT or cwd scan."""
    env_root = os.environ.get("IVY_WORKSPACE_ROOT")
    if env_root and os.path.isdir(env_root):
        return env_root
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        pt = parent / "protocol-testing"
        if pt.is_dir():
            return str(pt)
    return None


def _state_dir(protocol_dir: str) -> Path:
    return Path(protocol_dir) / ".panther-ivy"


def get_active_workflow(protocol_dir: str) -> dict | None:
    path = _state_dir(protocol_dir) / "active-workflow"
    if not path.exists():
        return None
    with open(path) as f:
        return yaml.safe_load(f)


def set_active_workflow(
    protocol_dir: str,
    workflow: str,
    phase: int,
    invocation_depth: int = 0,
    caller: str | None = None,
) -> None:
    d = _state_dir(protocol_dir)
    d.mkdir(parents=True, exist_ok=True)
    state = {
        "workflow": workflow,
        "phase": phase,
        "invocation_depth": invocation_depth,
        "started": datetime.now(timezone.utc).isoformat(),
        "caller": caller,
    }
    with open(d / "active-workflow", "w") as f:
        yaml.safe_dump(state, f)


def update_workflow_phase(protocol_dir: str, phase: int) -> None:
    state = get_active_workflow(protocol_dir)
    if state:
        state["phase"] = phase
        with open(_state_dir(protocol_dir) / "active-workflow", "w") as f:
            yaml.safe_dump(state, f)


def clear_active_workflow(protocol_dir: str) -> None:
    path = _state_dir(protocol_dir) / "active-workflow"
    if path.exists():
        path.unlink()


def is_workflow_stale(protocol_dir: str, max_age_hours: int = 2) -> bool:
    state = get_active_workflow(protocol_dir)
    if not state or "started" not in state:
        return False
    started = datetime.fromisoformat(state["started"])
    return datetime.now(timezone.utc) - started > timedelta(hours=max_age_hours)


def get_build_state(protocol_dir: str) -> dict | None:
    path = _state_dir(protocol_dir) / "build-state.yaml"
    if not path.exists():
        return None
    with open(path) as f:
        return yaml.safe_load(f)


def set_build_state(protocol_dir: str, state_dict: dict) -> None:
    d = _state_dir(protocol_dir)
    d.mkdir(parents=True, exist_ok=True)
    with open(d / "build-state.yaml", "w") as f:
        yaml.safe_dump(state_dict, f)
```

### Task 1.2: Create tests for workflow state

- [ ] **Create `tests/test_workflow_state.py`**

Tests to write:
- `test_set_and_get_active_workflow` -- Write, read, verify all fields
- `test_update_phase` -- Set workflow, update phase, verify only phase changed
- `test_clear_active_workflow` -- Set, clear, verify returns None
- `test_is_workflow_stale` -- Set with old timestamp, verify stale detection
- `test_missing_dir_returns_none` -- get returns None when dir doesn't exist
- `test_build_state_roundtrip` -- Write and read build-state

### Task 1.3: Create SessionStart staleness cleanup

- [ ] **Create `hooks/scripts/cleanup-stale-workflow.py`**

```python
#!/usr/bin/env python3
"""SessionStart hook: clear stale active-workflow flags from interrupted sessions."""
import json
import sys
import os

sys.path.insert(0, os.path.join(os.environ.get("CLAUDE_PLUGIN_ROOT", "."), "hooks", "scripts"))
from workflow_state import find_protocol_dir, get_active_workflow, is_workflow_stale, clear_active_workflow

def main():
    protocol_dir = find_protocol_dir()
    if not protocol_dir:
        return

    state = get_active_workflow(protocol_dir)
    if not state:
        return

    if is_workflow_stale(protocol_dir):
        clear_active_workflow(protocol_dir)
        result = {
            "hookSpecificOutput": {
                "additionalContext": (
                    f"Cleared stale workflow flag ('{state['workflow']}' phase {state['phase']}, "
                    f"started {state['started']}). The previous session was interrupted."
                )
            }
        }
    else:
        result = {
            "hookSpecificOutput": {
                "additionalContext": (
                    f"Active workflow detected: '{state['workflow']}' at phase {state['phase']}. "
                    f"Use the navigate workflow to resume or switch."
                )
            }
        }
    print(json.dumps(result))

if __name__ == "__main__":
    main()
```

- [ ] **Register in `hooks/hooks.json`**

Add to the `SessionStart` array, after `cleanup-stale-pids.sh`:

```json
{
  "hooks": [
    {
      "type": "command",
      "command": "python3 ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/cleanup-stale-workflow.py",
      "timeout": 5
    }
  ]
}
```

### Task 1.4: Add `.panther-ivy/` to `.gitignore`

- [ ] **Append to `.gitignore`:** `**/.panther-ivy/`

### Verification

- [ ] `python -m pytest tests/test_workflow_state.py -v` -- all pass
- [ ] Existing tests still pass
- [ ] New Claude Code session starts without error

---

## Phase 2: Routing Infrastructure

**Goal:** Introduce `routing-rules.json` and the `UserPromptSubmit` routing hook. The hook injects routing suggestions into context. Since workflow skills don't exist yet, the suggestions are advisory only.

### Task 2.1: Create routing rules config

- [ ] **Create `routing-rules.json`** at plugin root with content from the design spec (lines 35-74 of the spec).

### Task 2.2: Create routing hook

- [ ] **Create `hooks/scripts/route-user-prompt.py`**

Logic:
1. Read stdin JSON for `prompt` field
2. Load `routing-rules.json` from `CLAUDE_PLUGIN_ROOT`
3. Match prompt against each workflow's `keywords` (case-insensitive substring), `intentPatterns` (regex), `fileTriggers` (extension match on file paths in prompt)
4. Score: intentPattern > keyword. Apply priority: critical > high > medium > low
5. Read active-workflow flag. If workflow active, suppress routing unless prompt contains switch keywords ("switch to", "cancel", "stop this", "something else")
6. Output `additionalContext` with `[ROUTING]` directive for matched workflow, or nothing for no match
7. Check `learning_injection` separately; output `[ROUTING:KNOWLEDGE]` for knowledge skill loading

- [ ] **Register in `hooks/hooks.json`**

Add to `UserPromptSubmit` array, before the observability hook:

```json
{
  "hooks": [
    {
      "type": "command",
      "command": "python3 ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/route-user-prompt.py",
      "timeout": 5
    }
  ]
}
```

### Task 2.3: Create routing tests

- [ ] **Create `tests/test_routing.py`**

Tests: keyword match, intent pattern match, priority resolution, no-match fallthrough, learning injection, active-workflow suppression, explicit-switch override, file-trigger matching.

### Verification

- [ ] `python -m pytest tests/test_routing.py -v` -- all pass
- [ ] Existing tests still pass
- [ ] In Claude Code session, "check my spec" produces `[ROUTING]` in context

---

## Phase 3: Knowledge Skills Consolidation

**Goal:** Transform 7 knowledge skills to internal form. Absorb content from eliminated skills. Mark 13 skills as deprecated. No deletions yet.

### Task 3.1: Absorb content into methodology-reference

- [ ] **Modify `skills/methodology-reference/SKILL.md`:**
  - Description: `"Internal knowledge skill -- merged NCT/NACT/NSCT methodology and workflow guidance. Do not invoke directly; loaded by workflows."`
  - Remove `loads:` references to individual methodology skills
  - Absorb core content from `nct-methodology`, `nact-methodology`, `nsct-methodology`, `workflow-reference`

### Task 3.2: Absorb content into ivy-toolkit

- [ ] **Modify `skills/ivy-toolkit/SKILL.md`:**
  - Description: `"Internal knowledge skill -- 22-tool catalog, parameter matrix, selection guide, LSP patterns. Do not invoke directly; loaded by workflows."`
  - Absorb LSP patterns from `lsp-patterns` and walkthrough from `ivy-lsp-walkthrough`
  - Remove `loads:` references

### Task 3.3: Mark remaining knowledge skills as internal

- [ ] Update descriptions for: `counterexample-guide`, `specification-patterns`, `propagation-patterns`, `ivy-writing-guide`, `claim-discussion`
  - Each gets: `"Internal knowledge skill -- {purpose}. Do not invoke directly; loaded by {which workflows}."`
  - Remove stale `loads:` fields

### Task 3.4: Mark 13 eliminated skills as deprecated

- [ ] For each: change description to `"DEPRECATED -- absorbed into {target}. Will be removed in a future version."`
  - nct-methodology, nact-methodology, nsct-methodology, workflow-reference -> methodology-reference
  - lsp-patterns, ivy-lsp-walkthrough -> ivy-toolkit
  - workspace-management -> hooks only
  - interaction-patterns -> workflow skills (inlined)
  - adaptive-interview -> navigate workflow
  - incremental-spec-dev -> build workflow Phase 3
  - ivy-workflow-orchestrator -> workflow skills
  - ivy-protocol-model-builder -> build workflow
  - healthcheck -> triage workflow

### Verification

- [ ] All tests pass
- [ ] Deprecated skills visible but steered away from by description

---

## Phase 4: Navigate and Triage Workflows

**Goal:** Create the navigate (hub) and triage (diagnostics) workflow skills. These can function independently.

### Task 4.1: Create navigate workflow

- [ ] **Create `skills/navigate/SKILL.md`**

Content structure:
1. Opening: "Read `.panther-ivy/active-workflow` on every turn to determine current phase."
2. Phase 1 -- Silent context scan: read build-state.yaml, check git log, read JSONL logs, run triage preflight
3. Three branches: warm resume (build-state found), activity summary (recent changes), cold start (interview)
4. Dispatch: set active-workflow flag, invoke chosen workflow via Skill tool
5. Sub-workflow return rule using invocation_depth

### Task 4.2: Create triage workflow

- [ ] **Create `skills/triage/SKILL.md`**

Content structure:
1. Phase 1 -- Quick check: PID files, MCP ping, Serena ping, LSP check. If healthy, redirect.
2. Phase 2 -- Diagnose: identify dead components, check logs, check ports
3. Phase 3 -- Fix: restart, re-check, escalate if still broken
4. Preflight export: when invocation_depth > 0, only Phase 1, return without user interaction

### Task 4.3: Add transition note to navigator agent

- [ ] **Modify `agents/navigator.md`:** Add note at top: "NOTE: The `navigate` workflow skill is now the preferred entry point. This agent is retained during transition."

### Verification

- [ ] "what should I do next?" routes to navigate
- [ ] "MCP won't connect" routes to triage
- [ ] Active-workflow flag correctly written and read
- [ ] All tests pass

---

## Phase 5: Verify Workflow

**Goal:** Create the verify workflow -- the most commonly used workflow.

### Task 5.1: Create verify workflow

- [ ] **Create `skills/verify/SKILL.md`**

Content (6 phases):
1. Preflight: triage Phase 1 as sub-workflow. Detect protocol.
2. Test Selection: scan specs, present options. Gate checkpoint.
3. Compile: `ivy_compile`. On error, dispatch spec-analyst. Loop.
4. Execute: `ivy_verify`. PASS -> report + offer follow-ups. FAIL -> Phase 5.
5. Diagnose: load counterexample-guide. Dispatch spec-analyst. Classify failure. Gate.
6. Fix (optional): apply fix, loop to Phase 3.

### Verification

- [ ] "verify my QUIC handshake spec" activates verify workflow
- [ ] Phase tracking persists through phases 1-6
- [ ] Compile error flow dispatches spec-analyst agent
- [ ] All tests pass

---

## Phase 6: Build and Review Workflows

**Goal:** Create the remaining two workflows.

### Task 6.1: Create build workflow

- [ ] **Create `skills/build/SKILL.md`**

Content (6 phases):
1. Scope: detect methodology, load methodology-reference. Gate.
2. Blueprint: load specification-patterns, propose layers. Gate. Write build-state.yaml.
3. Write: load ivy-writing-guide, generate layer by layer, compile check after each.
4. Verify: invoke verify as sub-workflow (invocation_depth+1, caller=build).
5. Quality Gate: dispatch model-reviewer + traceability-agent. Gate on critical.
6. Wrap-up: summary, clear flag, return to navigate.

### Task 6.2: Create review workflow

- [ ] **Create `skills/review/SKILL.md`**

Content (3 phases):
1. Triage: detect review type (coverage/quality/both), detect protocol.
2. Execute: branch by type. Coverage -> traceability-agent. Quality -> model-reviewer + spec-analyst.
3. Findings: present with severity. Gate on critical. Offer fix or verify.

### Verification

- [ ] "build a QUIC connection model" routes to build
- [ ] "RFC coverage?" routes to review
- [ ] Build Phase 4 correctly invokes verify as sub-workflow (returns to build, not navigate)
- [ ] build-state.yaml written at Phase 2, readable by navigate for warm resume
- [ ] All tests pass

---

## Phase 7: Workflow-Aware Hook Modifications

**Goal:** Existing hooks become workflow-aware: suppress suggestions during active workflows.

### Task 7.1: Create workflow-aware PostToolUse script

- [ ] **Create `hooks/scripts/post-write-workflow-aware.py`**

Logic: read stdin, check if .ivy file, read active-workflow flag. If active: suppress. If not: output suggestion to consider review workflow or `ivy_diagnostics`.

- [ ] **Modify `hooks/hooks.json`:** Replace the `PostToolUse` `Write|Edit` prompt hook with:

```json
{
  "matcher": "Write|Edit",
  "hooks": [
    {
      "type": "command",
      "command": "python3 ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/post-write-workflow-aware.py",
      "timeout": 5
    }
  ]
}
```

### Task 7.2: Make interaction-checkpoint workflow-aware

- [ ] **Modify `hooks/scripts/interaction-checkpoint.py`:** Import `workflow_state`, check flag at top of `main()`. If workflow active, exit silently.

### Task 7.3: Tests

- [ ] **Create `tests/test_workflow_aware_hooks.py`** with suppression/non-suppression test cases.

### Verification

- [ ] With active workflow, .ivy edit produces no suggestion
- [ ] Without workflow, .ivy edit produces suggestion
- [ ] All tests pass

---

## Phase 8: Command Cleanup

**Goal:** Update 4 kept commands with shortcut notes. Mark 7 eliminated commands as deprecated.

### Task 8.1: Update kept commands

- [ ] `commands/nct-check.md` -- Add: "Shortcut command -- directly calls `ivy_verify`. For guided verification, use the `verify` workflow."
- [ ] `commands/nct-compile.md` -- Add similar shortcut note.
- [ ] `commands/nct-model-info.md` -- Add similar shortcut note.
- [ ] `commands/nct-observability.md` -- Add: "Shortcut command -- always available, never suppressed by active workflows."

### Task 8.2: Mark eliminated commands as deprecated

- [ ] For each of: nct-health, nct-review, nct-scaffold, nct-add-pattern, nct-propagate, nct-validate, nct-serena-health
  - Description: `"DEPRECATED: Use the {target} workflow instead. This command will be removed."`

### Verification

- [ ] `/nct-check` works with shortcut note
- [ ] `/nct-health` shows deprecation notice
- [ ] All tests pass

---

## Phase 9: Agent Adjustments

**Goal:** Mark 3 kept agents as internal. Deprecate 2 eliminated agents.

### Task 9.1: Update kept agents

- [ ] `agents/spec-analyst.md` -- Description: `"Internal agent -- dispatched by verify, build, review workflows. Not user-facing."`
- [ ] `agents/model-reviewer.md` -- Description: `"Internal agent -- dispatched by build and review workflows. Not user-facing."`
- [ ] `agents/traceability-agent.md` -- Description: `"Internal agent -- dispatched by build and review workflows. Not user-facing."`

### Task 9.2: Deprecate eliminated agents

- [ ] `agents/navigator.md` -- `"DEPRECATED: Use the navigate workflow skill instead."`
- [ ] `agents/methodology-guide.md` -- `"DEPRECATED: Content moved to methodology-reference knowledge skill."`

### Verification

- [ ] LLM no longer auto-dispatches deprecated agents
- [ ] Internal agents still dispatchable by workflow skills
- [ ] All tests pass

---

## Phase 10: CLAUDE.md Rewrite

**Goal:** Update the LLM operating guide to reflect the new architecture. Done last because all components must be in place.

### Task 10.1: Rewrite CLAUDE.md sections

- [ ] **Add "Workflow Routing" section** (after Mindset, before Tool Rules): Dispatch table from design spec. Five-row intent-to-workflow table. Rules: check active-workflow flag, shortcuts bypass workflows, learning questions use knowledge skills.

- [ ] **Add "State Management" section**: active-workflow flag format, build-state.yaml, "read `.panther-ivy/active-workflow` on every turn."

- [ ] **Replace "Available Skills" / "Available Agents" / "Commands" listings** with:
  - "Available Workflows": navigate, verify, build, review, triage
  - "Shortcut Commands": nct-check, nct-compile, nct-model-info, nct-observability
  - "Internal Components": 3 agents + 7 knowledge skills (do not invoke directly)

- [ ] **Update Quick Reference**:

```
**Workflows**: navigate, verify, build, review, triage
**Shortcuts**: /nct-check, /nct-compile, /nct-model-info, /nct-observability
**Internal agents**: spec-analyst, model-reviewer, traceability-agent
**Internal knowledge**: counterexample-guide, specification-patterns, propagation-patterns, ivy-writing-guide, ivy-toolkit, claim-discussion, methodology-reference
```

### Verification

- [ ] Fresh session reads new CLAUDE.md, understands routing model
- [ ] "check my spec" activates verify workflow end-to-end
- [ ] "how does NCT work?" answered from knowledge, no workflow
- [ ] All tests pass

---

## Phase 11: Delete Deprecated Components

**Goal:** Remove all deprecated components. Final phase.

### Task 11.1: Delete deprecated skills (13 directories)

- [ ] Delete: `skills/nct-methodology/`, `skills/nact-methodology/`, `skills/nsct-methodology/`, `skills/workflow-reference/`, `skills/lsp-patterns/`, `skills/ivy-lsp-walkthrough/`, `skills/workspace-management/`, `skills/interaction-patterns/`, `skills/adaptive-interview/`, `skills/incremental-spec-dev/`, `skills/ivy-workflow-orchestrator/`, `skills/ivy-protocol-model-builder/`, `skills/healthcheck/`

### Task 11.2: Delete deprecated commands (7 files)

- [ ] Delete: `commands/nct-health.md`, `commands/nct-review.md`, `commands/nct-scaffold.md`, `commands/nct-add-pattern.md`, `commands/nct-propagate.md`, `commands/nct-validate.md`, `commands/nct-serena-health.md`

### Task 11.3: Delete deprecated agents (2 files)

- [ ] Delete: `agents/navigator.md`, `agents/methodology-guide.md`

### Task 11.4: Update catalogs

- [ ] `agents/README.md` -- Remove deleted entries, note internal-only
- [ ] Update or create `skills/README.md` -- "Workflow Skills" (5) + "Knowledge Skills" (7) sections

### Task 11.5: Version bump

- [ ] `.claude-plugin/plugin.json` -- Version to `0.9.0`

### Task 11.6: Update test expectations

- [ ] `tests/test_documentation.py` -- Remove expectations for deleted components, add for new ones

### Verification

- [ ] `python -m pytest tests/ -v` -- all pass
- [ ] Fresh session: 5 workflows, 4 commands, 3 agents, 7 knowledge skills
- [ ] End-to-end: natural language -> routing hook -> workflow -> agents -> navigate return
- [ ] Build-state warm resume across sessions
- [ ] Stale flag cleanup on SessionStart

---

## Phase Ordering

```
Phase 1 (State Management)
  |
Phase 2 (Routing Infrastructure)
  |
Phase 3 (Knowledge Skills Consolidation)
  |
Phase 4 (Navigate + Triage)  -- needs state, routing, knowledge
  |
Phase 5 (Verify)  -- needs triage preflight
  |
Phase 6 (Build + Review)  -- needs verify sub-workflow
  |
  +-- Phase 7 (Workflow-aware hooks) --+
  +-- Phase 8 (Command cleanup)       +-- all independent, any order
  +-- Phase 9 (Agent adjustments)     +
  |
Phase 10 (CLAUDE.md rewrite)  -- needs everything above
  |
Phase 11 (Delete deprecated)  -- needs CLAUDE.md updated
```

Phases 7, 8, 9 are independent and can run in parallel.

---

## Commit Strategy

Each phase produces one commit:

1. `feat(ivy-plugin): add workflow state management infrastructure`
2. `feat(ivy-plugin): add two-tier routing (rules config + UserPromptSubmit hook)`
3. `refactor(ivy-plugin): consolidate knowledge skills, deprecate 13 eliminated skills`
4. `feat(ivy-plugin): add navigate and triage workflow skills`
5. `feat(ivy-plugin): add verify workflow skill`
6. `feat(ivy-plugin): add build and review workflow skills`
7. `feat(ivy-plugin): make hooks workflow-aware`
8. `refactor(ivy-plugin): update shortcut commands, deprecate eliminated commands`
9. `refactor(ivy-plugin): update agents (internal + deprecated)`
10. `docs(ivy-plugin): rewrite CLAUDE.md for routing architecture`
11. `chore(ivy-plugin): delete deprecated skills, commands, agents; bump to v0.9.0`
