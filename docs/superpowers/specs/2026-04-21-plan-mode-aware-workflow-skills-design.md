# Plan-Mode-Aware Workflow Skills — Design Spec

**Date:** 2026-04-21
**Status:** Draft
**Scope:** panther-ivy-plugin skills (text edits only; no new hooks)
**Out of scope:** hook-based hard-gate enforcement (tracked as follow-up)
**Related:** `docs/superpowers/specs/2026-04-16-bgp-scenario-builder-design.md`, plan `/Users/elniak/.claude/plans/bgp-synthetic-nest.md`

---

## Problem

During the 2026-04-21 BGP Synthetic-Nest planning session, two process gaps surfaced:

1. **Plan-mode preempts workflow dispatch silently.** The user invoked `/panther-ivy-plugin:navigate BGP`. Navigate's Phase 1 context scan ran, but Phase 2's dispatch step (`ivy_workflow_state(action="set", workflow="build")` + `Skill(skill="build")`) was skipped because plan mode was active and forbids state-mutating actions. Navigate's text does not currently detect this condition, so the skip happened without surfacing to the user and without a journal entry recording the plan-mode hand-off.
2. **Adversarial gates never fire during plan writing.** The plan-mode-approved artifact contained load-bearing decisions (socket-keyed `conn_state`, parameterized `bgp_speakers(I:speaker_idx)`, scenario-to-MUST mapping) that superseded prior `build-state.yaml` decisions. None of the plugin's G-gate critics (G1 exploration, G2 modeling, etc. in `reflection-patterns`) fired on the plan artifact. The session used `advisor()` as a single-critic proxy; advisor caught a soundness gap, but single-critic checks have a demonstrable false-SOUND rate on this material — prior G1 cycles on the same blueprint needed three critics to uncover the MUST #3 vacuity issue.

The common root cause: Claude Code's plan mode is a harness-level feature with no integration into the plugin's workflow skills or gate discipline. Skills do not know plan mode is active; gates defined in skill text are advisory and can be skipped when plan mode preempts the workflow that would otherwise invoke them.

## Approach

Modify skill text only. No new hooks, no plan-format schema enforcement, no hook-level hard gates. Rationale:

- Text edits are reversible by reverting markdown; hook edits require shell/Python and touch hook registration.
- SessionStart system-reminder context already carries plan-mode indicators (the string `Plan mode is active`, the plan file path, edit restrictions). Claude (the agent reading skills) can inspect this context directly — detection does not require a shell hook.
- The workflow journal (`<protocol-dir>/.panther-ivy/workflow-journal.yaml`) already records `decision`, `gate_verdict`, `session_end`, and similar entries. Adding `plan_approved` and `workflow_resumed` entries extends the existing schema without new infrastructure.
- Layer 3 (hook-enforced hard gates) is intentionally deferred. This spec names the gap explicitly rather than pretending text-only covers it.

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Detection mechanism | Read session-start context for plan-mode indicators | No hook needed; Claude has context access |
| Re-entry trigger | Journal-driven handoff (`plan_approved` → `workflow_resumed`) | Uses existing schema; auditable post-hoc |
| Gate for plan artifacts | New G0 variant in `reflection-patterns` | Distinct from G1 (blueprint) and G2 (modeling) — plans have different review targets |
| Hard-gate enforcement | Out of scope | Requires PreToolUse hook on `.ivy` writes; separate spec |
| Skill coverage | navigate + build + verify + review + reflection-patterns | All workflow entry points; plan-mode can preempt any |
| Knowledge-capture integration | Capture plan-approval learnings | Ensures future sessions benefit from each plan-mode cycle |

## Architecture

### Skills affected

Five skill files under `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/skills/`:

- `navigate/SKILL.md` — add Phase 0 plan-mode check, add plan-author branch, add re-entry logic
- `build/SKILL.md` — add Phase 1.5 plan-approval handoff; no changes to phase-0 or later phases
- `verify/SKILL.md` — mirror navigate's Phase 0 check; route plan-mode intent to navigate rather than dispatching verify actions
- `review/SKILL.md` — same mirror pattern as verify
- `reflection-patterns/SKILL.md` — add G0 plan-gate variant alongside existing G1..G5

### Detection mechanism

Skills inspect two signals at Phase 0:

1. **Session-start context** — check the session-start system-reminder message for any of:
   - `Plan mode is active`
   - `You MUST NOT make any edits` (plan mode's edit restriction)
   - A plan file path matching `/Users/.../plans/*.md` in the system-reminder
2. **Workflow journal** — read the protocol's workflow journal. If the most recent entry is `plan_approved` with no subsequent `workflow_resumed`, the session is in the re-entry window after plan approval.

Signal 1 means plan-writing is active; signal 2 means plan-writing just completed and a workflow needs to resume. They do not overlap — signal 1 blocks signal 2's re-entry logic from firing.

### Navigate Phase 0 — plan-mode detection

Insert before the current Phase 1 silent context scan:

```
## Phase 0 — Plan-mode detection

Before the silent context scan, inspect the active session context for plan-mode
indicators:
- The literal string "Plan mode is active" in a SessionStart system-reminder
- The edit-restriction phrase "You MUST NOT make any edits"
- A plan file path of the form /Users/.../plans/*.md in a system-reminder

If any indicator is present, set mode = "plan-author" and proceed directly to
the Plan-Author Branch below. Skip the normal workflow dispatch at the end of
Phase 2; plan mode would block it.

If no indicator is present, proceed to Phase 1 normally.

## Plan-Author Branch (only when plan mode is active)

1. Run the Phase 1 silent context scan as normal. Context gathering is always
   read-only and works in plan mode.
2. Run the Phase 2 situation briefing, but frame options in terms of what can
   be done from plan mode: "write a plan for X", "audit the existing plan",
   "clarify scope before writing".
3. When the user is ready, help them draft the plan file at the path named in
   the system-reminder. Pass the plan through the `/superpowers:writing-plans`
   skill if applicable, but do not try to dispatch the build or verify workflow.
4. Before calling ExitPlanMode, append a journal entry:
     type: plan_approved
     workflow: <caller workflow, e.g. "build">
     phase_before_plan: <phase name, e.g. "blueprint-done-revise-3">
     plan_file: <absolute path to plan file>
     supersedes: <optional list of build-state decisions this plan supersedes>
5. Call ExitPlanMode.
```

### Navigate re-entry after plan approval

Insert a new section at the end of Phase 1:

```
## Phase 1.5 — Post-plan-approval handoff

After the silent context scan, check the workflow journal's most recent entries.
If the latest entry is plan_approved with no subsequent workflow_resumed entry:

1. Load the referenced plan file.
2. Extract committed decisions (look for "Committed:", "Supersedes:",
   "Revises:" tags or structured "## Design Decisions" blocks).
3. Dispatch the plugin's G0 plan-gate critic via
   Skill(skill="panther-ivy-plugin:reflection-patterns") with the G0 variant.
4. Record the G0 verdict as a gate_verdict journal entry.
5. If G0 returns SOUND:
   - Update build-state.yaml's decisions: block with the new decisions,
     marking superseded entries.
   - Append a workflow_resumed entry to the journal.
   - Re-activate the caller workflow via ivy_workflow_state(action="set",
     workflow=<caller>, phase=<next phase after plan_approved>).
   - Dispatch Skill(skill=<caller workflow>).
6. If G0 returns UNSOUND:
   - Present the dissenter reasons to the user.
   - Do not re-activate the workflow. Remain in navigate's context and offer
     options: revise the plan (re-enter plan mode), overrule G0 (record user
     override in journal), or defer.
```

### Build Phase 1.5 — parallel entry path

If the build workflow is invoked directly (not through navigate's re-entry), it must perform the same handoff check. Insert at build's Phase 1 after the context scan:

```
## Phase 1.5 — Plan-approval handoff check

If the workflow journal's most recent entry is plan_approved with no subsequent
workflow_resumed, and the plan's caller field equals "build":

[Same 6 steps as navigate's Phase 1.5 above — duplicated rather than
cross-referenced because the build workflow may be invoked without going
through navigate.]

If no plan_approved handoff is pending, proceed to the normal build phase
logic.
```

### Reflection-patterns G0 plan-gate variant

Add a new section after the existing G1..G5 definitions:

```
## G0 — Plan-gate (pre-implementation plan audit)

Distinct from G1 (blueprint gate). G0 fires on plan artifacts — the artifact
is a plan file committing to design decisions that supersede prior build-state
entries.

Trigger:
- Journal entry plan_approved with a plan_file reference
- Before any workflow_resumed entry for the same caller workflow

Scope:
- The referenced plan file
- Any RFC sections cited in the plan
- The build-state decisions the plan supersedes
- The journal entries (decision, gate_verdict) that led to the superseded
  decisions

Critics:
- 3 Opus critics, confirmer-threshold 2, refute-threshold 1
- Each critic independently reads the plan file, the superseded decisions,
  and the cited RFC sections — no shared context between critics
- Verdict: SOUND / UNSOUND with a concrete pattern citation and locator
  (file:line or journal entry timestamp)

Budget:
- 3 G0 cycles per plan; after the third UNSOUND, escalate to the user for
  authority-override or plan revision

Output:
- gate_verdict journal entry:
    gate: G0_plan
    cycle: <N>
    verdict: SOUND | UNSOUND
    critics: 3
    tally: <SOUND count> / <UNSOUND count>
    primary_pattern: <pattern catalog ID if UNSOUND>
    locator: <file:line or journal reference>
    dissenter_reason: <if applicable>
```

### Knowledge-capture hook (text-only)

Add a trigger in `knowledge-capture/SKILL.md`:

```
## Plan-approval capture trigger

On plan_approved journal entries, prompt the user at next session start:
"Last session approved a plan superseding [N] prior decisions. Capture
learnings from the plan authoring process?"

Typical candidates for capture:
- Process gaps uncovered (e.g., why a gate did not fire)
- Decisions reversed by adversarial review
- Syntax or idiom confirmations from Ivy source-code inspection
```

## Trade-offs

| Pro | Con |
|-----|-----|
| Ships today as five skill-markdown edits | Gates remain advisory — Claude can skip G0 if the journal read misses, auto-compact drops context, or the skill text fails to load |
| No shell/Python hook dependencies | Re-entry is not automatic at ExitPlanMode; requires Claude's next-turn action to trigger Phase 1.5 |
| Detection via SessionStart context is robust to most session-start variants | Plan mode activated mid-session (not at SessionStart) may lack the indicator phrase; edge case not covered |
| G0 variant is additive to reflection-patterns; existing G1..G5 unchanged | G0 adds a 4th gate type for reviewers to track; small cognitive load |
| Journal schema extension is backward-compatible | Older journal entries before this change will not have plan_approved or workflow_resumed markers; re-entry logic degrades gracefully (treats missing as "no handoff pending") |

## Limitations explicitly named

1. **Gates are advisory, not enforced.** A follow-up spec covers hook-based PreToolUse enforcement on `.ivy` writes that blocks edits when the current phase's gate verdict is not SOUND.
2. **Plan format is convention, not schema.** The "Committed:", "Supersedes:", "Revises:" tags are conventions, not validated. Plan authors can omit them; extraction is best-effort.
3. **Session-start detection is fragile.** If Claude Code changes the plan-mode system-reminder format, detection breaks silently. Mitigation: add a canary line in a test plan that fails loudly if detection returns false negatives.
4. **Re-entry needs a user turn.** After ExitPlanMode, Phase 1.5 fires when the user next invokes a skill or asks a question. It does not fire automatically on ExitPlanMode itself. Automatic firing requires a PostToolUse hook on ExitPlanMode — out of scope here.

## Acceptance criteria

1. A session that enters plan mode with an active Ivy workspace records a `plan_approved` journal entry before ExitPlanMode, with the caller workflow and superseded decisions listed.
2. Navigate's Phase 0 check correctly routes to the plan-author branch when plan mode is detected. Verified by a session log showing Phase 0 evaluation and branch selection.
3. The first navigate or build invocation after ExitPlanMode fires the G0 plan-gate, records a `gate_verdict` entry with `gate: G0_plan`, and either re-activates the caller workflow (SOUND) or halts for user input (UNSOUND).
4. For the current BGP Synthetic-Nest plan (as a retrospective validation target), a dry-run G0 dispatch against the plan file returns a verdict. The verdict value is not a pass/fail criterion for this spec — the criterion is that the dispatch happens at all.
5. No regressions in the existing five workflow skills when plan mode is not active. Verified by running a normal build session and confirming phase transitions happen as before.

## Open Questions

1. **Should G0 run for every plan, or only plans that supersede prior decisions?** Running on every plan adds cost; running only on supersedes requires the `Supersedes:` tag discipline. Recommendation: default to every plan; authors can add a `skip_g0: true` front-matter field to opt out for trivial plans (e.g., typo fixes).
2. **Plan-mode activation mid-session.** If plan mode is entered via `/plan` or keybinding after session start, the SessionStart system-reminder does not contain the activation phrase. Detection via journal or the EnterPlanMode tool (if exposed to hooks) is a mid-session alternative. Out of scope for text-only; deferred to the follow-up hook spec.
3. **Interaction with `/compact`.** Auto-compaction may drop the session-start system-reminder containing the plan-mode indicator. If navigate's Phase 0 fires after compaction, detection may fail. Mitigation: re-check the current plan-file path against the system state at every Phase 0, not just at session start.
4. **Layer boundary with the follow-up hook spec.** When the hook spec adds hard-gate enforcement for `.ivy` writes, should G0 be enforced similarly for plan files? Probably yes, but the enforcement mechanism differs (PreToolUse on ExitPlanMode rather than PreToolUse on Edit). Spec the follow-up separately.

## Implementation Order

1. Reflection-patterns G0 variant — prerequisite for navigate's Phase 1.5 call.
2. Navigate Phase 0 + plan-author branch — first plan-mode-aware skill.
3. Navigate Phase 1.5 re-entry — closes the loop for navigate-mediated resumption.
4. Build Phase 1.5 parallel entry — covers the direct-build-invocation case.
5. Verify + review Phase 0 mirrors — minor additions; non-blocking.
6. Knowledge-capture hook text — last; depends on journal schema being updated.
7. End-to-end validation — re-run a throwaway Ivy workspace session with plan mode, confirm acceptance criteria.

Each step is a single skill-markdown edit; commits are per-step for bisectability.

## Migration from advisory gates

Existing G1..G5 gate definitions in `reflection-patterns` remain unchanged. G0 is additive. Existing journal entries remain compatible — `plan_approved` and `workflow_resumed` are new types, and legacy skills that do not read them are unaffected.

If a plan mode session runs before this spec is implemented, the G0 check simply does not fire; the plan is approved without critic review, matching current behavior. After implementation, new plan-mode sessions get the G0 pass.

## Success metrics (post-implementation)

- Zero plan-mode-approved plans in Ivy workspaces without a `gate_verdict` G0 journal entry.
- Reduction in late-stage G1/G2 UNSOUND verdicts tracing to plan-artifact soundness issues (measured by tagging which gate cycle catches each class of defect).
- At least one captured lesson per plan-mode session via the knowledge-capture trigger, contributing to the feedback-memory corpus.
