# SP7d deviation log

One entry per deviation from `docs/superpowers/plans/2026-09-15-arfc-sp7d.md`.
Three fields each: what the plan said, what the code or the tool showed, what I did.

**Entry 0 — the user decisions (U1–U3), the rulings (R1–R8), the Phase 1 baselines, and the
review findings D-1 through D-45 — lives in the plan file itself**, under "Entry 0 — rulings and
decisions carried into the row" and "Measured baselines". It is recorded there rather than
duplicated here so the two cannot drift: the plan is the artifact a reviewer reads, and every
ruling is a constraint on a task in it.

**Plan-mode transplant (CLI-2's R9 / CLI-3's precedent).** The plan was written under plan mode,
which permits writing only the harness plan file. On approval it was copied **verbatim** to
`docs/superpowers/plans/2026-09-15-arfc-sp7d.md` — verified byte-identical by sha256
`86c8cb432ff6729c9ee08123135dfa438288c68403933f255abc1e6d5db45273` — this log was opened beside it,
and both were committed in PANTHER with `git add -f` **before Task 1 ran**. The single `review-plan`
invocation was made against the harness file and is **not** repeated after the transplant.

**Summary of what entry 0 settles, for a reader who wants the shape before the detail:**

- **Three user decisions (2026-09-15).** U1 takes the **union** of the spec's judge argv and the
  codebase's hardened `ClaudeCliCall.argv()`, neither being a superset of the other. U2 makes the
  before/after table's "after" column a **pilot draft re-linted by the final instrument** — which
  D44 already designates as the free old-instrument reference, so the instrument-drift confound the
  spec's re-lint rule prevents is absent, and only a content confound remains. U3 scores
  ground-truth by **anchored fact plus value match**, which yields two zero-cost REDs.
- **Eight rulings I made** (R1–R8), each with its cost if wrong. The load-bearing ones: reuse
  `ClaudeCliCall` but **not** `build_judge`, which is welded to a three-value scale (R1); the init
  assertion and cost capture go **inside** the transport (R2); lint per revision uses the **frozen**
  checkpoint manifest, never the live one (R3); and new logic is a **module, never a `cli.py`**,
  because `test_cli_conventions.py:148-178` rglobs for those (R6).
- **One spec correction (D-1).** The spec frames the blinding leak as lasting "until an API key is
  provisioned". This project never uses one, so the leak is **permanent**, and the manifest says so.
- **Forty-five findings fixed before any task ran** (D-1 … D-45): 13 Critical and 10 Warning from
  one `review-plan` invocation, plus 12 from a following adversarial re-read.
  **Five of the thirteen Criticals were REDs that could never have gone red, or could never have
  gone green** — and the adversarial re-read caught **three more of the same classes reintroduced by
  the fixes themselves** (D-34, D-35, D-36).

**Measured at the gate, not inherited.** The installed `claude` is **2.1.272** — newer than the
spec's 2.1.259, `ClaudeCliCall`'s 2.1.260 and the memory's 2.1.268 — and **all eight union flags are
accepted** (D-37). The envelope shape on 2.1.272 is **not** measured; it moved once already.

**Operational hazard noted at the Phase 0 gate.** Two peer sessions were live (`iut-ai-rfc-7f`
interactive, `cli-one-core-refactor` background). Both repositories were clean, so nothing was
attributable to them. `git status --short` is checked in both repositories immediately before every
commit, and BASE is recorded before every dispatch.

---

# Execution-phase deviations (D46 onward)

One entry per task, added as tasks run.
