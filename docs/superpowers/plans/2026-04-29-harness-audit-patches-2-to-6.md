# Harness Audit Patches 2-6 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply the five remaining patches from the 2026-04-29 panther-ivy-plugin harness audit (orchestrator description rewrite, sub-agent return-size caps, manifest hardening, references/ scaffolding for review-ops, and a failure-recovery cross-reference).

**Architecture:** Surgical text edits across 7 modified files plus 2 new reference files plus 1 audit-report annotation, all inside the deepest submodule (`panther-ivy-plugin`). Per-patch commits in the submodule, single submodule-pointer bump in the parent submodule and the worktree at the end. No new dependencies, no behavioural changes — these are documentation, manifest, and skill-body refinements that improve trigger surface, progressive disclosure, and trace-fidelity discipline.

**Tech Stack:** Plain Markdown (`.md`), JSON manifest (`plugin.json`), git for source control. Verification uses `python3` one-liners (yaml/json), `grep`, `wc`. Pre-commit hooks (`black`, `isort`, `ruff`, `check json`, `check yaml`) run automatically and must pass before commit.

**Source spec:** `docs/superpowers/specs/2026-04-29-harness-audit-patches-2-to-6-design.md`.

---

## Baseline state

**Worktree:** `/Users/elniak/Documents/Documents/Work/Project/Protocol-Testing-Security/PANTHER/master/.claude/worktrees/lsp-to-claude/`
Operate from this directory. Do not `cd` to the parent repository root.

**Plugin path (relative to worktree):** `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/`
This path is referred to as `${PLUGIN}` throughout the plan. The deepest submodule (`panther-ivy-plugin`) lives at `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/`.

**Patch 1 (already applied during the audit session, currently unstaged in `panther-ivy-plugin`):**
- `commands/nct-health.md`
- `skills/verification-failures/SKILL.md`
- `skills/verification-failures/references/debugging-methodology.md`
- `skills/verification-failures/references/debugging-environment.md`
- `.claude/rules/mcp-tool-reliability.md`
- `skills/ivy-toolkit/references/tool-catalog.md`

The audit report `.harness-audit/report-2026-04-29.md` is also untracked.

**Unrelated changes also present (DO NOT stage with our commits):**
- `agents/ivy-reviewer-agent.md`
- `agents/ivy-triage-agent.md`
- `agents/ivy-verifier-agent.md`
- `hooks/scripts/hook_utils.py`
- `hooks/scripts/notify-mcp-disconnect.py`
- `hooks/scripts/render-summary.py`
- `tests/test_emit_hook_output.py`
- `tests/test_render_summary.py`

These were modified before this session. Every `git add` step in this plan names files explicitly to avoid accidental inclusion. Never use `git add .`, `git add -A`, or `git add -u`.

**Git scope:** Tasks 1-7 commit in the deepest submodule (`${PLUGIN}/../`, i.e. `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/`). Task 8 bumps submodule pointers in the parent submodule (`panther/plugins/services/testers/panther_ivy/`) and in the worktree.

**No tests exist for the artifacts being changed.** Verification per task uses deterministic shell commands described in the spec.

---

## Task 1: Baseline commit — Patch 1 changes

**Files:**
- Stage (already modified): `commands/nct-health.md`, `skills/verification-failures/SKILL.md`, `skills/verification-failures/references/debugging-methodology.md`, `skills/verification-failures/references/debugging-environment.md`, `.claude/rules/mcp-tool-reliability.md`, `skills/ivy-toolkit/references/tool-catalog.md`
- Stage (untracked, new): `.harness-audit/report-2026-04-29.md`

- [ ] **Step 1: Confirm Patch 1 changes intact**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin
grep -nE 'Skill\(skill="panther-ivy-plugin:workflow-(triage|verify|build|review|navigate)"' \
  skills/ .claude/rules/ commands/ -r 2>/dev/null
```

Expected: only `skills/ivy-toolkit/references/tool-catalog.md:435` (the deliberate `<!-- TODO -->`-gated line).

- [ ] **Step 2: Stage the 6 Patch 1 files plus the audit report**

```bash
git add commands/nct-health.md \
        skills/verification-failures/SKILL.md \
        skills/verification-failures/references/debugging-methodology.md \
        skills/verification-failures/references/debugging-environment.md \
        .claude/rules/mcp-tool-reliability.md \
        skills/ivy-toolkit/references/tool-catalog.md \
        .harness-audit/report-2026-04-29.md
```

- [ ] **Step 3: Confirm staged file list matches expectation**

```bash
git diff --cached --name-only
```

Expected (exactly 7 lines):
```
.claude/rules/mcp-tool-reliability.md
.harness-audit/report-2026-04-29.md
commands/nct-health.md
skills/ivy-toolkit/references/tool-catalog.md
skills/verification-failures/SKILL.md
skills/verification-failures/references/debugging-environment.md
skills/verification-failures/references/debugging-methodology.md
```

If any of the 8 unrelated files appear in the list, run `git restore --staged <file>` for each and re-verify.

- [ ] **Step 4: Commit**

```bash
git commit -m "$(cat <<'EOF'
fix: rewrite broken Skill() invocations to dispatch ivy-triage-agent (harness-audit Patch 1)

