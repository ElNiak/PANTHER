# Design — Harness Audit Patches 2 through 6 (panther-ivy-plugin)

Date: 2026-04-29
Source audit: `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/.harness-audit/report-2026-04-29.md`

## Context

The 2026-04-29 harness audit of `panther-ivy-plugin` produced six concrete patches. Patch 1 (workflow-name drift, CRITICAL) was applied during the audit session — five `Skill(...)` invocations that targeted removed skill names were rewritten to dispatch `ivy-triage-agent` instead, and one site that referenced two non-existent skills (`cross-cutting-reflection-patterns`, `workflow-navigate`) was preserved behind a `<!-- TODO -->` comment pending a separate decision.

This spec covers the remaining five patches (2 through 6). They are scoped together because they are all surfaced by the same audit, share no architectural dependencies on each other, and can be applied in sequence in a single work session. None is destructive; each has a deterministic verification step.

The user's goals for this batch:

- Restore the orchestrator description's effective triggering surface (Patch 2).
- Make sub-agent return-size caps explicit caller-side, not only on the agent contract (Patch 3).
- Land outstanding `plugin.json` polish before the next public release (Patch 4).
- Apply the one progressive-disclosure extraction the audit identified as cleanly worth doing — Phase 4 trace analysis and the MPE roles in `review-ops` — and downgrade the `meta-self-mod-ops` flag to INFO since it sits inside the strict rubric (Patch 5).
- Make the failure-recovery contract visible from the orchestrator body, not only via the auto-loaded rule (Patch 6).

## Scope

### In scope (this spec)

- Patch 2 — `skills/ivy/SKILL.md` description rewrite (1 file, 1 line).
- Patch 3 — return-size caps appended to every `Agent(...)` dispatch example across 5 dispatching skills (5 files).
- Patch 4 — `.claude-plugin/plugin.json` hardening: `repository` to object form, two `userConfig` `enum` additions (1 file, 3 edits).
- Patch 5 — Two new reference files under `skills/review-ops/references/`; corresponding body collapses in `review-ops/SKILL.md`; report update downgrading the `meta-self-mod-ops` finding to INFO (3 file edits + 1 audit-report edit).
- Patch 6 — One-line failure-recovery cross-reference inserted into `skills/ivy/SKILL.md` (1 file, 2 lines added).

Total: 7 modified files plus 2 new files plus 1 audit-report annotation. Distinct files touched: `skills/ivy/SKILL.md` (Patches 2, 3, 6), `skills/build-ops/SKILL.md` (Patch 3), `skills/verify-ops/SKILL.md` (Patch 3), `skills/review-ops/SKILL.md` (Patches 3, 5), `skills/meta-self-mod-ops/SKILL.md` (Patch 3), `.claude-plugin/plugin.json` (Patch 4), `skills/review-ops/references/phase-4-trace-analysis.md` (new, Patch 5), `skills/review-ops/references/mpe-roles.md` (new, Patch 5), `.harness-audit/report-2026-04-29.md` (Patch 5 annotation).

### Out of scope (separate brainstorms)

- `skills/README.md` whole-file rewrite to describe the actual 13-skill `*-ops` architecture (separate brainstorm — depends on whether `cross-cutting-reflection-patterns` and `workflow-navigate` are restored or deleted).
- `tool-catalog.md:435` TODO resolution (separate brainstorm — restore / redirect / delete the two missing-skill cross-references).
- Hook-tree four-pillar audit extension (separate brainstorm; lives in the audit skill at `~/.claude/skills/harness-audit/`, not in `panther-ivy-plugin`).

## The five patches

### Patch 2 — Orchestrator description rewrite

**File:** `skills/ivy/SKILL.md`
**Lines touched:** 1

Replace the 466-character second-person description with a 248-character third-person rewrite. The harness's empirical 250-character truncation point currently hides the routing payload (specialist agents, "first entry point") from trigger-time evaluation. The rewrite preserves all triggering signal in the visible region.

```diff
---
 name: ivy
-description: "You MUST use this on every panther-ivy-plugin session entry where the user wants to work with .ivy specs, run formal verification, build/extend protocol models, or triage MCP/LSP health. Routes to the matching specialist agent (verifier / builder / reviewer / triage / meta) or reads its own references for knowledge questions. This orchestrator runs first; the matching workflow specialist agent is invoked through this orchestrator's routing table, never directly."
+description: "Routes Ivy formal-verification work to the matching specialist agent (verifier, builder, reviewer, triage, meta). Use when working with .ivy specs, running formal verification, building or extending protocol models, or triaging MCP/LSP health. First entry point on every panther-ivy-plugin session."
 version: "1.0.0"
---
```

Body unchanged.

