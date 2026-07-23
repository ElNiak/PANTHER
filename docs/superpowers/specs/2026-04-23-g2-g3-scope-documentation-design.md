# Design — panther-ivy-plugin G2/G3 Gate Scope Documentation

Status: proposed
Author: workflow-audit follow-up (cluster-8 grilling session)
Date: 2026-04-23
Depends-on: `2026-04-23-workflow-state-model-refactor-design.md` (cluster 1) for the pending_dispatch verbiage used in the added notes.
Scope: close audit cluster 8 (G2/G3 adversarial gate scope gap) via documentation — no code changes.

## Context

The workflow audit on 2026-04-23 flagged `assess-modeling.py:102` and `assess-testspec.py` (G2 and G3 gate hooks) as firing only when `active-workflow.workflow == "build"`. `.ivy` edits made during `verify` Phase 7 (fix) or `review` Phase 3 (resolution) escape the adversarial audit. The audit classified this as Major ("workflow-critical edits escape adversarial audit").

The cluster-8 grilling reached the opposite conclusion: the scoping is intentional. G2/G3 audit *layer soundness during construction*. Verify's fix loop is expected to be narrow counterexample-driven repairs (protected by cluster 7's attempt cap). Review's Phase 3 inline edits are small. Broadening G2/G3 to all workflows would raise audit noise without clearly raising soundness confidence. The correct fix is documentation: explain the scope decision in the code, and tell users how to re-engage the gate when they legitimately need it.

## Decisions

1. **G2 and G3 remain build-only.** No code change to `assess-modeling.py` or `assess-testspec.py`. The `ctx.workflow != "build"` early-return stays.
2. **Hook docstrings explain "why build-only".** Plus an inline comment at the filter line pointing to this spec.
3. **`verify/SKILL.md` Phase 7 adds an explicit scope note** and names the re-engagement path: loop back to `build` via `pending_dispatch(build, phase_hint=layer-check)` (a pattern introduced by cluster 1).
4. **`review/SKILL.md` Phase 3 adds the same scope note.**
5. **`reflection-patterns/references/gates.md`** G2 and G3 sections name the workflow scope explicitly (currently they describe the *file* trigger without naming the workflow filter).
6. **No new command, no escape hatch, no G2/G3 scope extension.** Rejected during grilling.

## Architecture

No architectural change. The only moving pieces are paragraphs added to hook source docstrings, two workflow SKILL.md files, and one knowledge-skill reference document.

## File change inventory (5 files, all docs)

| File | Change |
|---|---|
| `hooks/scripts/assess-modeling.py` | Expand module docstring (currently lines 1-12) to add "Why build-only?" paragraph. Add a one-line comment above line 102 (`if ctx is None or ctx.workflow != "build": return`) pointing to this spec. No code change. |
| `hooks/scripts/assess-testspec.py` | Mirror the `assess-modeling.py` docstring treatment. |
| `skills/verify/SKILL.md` Phase 7 (or `references/failure-diagnosis.md` Phase 7 Step 1) | Add paragraph: "Adversarial gates G2/G3 do not fire on fix edits made inside the verify workflow; they are build-time gates. If a fix raises structural concerns the counterexample diagnosis did not catch, return to `build` via `pending_dispatch(build, phase_hint=layer-check)`. Navigate will re-enter build; the re-edit path re-engages G2 naturally." |
| `skills/review/SKILL.md` Phase 3 Step 2 | Add matching paragraph: "G2/G3 do not fire on review-inline fixes. For structural concerns, dispatch back to `build` via `pending_dispatch` — review is for audit, not construction." |
| `skills/reflection-patterns/references/gates.md` | G2 section: add "Fires only when `active-workflow.workflow == "build"`" to the trigger description. Same for G3. |

## Proposed docstring text for `hooks/scripts/assess-modeling.py`

After the current module docstring, append:

```
## Why build-only?

G2 audits layer modeling soundness during construction — ungrounded quantifiers,
missing invariants, actions without require guards, the structural pathologies
that matter most when a layer is being written for the first time.

Verify's fix loop is expected to be narrow counterexample-driven repairs bounded
by cluster-7's attempt cap. Broadening G2 to verify-phase edits raises audit
volume faster than it raises soundness confidence; the fix cycle already carries
attempt-counter accountability.

Review edits do not occur in its own phases under the cluster-1 design: any .ivy
modification triggered by a review finding dispatches back to build via
pending_dispatch, and the edit happens inside build where G2 does fire.

Users who want an adversarial audit outside build can emit
`pending_dispatch(build, phase_hint="layer-check")` from the current workflow
and let navigate re-engage build.
```

## Migration plan

Single docs-only commit. No tests affected.

## Risks

1. **Readers may interpret the scope as inertia, not intent.** Mitigation: the "Why build-only?" paragraph in the hook docstring makes the choice explicit and defensible. The cross-reference to cluster 7's attempt cap reinforces that verify is not unaudited — it has its own guardrail.
2. **Dependency on cluster 1's pending_dispatch verbiage.** Mitigation: spec frontmatter declares the dependency. If cluster 1 ships after cluster 8, the spec text still makes sense because navigate's re-dispatch path is a conceptual pointer, not a concrete code reference.

## Out of scope

- Broadening G2/G3 scope to non-build workflows.
- Adding a manual adversarial-audit command (`/nct-audit-layer` or similar).
- G0/G1/G4/G5 scope — each has its own firing hook and its own scope decisions; this spec covers only G2 and G3.
- Refactoring the hook to be file-shape-based rather than workflow-based.

## Verification

- Read `assess-modeling.py` + `assess-testspec.py` docstrings after the change; the "Why build-only?" rationale must be present.
- Read `verify/SKILL.md` Phase 7 and `review/SKILL.md` Phase 3 after the change; the scope note and re-engagement path must be present.
- Read `reflection-patterns/references/gates.md` G2 + G3 sections after the change; the workflow-scope constraint must be named.
- Run a session: invoke verify on a failing test, let Phase 7 fix-loop run; confirm no G2/G3 `additionalContext` is emitted — this is the expected (documented) behavior.
