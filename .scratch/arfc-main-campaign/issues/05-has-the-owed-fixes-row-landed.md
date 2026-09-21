# 05 — Has the owed-fixes row landed on `origin/main`, and does it fix R91/R92?

Type: task (HITL checkpoint)
Status: open
Claimed: —
Blocked by: — (ON THE FRONTIER)
Parent: [ai_rfc Main Campaign, Ready to Launch](../map.md)

## Question

The owed-fixes row (plan `docs/superpowers/plans/2026-09-21-arfc-owed-fixes.md`, 55 items from
CLI-3's whole-branch review) is **a given, outside this map** (user ruling at charting). It is
mid-execution in `<ai_rfc>` and owns files that three tickets here need:
`experiment/{runner,audit,per_cluster}.py` and `driver/{spawn,stop,coverage,record}.py`. This
ticket is the checkpoint that turns "the row has landed" into something the frontier can compute.

**Closes when both hold:**
1. The row's session has sent its promised pre-push message (it said on 2026-09-21 that it will
   message before the push and the gitlink bump; find its current name with `ListAgents`).
2. `git -C <ai_rfc> log origin/main` shows the row's range, **`8358238` (the ARM-B fix)
   included**, and PANTHER's gitlink points into it.

**The R91/R92 check below was done early (see Progress). The ticket now closes on 1 and 2 alone.**

**Then check R91/R92** (SP7d ledger `<ai_rfc>/.superpowers/sdd/2026-09-15-arfc-sp7d/progress.md`,
rulings R90–R92):
- **R91**: `consolidations_recorded` counts the `revisions.yaml` entry, which is written *before*
  the tag. A tag the build gate refuses therefore reports `recorded=True`.
- **R92**: the dangling entry then fails the strict citation gate on the final workspace. MARK's
  post-round copy went from completed 37/69 to 0/69, and completion is the protocol's primary
  outcome.

At charting, **the row's plan and deviation log never mention R91, R92, `consolidations_recorded`
or `recorded=True`**. The defects were reported to the row's session by `post-sp7d-cleanup-gepa`,
but adoption is unconfirmed. Grep the row's landed commits and ledger. **If R91/R92 are not
fixed, the user rules** whether this map takes them on (a new ticket that blocks
[Run the validation pilot](14-run-the-validation-pilot.md)) or waits for the row's follow-up. Any
fix must handle record-before-tag.

## Progress

**2026-09-21, 15:46 (read with `date`). The push has not happened. R91/R92 was checked early and
handed to a new ticket by the user's ruling.** The ticket stays open and unclaimed.

- **The push.** `git -C <ai_rfc> rev-list --left-right --count HEAD...origin/main` gives **20
  ahead, 0 behind**:
  - HEAD is `2c768b5` (15:45, "fix: escape every value the production report interpolates");
  - `origin/main` is still `3406985`;
  - `8358238` is in the unpushed range.

  No pre-push message has arrived. The row's session, `plan-review-and-task-dispatch`, was
  `busy`. By its commit messages, it has landed:
  - Task 1 (exit codes);
  - Task 2 (the stop vocabulary);
  - Task 3 (path guards);
  - Task 5 (the ledger reducer);
  - Task 9 (the D16 citations);
  - part of Task 4 (sinks).

  Left: the rest of 4, then 6 (run-directory claim), 7 (coverage detector), 8 (the hardened
  parser), 10 (the spec diff), 11 (the ADRs) and 12 (the whole-row review, the fix wave and the
  gate). Next run: compare HEAD and the ahead count with these to see whether anything moved.
- **R91/R92: not fixed, not planned.**
  - **Code**: at `2c768b5`, `driver/consolidation.py:29` still counts `revisions.yaml` entries;
    `experiment/per_cluster.py:281` credits a round by that count; and `server/core/draft.py`'s
    `tag_revision` leaves the entry in place when the manifest gate or the build refuses.
  - **Plans and commits**: zero hits for `R91`, `R92`, `consolidations_recorded` or
    `recorded=True` in the row's plan, its deviation log, and the 20 commit messages.
  - **Why it matters**: `metrics.py:39` defines `completed` at the run level, so one dangling
    entry fails the whole run. That makes it a defect in the headline metric.
- **User ruling (2026-09-21): this map fixes it**, in the new
  [Land the record-before-tag fix (R91/R92)](20-land-the-record-before-tag-fix.md). That ticket
  waits on this one and blocks the freeze. The row's session is told that this map has R91/R92,
  so it leaves them.