Five Skill(skill="panther-ivy-plugin:workflow-triage") call sites referenced a removed skill name and would have returned "Unknown skill" at runtime. Rewritten to Agent(subagent_type="panther-ivy-plugin:ivy-triage-agent", ...) which restores intent and matches the rest of the plugin's dispatch model. Sixth call site (tool-catalog.md:435) preserved behind a <!-- TODO --> comment because it references two skills that do not exist anywhere in the plugin (cross-cutting-reflection-patterns, workflow-navigate); pending a separate refactor decision.

Audit report saved to .harness-audit/report-2026-04-29.md.
EOF
)"
```

Expected: pre-commit hooks pass (`black`, `isort`, `ruff` for any python touched — none here, so skipped; `check json`, `check yaml` skipped; `trim trailing whitespace`, `fix end of files`, `check for added large files`, `check for merge conflicts`, `Test Syntax Check` pass).

---

## Task 2: Patch 4 — Manifest hardening

**Files:**
- Modify: `${PLUGIN}/.claude-plugin/plugin.json` — `repository` to object form, two `userConfig` `enum` additions

- [ ] **Step 1: Apply Edit — `repository` to object**

In `panther-ivy-plugin/.claude-plugin/plugin.json`, replace:

```json
"repository": "https://github.com/ElNiak/panther-ivy-plugin",
```

with:

```json
"repository": {"type": "git", "url": "https://github.com/ElNiak/panther-ivy-plugin"},
```

- [ ] **Step 2: Apply Edit — log_level enum**

Replace:

```json
    "log_level": {
      "title": "Log Level",
      "type": "string",
      "description": "Ivy LSP/MCP log verbosity (DEBUG, INFO, WARN, ERROR)",
      "default": "DEBUG",
      "sensitive": false
    },
```

with:

```json
    "log_level": {
      "title": "Log Level",
      "type": "string",
      "enum": ["DEBUG", "INFO", "WARN", "ERROR"],
      "description": "Ivy LSP/MCP log verbosity (DEBUG, INFO, WARN, ERROR)",
      "default": "DEBUG",
      "sensitive": false
    },
```

- [ ] **Step 3: Apply Edit — statusline_mode enum**

Replace:

```json
    "statusline_mode": {
      "title": "Statusline Mode",
      "type": "string",
      "description": "How the plugin statusline composes with the global statusline: ivy-only | minimal | full-delegate | suppress-overlaps (default)",
      "default": "suppress-overlaps",
      "sensitive": false
    },
```

with:

```json
    "statusline_mode": {
      "title": "Statusline Mode",
      "type": "string",
      "enum": ["ivy-only", "minimal", "full-delegate", "suppress-overlaps"],
      "description": "How the plugin statusline composes with the global statusline: ivy-only | minimal | full-delegate | suppress-overlaps (default)",
      "default": "suppress-overlaps",
      "sensitive": false
    },
```

- [ ] **Step 4: Verify**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin
python3 -c "import json; m=json.load(open('plugins/panther-ivy-plugin/.claude-plugin/plugin.json')); print(type(m['repository']).__name__, 'enum' in m['userConfig']['log_level'], 'enum' in m['userConfig']['statusline_mode'])"
```

Expected output: `dict True True`

- [ ] **Step 5: Stage and commit**

```bash
git add plugins/panther-ivy-plugin/.claude-plugin/plugin.json
git diff --cached --name-only
```

Expected: exactly `plugins/panther-ivy-plugin/.claude-plugin/plugin.json`.

```bash
git commit -m "$(cat <<'EOF'
chore: harden plugin manifest (harness-audit Patch 4)

Convert repository to {type, url} object form and add enum constraints
to userConfig.log_level and userConfig.statusline_mode. Enum values come
from the existing description fields; no new vocabulary introduced.
EOF
)"
```

Expected: `check json` pre-commit hook passes; commit lands.

---

## Task 3: Patch 2 — Orchestrator description rewrite

**Files:**
- Modify: `${PLUGIN}/skills/ivy/SKILL.md:3` — replace 466-char description with 248-char rewrite

- [ ] **Step 1: Read current frontmatter**

Read `skills/ivy/SKILL.md` lines 1-6 to confirm current frontmatter shape before editing.

- [ ] **Step 2: Apply Edit — description**

Replace exact line 3 (the `description:` field):

```yaml
description: "You MUST use this on every panther-ivy-plugin session entry where the user wants to work with .ivy specs, run formal verification, build/extend protocol models, or triage MCP/LSP health. Routes to the matching specialist agent (verifier / builder / reviewer / triage / meta) or reads its own references for knowledge questions. This orchestrator runs first; the matching workflow specialist agent is invoked through this orchestrator's routing table, never directly."
```

with:

```yaml
description: "Routes Ivy formal-verification work to the matching specialist agent (verifier, builder, reviewer, triage, meta). Use when working with .ivy specs, running formal verification, building or extending protocol models, or triaging MCP/LSP health. First entry point on every panther-ivy-plugin session."
```

