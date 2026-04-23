# Design — panther-ivy-plugin Workflow State-Model Refactor

Status: proposed
Author: workflow-audit follow-up (cluster-1 grilling session)
Date: 2026-04-23
Scope: refactor the sub-workflow invocation model; close audit findings in clusters 1, 2, 3, 4, and part of 5.

## Context

The audit at `2026-04-23-workflow-audit-results` (produced in this session, not yet written to disk) surfaced 46 findings across the 5 user-facing workflow skills in `panther-ivy-plugin`. One Critical finding — the contradiction between README Rule #4 and the Sub-workflow Protocol block in the same README — is load-bearing: its resolution determines the state-machine semantics for every workflow's completion, which in turn determines the shape of five more findings (clusters 2 and 4 in the audit's taxonomy).

This spec commits to the simpler of the two resolutions: make Rule #37 (every workflow returns to navigate on completion) canonical, eliminate the caller-chain (`invocation_depth` + `caller` fields), and introduce a `pending_dispatch` journal event to drive multi-workflow composition. Navigate processes pending_dispatch entries same-turn, re-entering itself transparently so multi-workflow chains (e.g., `build → verify → review`) remain a single user-observable interaction.

The refactor is intentionally big-bang: one coordinated edit across ~15 files eliminates the dual-mode risk of a phased migration. A bundled change to `build/SKILL.md` also adds the missing Phase 0 plan-mode preamble (closing audit cluster 3 incidentally).

## Decisions

1. **Rule #37 is canonical.** Every workflow returns to navigate on completion. The phrase "decrement and return to caller — not to navigate" is removed from README.md; the Sub-workflow Protocol section is rewritten in terms of pending_dispatch.
2. **Caller-chain is eliminated.** `invocation_depth` and `caller` are removed from the `active-workflow` YAML schema. The schema reduces from 5 fields to 3: `workflow`, `phase`, `started`.
3. **Workflows compose via a new journal event.** `event_type: pending_dispatch` with payload `{workflow: <name>, phase_hint: <string, optional>, reason: <string>}`. Workflows signal "run X next" by appending this event before clearing their own active-workflow flag.
4. **Navigate processes pending_dispatch same-turn.** Phase 1 Step 2b is extended to detect a `pending_dispatch` with no subsequent `workflow_resumed` (the existing journal convention). When found, navigate advances directly to Dispatch and calls `Skill(skill=<next>)` within the same turn. The invariant at navigate:63 ("never returns to itself") is rewritten: navigate re-enters itself same-turn only via an explicit pending_dispatch — the self-reentry is bounded and visible in the journal.
5. **Journal is the data-passing bus.** Re-activated workflows read recent `gate_verdict`, `progress`, and `decision` events to learn prior outcomes. No data is carried in the pending_dispatch payload beyond `phase_hint` and `reason`.
6. **Migration is big-bang.** One coordinated edit across the files below. No dual-mode flag; no phased deprecation.
7. **Build gets Phase 0 plan-mode preamble** (bundled fix for audit cluster 3) since `build/SKILL.md` is already being rewritten.

## Transitive audit closures

The refactor closes, beyond its stated cluster-1 scope:

- Cluster 2 (exit-side decrement is prose, 4 findings) — no decrement exists; every `On Completion` becomes one sentence (clear flag).
- Cluster 4 (build→verify→IUT gap, 1 Critical) — verify no longer detects "I am a sub-workflow". Phase 5 (IUT testing) runs unconditionally whenever verify reaches Phase 4 PASS, including in chains reached via pending_dispatch from build.
- Cluster 5 item "navigate:111 `navigate/init` schema mismatch" — fixed incidentally in the navigate rewrite.
- Cluster 3 (build missing Phase 0) — bundled per decision #7.

Remaining audit findings that are *not* closed by this refactor (still to be addressed in later clusters):

- Cluster 5 items "Task 3" and "defined later in this skill" references — fixed incidentally in navigate rewrite but listed separately here because they're independent writes.
- Cluster 6 (severity taxonomy drift) — independent; next grill.
- Cluster 7 (iteration counters untracked) — independent.
- Cluster 8 (G2/G3 scope gap) — independent; requires hook edits.
- Cluster 9 (NACT/NSCT workflow specialization) — independent; requires build Phase 2 changes.
- Cluster 10 (agent-dispatch failure handling) — independent; requires agent file edits.
- Cluster 11 (convention drift) — independent.
- Cluster 12 (tool-level robustness) — partially related (see Risks below, item "pending_dispatch crash recovery").

