# Design — panther-ivy-plugin Attempt-Counter Persistence

Status: proposed
Author: workflow-audit follow-up (cluster-7 grilling session)
Date: 2026-04-23
Scope: close audit cluster 7 (iteration counters untracked across sessions — verify 5-attempt fix cap, build 5-attempt compile cap).

## Context

The workflow audit on 2026-04-23 identified that both the `verify` workflow's 5-attempt fix cap (`skills/verify/SKILL.md:334`) and the `build` workflow's 5-attempt compile cap per layer (`skills/build/references/layer-scaffolding.md:23-25`) are documented in prose but never persisted. A session restart silently resets the counter to 0. The audit classified this as Major because the cap is the exact mechanism that protects against the anti-patterns `#405` / `#403` ("error whitelisting / silent retry past cap") in `ivy-error-patterns`.

This spec makes the counter real: each attempt appends a structured `progress` journal event; the workflow body reads the journal to compute the current count before looping. A user-authorized override via an existing `decision` event provides a soft-reset escape hatch.

The design piggybacks on cluster 1's "journal as data-passing bus" direction (see `2026-04-23-workflow-state-model-refactor-design.md`): no new state file, no regrowth of the `active-workflow` schema, no new event type. The journal is already persistent, per-protocol, and queryable via `ivy_workflow_state(action="get_journal", …)`.

## Decisions

1. **Per-file / per-layer scope, cumulative across sessions.** The counter is keyed by the artifact being operated on (a `.ivy` test file for verify's fix loop; a layer name for build's compile loop) and carries across session boundaries.
2. **Structured `progress` journal event** records each attempt. Payload shape: `{kind: "fix_attempt" | "compile_attempt", key: <canonical_relative_path> | <layer_name>, protocol: <protocol_name>}`.
3. **Workflow body counts events on demand** before each loop iteration: filter `progress` events by `kind` + `key`, count entries since the most recent `decision{kind: "override_attempt_cap", key: same}` event (if any). Escalate if count >= 5.
4. **Soft override semantics**: a user-authorized `decision{kind: "override_attempt_cap", key: same}` event resets the counter for that key; the cap re-engages after the override (the next 5 attempts trigger escalation again).
5. **Canonical `key` form**: paths are made relative to the protocol directory (e.g., `bgp_stack/bgp_frame.ivy`, not absolute). Layer names use the layer's canonical name from `build-state.yaml.layers` (e.g., `bgp_open`).
6. **`/nct-observability` extension**: summary mode reports a new "Attempt Counts" table showing per-key attempts + overrides in this session.

## Architecture

### Journal payload additions

Existing `progress` event payload is free-form `{detail: string}`. This spec formalizes an additional shape (non-exclusive):

```json
{
  "event_type": "progress",
  "timestamp": "2026-04-23T11:20:00Z",
  "payload": {
    "kind": "fix_attempt",
    "key": "bgp/bgp_tests/server_tests/bgp_server_test_join.ivy",
    "protocol": "bgp"
  }
}
```

Compatible with legacy `{detail: string}` payloads (workflows filter on presence of `kind`).

### Override event

Existing `decision` event with new payload shape:

```json
{
  "event_type": "decision",
  "timestamp": "2026-04-23T11:32:00Z",
  "payload": {
    "summary": "Override attempt cap for bgp_server_test_join.ivy",
    "context": "User: keep going, believe the next fix resolves",
    "kind": "override_attempt_cap",
    "key": "bgp/bgp_tests/server_tests/bgp_server_test_join.ivy"
  }
}
```

### Counting algorithm (workflow body)

Pseudo-code for verify Phase 7 fix loop entry:

```
events = ivy_workflow_state(action="get_journal", protocol=<prot>, last_n=100).events
# Walk backward to find the most recent override decision for this key
override_idx = -1
for i, ev in reversed(events):
    if ev.type == "decision"
       and ev.payload.kind == "override_attempt_cap"
       and ev.payload.key == <current_test_file>:
        override_idx = i
        break
# Count fix_attempt progress events after the override (or all of them if no override)
count = sum(1 for ev in events[override_idx+1:]
            if ev.type == "progress"
               and ev.payload.kind == "fix_attempt"
               and ev.payload.key == <current_test_file>)
if count >= 5: ESCALATE
else: APPEND progress{fix_attempt, key, protocol}; LOOP
```

### Escalation menu (three-option)

When count >= 5:

1. **Continue anyway** — user is sure the next fix resolves. Workflow appends `decision{kind: "override_attempt_cap", key}` and resumes. Cap re-engages for next 5.
2. **Abandon this file/layer** — workflow records abandonment as a `decision{summary: "Abandon <key> after N attempts"}` and proceeds to workflow completion (no further attempts on this key this session).
3. **Switch workflow** — typically back to `build` for structural rethink; emit `pending_dispatch(build, phase_hint=<appropriate>)` per cluster-1's hand-off semantics.

## File change inventory (6 files)

| File | Change |
|---|---|
| `skills/verify/SKILL.md` | Lines 325-336 Phase 6/7 summary: replace prose iteration cap with concrete journal-counted cap. Before the fix loop, append `progress{kind: "fix_attempt", key: <test_file>, protocol: <prot>}`. Read journal, count, escalate as above. Update Step Tracking Phase 7 block to include "Record fix attempt" task. |
| `skills/verify/references/failure-diagnosis.md` | Phase 7 Step 1-2: specify journal-append + count before each Apply fix step. Document the 3-option escalation menu. |
| `skills/build/SKILL.md` | Line 204 Phase 3 summary: same journal-counted pattern for `kind: "compile_attempt", key: <layer_name>, protocol: <prot>`. Update Step Tracking Phase 3 per-layer block. |
| `skills/build/references/layer-scaffolding.md` | Lines 23-25 per-layer compile-fix loop: explicit journal-append before compile; explicit count before loop; 3-option escalation. |
| `commands/nct-observability.md` | Summary mode Step 3: add new "### Attempt Counts" table subsection after "Tool Usage Breakdown". Show per-key counts: `{key, kind, count, overrides}`. Existing journal-reading logic covers the read; just a new presentation. |
| `.claude/rules/iron-laws.md` | Audit the STALENESS RULE section for any mention of attempt accumulation. Update if the current prose assumes session-scoped counters. |

## Migration plan

Single commit. Older `progress` events with `{detail: string}` payloads remain valid and are simply not counted as attempts (they lack a `kind` field). No retroactive counter application — attempt tracking starts the moment this spec lands.

## Risks

1. **Journal scan cost.** `get_journal(last_n=100)` is the default. For a key with many attempts, this is sufficient. For extremely long-running sessions (>100 attempt events), the read budget may clip. Mitigation: workflows parametrize `last_n` (e.g., `last_n=200`) with an inline comment documenting the choice. Future enhancement: index-by-kind support in the journal MCP tool.
2. **Override re-engagement**. The soft override means a user stuck in a loop can keep overriding forever. Mitigation: `/nct-observability` surfaces overrides alongside attempts. The user (and downstream reviewers) can see the pattern.
3. **Key canonicalization drift**. If the workspace root changes between sessions, absolute-path keys would fail to match. Mitigation: decision #5 requires relative-to-protocol paths. Enforced in the workflow body (workflows pass the relative path to `append_journal`, not the absolute path).
4. **No cross-key correlation**. Fix attempts for `file_A.ivy` don't count against `file_B.ivy`. This is intended per cluster-7's per-file scope, but a user oscillating between two files indefinitely is not caught. Mitigation: out of scope for this cluster; could be addressed by a future "phase-level attempt cap" cluster if needed.

## Out of scope

- A dedicated `/nct-reset-attempts <key>` command. The override decision path fulfills the reset need.
- Global (session-wide, cross-key) attempt caps.
- Time-based attempt caps (walltime rather than cycle count).
- Retroactive counting of pre-spec attempts.
- Changes to `workflow_state.py` (no new schema; existing `append_journal` and `get_journal` are sufficient).

## Verification

- Run `verify` on a broken test file; fix loop appends `progress{fix_attempt, key}` each iteration.
- Run `/nct-observability` summary after 3 attempts; see attempt count = 3 for that key.
- Trigger escalation: simulate 5 failed attempts. Confirm escalation menu appears.
- Pick "Continue anyway"; confirm `decision{override_attempt_cap}` is appended; confirm next attempt counts as attempt #1 after the override.
- Pick "Abandon"; confirm workflow exits without appending override.
- Spot-check: key canonicalization — attempt events on `protocol-testing/bgp/...` and `bgp/...` (same file, different relative anchoring) must produce consistent keys.
- Run full pytest suite; should be unaffected since the spec touches only skill bodies and a command.