- [ ] **Step 3: Verify length**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin
python3 -c "import yaml; \
fm = open('plugins/panther-ivy-plugin/skills/ivy/SKILL.md').read().split('---')[1]; \
d = yaml.safe_load(fm); \
print('len:', len(d['description'])); \
print('first_word:', d['description'].split()[0])"
```

Expected: `len: 248` (or close — must be ≤ 250) and `first_word: Routes` (third person, not "You").

- [ ] **Step 4: Stage and commit**

```bash
git add plugins/panther-ivy-plugin/skills/ivy/SKILL.md
git diff --cached --name-only
```

Expected: exactly `plugins/panther-ivy-plugin/skills/ivy/SKILL.md`.

```bash
git commit -m "$(cat <<'EOF'
refactor: rewrite ivy orchestrator description for trigger surface (harness-audit Patch 2)

Replace 466-char second-person "You MUST use this..." description with a
248-char third-person rewrite. Harness truncates descriptions at ~250
chars; the routing payload (specialist list, "first entry point")
previously lived past the cutoff and was invisible at trigger time.
Body unchanged.
EOF
)"
```

---

## Task 4: Patch 6 — Failure-recovery cross-reference in `ivy/SKILL.md`

**Files:**
- Modify: `${PLUGIN}/skills/ivy/SKILL.md` — insert 2 lines under `## Dispatch — workflow specialist agents`, after the existing `Dispatch context (per agent-dispatch.md)` line

- [ ] **Step 1: Apply Edit**

Locate this paragraph (currently at line 60 after Patch 2 lands):

```markdown
Dispatch context (per `agent-dispatch.md`): every dispatch fills `target_files`, `workspace`, `phase_context` plus agent-specific optional fields.
```

Replace with:

```markdown
Dispatch context (per `agent-dispatch.md`): every dispatch fills `target_files`, `workspace`, `phase_context` plus agent-specific optional fields.

Failure recovery: see `.claude/rules/agent-dispatch.md` for timeout, context-exhaustion, partial-output, malformed-output, and tool-not-found handling. The rule auto-loads on agent dispatch.
```

- [ ] **Step 2: Verify**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin
grep -A2 'Dispatch context' plugins/panther-ivy-plugin/skills/ivy/SKILL.md | head -4
```

Expected: shows `Dispatch context...` line, blank line, `Failure recovery: see ...` line.

- [ ] **Step 3: Stage and commit**

```bash
git add plugins/panther-ivy-plugin/skills/ivy/SKILL.md
git diff --cached --name-only
```

Expected: exactly `plugins/panther-ivy-plugin/skills/ivy/SKILL.md`.

```bash
git commit -m "$(cat <<'EOF'
docs: cross-reference agent-dispatch.md from ivy orchestrator body (harness-audit Patch 6)

Insert one line under "Dispatch — workflow specialist agents" naming
.claude/rules/agent-dispatch.md as the authority for timeout /
context-exhaustion / partial-output / malformed-output / tool-not-found
handling. The rule auto-loads on agent dispatch; the cross-reference
makes the failure contract auditable from the orchestrator body alone.
EOF
)"
```

---

## Task 5: Patch 5 — references/ scaffolding for `review-ops`

**Files:**
- Create: `${PLUGIN}/skills/review-ops/references/phase-4-trace-analysis.md` (~50 lines)
- Create: `${PLUGIN}/skills/review-ops/references/mpe-roles.md` (~30 lines)
- Modify: `${PLUGIN}/skills/review-ops/SKILL.md` — collapse Phase 4 (lines 199-228) and Phase 2 Quality MPE step (lines 121-127) to pointer lines
- Modify: `${PLUGIN}/.harness-audit/report-2026-04-29.md` — annotate the `context.progressive_disclosure` finding with the meta-self-mod-ops INFO downgrade

- [ ] **Step 1: Create references/ directory**

```bash
mkdir -p panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/skills/review-ops/references
```

- [ ] **Step 2: Write `phase-4-trace-analysis.md`**

Create `${PLUGIN}/skills/review-ops/references/phase-4-trace-analysis.md` with this content (verbatim from the spec):

````markdown
# Phase 4 — Trace analysis (post-IUT, optional)

Reference loaded from `review-ops/SKILL.md` Phase 4 when review is dispatched on IUT-test results (typically via `pending_dispatch(review, ...)` from verify Phase 5 with a `reason` referencing `ivy_iut_test`). Skip the entire phase if no IUT run is in scope.

## G5 trace-analysis gate (inline dispatch)

<HARD-GATE>
G5 trace-analysis gate (every IUT-test scope): apply the
**Multi-Perspective Exploration (MPE)** pattern. The reviewer agent dispatches
`g-fidelity-critic` ×3 in parallel (single message, three `Agent` calls) for
asymmetric vote, using verbatim G5 prompts
(`critic_prompts/g5_trace_analysis`), catalog slices `#100-107` +
`#500-559` (+ `#560-589` for NSCT). Critics analyse the existing run's output
directory in fixed read order: `analysis/ivy_tester_results.json` → compile
log → tester log → IUT log → pcap. Primary checks: `#501` (Ivy trace claims
event, pcap shows nothing) and `#505` (model bug misattributed to IUT).
Critics may NOT re-invoke `ivy_iut_test`. The PostToolUse hook
(`assess-trace.py`) is a backstop — the reviewer is responsible for inline
dispatch and must not defer to the hook for the primary G5 invocation.
Dispatch shape: `Skill(skill="panther-ivy-plugin:ivy")`
`references/parallel-dispatch.md`.
</HARD-GATE>