## Architecture

### State-file schema (before → after)

Before (`<protocol-dir>/.panther-ivy/active-workflow`):
```yaml
workflow: verify
phase: compile
invocation_depth: 0
started: "2026-04-07T14:30:00Z"
caller: null
```

After:
```yaml
workflow: verify
phase: compile
started: "2026-04-07T14:30:00Z"
```

### Journal event — new type

Schema for `pending_dispatch`:
```json
{
  "event_type": "pending_dispatch",
  "timestamp": "2026-04-23T09:15:00Z",
  "payload": {
    "workflow": "verify",
    "phase_hint": "preflight",
    "reason": "build phase 4 requires verification"
  }
}
```

Lifecycle:
1. A workflow emits `pending_dispatch` immediately before clearing `active-workflow`.
2. Navigate's Phase 1 Step 2c (new) scans journal for most recent `pending_dispatch` with no subsequent `workflow_resumed` naming the same target.
3. On dispatch, navigate writes `workflow_resumed` naming the target to mark consumption. This is the idempotency marker.
4. Navigate then writes `active-workflow` with `workflow=<target>, phase=<phase_hint or "init">` and calls `Skill(skill=<target>)`.

### Phase 1 Step 2c (new, navigate)

```
2c. Check journal for a pending_dispatch without a subsequent workflow_resumed
    entry naming the same target. If found:
    - Append workflow_resumed{workflow=<target>} to mark consumption.
    - Skip Branch A/B/C; proceed directly to Dispatch section.
    - Dispatch section sets active-workflow and invokes Skill(skill=<target>).
```

### On Completion pattern (all 4 non-navigate workflows)

Before:
```
If invocation_depth > 0: decrement depth, restore caller as active workflow.
If invocation_depth == 0: clear active-workflow flag.
```

After:
```
If this workflow needs another workflow to run next:
    - Append pending_dispatch{workflow=<next>, phase_hint=<phase>, reason=<why>}.
Clear active-workflow flag via ivy_workflow_state(action="clear", protocol=...).
```

## File change inventory (~15 files)

