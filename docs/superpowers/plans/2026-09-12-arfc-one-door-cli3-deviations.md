# CLI-3 deviation log

One entry per deviation from `docs/superpowers/plans/2026-09-12-arfc-one-door-cli3.md`.
Three fields each: what the plan said, what the code or the tool showed, what I did.

**Entry 0 — the rulings, the measured corrections to the brief, D1–D17 and the Phase 1 baselines —
lives in the plan file itself**, under "Entry 0 — rulings carried into the row", "Measured
corrections to the brief", "D1–D17 — review findings, fixed in this plan before Task 1" and
"Baselines measured at Phase 1". It is recorded there rather than duplicated here so the two cannot
drift: the plan is the artifact a reviewer reads, and every ruling is a constraint on a task in it.

**Plan-mode transplant (CLI-2's R9 precedent).** The plan was written under plan mode, which permits
writing only the harness plan file. On approval it was copied **verbatim** to
`docs/superpowers/plans/2026-09-12-arfc-one-door-cli3.md` — verified byte-identical by sha256
`6b98961b248da18b22831f3f4b9024bbfc5c95d54ea46cdf196bbfcbeaccd5d3` — this log was opened beside it,
and both were committed in PANTHER with `git add -f` **before Task 1 ran**. The single `review-plan`
invocation was made against the harness file and is **not** repeated after the transplant.

**Summary of what entry 0 settles, for a reader who wants the shape before the detail:**

- **Four user rulings (2026-09-12).** U1 restates §6's "`checkpoint` regains 3" as "stops
  collapsing"; U2 lands CLI-2's two owed spec amendments (the `bound_reached`/`action_performed`
  D-row and §5's exit-code sentence); U3 retires the folded `status` verb's CLI form and keeps the
  MCP tool; U4 pre-authorises `--panther-repo` (Task 10) as the cut line if the row overruns.
- **Eleven rulings I made** (R1–R11), each with its cost if wrong. The load-bearing ones: the core
  calls the **API functions**, not `main(argv)` (R1, from a measured discriminator about who reads
  the report artifacts); the leaf verbs are **hidden, not deleted**, because arm C types them
  through the root door (R3); the workspace is derived from the config file's **own directory**,
  never from its `workspace:` field (R9); and `ai_rfc/server/cli.py` is **deleted**, not merely
  re-`prog`ged, because a second parser tree kept only for tests is the compat layer this codebase
  forbids (R11, with a stated fallback).
- **Seven measured corrections to the brief** (M1–M7). The largest: the captured arm-B transcript
  needs **no** regeneration — it is `arfc`-spelled, carries its own `families` key, and its own
  docstring states the principle that a recording is never edited to match a rename (M1).
- **Seventeen review findings fixed before any task ran** (D1–D17): nine Critical and five Warning
  from one `review-plan` invocation, plus three from a following adversarial read, one of which was
  an internal contradiction between Task 5 and U3. **Five of the seventeen were REDs that would
  have passed against unfixed code or could never have gone green afterwards.**

**Operational hazard noted at the Phase 0 gate.** Six peer sessions were live in this worktree at
the gate, three of them busy. Both repositories were clean, so no uncommitted `ai_rfc/server/` or
`ai_rfc/experiment/` edits existed. `git status -sb` is checked in both repositories immediately
before every commit, and BASE is recorded before every dispatch.

---

# Execution-phase deviations (D18 onward)

One entry per task, added as tasks run.
