# Plan-Mode-Aware Workflow Skills — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL — use `superpowers:executing-plans` (one task per turn) or `superpowers:subagent-driven-development` (parallel tasks where file ownership is disjoint). Steps use checkbox (`- [ ]`) syntax.
>
> **Per-task decision discipline:** Each task below presents 2–3 implementation options with trade-offs and a `Decision needed` prompt. The user picks before the worker executes that task. Mechanical tasks (pointer updates, validation runs) declare "no genuine alternatives" explicitly rather than forcing options. Rationale and convention tracked in `feedback_plan_task_options` memory.

**Goal:** Make the Ivy plugin's workflow skills plan-mode-aware and introduce a G0 plan-gate critic, via skill-markdown edits only. No new hooks in this plan; hook-based hard-gate enforcement is a separate follow-up spec.

**Spec:** `docs/superpowers/specs/2026-04-21-plan-mode-aware-workflow-skills-design.md`

**Submodule working directory:** `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/`
**Skill root (within submodule):** `plugins/panther-ivy-plugin/skills/`
**Nested-submodule note:** Edits happen in the `panther-ivy-plugin` submodule. After each commit there, the `panther_ivy` submodule pointer (one level up) needs updating, and finally the PANTHER parent repository's `panther_ivy` pointer. Task 9 handles the two-level chain.

---

## Task 1 — Add G0 plan-gate variant to `reflection-patterns`

**File:** `plugins/panther-ivy-plugin/skills/reflection-patterns/SKILL.md`

### Options

**Option 1A — Inline G0 section alongside G1..G5.**
Append a new `## G0 — Plan-gate` section after the existing G5 block, inside the same SKILL.md.

- **Pro:** Single-file edit; G0 appears in the same loading context as G1..G5; no new reference files to maintain.
- **Con:** Pushes the skill closer to the 300-line best-practice soft limit in `feedback skill-conventions`. Current size 220 lines; G0 adds ~40 lines. Still within bounds, but reduces room for future gate additions.

**Option 1B — Extract all gates to `references/gates.md`, SKILL.md points to it.**
Move G1..G5 definitions out of SKILL.md into a new `references/gates.md`, add G0 alongside. SKILL.md keeps a one-line-per-gate summary table and a `See references/gates.md` link.

- **Pro:** SKILL.md stays under 150 lines; future gate additions touch only `references/gates.md`. Matches the plugin's progressive-disclosure style (`references/` under a skill per `feedback_references_under_skill`).
- **Con:** Larger refactor surface. Risks regressing the existing G1..G5 loading behaviour if any caller depends on those being in SKILL.md directly. Requires a dedicated verification pass on existing G1..G5 dispatches.

**Option 1C — G0 in its own reference file alongside G1..G5 staying inline.**
Add `references/g0-plan-gate.md` with the full G0 spec. SKILL.md adds a one-paragraph G0 overview pointing at the reference.

- **Pro:** Smallest blast radius — no touch to existing G1..G5 text; additive-only change. Good isolation for later revision of G0 without re-reading the whole SKILL.md.
- **Con:** Introduces asymmetry between G0 (referenced) and G1..G5 (inline). A future maintainer might not realize G0 exists from a quick read of SKILL.md.

### Decision needed
Choose 1A, 1B, or 1C. Recommendation axes: if you value uniform gate treatment, pick 1B (at higher refactor cost). If you want minimal disruption, pick 1C. If you want the quickest ship, pick 1A.

### Steps (apply after selection)
- [ ] Read the current skill and locate the relevant insertion point per the chosen option.
- [ ] Insert G0 content verbatim from the design spec's "Reflection-patterns G0 plan-gate variant" section.
- [ ] Verify by re-reading: G0 present, existing G1..G5 byte-identical (1A/1C) or faithfully relocated (1B), frontmatter unchanged.
- [ ] Commit: `feat(reflection-patterns): add G0 plan-gate variant for plan-artifact audits` (adjust wording if 1B/1C).

---

## Task 2 — Navigate Phase 0 plan-mode detection

**File:** `plugins/panther-ivy-plugin/skills/navigate/SKILL.md`

### Options

**Option 2A — Insert Phase 0 as a new top-level heading before Phase 1.**
New `## Phase 0 — Plan-mode detection` section. Existing Phase 1/2 headings untouched except for an added cross-reference line.