| File | Change |
|---|---|
| `README.md` | State Management section: update YAML example to drop `invocation_depth: 0` and `caller: null`. Delete Sub-workflow Protocol paragraph; replace with one sentence referencing `pending_dispatch` events. Rule #37 phrasing retained but becomes unqualified (no longer contradicted by a rule below it). |
| `hooks/scripts/workflow_state.py` | ActiveWorkflow dataclass: remove `invocation_depth: int` and `caller: str \| None` fields. `set_active_workflow()` signature: remove those two keyword params. Add `append_pending_dispatch(protocol_dir, target_workflow, phase_hint=None, reason=None)` helper. Update JournalEvent type union to include `pending_dispatch`. |
| `hooks/scripts/track-workflow-skill.py` | Rewrite to simple pattern: every Skill invocation that names a known workflow overwrites active-workflow with `{workflow=<new>, phase=init, started=now()}`. Delete the three branches (same-workflow no-op, different-workflow-nested increment, different-workflow-stale fresh start). Keep the fcntl.flock for concurrent safety. |
| `hooks/scripts/cleanup-stale-workflow.py` | Minor: staleness still judged by `started` timestamp; no depth/caller considerations to remove. File may need no edit; audit to confirm. |
| `hooks/scripts/route-user-prompt.py` | Minor: no structural change. The G1 gate emission at line 186 already keys only on `workflow == "build"` and `phase == "blueprint-done"` — both fields persist. |
| `skills/reflection-patterns/SKILL.md` | Pattern A (Reflection Gate) line 20: delete "Skip check: If `invocation_depth > 0` (this workflow was called as a sub-workflow), skip this Reflection Gate entirely. Sub-workflows must not interrupt their parent's flow." Sub-workflows don't exist as a concept. Pattern A fires unconditionally. |
| `skills/reflection-patterns/references/gates.md` | Update any cross-references to `invocation_depth` (if present). |
| `skills/navigate/SKILL.md` | Rewrite line 63 ("navigate re-enters itself same-turn only via pending_dispatch consumption"). Add Phase 1 Step 2c (pending_dispatch detection; see Architecture above). Delete Sub-Workflow Return Rule section (lines 438-444). Remove Phase 1 Step 4's `invocation_depth=1, caller="navigate"` writes — triage preflight becomes inline (see below). Remove Phase 1.5 Step 5's `invocation_depth` restoration; rewrite Step 5 SOUND path to use `pending_dispatch(<caller>)` instead. Fix orphaned "Task 3" reference (line 382) and "defined later in this skill" (line 402) — both resolve to explicit anchors. Fix line 111 `"navigate/init"` → explicit `workflow="navigate", phase="init"` pair. |
| `skills/triage/SKILL.md` | On Completion (lines 249-250): simplify to single-mode "clear flag". Preflight Export section (234-242): reframe — triage's Phase 1 quick check becomes a skill-loadable pattern that navigate/verify/build/review each apply inline. Users who type "things are broken" still dispatch triage as a workflow (Phase 2/3 interactive). Add a `mode` argument: `mode="preflight"` runs Phase 1 inline and returns; `mode="direct"` runs full Phase 1-3 interactively. Line 92 `invocation_depth > 0` check is replaced by the `mode` argument. |
| `skills/verify/SKILL.md` | On Completion (line 344) simplified. Phase 1 Step 1 triage preflight: call `Skill(skill="triage", args="preflight")` — no state writes. Phase 4 On PASS review follow-up (lines 218-222): replace with "emit `pending_dispatch(review)`, clear flag, end". **Phase 5 line 252: DELETE the `Skipped when invocation_depth > 0` skip guard** — this is the cluster-4 fix. IUT runs whenever Phase 4 passes. Remove Phase 5 Phase-6 `invocation_depth >= 3` depth guard at line 219 (guard is gone with caller chain). |
| `skills/build/SKILL.md` | **Add Phase 0 plan-mode preamble** (cluster-3 fix — copy verify/SKILL.md:13-31 adjusting `workflow: "build"`). Phase 4 (line 222): replace "Invoke verify as sub-workflow" with "emit `pending_dispatch(verify)`, clear active-workflow, end Phase 4". Build's Phase 5 re-activates on next turn when navigate processes the pending_dispatch verify emits on its return. Phase 5 reads `gate_verdict` from journal to learn verify's outcome. On Completion (line 294) simplified. |
| `skills/review/SKILL.md` | Phase 1 Step 3 triage preflight (lines 107-117): call `Skill(skill="triage", args="preflight")` — no state writes. Phase 3 Step 2 verify follow-up (lines 236-248): replace sub-workflow dispatch with `pending_dispatch(verify)`. Remove line 236 depth guard. On Completion (line 269) simplified. |
| `commands/*.md` | No change. Commands never manipulated workflow state. |
| `agents/*.md` | No change. |
| `hooks/hooks.json` | No change. |
| `evals/g*_trigger_eval.json` (if present) | Audit fixtures for `invocation_depth` or `caller` references. Expected scope: none or trivial. |
| `.claude/rules/iron-laws.md` | Line 53: rewrite "A sub-workflow invoked at `invocation_depth > 0` does not invalidate parent-frame results" → "A workflow dispatched via pending_dispatch is a new causal frame; prior tool results in the emitting workflow remain valid unless the dispatched workflow edits files in the emitting workflow's include closure." |

## Migration plan (big-bang)

One PR with the following commit structure (for reviewer clarity):

1. Commit A: `workflow_state.py` + `track-workflow-skill.py` (schema change + hook simplification). Includes `pending_dispatch` helper.
2. Commit B: `cleanup-stale-workflow.py` + `reflection-patterns/SKILL.md` Pattern A update + `.claude/rules/iron-laws.md`.
3. Commit C: 5 workflow SKILL.md rewrites (navigate, triage, verify, build, review) — all On Completion + dispatch sites. Includes build Phase 0 preamble.
4. Commit D: `README.md` + `evals/g*_trigger_eval.json` cleanup.
5. Commit E: release notes / CHANGELOG.