## Verdict actions

- **SOUND** — IUT/model fidelity confirmed; record the gate verdict in the journal and proceed to completion.
- **UNSOUND(#NN)** — write `[GAP: #NN]` markers and feed back into Phase 3 findings; the trace-fidelity finding is treated as ERROR severity unless the user explicitly DEFERRED-promotes it with date + reason.
- **ABSTAIN** — append `gate_verdict{verdict: "abstain", abstain_reason: "<text>"}` and ask the user whether to re-run the IUT test (route via `pending_dispatch(verify, phase_hint="iut")`) or accept inconclusive.

## Cross-validation rule

For Ivy trace vs. wire validation discipline — events in the Ivy log do not guarantee wire transmission — always cross-validate via pcap (`tshark`). The G5 catalog patterns above are the calibrated source for the model-bug-vs-IUT-bug classification; do not classify without the gate.
````

- [ ] **Step 3: Write `mpe-roles.md`**

Create `${PLUGIN}/skills/review-ops/references/mpe-roles.md` with this content (verbatim from the spec):

````markdown
# MPE roles — Quality path (Conservative Architect / Pragmatic Engineer / Adversarial Auditor)

Reference loaded from `review-ops/SKILL.md` Phase 2 Quality path before composing the three Multi-Perspective Exploration (MPE) Explore-agent dispatches. The reviewer agent dispatches all three in parallel — single message, three `Agent` tool calls — and aggregates findings before classifying severity.

## Conservative Architect

6-category structural audit:

- **Structural correctness** — headers, includes, circular dependencies.
- **Type safety** — annotations, type mismatches, enumerations, sentinel values.
- **Invariant completeness** — ungrounded variables, missing invariants, invariant strength.
- **Action well-formedness** — preconditions, postconditions, guards.
- **Initialization** — `after init` blocks, consistency with invariants.
- **Organization** — naming, isolate boundaries, duplication.

## Pragmatic Engineer

- **Verification readiness** — will `ivy_verify` pass on this state of the model?
- **Include trace correctness** — resolved paths, missing modules, layer-include ordering.
- **Layer coherence** — consistent use of the 14-layer template, no off-template layers.

## Adversarial Auditor

Red-team the model:

- Edge cases the structured roles miss.
- Assumptions baked into the spec.
- Unreachable-but-asserted states.
- Counterexamples the verifier might find but the structural audit would not.

## Aggregation

Bucket all findings from the three roles by severity: ERROR / WARNING / INFO (per `.claude/rules/ivy-formatting.md` "Finding severity"). Different roles may flag the same issue from different angles; deduplicate by file:line + finding category before reporting.
````

- [ ] **Step 4: Collapse Phase 4 in `review-ops/SKILL.md`**

Replace Phase 4 (currently lines 199-228; the section starting `### Phase 4 — Trace analysis (post-IUT, optional)` and ending before `## Process Flow`):

```markdown
### Phase 4 — Trace analysis (post-IUT, optional)

Entered when review is dispatched on IUT-test results (typically via `pending_dispatch(review, ...)` from verify Phase 5 with a `reason` referencing `ivy_iut_test`). Skip this phase entirely if no IUT run is in scope.

#### G5 trace-analysis gate (inline dispatch)

<HARD-GATE>
G5 trace-analysis gate (every IUT-test scope): apply the
**Multi-Perspective Exploration (MPE)** pattern. The reviewer agent dispatches
`g-fidelity-critic` ×3 in parallel (single message, three `Agent` calls) for
asymmetric vote, using verbatim G5 prompts
(`critic_prompts/g5_trace_analysis`), catalog slices `#100-107` +
`#500-559` (+ `#560-589` for NSCT). Critics analyse the existing run's output
directory in fixed read order: `analysis/ivy_tester_results.json` → compile
log → tester log → IUT log → pcap. Primary checks: `#501` (Ivy trace claims
event, pcap shows nothing) and `#505` (model bug misattributed to IUT).
Critics may NOT re-invoke `ivy_iut_test`. The PostToolUse hook
(`assess-trace.py`) is a backstop — the reviewer is responsible for inline
dispatch and must not defer to the hook for the primary G5 invocation.
Dispatch shape: `Skill(skill="panther-ivy-plugin:ivy")`
`references/parallel-dispatch.md`.
</HARD-GATE>

Verdict actions:

- **SOUND** — IUT/model fidelity confirmed; record the gate verdict in the journal and proceed to completion.
- **UNSOUND(#NN)** — write `[GAP: #NN]` markers and feed back into Phase 3 findings; the trace-fidelity finding is treated as ERROR severity unless the user explicitly DEFERRED-promotes it with date + reason.
- **ABSTAIN** — append `gate_verdict{verdict: "abstain", abstain_reason: "<text>"}` and ask the user whether to re-run the IUT test (route via `pending_dispatch(verify, phase_hint="iut")`) or accept inconclusive.

For Ivy trace vs. wire validation discipline — events in the Ivy log do not guarantee wire transmission — always cross-validate via pcap (`tshark`). The G5 catalog patterns above are the calibrated source for the model-bug-vs-IUT-bug classification; do not classify without the gate.
```

with:

```markdown
### Phase 4 — Trace analysis (post-IUT, optional)

Entered when review is dispatched on IUT-test results (typically via `pending_dispatch(review, ...)` from verify Phase 5 with a `reason` referencing `ivy_iut_test`). Skip this phase entirely if no IUT run is in scope.

**Read `references/phase-4-trace-analysis.md` when entering this phase.** It owns the G5 trace-analysis HARD-GATE, the 3-critic parallel-dispatch shape, the fixed read order, the catalog slice references, the verdict actions, and the Ivy-trace-vs-pcap cross-validation rule.
```

- [ ] **Step 5: Collapse Phase 2 Quality MPE step in `review-ops/SKILL.md`**

Replace the existing MPE step in Phase 2 Quality path (currently lines 121-127):

```markdown
2. **Multi-Perspective Exploration.** Apply the **Multi-Perspective Exploration (MPE)** pattern. Dispatch 3 sibling `Explore` agents in parallel — single message, three `Agent` tool calls (`Skill(skill="panther-ivy-plugin:ivy")` `references/parallel-dispatch.md` for the canonical dispatch shape). The three roles:

   - **Conservative Architect** — 6-category structural audit: structural correctness (headers, includes, circular deps), type safety (annotations, mismatches, enumerations), invariant completeness (ungrounded vars, missing invariants, strength), action well-formedness (preconditions, postconditions, guards), initialization (`after init` blocks, consistency with invariants), organization (naming, isolate boundaries, duplication).
   - **Pragmatic Engineer** — verification readiness (will `ivy_verify` pass?), include trace correctness (resolved paths, missing modules), layer coherence (consistent use of the 14-layer template).
   - **Adversarial Auditor** — red-team the model: edge cases the structured roles miss, assumptions in the spec, unreachable-but-asserted states.
```

with:

```markdown
2. **Multi-Perspective Exploration.** Apply the **Multi-Perspective Exploration (MPE)** pattern. Dispatch 3 sibling `Explore` agents in parallel — single message, three `Agent` tool calls (see `Skill(skill="panther-ivy-plugin:ivy")` `references/parallel-dispatch.md` for the canonical dispatch shape). Read `references/mpe-roles.md` for the calibrated role descriptions (Conservative Architect / Pragmatic Engineer / Adversarial Auditor) before composing the dispatch prompts.
```

- [ ] **Step 6: Annotate the audit report**

In `${PLUGIN}/.harness-audit/report-2026-04-29.md`, locate the bullet:

```markdown
- **[WARNING] context.progressive_disclosure — `skills/review-ops/` and `skills/meta-self-mod-ops/` (no `references/` directory at all)**
```

Replace with:

```markdown
- **[WARNING] context.progressive_disclosure — `skills/review-ops/`** (resolved 2026-04-29 by Patch 5: created `references/phase-4-trace-analysis.md` and `references/mpe-roles.md`; body collapsed to pointer lines.)
- **[INFO] context.progressive_disclosure — `skills/meta-self-mod-ops/` (downgraded from WARNING on 2026-04-29).** meta-self-mod-ops body 224 lines is under the strict 400-line progressive-disclosure threshold. The skill's explicit "References" section documents an intentional self-contained design. Finding downgraded to INFO; no action required.
```

- [ ] **Step 7: Verify**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin
ls plugins/panther-ivy-plugin/skills/review-ops/references/phase-4-trace-analysis.md \
   plugins/panther-ivy-plugin/skills/review-ops/references/mpe-roles.md
wc -l plugins/panther-ivy-plugin/skills/review-ops/SKILL.md
grep -n 'phase-4-trace-analysis.md\|mpe-roles.md' plugins/panther-ivy-plugin/skills/review-ops/SKILL.md
```

Expected: both reference files exist; `wc -l` reports a number ≤ 290 (originally 365, dropping ~75 lines of inlined content); `grep` shows two pointer matches in the body.

- [ ] **Step 8: Stage and commit**

```bash
git add plugins/panther-ivy-plugin/skills/review-ops/references/phase-4-trace-analysis.md \
        plugins/panther-ivy-plugin/skills/review-ops/references/mpe-roles.md \
        plugins/panther-ivy-plugin/skills/review-ops/SKILL.md \
        plugins/panther-ivy-plugin/.harness-audit/report-2026-04-29.md
git diff --cached --name-only
```

Expected (4 files):
```
plugins/panther-ivy-plugin/.harness-audit/report-2026-04-29.md
plugins/panther-ivy-plugin/skills/review-ops/SKILL.md
plugins/panther-ivy-plugin/skills/review-ops/references/mpe-roles.md
plugins/panther-ivy-plugin/skills/review-ops/references/phase-4-trace-analysis.md
```

```bash
git commit -m "$(cat <<'EOF'
refactor: extract Phase 4 trace analysis and MPE roles to references/ (harness-audit Patch 5)

Create skills/review-ops/references/phase-4-trace-analysis.md (~50
lines, owns G5 HARD-GATE + read order + verdict actions) and
references/mpe-roles.md (~30 lines, owns the three calibrated MPE role
descriptions). Body of skills/review-ops/SKILL.md collapses Phase 4 and
Phase 2 Quality MPE step to pointer lines, dropping the body from 365
to <290 lines.

meta-self-mod-ops finding downgraded from WARNING to INFO in the audit
report — body 224 lines is under the strict 400-line threshold and the
skill explicitly declares its references-free design.
EOF
)"
```

---

## Task 6: Patch 3 — Sub-agent return-size caps

**Files:**
- Modify: `${PLUGIN}/skills/ivy/SKILL.md` — add 1 prose line under `## Dispatch — workflow specialist agents`
- Modify: `${PLUGIN}/skills/build-ops/SKILL.md` — add 1 prose return-cap directive under iron-law section
- Modify: `${PLUGIN}/skills/verify-ops/SKILL.md` — add 1 prose directive
- Modify: `${PLUGIN}/skills/review-ops/SKILL.md` — add 1 prose directive
- Modify: `${PLUGIN}/skills/meta-self-mod-ops/SKILL.md` — add 1 prose directive AND amend 3 inline `Agent(...)` examples (lines 80, 92, 111 of the pre-Patch-5 body; recompute after Patch 5 lands)

**Order constraint:** This task lands AFTER Patches 2/5/6 because it edits `ivy/SKILL.md` and `review-ops/SKILL.md`, both already touched by earlier patches. Editing them last avoids overlapping diffs in the same pre-commit window.

- [ ] **Step 1: Locate the insertion site for `ivy/SKILL.md`**

Find the line immediately after the failure-recovery cross-reference added by Patch 6 (Task 4):

```markdown
Failure recovery: see `.claude/rules/agent-dispatch.md` for timeout, context-exhaustion, partial-output, malformed-output, and tool-not-found handling. The rule auto-loads on agent dispatch.
```

Replace with:

```markdown
Failure recovery: see `.claude/rules/agent-dispatch.md` for timeout, context-exhaustion, partial-output, malformed-output, and tool-not-found handling. The rule auto-loads on agent dispatch.

**Return cap.** Every dispatch should specify `Return under 800 words; JSON output per <output_schema>.` in the prompt. Matches the agent-side cap declared in each agent's frontmatter.
```

- [ ] **Step 2: Add return-cap directive to `build-ops/SKILL.md`**

Locate the section between the end of the iron-law block and the `## Phases` header. Insert immediately before the `## Phases` heading:

```markdown
## Sub-agent dispatch — return cap

Every `Agent(...)` dispatch in this skill should specify `Return under 800 words; JSON output per <output_schema>.` in the prompt. Matches the agent-side cap declared in each specialist agent's frontmatter and keeps the lead's context lean.

```

- [ ] **Step 3: Add return-cap directive to `verify-ops/SKILL.md`**

Same pattern as Step 2 — insert the same `## Sub-agent dispatch — return cap` section between the end of the iron-law block and the `## Phases` header.

- [ ] **Step 4: Add return-cap directive to `review-ops/SKILL.md`**

Same pattern as Step 2 — insert between the end of the iron-law block and the `## Phases` header.

- [ ] **Step 5: Add return-cap directive AND amend inline dispatches in `meta-self-mod-ops/SKILL.md`**

Step 5a — directive:

Insert the same `## Sub-agent dispatch — return cap` section between the end of the iron-law block (`</iron-law>` closing tag) and the `## Phases` header.

Step 5b — amend implementer dispatch (currently around line 80):

Replace:

```python
Agent(subagent_type="Explore",
      description="Implement <task>",
      prompt="<target files + change spec + acceptance criteria>")
```

with:

```python
Agent(subagent_type="Explore",
      description="Implement <task>",
      prompt="<target files + change spec + acceptance criteria>. Return under 800 words; JSON output per <output_schema>.")
```

Step 5c — amend spec-compliance reviewer dispatch (around line 92):

Replace:

```python
Agent(subagent_type="panther-ivy-plugin:model-reviewer",
      description="Spec-compliance review of <task>",
      prompt="<diff + original spec + acceptance criteria>")
```

with:

```python
Agent(subagent_type="panther-ivy-plugin:model-reviewer",
      description="Spec-compliance review of <task>",
      prompt="<diff + original spec + acceptance criteria>. Return under 800 words; JSON output per <output_schema>.")
```

Step 5d — amend plugin-conventions reviewer dispatch (around line 111):

Replace:

```python
Agent(subagent_type="panther-ivy-plugin:plugin-conventions-reviewer",
      description="Plugin-conventions review of <task>",
      prompt="<diff + plugin-conventions checklist>")
```

with:

```python
Agent(subagent_type="panther-ivy-plugin:plugin-conventions-reviewer",
      description="Plugin-conventions review of <task>",
      prompt="<diff + plugin-conventions checklist>. Return under 800 words; JSON output per <output_schema>.")
```

- [ ] **Step 6: Verify all 5 skills carry the directive**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin
for f in plugins/panther-ivy-plugin/skills/ivy/SKILL.md \
         plugins/panther-ivy-plugin/skills/build-ops/SKILL.md \
         plugins/panther-ivy-plugin/skills/verify-ops/SKILL.md \
         plugins/panther-ivy-plugin/skills/review-ops/SKILL.md \
         plugins/panther-ivy-plugin/skills/meta-self-mod-ops/SKILL.md; do
  echo "=== $f ==="
  grep -c '800 words' "$f"
done
```

Expected: each file reports at least 1 match. (`meta-self-mod-ops` reports ≥ 4: 1 directive + 3 inline amendments.)

- [ ] **Step 7: Stage and commit**

```bash
git add plugins/panther-ivy-plugin/skills/ivy/SKILL.md \
        plugins/panther-ivy-plugin/skills/build-ops/SKILL.md \
        plugins/panther-ivy-plugin/skills/verify-ops/SKILL.md \
        plugins/panther-ivy-plugin/skills/review-ops/SKILL.md \
        plugins/panther-ivy-plugin/skills/meta-self-mod-ops/SKILL.md
git diff --cached --name-only
```

Expected (5 files):
```
plugins/panther-ivy-plugin/skills/build-ops/SKILL.md
plugins/panther-ivy-plugin/skills/ivy/SKILL.md
plugins/panther-ivy-plugin/skills/meta-self-mod-ops/SKILL.md
plugins/panther-ivy-plugin/skills/review-ops/SKILL.md
plugins/panther-ivy-plugin/skills/verify-ops/SKILL.md
```

```bash
git commit -m "$(cat <<'EOF'
docs: add caller-side return-size caps to sub-agent dispatches (harness-audit Patch 3)

Add a "Sub-agent dispatch — return cap" prose directive to each of the
five dispatching skills (ivy, build-ops, verify-ops, review-ops,
meta-self-mod-ops) instructing the lead to specify "Return under 800
words; JSON output per <output_schema>" in every dispatch prompt.

Amend the three inline Agent(...) examples in meta-self-mod-ops to
include the cap explicitly.

Cap value matches the agent-side <output_schema> declaration in
agents/ivy-builder-agent.md (≤ 800 words). Restores caller-side
explicitness per Anthropic context-engineering Q-E9.
EOF
)"
```

---

## Task 7: Final verification — re-run the audit helper

**Files:** None modified; this is a verification-only task.

- [ ] **Step 1: Re-run the audit helper on the plugin**

```bash
P="panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin"
python3 ~/.claude/skills/harness-audit/scripts/audit_helpers.py audit plugin "$PWD/$P" > "$TMPDIR/audit_post.json"
python3 -c "import json; d=json.load(open('$TMPDIR/audit_post.json')); \
ivy = next(s for s in d['skills'] if s['frontmatter']['name'] == 'ivy'); \
review = next(s for s in d['skills'] if s['frontmatter']['name'] == 'review-ops'); \
print('ivy desc len:', ivy['frontmatter']['description_length']); \
print('review-ops body lines:', review['body_lines']); \
print('review-ops has refs:', review['has_references_dir'])"
```

Expected:

```
ivy desc len: 248
review-ops body lines: <= 290
review-ops has refs: True
```

- [ ] **Step 2: Confirm no remaining drifted Skill() invocations (regression check)**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin
grep -rnE 'Skill\(skill="panther-ivy-plugin:workflow-' plugins/panther-ivy-plugin/skills plugins/panther-ivy-plugin/.claude plugins/panther-ivy-plugin/commands 2>/dev/null
```

Expected: only the deliberate `<!-- TODO -->`-gated line in `tool-catalog.md:435`. Output should look like:

```
plugins/panther-ivy-plugin/skills/ivy-toolkit/references/tool-catalog.md:<line>:Detailed payload shapes for `gate_verdict` live in the reflection-patterns skill (load via `Skill(skill="panther-ivy-plugin:cross-cutting-reflection-patterns")`; ...
```

- [ ] **Step 3: Confirm git status is clean except for the 8 unrelated pre-existing changes**

```bash
git status --short
```

Expected: only the 8 unrelated files from the baseline (`agents/ivy-{reviewer,triage,verifier}-agent.md`, `hooks/scripts/{hook_utils,notify-mcp-disconnect,render-summary}.py`, `tests/test_emit_hook_output.py`, `tests/test_render_summary.py`). No staged or working-tree modifications from our patches.

---

## Task 8: Submodule-pointer bumps (parent + worktree)

**Files:**
- Modify (pointer-bump only, no content): `panther/plugins/services/testers/panther_ivy/` (the parent submodule's view of the `panther-ivy-plugin` SHA)
- Modify (pointer-bump only): the worktree's view of `panther/plugins/services/testers/panther_ivy/` SHA

- [ ] **Step 1: Capture deepest-submodule HEAD SHA**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin
NEW_SHA=$(git rev-parse HEAD)
echo "panther-ivy-plugin HEAD: $NEW_SHA"
```

- [ ] **Step 2: Bump parent-submodule pointer**

```bash
cd ../..
# now in panther/plugins/services/testers/panther_ivy/
git status --short
```

Expected: shows `M submodules/panther-ivy-plugin` (modified-pointer marker).

```bash
git add submodules/panther-ivy-plugin
git commit -m "$(cat <<'EOF'
chore: bump panther-ivy-plugin submodule (harness-audit Patches 1-6)

Captures Tasks 1-7 of the 2026-04-29 harness audit follow-up:
- Patch 1: workflow-name drift (5 Skill() rewrites + 1 TODO) — applied in audit
- Patch 2: ivy/SKILL.md description rewrite (466 → 248 chars)
- Patch 3: caller-side sub-agent return-size cap (5 skills)
- Patch 4: plugin.json hardening (repository, 2 enums)
- Patch 5: review-ops references/ scaffolding (Phase 4 + MPE roles)
- Patch 6: failure-recovery cross-reference in ivy/SKILL.md
EOF
)"
```

- [ ] **Step 3: Bump worktree pointer**

```bash
cd ../../../../..
# now in worktree root (.../lsp-to-claude/)
git status --short
```

Expected: shows `M panther/plugins/services/testers/panther_ivy` (modified-pointer marker), plus any unrelated worktree changes.

```bash
git add panther/plugins/services/testers/panther_ivy
git diff --cached --name-only
```

Expected: exactly `panther/plugins/services/testers/panther_ivy`.

```bash
git commit -m "$(cat <<'EOF'
chore: bump panther_ivy submodule (harness-audit Patches 1-6)

Captures the parent-submodule pointer bump for the harness-audit
follow-up applied in panther-ivy-plugin (Patches 1 through 6 — see
docs/superpowers/specs/2026-04-29-harness-audit-patches-2-to-6-design.md
for the spec, docs/superpowers/plans/2026-04-29-harness-audit-patches-2-to-6.md
for the implementation plan).
EOF
)"
```

- [ ] **Step 4: Final git log review**

```bash
git log --oneline -7
```

Expected: 7 commits, in this order from newest to oldest:

```
chore: bump panther_ivy submodule (harness-audit Patches 1-6)
docs: spec for harness-audit Patches 2-6 (panther-ivy-plugin)   ← already on the worktree from prior session
```

…and inside the panther-ivy-plugin submodule (from `git log --oneline -7` after `cd panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin`):

```
docs: add caller-side return-size caps to sub-agent dispatches (harness-audit Patch 3)
refactor: extract Phase 4 trace analysis and MPE roles to references/ (harness-audit Patch 5)
docs: cross-reference agent-dispatch.md from ivy orchestrator body (harness-audit Patch 6)
refactor: rewrite ivy orchestrator description for trigger surface (harness-audit Patch 2)
chore: harden plugin manifest (harness-audit Patch 4)
fix: rewrite broken Skill() invocations to dispatch ivy-triage-agent (harness-audit Patch 1)
```

---

## Self-review checklist (run after writing the plan, fix inline)

- **Spec coverage.** Patches 2, 3, 4, 5, 6 are each implemented in Tasks 3, 6, 2, 5, 4 respectively. The audit report annotation (downgrading meta-self-mod-ops) is in Task 5 Step 6. The Patch 1 commit is in Task 1.

- **Placeholder scan.** All Edit blocks contain the literal "before" and "after" text. All commands are runnable as written. All commit messages are full text. No "TBD", "TODO", or "implement later" markers in step content. (The `<!-- TODO -->` comment in `tool-catalog.md:435` is preserved deliberately — out of scope for this plan.)

- **Type consistency.** `${PLUGIN}` is defined once and used consistently. Skill names: `ivy`, `build-ops`, `verify-ops`, `review-ops`, `meta-self-mod-ops` (no drift between tasks). Agent name: `ivy-triage-agent` is used uniformly. Reference file names: `phase-4-trace-analysis.md` and `mpe-roles.md` are used identically in Step 2/3 (creation), Steps 4/5 (pointer lines), and Step 7 (verification).

- **Sequencing.** Tasks 2-6 follow the spec's order (4 → 2 → 6 → 5 → 3). Task 1 (baseline) precedes them; Tasks 7-8 (verify and pointer-bump) follow. Patch 3 lands last because `ivy/SKILL.md` is touched by Patches 2, 6, 3 and `review-ops/SKILL.md` is touched by Patches 5, 3 — sequencing this way avoids overlapping commit windows in the same file.

- **No `git add .`** — every staging step names files explicitly.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-29-harness-audit-patches-2-to-6.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration. Good fit here because the 5 patches are small and independently verifiable.

**2. Inline Execution** — Execute tasks in this session using `superpowers:executing-plans`, batch execution with checkpoints. Faster end-to-end but consumes the lead's context.

Which approach?