- **Pro:** Sequential reading flow; users scanning the skill see detection first, scan next. Matches existing phase-numbering convention.
- **Con:** Renumbers the skill's mental model from "two phases" to "three phases." May confuse tooling or docs that enumerate phases.

**Option 2B — Add detection as a preamble inside the existing Phase 1.**
Keep only Phase 1 and Phase 2 as headings. At the very top of Phase 1, add a "Before the silent context scan" subsection with the three-signal detection and the route-to-plan-author rule.

- **Pro:** No phase renumbering; external docs referencing "Phase 1" and "Phase 2" continue to match.
- **Con:** Hides the detection step inside another phase; a reader looking for "where does navigate react to plan mode" has to search inside Phase 1 rather than see it in the phase list.

**Option 2C — Replace Phase 1's opening with a branch statement, no new phase added.**
Phase 1 begins: "If plan mode is detected, skip the normal context scan below and proceed to the Plan-Author Branch further down. Otherwise:" followed by the existing context-scan text.

- **Pro:** Minimal textual addition; zero restructuring.
- **Con:** Obscures detection as a separate concern; debugging "did Phase 0 fire" becomes "did the first paragraph of Phase 1 fire," harder to attribute in logs.

### Decision needed
Choose 2A, 2B, or 2C. Note that Task 3 (Phase 1.5 post-approval handoff) adds another phase-like block — picking 2A makes Task 3's structure consistent; picking 2B/2C forces Task 3 to follow the same mold.

### Steps (apply after selection)
- [ ] Read navigate skill (249 lines), locate the chosen insertion point.
- [ ] Insert detection block using the design spec's "Navigate Phase 0" template.
- [ ] Add the Plan-Author Branch section with its six-step logic (see Task 3 if decoupled, else include here).
- [ ] Update Integration appendix at the bottom of navigate's SKILL.md to reference the new journal entry types.
- [ ] Verify: detection appears in the chosen location; Plan-Author Branch exists and references the journal-append step correctly.
- [ ] Commit: `feat(navigate): add Phase 0 plan-mode detection`.

---

## Task 3 — Navigate post-plan-approval handoff

**File:** `plugins/panther-ivy-plugin/skills/navigate/SKILL.md`

### Options

**Option 3A — New Phase 1.5 section between Phase 1 and Phase 2.**
Explicit phase with six steps for journal read, G0 dispatch, SOUND/UNSOUND branches. Matches the spec's template.

- **Pro:** Clear separation of concerns; journal-driven re-entry is visibly distinct from normal dispatch.
- **Con:** Adds a fourth phase to navigate (or third if 2B/2C were chosen earlier); the Phase 0/1/1.5/2 sequencing is slightly unusual.

**Option 3B — Fold handoff into Phase 2's dispatch logic.**
Phase 2's dispatch opens with: "If the journal's latest entry is `plan_approved` without a subsequent `workflow_resumed`, handle the plan-approval handoff before normal dispatch:" followed by the six steps.

- **Pro:** No new phase; Phase 2 is already the dispatch phase, so extending it with a handoff preamble is natural.
- **Con:** Phase 2 becomes longer and mixes two concerns (handoff + normal dispatch). Readability suffers once both branches have edge cases.

**Option 3C — Extract handoff to a sub-skill `navigate-resume`.**
Create `skills/navigate-resume/SKILL.md` with the six-step handoff logic. Navigate's Phase 2 dispatches to it via `Skill(skill="panther-ivy-plugin:navigate-resume")` when the journal condition is met.

- **Pro:** Single-responsibility sub-skill; handoff logic can evolve independently. Matches existing pattern of user-invocable and internal skills.
- **Con:** Adds a new skill directory; introduces cross-skill dispatch on every session resume; higher invocation overhead.

### Decision needed
Choose 3A, 3B, or 3C. If Task 2 picked 2A, 3A is the consistent choice. If Task 2 picked 2B/2C, 3B avoids a new phase. 3C is the right pick only if you expect the handoff logic to grow significantly.