Tests:
- Extend existing unit tests in `panther-ivy-plugin/tests/` (if any target workflow_state.py) to cover the new schema.
- Add a manual integration test: user types "build a QUIC stream model", observe that build emits `pending_dispatch(verify)` on Phase 4 exit and navigate re-enters verify same-turn.
- Run `/nct-observability` after a chained session to confirm pending_dispatch + workflow_resumed pairs appear correctly.
- Run full pytest suite and report pass/fail count.

## Risks + mitigations

1. **Turn-count UX regression.** Same-turn chained dispatch is the intended UX, but if `Skill()` re-dispatch fails to run in-line (e.g., the harness treats it as a turn break), a `build→verify→review` chain fragments. Mitigation: integration-test the chain in a fresh session before landing; if the harness forces a turn break, fall back to Option 2 ("Next-turn hand-off only") which has the same correctness guarantees but degraded UX.
2. **Pending_dispatch crash recovery.** If a workflow crashes mid-phase before emitting its `pending_dispatch`, the chain breaks silently. Mitigation: emit `pending_dispatch` early (at phase entry, not phase exit) when the next workflow is unambiguously determined (e.g., build Phase 4 emits pending_dispatch(verify) at Phase 4 entry, not exit). For phase-dependent continuations (where the next workflow depends on the phase's outcome), accept the silent-break risk; surface in a later "cluster 12 — tool-level robustness" grill.
3. **Idempotency of consumption.** Navigate re-entering twice for the same pending_dispatch (e.g., user interrupts mid-chain, session resumes, navigate re-reads journal) could double-dispatch. Mitigation: `workflow_resumed` entry is the consumption marker; navigate's Phase 1 Step 2c skips pending_dispatch entries that have a subsequent `workflow_resumed` naming the same target. Mitigation requires all navigate implementations to write the marker BEFORE dispatching.
4. **Observability of chain failure.** If step 3's marker isn't written (e.g., navigate's own edit to journal fails), the chain can stall without user notice. Mitigation: `/nct-observability` already surfaces missing pairs; document in the `/nct-observability` command a "pending_dispatch without workflow_resumed = stalled chain" pattern.
5. **Eval fixture drift.** Gate-trigger evals may reference the old schema. Mitigation: grep `evals/` for `invocation_depth|caller` and adjust; add regression tests for the new schema.

## Out of scope

- Changes to the `ivy-tools` MCP server or the LSP (not affected by workflow semantics).
- The severity-taxonomy unification (cluster 6) — next grill.
- The iteration-counter tracking across sessions (cluster 7) — independent.
- The G2/G3 hook scope gap (cluster 8) — independent, requires hook edits; the new pending_dispatch schema does not alter the hook-firing conditions.
- The NACT/NSCT workflow specialization (cluster 9).
- The agent-dispatch failure recovery (cluster 10).
- Performance tuning of navigate's Phase 1 journal scan under very long journals (> 1000 events).
- Concurrency safety between two Claude sessions writing journals simultaneously (workflow_state.py already uses fcntl; this is unchanged).

## Open questions

1. Does the Skill() tool guarantee same-turn dispatch of a nested Skill() call made from inside another skill? The design assumes yes (based on current navigate→triage behavior). If the harness forces turn breaks, fall back to next-turn hand-off.
2. Should `pending_dispatch` have a TTL? A stale pending_dispatch from an earlier session could confuse navigate. Likely yes — 2h, matching the active-workflow staleness rule. To be decided before implementation.
3. For the `workflow_resumed` consumption marker: should navigate write it before or after the `Skill()` call? Before is idempotency-safe; after is atomicity-safe (if dispatch fails, we don't mark consumed). Recommendation: before, per the "idempotency > atomicity" preference in multi-session plugin work.

## Verification

- Schema change verified by unit tests on `workflow_state.py`.
- Functional change verified by integration scenario: run `verify` alone (baseline), run `build` and observe it emit pending_dispatch(verify), observe navigate re-enters + dispatches verify, observe verify emits pending_dispatch(build, phase=quality-gate), observe navigate re-enters build at Phase 5.
- Full pytest suite must pass before merging.
- `/nct-health` (full 9-step runbook) must still pass after the refactor; triage's `args="preflight"` mode is new and must not break the runbook.
- Manual check: an intentionally-corrupt `active-workflow` with stray `invocation_depth: 0` field must be tolerated during migration (ignored, not errored).