**Verification.** `python3 -c "import yaml; d=yaml.safe_load(open('skills/ivy/SKILL.md').read().split('---')[1]); print(len(d['description']))"` reports ≤ 250.

### Patch 3 — Sub-agent return-size caps

**Files:** `skills/ivy/SKILL.md`, `skills/build-ops/SKILL.md`, `skills/verify-ops/SKILL.md`, `skills/review-ops/SKILL.md`, `skills/meta-self-mod-ops/SKILL.md`
**Cap value:** uniform 800 words, matching the agent-side `<output_schema>` declaration in `agents/ivy-builder-agent.md:48`.

**Application.** For each dispatching skill, append `Return under 800 words; JSON output per <output_schema>.` to every `Agent(...)` dispatch example.

For `skills/ivy/SKILL.md`, the orchestrator's dispatch table is a Markdown summary, not full prompt examples. Add one prose line under `## Dispatch — workflow specialist agents`:

```markdown
**Return cap.** Every dispatch should specify `Return under 800 words; JSON output per <output_schema>.` in the prompt. Matches the agent-side cap declared in each agent's frontmatter.
```

For the four ops skills (`build-ops`, `verify-ops`, `review-ops`, `meta-self-mod-ops`), each existing `Agent(subagent_type=...)` example gets the cap appended to its `prompt:` value. Example, in `meta-self-mod-ops/SKILL.md` Phase 2 Step 1:

```diff
 Agent(subagent_type="Explore",
       description="Implement <task>",
-      prompt="<target files + change spec + acceptance criteria>")
+      prompt="<target files + change spec + acceptance criteria>. Return under 800 words; JSON output per <output_schema>.")
```

**Why uniform 800 rather than varying by agent.** Two reasons. First, every existing agent that already declares an `<output_schema>` uses ≤ 800 words; a uniform cap matches the existing contract. Second, varying caps per agent in the dispatch examples adds load on every reader to remember which agent gets which budget — and the cap is supposed to be the simple, visible shorthand for "small return."

**Verification.** `grep -nE 'Agent\(.*subagent_type' skills/ivy/SKILL.md skills/build-ops/SKILL.md skills/verify-ops/SKILL.md skills/review-ops/SKILL.md skills/meta-self-mod-ops/SKILL.md` followed by manual check that "Return under 800 words" appears within 5 lines of each match.

### Patch 4 — Manifest hardening

**File:** `.claude-plugin/plugin.json`
**Edits:** 3 — `repository` to object, two `userConfig` `enum` additions.

Enum values come straight from the existing `description` fields — no new vocabulary introduced.

```diff
   "license": "MIT",
   "keywords": ["ivy", "formal-verification", "protocol-testing", "panther", "interactive"],
-  "repository": "https://github.com/ElNiak/panther-ivy-plugin",
+  "repository": {"type": "git", "url": "https://github.com/ElNiak/panther-ivy-plugin"},
   "homepage": "https://github.com/ElNiak/panther-ivy-plugin",
```

```diff
     "log_level": {
       "title": "Log Level",
       "type": "string",
+      "enum": ["DEBUG", "INFO", "WARN", "ERROR"],
       "description": "Ivy LSP/MCP log verbosity (DEBUG, INFO, WARN, ERROR)",
       "default": "DEBUG",
       "sensitive": false
     },
```

```diff
     "statusline_mode": {
       "title": "Statusline Mode",
       "type": "string",
+      "enum": ["ivy-only", "minimal", "full-delegate", "suppress-overlaps"],
       "description": "How the plugin statusline composes with the global statusline: ivy-only | minimal | full-delegate | suppress-overlaps (default)",
       "default": "suppress-overlaps",
```

**Verification.**

```bash
python3 -c "import json; m=json.load(open('.claude-plugin/plugin.json')); \
print(type(m['repository']).__name__, \
'enum' in m['userConfig']['log_level'], \
'enum' in m['userConfig']['statusline_mode'])"
```

Should print `dict True True`.

### Patch 5 — `references/` scaffolding for `review-ops`

**Files:** `skills/review-ops/references/phase-4-trace-analysis.md` (new), `skills/review-ops/references/mpe-roles.md` (new), `skills/review-ops/SKILL.md` (collapsed body), audit report annotation.

#### New file: `skills/review-ops/references/phase-4-trace-analysis.md`

Extracted from current `review-ops/SKILL.md` lines 199–228 (~50 lines). Contains:

- Phase 4 entry condition (post-IUT trigger via `pending_dispatch(review, ...)` from verify Phase 5 with `reason` referencing `ivy_iut_test`).
- The `<HARD-GATE>` block for the G5 trace-analysis dispatch (3 × `g-fidelity-critic` parallel, asymmetric vote, verbatim G5 prompts).
- The fixed read order: `analysis/ivy_tester_results.json` → compile log → tester log → IUT log → pcap.
- Catalog slice references: `#100-107` + `#500-559` + `#560-589` (NSCT additions).
- Primary checks: `#501` (Ivy trace claims event, pcap shows nothing), `#505` (model bug misattributed to IUT).
- Constraint: critics MUST NOT re-invoke `ivy_iut_test`.
- PostToolUse hook (`assess-trace.py`) is backstop, not primary.
- Verdict actions for SOUND / UNSOUND(#NN) / ABSTAIN.
- Ivy-trace-vs-pcap cross-validation rule (events in Ivy log do not guarantee wire transmission).

#### New file: `skills/review-ops/references/mpe-roles.md`

Extracted from current Phase 2 Quality path lines 121–127 (~30 lines). Contains the three calibrated MPE role descriptions:

- **Conservative Architect** — 6-category structural audit (structural correctness, type safety, invariant completeness, action well-formedness, initialization, organization).
- **Pragmatic Engineer** — verification readiness, include trace correctness, layer coherence.
- **Adversarial Auditor** — red-team angles, edge cases, unreachable-but-asserted states.

Each role section enumerates the audit categories with one-line descriptions matching the current inline content verbatim.

#### Body collapse in `review-ops/SKILL.md`

**Phase 4 (lines 199–228) collapses to:**

```markdown
### Phase 4 — Trace analysis (post-IUT, optional)

Entered when review is dispatched on IUT-test results (typically via `pending_dispatch(review, ...)` from verify Phase 5 with a `reason` referencing `ivy_iut_test`). Skip this phase entirely if no IUT run is in scope.

**Read `references/phase-4-trace-analysis.md` when entering this phase.** It owns the G5 trace-analysis HARD-GATE, the 3-critic parallel-dispatch shape, the fixed read order, the catalog slice references, the verdict actions, and the Ivy-trace-vs-pcap cross-validation rule.
```

**Phase 2 Quality path MPE step (lines 121–127) collapses to:**

```markdown
2. **Multi-Perspective Exploration.** Apply the **Multi-Perspective Exploration (MPE)** pattern. Dispatch 3 sibling `Explore` agents in parallel — single message, three `Agent` tool calls (see `Skill(skill="panther-ivy-plugin:ivy")` `references/parallel-dispatch.md` for the canonical dispatch shape). Read `references/mpe-roles.md` for the calibrated role descriptions (Conservative Architect / Pragmatic Engineer / Adversarial Auditor) before composing the dispatch prompts.
```

#### Audit report annotation

In `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/.harness-audit/report-2026-04-29.md`, modify the Pillar 1 finding `context.progressive_disclosure` to:

- Keep the `review-ops` warning (action taken: reference scaffolding applied).
- Downgrade the `meta-self-mod-ops` warning to INFO with this rationale:
  > meta-self-mod-ops body 224 lines is under the strict 400-line progressive-disclosure threshold. The skill's explicit "References" section documents an intentional self-contained design. Finding downgraded to INFO; no action required.

**Verification.**

- `wc -l skills/review-ops/SKILL.md` reports ≤ 290.
- `ls skills/review-ops/references/phase-4-trace-analysis.md skills/review-ops/references/mpe-roles.md` succeeds.
- `grep -n 'phase-4-trace-analysis.md\|mpe-roles.md' skills/review-ops/SKILL.md` shows the two pointer lines in their expected positions (Phase 4 body, Phase 2 Quality MPE step).
- The audit report's `context.progressive_disclosure` finding now reads with the INFO downgrade for `meta-self-mod-ops`.

### Patch 6 — Failure-recovery cross-reference

**File:** `skills/ivy/SKILL.md`
**Edit:** 2 lines added under `## Dispatch — workflow specialist agents`, directly after the existing `Dispatch context (per agent-dispatch.md)` line.

```diff
 Dispatch context (per `agent-dispatch.md`): every dispatch fills `target_files`, `workspace`, `phase_context` plus agent-specific optional fields.
+
+Failure recovery: see `.claude/rules/agent-dispatch.md` for timeout, context-exhaustion, partial-output, malformed-output, and tool-not-found handling. The rule auto-loads on agent dispatch.
```

**Why surface the rule explicitly when it auto-loads.** A fresh reader of `ivy/SKILL.md` does not see the failure contract until they encounter the rule mid-session. The rule does load automatically, but the orchestrator body is the page that names it as part of the dispatch contract — having the cross-reference there makes the contract auditable from the orchestrator alone.

**Verification.** `grep -A1 'Dispatch context' skills/ivy/SKILL.md` shows the failure-recovery line directly after.

## Sequencing

The 5 patches touch 9 distinct files. None has authorship overlap with another patch except where two patches both edit `ivy/SKILL.md` (Patches 2, 3, 6) or both edit `review-ops/SKILL.md` (Patches 3, 5). To avoid conflicting edits during application, the sequence below batches edits to the same file.

1. **Patch 4** (manifest) — single file (`.claude-plugin/plugin.json`), lowest blast radius, fastest verification.
2. **Patch 2** (orchestrator description) — single line in `ivy/SKILL.md`. Verify with the truncation-length check.
3. **Patch 6** (failure-recovery cross-reference) — single line insertion in `ivy/SKILL.md`. Lands on the same file as Patch 2 but in a different section, so no merge.
4. **Patch 5** (references scaffolding) — 2 new files + body-collapse edits in `review-ops/SKILL.md` + audit-report annotation.
5. **Patch 3** (return caps) — touches the most files (5 skills including `ivy/SKILL.md` and `review-ops/SKILL.md`). Lands last so Patches 2/5/6 are already in the file when Patch 3 appends to dispatch examples.

## Acceptance criteria

This work is complete when all of the following hold:

- All five Patch verifications above pass.
- `git diff --stat` shows the 9 modified files plus 2 new files plus the audit-report annotation. No unintended files in the diff.
- The `harness-audit` skill's `audit_helpers.py` re-run on the plugin reports `body_lines` for `review-ops/SKILL.md` ≤ 290 (down from 365).
- A second run of `~/.claude/skills/harness-audit` against the plugin reports the `context.progressive_disclosure` finding for `meta-self-mod-ops` as INFO (or absent if the helper rubric is satisfied), and reports the `prompt.description_truncation` finding for `ivy/SKILL.md` as INFO (or absent).

## Rationale linkage

Each patch traces back to a specific Anthropic engineering quote from the audit report:

- Patch 2 → Q-E2 ("smallest possible set of high-signal tokens") — the truncated description wastes routing tokens.
- Patch 3 → Q-E9 ("Returns only a condensed, distilled summary of its work, often 1,000-2,000 tokens") — caller-side cap is the place to express intent.
- Patch 4 → No quote required; structural manifest hardening flagged by `plugin-validator`.
- Patch 5 → Q-E1, Q-E7 ("Reference files clearly from SKILL.md with guidance on when to read them") — progressive disclosure for ops skills preloaded at every spawn.
- Patch 6 → Q-A2 ("the harness caught the failure as a tool-call error and passed it back") — visible failure contract from the orchestrator body.

Quote IDs resolve to `~/.claude/skills/harness-audit/references/article-quotes.md`.

## Risks and mitigations

- **Risk:** Patch 5's body collapse changes the verbatim text the agent reads at every spawn. If the new pointer lines are missed by a future reader, they would not know to load the references.
  **Mitigation:** Each pointer line names the file path explicitly and uses the canonical `**Read `references/<file>.md` when entering this phase.**` form. The audit-skill's helper detects `references/` presence via the `has_references_dir` field, so the next audit run will catch a regression where the pointers get rewritten away.

- **Risk:** Patch 3's uniform 800-word cap could in some cases be too tight for a reviewer agent that needs to enumerate many findings.
  **Mitigation:** The cap matches the existing agent-side `<output_schema>` value already in production. The G5 dispatch in `review-ops` produces structured verdicts (SOUND / UNSOUND(#NN) / ABSTAIN), not free-form prose, so 800 words is generous. If a future return-size-too-tight report surfaces, raise the cap on the specific dispatch — uniform-by-default is not uniform-forever.

- **Risk:** Patch 6's added line duplicates content already auto-loaded by the rule.
  **Mitigation:** The new line is one cross-reference, not a restatement of the contract. It names the rule path and the failure-mode list, which is metadata; it does not duplicate the recovery procedure itself.

## Out-of-scope (deferred to separate brainstorms)

- **Item A — `skills/README.md` rewrite.** Whole-file rewrite to describe the 13-skill `*-ops` layout. Depends on the `tool-catalog.md:435` decision (whether to restore the missing `cross-cutting-*` and `workflow-navigate` skills) — if those are restored, the README's 18-skill layout becomes mostly correct again.

- **Item B — `tool-catalog.md:435` TODO resolution.** Decide: restore the two missing skills, redirect to existing skills that own the gate-verdict / plan-mode functions, or delete the cross-references. The TODO comment is already in place from the Patch 1 application.

- **Item D — Hook-tree four-pillar audit extension.** Add hook-specific checks to `~/.claude/skills/harness-audit/`. Independent of this plugin; can run in parallel.

## After this spec

Once this design is approved, the next step is to invoke the `superpowers:writing-plans` skill to produce a step-by-step implementation plan with subagent assignments and verification checkpoints. The plan will sequence the 5 patches in the recommended order above, name a verification command per step, and identify the file-ownership boundary so a single implementer can execute without conflict.