### Steps (apply after selection)
- [ ] Locate the insertion point chosen above.
- [ ] Insert the six-step handoff (load plan, extract decisions, dispatch G0, record verdict, SOUND re-activation, UNSOUND halt).
- [ ] Add a mutual-exclusion note: handoff only fires when plan mode is NOT active (post-ExitPlanMode only).
- [ ] Verify: the G0 `Skill()` invocation syntax matches Task 1's chosen location; journal payload matches the schema established in Task 1's G0 output.
- [ ] Commit: `feat(navigate): add post-plan-approval handoff with G0 dispatch`.

---

## Task 4 — Build parallel entry path for direct invocation

**File:** `plugins/panther-ivy-plugin/skills/build/SKILL.md`

### Options

**Option 4A — Duplicate navigate's handoff logic in build's Phase 1.**
Copy the six-step handoff into build's Phase 1 with the caller-filter (`caller == "build"`).

- **Pro:** Build can be invoked directly without going through navigate; handoff still fires. Matches the spec's recommendation.
- **Con:** Code duplication between navigate and build. Future changes to handoff logic require edits in both places.

**Option 4B — Build delegates to navigate-resume sub-skill (depends on 3C).**
If Task 3 chose 3C, build's Phase 1 dispatches to `panther-ivy-plugin:navigate-resume` when the condition matches.

- **Pro:** Single source of truth for handoff logic; no duplication.
- **Con:** Only viable if 3C was picked. Cross-skill dispatch overhead per session.

**Option 4C — Defer build parallel entry; require navigate as entry.**
Don't modify build. Document that direct build invocation post-plan-approval is unsupported — users must invoke navigate first.

- **Pro:** Zero code change to build. Keeps navigate as the canonical entry.
- **Con:** User experience regression for workflows that invoke build directly. The user would see build run without the G0 gate, defeating the spec's acceptance criterion.

### Decision needed
Choose 4A, 4B, or 4C. 4A is the default if 3A or 3B was chosen. 4B only if 3C. 4C only if build direct-invocation after plan approval is acceptable to skip the gate.

### Steps (apply after selection)
- [ ] Read build skill (379 lines), locate Phase 1 end.
- [ ] Insert handoff logic per the chosen option.
- [ ] Add caller-filter so build's handoff only fires when the `plan_approved` entry's `caller` equals `"build"`.
- [ ] Document phase-reversal behaviour: if the plan supersedes a decision from an earlier phase (e.g., blueprint) but build is in a later phase (e.g., modeling), build reverts to the earlier phase before re-entering.
- [ ] Verify: build's handoff does not trigger if navigate already ran the handoff (journal has `workflow_resumed`).
- [ ] Commit: `feat(build): add parallel entry for direct-invocation post-plan-approval`.

---

## Task 5 — Verify + Review plan-mode redirect

**Files:**
- `plugins/panther-ivy-plugin/skills/verify/SKILL.md`
- `plugins/panther-ivy-plugin/skills/review/SKILL.md`

### Options

**Option 5A — Both skills redirect to navigate via `Skill()`.**
When plan mode is detected in verify or review, invoke `Skill(skill="panther-ivy-plugin:navigate")` and stop verify/review logic.

- **Pro:** Single source of plan-mode handling (navigate). Verify/review stay focused on tool dispatch.
- **Con:** Redirect adds a layer of indirection. Users invoking `/panther-ivy-plugin:verify` in plan mode see navigate's output instead.

**Option 5B — Both skills implement a mini plan-author preamble.**
Each skill gets its own Phase 0 plan-author branch with the minimum necessary text, without redirecting to navigate.

- **Pro:** No cross-skill dispatch. Each skill is self-contained.
- **Con:** Triplicates plan-author logic (navigate, verify, review all have it). Any change to plan-author behaviour requires three edits.

