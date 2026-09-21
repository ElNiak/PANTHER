# 20 — Land the record-before-tag fix (R91/R92)

Type: task (AFK)
Status: open
Claimed: —
Blocked by: [Has the owed-fixes row landed](05-has-the-owed-fixes-row-landed.md)
Parent: [ai_rfc Main Campaign, Ready to Launch](../map.md)

## Question

Graduated on 2026-09-21 from
[Has the owed-fixes row landed on `origin/main`, and does it fix R91/R92?](05-has-the-owed-fixes-row-landed.md).
Its R91/R92 half was checked early and found **not fixed and not planned**. The user then ruled
that **this map fixes it** through this ticket. **This ticket makes a gate-refused tag stop
corrupting the headline metric.**

Execution is carried (map Notes). The work is ai_rfc code, landed RED-test first, committed by
explicit path in `<ai_rfc>`, $0. It waits on the owed-fixes checkpoint because it touches that
row's `experiment/per_cluster.py`. It lands **one at a time** with
[Land the fault, retry and exclusion rules](18-land-the-fault-retry-and-exclusion-rules.md),
which edits the same attempt loop. Whichever lands second rebases its tests onto the first. Find
the row's session with `ListAgents` before touching anything it owns.

**The defect, at ai_rfc `2c768b5`** (SP7d ledger
`<ai_rfc>/.superpowers/sdd/2026-09-15-arfc-sp7d/progress.md`, R91 at line 4077, R92 at line 4144):
- **Record comes before tag, by design.** `server/core/draft.py`'s `tag_revision` refuses a tag
  that `revisions.yaml` does not already hold ("record the revision first"). It then runs the
  strict manifest gate and the build. On either refusal it returns `rolled_back: False` and
  leaves the entry in place. Only a citation-gate refusal deletes the tag, and even then the
  entry stays. Both arms reach this one function: A through `server/tools.py:138`, B through
  `agent/revision/cli.py:110`.
- **R91: "recorded" counts the entry, not the tag.** `driver/consolidation.py:29`,
  `consolidations_recorded`, counts `kind: consolidation` entries. `experiment/per_cluster.py:281`
  (and `driver/sweep.py:1204`) credit a consolidation round by that count, so a round whose tag
  was refused prints `recorded=True`. `analyze`'s artifact rule (the tag must exist) catches it;
  the run layer does not.
- **R92: the dangling entry zeroes the run.** `experiment/metrics.py:39` defines `completed` at
  the run level: artifacts, **and** both strict gates exiting 0 on the final workspace. The strict
  citation gate reports "registered in revisions.yaml but absent from the draft repository", so
  one refused tag anywhere fails every cluster of the run. MARK's `mark-full-1` copy went from
  completed 37/69 to **0/69** this way. Completion is **H1, the headline**
  ([What are the hypotheses](01-what-are-the-hypotheses-and-primary-metrics.md)).
- **It probably also poisons the cluster's next attempt.** `server/core/revisions.py`'s
  `record_revision` refuses a tag already recorded ("revision … is already recorded") and a
  second cluster revision for the same cluster. `per_cluster.py` restores nothing between its
  `ATTEMPTS_PER_CLUSTER = 2` attempts. So attempt 2 inherits attempt 1's dangling entry. Measure
  this; it is not yet shown.
- **The fault retries of ticket 18 inherit it too.** A session killed between record and tag
  leaves the same dangling entry for its retry.

**The design is this ticket's to choose, tests first, within these limits:**
- **Never change `metrics.py`'s definition of `completed`.** The hypotheses ticket fixed the
  instruments' definitions. The fix keeps recording and tagging consistent in the run layer, or
  in `tag_revision`, which both arms share.
- **Counting tags instead of entries fixes R91 only.** The dangling entry would still fail the
  citation gate, so R92 would stand. The fix must remove or prevent the dangling entry. Two
  candidates, for example: `tag_revision` rolls back its own entry on every refusal, or the
  driver reconciles after each session by removing any entry whose tag does not exist and
  reporting it.
- **Parity holds.** Whatever an agent sees change (an error text, a re-record step after a
  refusal) must change identically for arms A and B. If a prompt or skill has to change, it
  changes through
  [Land the arm-parity fixes](19-land-the-arm-parity-fixes.md)'s re-rendered pair, before the
  freeze.
- **The refusal stays visible.** A removed entry is reported in the run's log and in
  `sessions.jsonl`, never silently dropped: a refused tag is the model's failure, not the
  instrument's.

**Done when**:
- Each item below has a test shown RED at `2c768b5`'s behaviour, then GREEN:
  1. A tag refused by the manifest gate or by the build, at a cluster or at a consolidation,
     leaves the run's other completed clusters completed under `metrics.py`'s unchanged
     definition.
  2. The refusal is reported.
  3. `consolidations_recorded`, or its replacement, credits no round whose tag does not exist.
  4. A refused tag in attempt 1 does not block attempt 2 on the same cluster.
- The full ai_rfc suite passes; report collected, passed, failed and skipped separately.
- A $0 check on the R92 evidence: `mark-full-1`'s post-round copy, which the user's SP7d ruling
  keeps exactly as the round left it. Take a copy of the copy, apply the fix's rollback or
  reconciliation there, then re-run the strict gates the way `analyze` does
  (`metrics.run_gates`). Expected: the citation gate is clean again and the artifacts give 37/69
  completed. **Never edit the evidence itself.**

**Output:** the commits, the RED and GREEN test names, the suite counts and the $0 check's
result, each linked from the resolution comment.