**Option 5C — Only verify redirects; review skips redirect.**
Verify gets the redirect (since it's commonly invoked mid-session). Review does not, on the assumption that review is invoked only in analysis contexts where plan mode is unusual.

- **Pro:** Partial coverage; smaller edit surface than 5A.
- **Con:** Inconsistent UX between verify and review. Users may wonder why one redirects and the other doesn't.

### Decision needed
Choose 5A, 5B, or 5C. 5A is the default for consistency; 5B only if you want to avoid skill-to-skill dispatch at all costs; 5C only if review's plan-mode entry is genuinely rare.

### Steps (apply after selection)
- [ ] Add Phase 0 block to each target skill per the chosen option.
- [ ] Include rationale text: "Plan mode in this skill's context is usually navigational ambiguity — the user meant to plan, not to dispatch."
- [ ] Verify: each modified skill's Phase 0 fires before any tool invocation logic; the redirect/local-branch path is correctly invoked.
- [ ] Commit each skill separately: `feat(verify): ...` and `feat(review): ...`.

---

## Task 6 — Knowledge-capture plan-approval trigger

**File:** `plugins/panther-ivy-plugin/skills/knowledge-capture/SKILL.md`

### Options

**Option 6A — Add a new trigger subsection, user-prompted capture.**
On `plan_approved` journal entries at next session start, prompt the user with the supersedes count and proposed capture candidates.

- **Pro:** Opt-in; matches the skill's existing non-automatic discipline.
- **Con:** Requires user action; may be missed if the user doesn't notice the prompt.

**Option 6B — Automatic capture of a minimal summary, opt-out via flag.**
Auto-capture a one-line summary on each `plan_approved` (plan filename, caller, supersedes count). Full capture is still user-opt-in.

- **Pro:** Lowest-effort durable record; future sessions can see at a glance that plan-mode work happened.
- **Con:** Creates noise if trivial plans are approved frequently. Requires an opt-out mechanism.

**Option 6C — No knowledge-capture trigger in this spec.**
Defer the capture integration to a later iteration. Plan-mode awareness without knowledge-capture still delivers the gate discipline.

- **Pro:** Smallest scope for this spec.
- **Con:** Loses the feedback loop between plan-mode sessions and future plugin improvements. The lesson from this very session (gates don't fire during plan writing) would not be captured automatically.

### Decision needed
Choose 6A, 6B, or 6C. 6A is the spec's default. 6C only if the knowledge-capture integration feels premature.

### Steps (apply after selection)
- [ ] Read knowledge-capture skill.
- [ ] Add trigger subsection per the chosen option (skip if 6C).
- [ ] Verify non-blocking behaviour (prompts rather than unilaterally captures for 6A, minimal-auto for 6B).
- [ ] Commit: `feat(knowledge-capture): add plan-approval capture trigger` (or skip commit for 6C).

---

## Task 7 — Journal schema documentation

### Options

**Option 7A — Document schema in navigate + build SKILL.md appendices (one each).**
Each skill has a "Journal entry types" appendix listing `plan_approved`, `workflow_resumed`, and the `G0_plan` gate value. Some duplication.

- **Pro:** Direct-readers of either skill see the schema without cross-reference.
- **Con:** Duplication; schema drift risk if one appendix updates without the other.

**Option 7B — Single `references/journal-schema.md` under navigate, linked from build.**
Authoritative schema file under navigate's `references/`. Build's SKILL.md links to it with a one-line summary.

- **Pro:** Single source of truth; future entry types go in one place.
- **Con:** Cross-skill reference file (navigate's `references/` read from build) is an unusual access pattern; per `feedback_skill_cross_refs`, cross-skill access goes through `Skill()`, not hardcoded reference paths.

**Option 7C — New `skills/_schema/SKILL.md` as an internal schema-only skill.**
Dedicated schema skill that any workflow skill can load via `Skill(skill="panther-ivy-plugin:_schema")` when it needs the journal contract.

- **Pro:** Clean cross-skill access through the Skill tool, matching plugin conventions.
- **Con:** New skill directory for what is just documentation; adds invocation overhead for simple schema lookups.

### Decision needed
Choose 7A, 7B, or 7C. 7A is the simplest and closest to the current plugin style; 7C is the most principled long-term but heavier. 7B is rejected unless the cross-skill-reference antipattern is explicitly accepted.

### Steps (apply after selection)
- [ ] Write schema content per the design spec (plan_approved fields, workflow_resumed fields, G0_plan gate_verdict fields).
- [ ] Place it per the chosen option.
- [ ] Grep check: `grep -rn "plan_approved\|workflow_resumed\|G0_plan" plugins/panther-ivy-plugin/skills/` — matches only in edited files.
- [ ] Commit: `docs(skills): document journal schema for plan-approval workflow`.

---

## Task 8 — End-to-end validation — **PENDING MANUAL VALIDATION**

**Status:** Deferred to a follow-up session per user decision on 2026-04-21.

**Blockers that forced the defer:**
- Task 8 requires a fresh Claude Code session with plan mode active to exercise the full detection → Plan-Author Branch → ExitPlanMode → Phase 1.5 path. Cannot be done inside the authoring session that just wrote the plan.
- The `ivy_*` MCP tools (including `ivy_workflow_state`) disconnected during the authoring session, so the retrospective dry-run G0 against the BGP Synthetic-Nest plan was not runnable.

### Checklist for the next-session reviewer

Run these steps in a fresh session (cold start, or immediately after `/clear`) with the `panther-ivy-plugin` submodule pointer pointing at `bcd7e6b` or later (Task 7 commit). Confirm the `ivy_*` MCP tools are connected via `ivy_status(mode="health")` before starting.

- [ ] **Plan-mode entry.** Start Claude Code with plan mode active (CLI flag `--permission-mode plan` or invoke `/plan` after startup). Confirm `[ROUTING:AVAILABLE]` fires on the first user prompt.
- [ ] **Navigate Phase 0 detection.** Invoke `/panther-ivy-plugin:navigate bgp`. Expected: the skill inspects the session-start context for the three plan-mode indicators (`Plan mode is active`, `You MUST NOT make any edits`, `/Users/*/plans/*.md` path), detects plan mode, and routes to the Plan-Author Branch rather than dispatching a workflow. Read-only context scan runs; `ivy_workflow_state(action="append_journal", event_type="context_switch", ...)` writes a `{"detection": "plan_mode_active", "mode": "plan-author"}` payload.
- [ ] **Plan authoring.** Walk the Plan-Author Branch's five steps. Draft a trivial test plan (e.g., "fix a typo in some README"). Before `ExitPlanMode`, confirm a `plan_approved` journal entry is appended with `workflow`, `phase_before_plan`, `plan_file`, `supersedes` fields.
- [ ] **ExitPlanMode + Phase 1.5 re-entry.** After approval, invoke navigate again (or ask any question — the routing hook re-fires navigate). Expected: Phase 0 no longer detects plan mode, Phase 1.5 fires because the journal has an unmatched `plan_approved` entry. Phase 1.5 loads the plan file, dispatches three G0 Opus critics in parallel using the verbatim `references/critic_prompts/g0_plan.md` template, aggregates the verdict, writes a `gate_verdict` entry with `gate: "g0"`.
- [ ] **SOUND path.** On `VERDICT_SOUND`, confirm: `build-state.yaml` is merged with the plan's decisions, a `workflow_resumed` entry is appended, the caller workflow re-activates.
- [ ] **UNSOUND path** (if the trivial-plan G0 happens to come back UNSOUND, or author a deliberately flawed plan to force it). Confirm: dissenter reasons surface via `AskUserQuestion`, no workflow re-activation, three-option revise/overrule/defer branch runs.
- [ ] **Retrospective BGP dry-run.** Run a G0 dispatch against `/Users/elniak/.claude/plans/bgp-synthetic-nest.md` — simulate post-approval by appending a `plan_approved` entry manually to the BGP protocol's journal, then invoke navigate. Record the verdict. The verdict value is a data point for BGP Track 6 Group D work, not a pass/fail criterion for this spec.
- [ ] **Control session.** Start a separate session WITHOUT plan mode. Invoke `/panther-ivy-plugin:navigate bgp`. Expected: Phase 0 detection returns negative, skill falls through to Phase 1 normally, no regression in the existing warm-resume / activity-summary / cold-start branches. Phase 1.5 does NOT fire unless the journal happens to have a pending `plan_approved`.
- [ ] **Verify/review plan-mode preambles.** In a plan-mode session, invoke `/panther-ivy-plugin:verify` and `/panther-ivy-plugin:review`. Expected: each skill's Phase 0 preamble detects plan mode, switches to plan authoring, does NOT attempt to dispatch `ivy_verify` / `ivy_coverage` / other state-mutating tools.
- [ ] **Knowledge-capture trigger.** After one complete plan-approval cycle, start a new session. The knowledge-capture skill's Plan-Approval Capture Trigger should prompt once at session start with the `plan_approved` entry's details.
- [ ] **Write the validation report.** Create `docs/superpowers/validation/2026-04-21-plan-mode-aware-skills-validation.md` with one section per acceptance criterion, marked PASS / FAIL / N/A with evidence (journal-entry excerpts, screenshot transcripts).
- [ ] **Commit the validation report** in the PANTHER parent repo on the `production` branch.

### Commit hashes to reference in the validation report

- `abe0538` (panther-ivy-plugin) — Task 1: G0 gate variant
- `da3964d` — Task 2: navigate Phase 0 + Plan-Author Branch
- `af394ce` — Task 3: navigate Phase 1.5
- `5eaf146` — Task 5a: verify Phase 0 preamble
- `0d79182` — Task 5b: review Phase 0 preamble
- `b8b1d76` — Task 6: knowledge-capture trigger
- `bcd7e6b` — Task 7: whitelist + tool-reference.md
- `58049a9` (ivy-lsp) — Task 7 MCP-tool whitelist sibling commit

---

## Task 9 — Submodule pointer chain update

**Scope:** two-level submodule pointer update. No genuine alternatives — this is the mechanical integration step required to land the plugin edits in the PANTHER parent.

### Steps
- [ ] Ensure all Task 1–7 commits inside `panther-ivy-plugin` submodule are ready (pushed if the user's workflow requires).
- [ ] Update `panther_ivy` submodule pointer (one level up):
  ```bash
  cd panther/plugins/services/testers/panther_ivy
  git add submodules/panther-ivy-plugin
  git commit -m "chore: update panther-ivy-plugin submodule for plan-mode-aware skills"
  ```
- [ ] Update PANTHER parent submodule pointer:
  ```bash
  cd $(git rev-parse --show-toplevel)
  git add panther/plugins/services/testers/panther_ivy
  git commit -m "chore: update panther_ivy submodule for plan-mode-aware skills"
  ```
- [ ] Verify clean state: `git status` and `git submodule status` on the parent.

---

## Verification Checklist (aggregate acceptance criteria from the spec)

- [ ] A session entering plan mode in an Ivy workspace records a `plan_approved` entry with `workflow`, `phase_before_plan`, `plan_file`, `supersedes` fields.
- [ ] Navigate's plan-mode detection correctly routes to the Plan-Author Branch (path depends on Task 2 option).
- [ ] The first navigate/build invocation after ExitPlanMode fires G0, records a `gate_verdict` with `gate: G0_plan`, and either resumes (SOUND) or halts (UNSOUND).
- [ ] Retrospective G0 dispatch on the BGP Synthetic-Nest plan returns a verdict (dispatch happening is the criterion; verdict value is informational).
- [ ] No regressions in normal invocations of navigate, build, verify, review.
- [ ] Journal-schema grep returns matches only in edited skills.
- [ ] Two-level submodule pointer chain updated and committed.

## Rollback

Each task is a single skill-markdown commit (or two for Task 5's split). `git revert <hash>` on any one restores prior behaviour without affecting other tasks. G0 (Task 1) is additive. Phase 0 / handoff insertions (Tasks 2–4) are self-contained blocks.

If Task 8 validation surfaces a regression, revert the responsible task's commit, fix, recommit, rerun Task 8.

## Risks

- **Markdown-context pressure.** Large additions near the top of a skill file may push later sections out of Claude's skill-loading context budget. Mitigation: per-task option choices that favour extraction (1B, 1C, 7B, 7C) reduce per-file size.
- **Cross-skill reference antipattern.** Option 7B hardcodes a reference path from build into navigate's `references/`; `feedback_skill_cross_refs` rules against this. If picked, flag as a conscious deviation.
- **Two-submodule commit chain mistakes.** Task 9's Step 4 `git submodule status` verification catches a missed level before shipping.
- **Journal-schema drift.** Future skill edits may add fields without updating Task 7's source of truth. Mitigation: the Task 7 grep canary can be promoted to a CI check in a follow-up.

## Out of scope (same as the spec)

- Hook-based hard-gate enforcement on `.ivy` writes (Layer 3).
- Plan-format schema validation (tags are convention, not validated).
- Automatic re-entry at ExitPlanMode itself (requires a PostToolUse hook).
- Session-start detection after `/compact` drops the plan-mode system-reminder.
